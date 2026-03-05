<template>
    <div
        class="audio-waveform-player flex items-center gap-3 p-2 rounded-xl transition-all w-full min-w-0"
        :class="[
            isOutbound ? 'bg-white/10 text-white' : 'bg-gray-100 dark:bg-zinc-800/80 text-gray-800 dark:text-zinc-200',
        ]"
    >
        <!-- Play/Pause Button -->
        <button
            class="flex items-center justify-center size-10 rounded-full shrink-0 transition-all active:scale-90"
            :class="[
                isOutbound ? 'bg-white/20 hover:bg-white/30 text-white' : 'bg-blue-500 hover:bg-blue-600 text-white',
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
                class="absolute top-0 bottom-0 w-0.5 bg-blue-400 z-10 pointer-events-none transition-[left] duration-100 ease-linear"
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
        this.stopPlayback();
        window.removeEventListener("resize", this.drawWaveform);
        if (this.darkObserver) {
            this.darkObserver.disconnect();
            this.darkObserver = null;
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
    },
    methods: {
        async loadAudio() {
            if (!this.src) return;
            try {
                this.loading = true;
                this.stopPlayback();

                const response = await fetch(this.src);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const arrayBuffer = await response.arrayBuffer();

                if (!this.audioContext) {
                    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }

                this.audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
                this.totalDuration = this.audioBuffer.duration;
                this.currentTime = 0;
                this.progressPercent = 0;

                this.$nextTick(() => {
                    this.drawWaveform();
                });
            } catch (e) {
                console.error("Failed to load audio for player:", e);
            } finally {
                this.loading = false;
            }
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

            const dark = this.isDarkMode();
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

            // Progress waveform (colored)
            const progressX = (this.progressPercent / 100) * width;
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
        startPlayback() {
            if (!this.audioBuffer) return;

            this.stopPlayback();

            if (this.audioContext.state === "suspended") {
                this.audioContext.resume();
            }

            this.sourceNode = this.audioContext.createBufferSource();
            this.sourceNode.buffer = this.audioBuffer;
            this.sourceNode.connect(this.audioContext.destination);

            const startOffset = this.currentTime >= this.totalDuration ? 0 : this.currentTime;
            this.playbackStartOffset = startOffset;
            this.playbackStartTime = this.audioContext.currentTime;

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
        stopPlayback() {
            if (this.sourceNode) {
                try {
                    this.sourceNode.stop();
                } catch {
                    // ignore
                }
                this.sourceNode = null;
            }
            this.isPlaying = false;
            cancelAnimationFrame(this.animationFrame);
        },
        updateProgress() {
            if (!this.isPlaying) return;

            const elapsed = this.audioContext.currentTime - this.playbackStartTime;
            this.currentTime = Math.min(this.playbackStartOffset + elapsed, this.totalDuration);
            this.progressPercent = (this.currentTime / this.totalDuration) * 100;

            this.drawWaveform();

            if (this.currentTime >= this.totalDuration) {
                this.isPlaying = false;
                return;
            }

            this.animationFrame = requestAnimationFrame(this.updateProgress);
        },
        handleWaveformClick(e) {
            const canvas = this.$refs.waveform;
            const rect = canvas.getBoundingClientRect();
            const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
            const time = (x / rect.width) * this.totalDuration;

            this.currentTime = time;
            this.progressPercent = (this.currentTime / this.totalDuration) * 100;

            if (this.isPlaying) {
                this.startPlayback(); // Restart from new position
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
