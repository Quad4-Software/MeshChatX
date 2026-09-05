<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";

    let {
        src,
        isOutbound = false,
        onplay,
    }: {
        src: string;
        isOutbound?: boolean;
        onplay?: () => void;
    } = $props();

    let loading = $state(true);
    let audioBuffer: AudioBuffer | null = $state(null);
    let audioContext: AudioContext | null = $state(null);
    let sourceNode: AudioBufferSourceNode | null = $state(null);
    let totalDuration = $state(0);
    let currentTime = $state(0);
    let isPlaying = $state(false);
    let playbackStartTime = $state(0);
    let playbackStartOffset = $state(0);
    let progressPercent = $state(0);
    let hoverPercent = $state(0);
    let animationFrame: number | null = $state(null);
    let waveform: HTMLCanvasElement | undefined = $state();

    function isDarkMode() {
        return document.documentElement.classList.contains("dark");
    }

    function formatTime(seconds: number) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, "0")}`;
    }

    function drawWaveform() {
        const canvas = waveform;
        if (!canvas || !audioBuffer) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        const width = canvas.clientWidth;
        const height = canvas.clientHeight;
        canvas.width = width * window.devicePixelRatio;
        canvas.height = height * window.devicePixelRatio;
        ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
        const data = audioBuffer.getChannelData(0);
        const step = Math.ceil(data.length / width);
        const amp = height / 2;
        ctx.clearRect(0, 0, width, height);
        const dark = isDarkMode();
        const waveBg = dark ? "rgba(255, 255, 255, 0.3)" : "rgba(0, 0, 0, 0.2)";
        const waveFg = dark ? "#fff" : "#000";
        ctx.beginPath();
        ctx.strokeStyle = waveBg;
        ctx.lineWidth = 1.5;
        for (let i = 0; i < width; i++) {
            let min = 1.0;
            let max = -1.0;
            for (let j = 0; j < step; j++) {
                const datum = data[i * step + j];
                if (datum < min) min = datum;
                if (datum > max) max = datum;
            }
            ctx.moveTo(i, amp + min * amp);
            ctx.lineTo(i, amp + max * amp);
        }
        ctx.stroke();
        const progressX = (progressPercent / 100) * width;
        if (progressX > 0) {
            ctx.beginPath();
            ctx.strokeStyle = waveFg;
            ctx.lineWidth = 2;
            for (let i = 0; i < progressX; i++) {
                let min = 1.0;
                let max = -1.0;
                for (let j = 0; j < step; j++) {
                    const datum = data[i * step + j];
                    if (datum < min) min = datum;
                    if (datum > max) max = datum;
                }
                ctx.moveTo(i, amp + min * amp);
                ctx.lineTo(i, amp + max * amp);
            }
            ctx.stroke();
        }
    }

    function stopPlayback() {
        if (sourceNode) {
            try {
                sourceNode.stop();
            } catch {
                // ignore
            }
            sourceNode = null;
        }
        isPlaying = false;
        if (animationFrame != null) {
            cancelAnimationFrame(animationFrame);
            animationFrame = null;
        }
    }

    function updateProgress() {
        if (!isPlaying || !audioContext) return;
        const elapsed = audioContext.currentTime - playbackStartTime;
        currentTime = Math.min(playbackStartOffset + elapsed, totalDuration);
        progressPercent = (currentTime / totalDuration) * 100;
        drawWaveform();
        if (currentTime >= totalDuration) {
            isPlaying = false;
            return;
        }
        animationFrame = requestAnimationFrame(updateProgress);
    }

    function startPlayback() {
        if (!audioBuffer || !audioContext) return;
        stopPlayback();
        if (audioContext.state === "suspended") {
            void audioContext.resume();
        }
        sourceNode = audioContext.createBufferSource();
        sourceNode.buffer = audioBuffer;
        sourceNode.connect(audioContext.destination);
        const startOffset = currentTime >= totalDuration ? 0 : currentTime;
        playbackStartOffset = startOffset;
        playbackStartTime = audioContext.currentTime;
        sourceNode.start(0, startOffset);
        isPlaying = true;
        onplay?.();
        sourceNode.onended = () => {
            if (isPlaying) {
                isPlaying = false;
                currentTime = totalDuration;
                progressPercent = 100;
                if (animationFrame != null) cancelAnimationFrame(animationFrame);
                drawWaveform();
            }
        };
        updateProgress();
    }

    function togglePlay() {
        if (isPlaying) stopPlayback();
        else startPlayback();
    }

    function handleWaveformClick(e: MouseEvent) {
        const canvas = waveform;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
        const time = (x / rect.width) * totalDuration;
        currentTime = time;
        progressPercent = (currentTime / totalDuration) * 100;
        if (isPlaying) startPlayback();
        else drawWaveform();
    }

    function handleWaveformMove(e: MouseEvent) {
        const canvas = waveform;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
        hoverPercent = (x / rect.width) * 100;
    }

    async function loadAudio() {
        if (!src) return;
        try {
            loading = true;
            stopPlayback();
            const response = await fetch(src);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const arrayBuffer = await response.arrayBuffer();
            if (!audioContext) {
                const AC =
                    window.AudioContext ||
                    (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
                audioContext = new AC();
            }
            audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            totalDuration = audioBuffer.duration;
            currentTime = 0;
            progressPercent = 0;
            requestAnimationFrame(() => drawWaveform());
        } catch (e) {
            console.error("Failed to load audio for player:", e);
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        void src;
        void loadAudio();
    });

    $effect(() => {
        const onResize = () => drawWaveform();
        window.addEventListener("resize", onResize);
        const darkObserver = new MutationObserver(() => drawWaveform());
        darkObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
        return () => {
            stopPlayback();
            window.removeEventListener("resize", onResize);
            darkObserver.disconnect();
            if (audioContext) {
                void audioContext.close();
                audioContext = null;
            }
        };
    });
</script>

<div
    class="audio-waveform-player flex items-center gap-3 p-2 rounded-xl transition-all w-full min-w-0 {isOutbound
        ? 'bg-white/10 text-white'
        : 'bg-gray-100 dark:bg-zinc-800/80 text-sem-fg'}"
>
    <button
        type="button"
        class="flex items-center justify-center size-10 rounded-full shrink-0 transition-all active:scale-90 {isOutbound
            ? 'bg-white/20 hover:bg-white/30 text-white'
            : 'bg-blue-500 hover:bg-blue-600 text-white'}"
        onclick={togglePlay}
    >
        <MaterialDesignIcon iconName={isPlaying ? "pause" : "play"} class="size-6" />
    </button>

    <div
        class="flex-1 relative h-11 group cursor-pointer min-w-0"
        onmousedown={handleWaveformClick}
        onmousemove={handleWaveformMove}
        role="slider"
        aria-valuemin={0}
        aria-valuemax={totalDuration}
        aria-valuenow={currentTime}
        tabindex="0"
    >
        {#if loading}
            <div class="absolute inset-0 flex items-center justify-center">
                <div
                    class="size-4 border-2 border-current/20 border-t-current rounded-full animate-spin opacity-50"
                ></div>
            </div>
        {/if}
        <canvas bind:this={waveform} class="w-full h-full" hidden={loading}></canvas>
        {#if !loading && (isPlaying || progressPercent > 0)}
            <div
                class="absolute top-0 bottom-0 w-0.5 bg-blue-400 z-10 pointer-events-none transition-[left] duration-100 ease-linear"
                style="left: {progressPercent}%"
            ></div>
        {/if}
        <div
            class="absolute top-0 bottom-0 w-px bg-current opacity-0 group-hover:opacity-20 z-0 pointer-events-none"
            style="left: {hoverPercent}%"
        ></div>
    </div>

    <div class="text-[10px] font-mono opacity-60 tabular-nums select-none shrink-0 pr-1">
        {formatTime(currentTime)} / {formatTime(totalDuration)}
    </div>
</div>

<style>
    canvas {
        image-rendering: auto;
    }
</style>
