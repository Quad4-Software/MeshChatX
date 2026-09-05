<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy, tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import LoadingState from "../../../ui/svelte/LoadingState.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import {
        type RingtoneItem,
        formatRingtoneTime,
        drawWaveformCanvas,
        fetchAndDecodeAudio,
        trimAudioBuffer,
        audioBufferToWav,
    } from "../lib/ringtoneEditorLogic.js";

    import type { Ringtone } from "../lib/types.js";

    interface Props {
        ringtone: RingtoneItem | Ringtone | Record<string, any>;
        onclose?: () => void;
        onsaved?: () => void;
    }

    let { ringtone, onclose, onsaved }: Props = $props();

    let loading = $state(true);
    let saving = $state(false);
    let audioBuffer: AudioBuffer | null = $state(null);
    let audioContext: AudioContext | null = $state(null);
    let sourceNode: AudioBufferSourceNode | null = $state(null);
    let startTime = $state(0);
    let endTime = $state(0);
    let totalDuration = $state(0);
    let isPlaying = $state(false);
    let playbackStartTime = $state(0);
    let playbackStartOffset = $state(0);
    let progressPercent = $state(0);
    let animationFrame: number | null = null;
    let dragging = $state<"start" | "end" | null>(null);
    let saveAsNew = $state(false);
    let waveformCanvas: HTMLCanvasElement | null = $state(null);

    const startPercent = $derived((startTime / (totalDuration || 1)) * 100 || 0);
    const endPercent = $derived((endTime / (totalDuration || 1)) * 100 || 100);

    function draw() {
        if (!waveformCanvas || !audioBuffer) return;
        drawWaveformCanvas(waveformCanvas, audioBuffer, startTime, endTime, totalDuration);
    }

    async function loadAudio() {
        try {
            loading = true;
            const res = await fetchAndDecodeAudio(ringtone.id);
            audioContext = res.audioContext;
            audioBuffer = res.audioBuffer;
            totalDuration = res.audioBuffer.duration;
            startTime = 0;
            endTime = totalDuration;
            await tick();
            draw();
        } catch (e) {
            console.error("Failed to load audio:", e);
            ToastUtils.error(t("call.failed_load_audio_edit"));
            onclose?.();
        } finally {
            loading = false;
        }
    }

    function startDragging(type: "start" | "end") {
        dragging = type;
    }

    function stopDragging() {
        dragging = null;
        draw();
    }

    function handleDragging(e: MouseEvent) {
        if (!dragging || !waveformCanvas || totalDuration <= 0) return;
        const rect = waveformCanvas.getBoundingClientRect();
        const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
        const time = (x / rect.width) * totalDuration;
        if (dragging === "start") {
            startTime = Math.min(time, endTime - 0.1);
        } else if (dragging === "end") {
            endTime = Math.max(time, startTime + 0.1);
        }
        draw();
    }

    function handleWaveformClick(e: MouseEvent) {
        if (!waveformCanvas || totalDuration <= 0) return;
        const rect = waveformCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const time = (x / rect.width) * totalDuration;
        if (time < startTime) startTime = time;
        else if (time > endTime) endTime = time;
        draw();
    }

    function updateProgress() {
        if (!isPlaying || !audioContext) return;
        const elapsed = audioContext.currentTime - playbackStartTime;
        const currentTime = playbackStartOffset + elapsed;
        progressPercent = (currentTime / (totalDuration || 1)) * 100;
        if (currentTime >= endTime) {
            stopPlayback();
            return;
        }
        animationFrame = requestAnimationFrame(updateProgress);
    }

    function startPlayback() {
        if (!audioBuffer || !audioContext) return;
        stopPlayback();

        sourceNode = audioContext.createBufferSource();
        sourceNode.buffer = audioBuffer;
        sourceNode.connect(audioContext.destination);
        playbackStartOffset = startTime;
        playbackStartTime = audioContext.currentTime;
        sourceNode.start(0, startTime, Math.max(0.05, endTime - startTime));
        isPlaying = true;

        sourceNode.onended = () => {
            isPlaying = false;
            progressPercent = 0;
            if (animationFrame) cancelAnimationFrame(animationFrame);
        };
        updateProgress();
    }

    function stopPlayback() {
        if (sourceNode) {
            try {
                sourceNode.stop();
            } catch (_err) {
                // Ignore stop error if already stopped
            }
            sourceNode = null;
        }
        isPlaying = false;
        progressPercent = 0;
        if (animationFrame) {
            cancelAnimationFrame(animationFrame);
            animationFrame = null;
        }
    }

    function togglePlay() {
        if (isPlaying) stopPlayback();
        else startPlayback();
    }

    async function save() {
        if (!audioBuffer) return;
        try {
            saving = true;
            const trimmed = trimAudioBuffer(audioBuffer, startTime, endTime);
            const blob = audioBufferToWav(trimmed);
            const formData = new FormData();
            const filename = saveAsNew ? `edited_${ringtone.filename}` : ringtone.filename;
            formData.append("file", blob, filename);

            await (window as any).api.post("/api/v1/telephone/ringtones/upload", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });

            ToastUtils.success(t("call.ringtone_saved"));
            onsaved?.();
            onclose?.();
        } catch (e) {
            console.error("Failed to save ringtone:", e);
            ToastUtils.error(t("call.failed_save_ringtone"));
        } finally {
            saving = false;
        }
    }

    onMount(() => {
        loadAudio();
        window.addEventListener("mousemove", handleDragging);
        window.addEventListener("mouseup", stopDragging);
        window.addEventListener("resize", draw);
    });

    onDestroy(() => {
        stopPlayback();
        window.removeEventListener("mousemove", handleDragging);
        window.removeEventListener("mouseup", stopDragging);
        window.removeEventListener("resize", draw);
        if (audioContext) audioContext.close();
    });
</script>

<div class="space-y-6">
    <div class="flex items-center justify-between">
        <div>
            <h3 class="text-lg font-bold text-sem-fg">{t("call.edit_ringtone")}</h3>
            <p class="text-xs text-sem-fg-muted">{ringtone.display_name || ringtone.filename}</p>
        </div>
        <button
            type="button"
            class="p-2 hover:bg-sem-surface-muted rounded-full transition-colors focus-ring-sem cursor-pointer"
            onclick={() => onclose?.()}
        >
            <MaterialDesignIcon iconName="close" class="size-6 text-sem-fg-muted" />
        </button>
    </div>

    <div
        class="relative bg-sem-surface-muted/50 rounded-2xl p-4 border border-sem-border min-h-[200px] flex flex-col justify-center"
    >
        {#if loading}
            <LoadingState message={t("call.loading_audio")} />
        {/if}

        <div class="relative" class:hidden={loading}>
            <canvas bind:this={waveformCanvas} class="w-full h-40 cursor-pointer" onmousedown={handleWaveformClick}
            ></canvas>

            <div
                class="absolute top-0 bottom-0 w-0.5 bg-sem-accent z-10 pointer-events-none"
                style:left="{progressPercent}%"
            ></div>

            <div
                class="absolute top-0 bottom-0 bg-sem-accent/10 border-x-2 border-sem-accent z-20 pointer-events-none"
                style:left="{startPercent}%"
                style:width="{endPercent - startPercent}%"
            >
                <div
                    class="absolute top-1/2 -left-3 -translate-y-1/2 size-6 bg-sem-surface border-2 border-sem-accent rounded-full shadow-lg cursor-ew-resize flex items-center justify-center group pointer-events-auto focus-ring-sem"
                    role="slider"
                    tabindex="0"
                    aria-label={t("call.start_time")}
                    aria-valuenow={startTime}
                    aria-valuemin={0}
                    aria-valuemax={endTime}
                    onkeydown={(e) => {
                        if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
                            e.preventDefault();
                            startTime = Math.max(0, Number((startTime - 0.1).toFixed(2)));
                            draw();
                        } else if (e.key === "ArrowRight" || e.key === "ArrowUp") {
                            e.preventDefault();
                            startTime = Math.min(endTime - 0.1, Number((startTime + 0.1).toFixed(2)));
                            draw();
                        }
                    }}
                    onmousedown={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        startDragging("start");
                    }}
                >
                    <div class="w-0.5 h-3 bg-sem-accent group-hover:h-4 transition-all"></div>
                </div>
                <div
                    class="absolute top-1/2 -right-3 -translate-y-1/2 size-6 bg-sem-surface border-2 border-sem-accent rounded-full shadow-lg cursor-ew-resize flex items-center justify-center group pointer-events-auto focus-ring-sem"
                    role="slider"
                    tabindex="0"
                    aria-label={t("call.end_time")}
                    aria-valuenow={endTime}
                    aria-valuemin={startTime}
                    aria-valuemax={totalDuration}
                    onkeydown={(e) => {
                        if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
                            e.preventDefault();
                            endTime = Math.max(startTime + 0.1, Number((endTime - 0.1).toFixed(2)));
                            draw();
                        } else if (e.key === "ArrowRight" || e.key === "ArrowUp") {
                            e.preventDefault();
                            endTime = Math.min(totalDuration, Number((endTime + 0.1).toFixed(2)));
                            draw();
                        }
                    }}
                    onmousedown={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        startDragging("end");
                    }}
                >
                    <div class="w-0.5 h-3 bg-sem-accent group-hover:h-4 transition-all"></div>
                </div>
            </div>
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-4">
            <div class="flex items-center justify-between">
                <span class="text-sm font-bold text-sem-fg-muted">{t("call.time_range")}</span>
                <span class="text-[10px] font-mono text-sem-fg-muted">
                    {formatRingtoneTime(startTime)} - {formatRingtoneTime(endTime)} ({formatRingtoneTime(
                        Math.max(0, endTime - startTime)
                    )})
                </span>
            </div>
            <div class="flex gap-4">
                <div class="flex-1">
                    <label
                        for="ringtone-start-time"
                        class="block text-[10px] uppercase font-bold text-sem-fg-muted mb-1"
                    >
                        {t("call.start")}
                    </label>
                    <input
                        id="ringtone-start-time"
                        bind:value={startTime}
                        type="number"
                        step="0.01"
                        min="0"
                        max={endTime}
                        class="input-field w-full text-sm py-2"
                        oninput={() => draw()}
                    />
                </div>
                <div class="flex-1">
                    <label for="ringtone-end-time" class="block text-[10px] uppercase font-bold text-sem-fg-muted mb-1">
                        {t("call.end")}
                    </label>
                    <input
                        id="ringtone-end-time"
                        bind:value={endTime}
                        type="number"
                        step="0.01"
                        min={startTime}
                        max={totalDuration}
                        class="input-field w-full text-sm py-2"
                        oninput={() => draw()}
                    />
                </div>
            </div>
        </div>

        <div class="flex flex-col justify-end">
            <button
                type="button"
                class="flex items-center justify-center gap-2 py-3 rounded-xl font-bold transition-all w-full focus-ring-sem cursor-pointer {isPlaying
                    ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/20'
                    : 'bg-sem-accent text-white shadow-lg shadow-sem-accent/20 hover:bg-sem-accent/90'}"
                onclick={togglePlay}
            >
                <MaterialDesignIcon iconName={isPlaying ? "pause" : "play"} class="size-5" />
                {isPlaying ? t("call.pause_selection") : t("call.play_selection")}
            </button>
        </div>
    </div>

    <div class="pt-6 border-t border-sem-border flex items-center justify-between">
        <div class="flex items-center gap-2">
            <input
                id="saveAsNew"
                bind:checked={saveAsNew}
                type="checkbox"
                class="rounded-sm border-sem-border text-sem-accent focus:ring-sem-accent"
            />
            <label for="saveAsNew" class="text-sm text-sem-fg-muted cursor-pointer"
                >{t("call.save_as_new_ringtone")}</label
            >
        </div>
        <div class="flex items-center gap-3">
            <button
                type="button"
                class="px-4 py-2 text-sm font-bold text-sem-fg-muted hover:text-sem-fg transition-colors focus-ring-sem cursor-pointer"
                onclick={() => onclose?.()}
            >
                {t("common.cancel")}
            </button>
            <button
                type="button"
                disabled={saving || loading}
                class="px-6 py-2 bg-sem-accent text-white rounded-xl text-sm font-bold shadow-lg shadow-sem-accent/20 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 focus-ring-sem cursor-pointer"
                onclick={save}
            >
                {#if saving}
                    <MaterialDesignIcon iconName="loading" class="size-4 animate-spin" />
                {/if}
                {saving ? t("call.saving") : t("call.save_audio")}
            </button>
        </div>
    </div>
</div>

<style>
    canvas {
        image-rendering: pixelated;
    }
</style>
