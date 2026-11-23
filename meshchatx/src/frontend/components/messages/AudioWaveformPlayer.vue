<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="audio-waveform-player flex items-center gap-3 p-2 rounded-xl transition-all w-full min-w-0"
        :class="[isOutbound ? 'bg-sem-fg/10 text-sem-fg' : 'bg-sem-surface-muted text-sem-fg']"
    >
        <!-- Play/Pause Button -->
        <button
            class="flex items-center justify-center size-10 rounded-full shrink-0 transition-all active:scale-90"
            :class="[
                isOutbound
                    ? 'bg-sem-fg/15 hover:bg-sem-fg/25 text-sem-fg'
                    : 'bg-sem-action-primary hover:bg-sem-action-primary-hover text-sem-action-primary-text',
            ]"
            @click="togglePlay"
        >
            <MaterialDesignIcon :icon-name="isPlaying ? 'pause' : 'play'" class="size-6" />
        </button>

        <!-- Waveform and Progress -->
        <div class="flex-1 relative h-11 group cursor-pointer min-w-0" @mousedown="handleWaveformClick">
            <div v-if="loading" class="absolute inset-0 flex items-center justify-center">
                <div
                    class="size-4 border-2 border-current/20 border-t-current rounded-full animate-spin opacity-50"
                ></div>
            </div>

            <canvas v-show="!loading" ref="waveform" class="w-full h-full"></canvas>

            <!-- Progress Line -->
            <div
                v-if="!loading && (isPlaying || progressPercent > 0)"
                class="absolute top-0 bottom-0 w-0.5 bg-sem-accent z-10 pointer-events-none transition-[left] duration-100 ease-linear"
                :style="{ left: progressPercent + '%' }"
            ></div>

            <!-- Hover Seek Line -->
            <div
                class="absolute top-0 bottom-0 w-px bg-current opacity-0 group-hover:opacity-20 z-0 pointer-events-none"
                :style="{ left: hoverPercent + '%' }"
            ></div>
        </div>

        <!-- Time Info -->
        <div class="text-[10px] font-mono opacity-60 tabular-nums select-none shrink-0 pr-1">
            {{ formatTime(currentTime) }} / {{ formatTime(totalDuration) }}
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import { decodeAudioArrayBuffer, ensureAudioContextRunning } from "../../js/audioContextUtils.js";

export default {
    name: "AudioWaveformPlayer",
    components: {
        MaterialDesignIcon,
    },
    props: {
        src: {
            type: String,
            required: true,
        },
        isOutbound: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["play"],
    data() {
        return {
            loading: true,
            audioBuffer: null,
            audioContext: null,
            sourceNode: null,
            audioElement: null,
            blobUrl: null,
            playbackMode: null,
            useElementPlayback: false,
            audioBytes: null,
            audioMimeType: "",
            totalDuration: 0,
            currentTime: 0,
            isPlaying: false,
            playbackStartTime: 0,
            playbackStartOffset: 0,
            progressPercent: 0,
            hoverPercent: 0,
            animationFrame: null,
            darkObserver: null,
        };
    },
    watch: {
        src: {
            immediate: true,
            handler() {
                this.loadAudio();
            },
        },
    },
    mounted() {
        window.addEventListener("resize", this.drawWaveform);
        this.darkObserver = new MutationObserver(() => this.drawWaveform());
        this.darkObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    },
    beforeUnmount() {
        this._unmounted = true;
        // Any in-flight load is superseded so it cannot create a new
        // AudioContext or write state after this component is gone.
        this._loadGeneration = (this._loadGeneration || 0) + 1;
        this.stopPlayback();
        window.removeEventListener("resize", this.drawWaveform);
        if (this.darkObserver) {
            this.darkObserver.disconnect();
            this.darkObserver = null;
        }
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        this.teardownElementPlayback();
    },
    methods: {
        async loadAudio() {
            if (!this.src) return;
            const generation = (this._loadGeneration = (this._loadGeneration || 0) + 1);
            try {
                this.loading = true;
                this.stopPlayback();
                this.teardownElementPlayback();
                this.useElementPlayback = false;
                this.audioBytes = null;
                this.audioMimeType = "";

                const response = await fetch(this.src);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const arrayBuffer = await response.arrayBuffer();

                if (this._unmounted || generation !== this._loadGeneration) {
                    return;
                }

                this.audioBytes = arrayBuffer;
                this.audioMimeType = String(response.headers?.get?.("content-type") || "");
                this.audioBuffer = null;
                try {
                    this.audioBuffer = await decodeAudioArrayBuffer(arrayBuffer.slice(0));
                } catch (decodeError) {
                    console.warn("AudioWaveformPlayer: Web Audio decode failed, using element playback:", decodeError);
                    this.useElementPlayback = true;
                }
                if (this._unmounted || generation !== this._loadGeneration) {
                    return;
                }
                this.totalDuration = this.audioBuffer ? this.audioBuffer.duration : 0;
                this.currentTime = 0;
                this.progressPercent = 0;

                this.$nextTick(() => {
                    this.drawWaveform();
                });
            } catch (e) {
                console.error("Failed to load audio for player:", e);
            } finally {
                if (generation === this._loadGeneration && !this._unmounted) {
                    this.loading = false;
                }
            }
        },
        teardownElementPlayback() {
            if (this.audioElement) {
                try {
                    this.audioElement.pause();
                } catch {
                    // ignore
                }
                this.audioElement = null;
            }
            if (this.blobUrl) {
                try {
                    URL.revokeObjectURL(this.blobUrl);
                } catch {
                    // ignore
                }
                this.blobUrl = null;
            }
            this.playbackMode = null;
        },
        drawWaveform() {
            const canvas = this.$refs.waveform;
            if (!canvas || !this.audioBuffer) return;

            const ctx = canvas.getContext("2d");
            const width = canvas.clientWidth;
            const height = canvas.clientHeight;

            canvas.width = width * window.devicePixelRatio;
            canvas.height = height * window.devicePixelRatio;
            ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

            const data = this.audioBuffer.getChannelData(0);
            const step = Math.ceil(data.length / width);
            const amp = height / 2;

            ctx.clearRect(0, 0, width, height);

            // Follow the surrounding text colour so the waveform respects the
            // active theme instead of guessing light vs dark.
            const waveFg = getComputedStyle(canvas).color || "#000";

            ctx.beginPath();
            ctx.globalAlpha = 0.25;
            ctx.strokeStyle = waveFg;
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

            // Progress waveform (colored)
            const progressX = (this.progressPercent / 100) * width;
            if (progressX > 0) {
                ctx.beginPath();
                ctx.globalAlpha = 0.9;
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
        },
        isDarkMode() {
            return document.documentElement.classList.contains("dark");
        },
        formatTime(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, "0")}`;
        },
        togglePlay() {
            if (this.isPlaying) {
                this.stopPlayback();
            } else {
                this.startPlayback();
            }
        },
        async startPlayback() {
            if (!this.audioBuffer && !this.audioBytes) return;

            try {
                this.stopPlayback();

                const startOffset = this.currentTime >= this.totalDuration ? 0 : this.currentTime;

                if (!this.useElementPlayback) {
                    const ctx = this.ensurePlaybackContext();
                    const running = await ensureAudioContextRunning(ctx);
                    if (running) {
                        this.startBufferPlayback(running, startOffset);
                        return;
                    }
                    this.useElementPlayback = true;
                }
                await this.startElementPlayback(startOffset);
            } catch (error) {
                console.error("AudioWaveformPlayer: playback failed:", error);
            }
        },
        ensurePlaybackContext() {
            if (this.audioContext) {
                return this.audioContext;
            }
            const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
            if (typeof AudioContextCtor !== "function") {
                return null;
            }
            try {
                this.audioContext = new AudioContextCtor();
            } catch {
                return null;
            }
            return this.audioContext;
        },
        startBufferPlayback(ctx, startOffset) {
            this.sourceNode = ctx.createBufferSource();
            this.sourceNode.buffer = this.audioBuffer;
            this.sourceNode.connect(ctx.destination);

            this.playbackMode = "webaudio";
            this.playbackStartOffset = startOffset;
            this.playbackStartTime = ctx.currentTime;

            this.sourceNode.start(0, startOffset);
            this.isPlaying = true;
            this.$emit("play");

            this.sourceNode.onended = () => {
                if (this.isPlaying) {
                    this.isPlaying = false;
                    this.currentTime = this.totalDuration;
                    this.progressPercent = 100;
                    cancelAnimationFrame(this.animationFrame);
                    this.drawWaveform();
                }
            };

            this.updateProgress();
        },
        ensureAudioElement() {
            if (this.audioElement) {
                return this.audioElement;
            }
            if (!this.audioBytes || typeof Audio === "undefined") {
                return null;
            }
            if (!this.blobUrl && typeof URL.createObjectURL === "function") {
                const type = this.audioMimeType.startsWith("audio/") ? this.audioMimeType : "";
                this.blobUrl = URL.createObjectURL(new Blob([this.audioBytes], { type }));
            }
            if (!this.blobUrl) {
                return null;
            }
            const el = new Audio(this.blobUrl);
            el.preload = "auto";
            el.onended = () => {
                if (this.isPlaying && this.playbackMode === "element") {
                    this.isPlaying = false;
                    this.currentTime = this.totalDuration;
                    this.progressPercent = 100;
                    cancelAnimationFrame(this.animationFrame);
                    this.drawWaveform();
                }
            };
            this.audioElement = el;
            return el;
        },
        async startElementPlayback(startOffset) {
            const el = this.ensureAudioElement();
            if (!el) {
                return;
            }
            const applyOffset = () => {
                try {
                    el.currentTime = startOffset;
                } catch {
                    // ignore
                }
            };
            if (el.readyState >= 1) {
                applyOffset();
            } else {
                el.addEventListener("loadedmetadata", applyOffset, { once: true });
            }
            try {
                await el.play();
            } catch (error) {
                console.warn("AudioWaveformPlayer: element playback failed:", error);
                return;
            }
            this.playbackMode = "element";
            this.isPlaying = true;
            this.$emit("play");
            this.updateProgress();
        },
        stopPlayback() {
            if (this.sourceNode) {
                try {
                    this.sourceNode.stop();
                } catch {
                    // ignore
                }
                this.sourceNode = null;
            }
            if (this.audioElement) {
                try {
                    this.audioElement.pause();
                } catch {
                    // ignore
                }
            }
            this.isPlaying = false;
            this.playbackMode = null;
            cancelAnimationFrame(this.animationFrame);
        },
        updateProgress() {
            if (!this.isPlaying) return;

            if (this.playbackMode === "element" && this.audioElement) {
                const el = this.audioElement;
                const duration = Number.isFinite(el.duration) && el.duration > 0 ? el.duration : this.totalDuration;
                if (duration > 0) {
                    this.totalDuration = duration;
                    this.currentTime = Math.min(el.currentTime || 0, duration);
                    this.progressPercent = (this.currentTime / duration) * 100;
                } else {
                    this.currentTime = el.currentTime || 0;
                    this.progressPercent = 0;
                }
                this.drawWaveform();
                if (duration > 0 && this.currentTime >= duration) {
                    this.isPlaying = false;
                    return;
                }
                this.animationFrame = requestAnimationFrame(this.updateProgress);
                return;
            }

            if (!this.audioContext) return;
            const elapsed = this.audioContext.currentTime - this.playbackStartTime;
            this.currentTime = Math.min(this.playbackStartOffset + elapsed, this.totalDuration);
            this.progressPercent = this.totalDuration > 0 ? (this.currentTime / this.totalDuration) * 100 : 0;

            this.drawWaveform();

            if (this.totalDuration > 0 && this.currentTime >= this.totalDuration) {
                this.isPlaying = false;
                return;
            }

            this.animationFrame = requestAnimationFrame(this.updateProgress);
        },
        handleWaveformClick(e) {
            const canvas = this.$refs.waveform;
            const rect = canvas.getBoundingClientRect();
            const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
            const time = this.totalDuration > 0 ? (x / rect.width) * this.totalDuration : 0;

            this.currentTime = time;
            this.progressPercent = this.totalDuration > 0 ? (this.currentTime / this.totalDuration) * 100 : 0;

            if (this.isPlaying) {
                if (this.playbackMode === "element" && this.audioElement) {
                    try {
                        this.audioElement.currentTime = time;
                    } catch {
                        // ignore
                    }
                } else {
                    this.startPlayback();
                }
            } else {
                this.drawWaveform();
            }
        },
    },
};
</script>

<style scoped>
canvas {
    image-rendering: auto;
}
</style>
