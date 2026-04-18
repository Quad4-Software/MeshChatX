<template>
    <div ref="stickerRoot" :class="['sticker-view', sizeClass]">
        <video v-if="isVideo" ref="videoEl" :src="src" class="sticker-media" loop muted playsinline @error="onError" />
        <div v-else-if="isAnimated" ref="lottieMount" class="sticker-media" />
        <img
            v-else
            :src="src"
            class="sticker-media"
            decoding="async"
            loading="lazy"
            :alt="alt || ''"
            @error="onError"
        />
    </div>
</template>

<script>
import { attachInView } from "../../js/inViewObserver.js";
import { decodeTgsBuffer } from "../../js/tgsDecode.js";

export default {
    name: "StickerView",
    props: {
        src: { type: String, required: true },
        imageType: { type: String, default: "" },
        alt: { type: String, default: "" },
        size: { type: String, default: "auto" },
    },
    emits: ["error"],
    data() {
        return {
            lottieAnim: null,
            destroyed: false,
            inView: false,
            ioCleanup: null,
        };
    },
    computed: {
        isVideo() {
            return (this.imageType || "").toLowerCase() === "webm";
        },
        isAnimated() {
            return (this.imageType || "").toLowerCase() === "tgs";
        },
        sizeClass() {
            return `sticker-view--${this.size}`;
        },
    },
    watch: {
        inView() {
            this.onInViewChanged();
        },
        src() {
            if (this.isAnimated) {
                this.teardownLottie();
                this.$nextTick(() => {
                    if (this.inView) {
                        this.mountLottie();
                    }
                });
            } else if (this.isVideo) {
                this.$nextTick(() => this.syncVideoPlayback());
            }
        },
        imageType() {
            this.teardownLottie();
            if (this.isAnimated) {
                this.$nextTick(() => {
                    if (this.inView) {
                        this.mountLottie();
                    }
                });
            }
        },
    },
    mounted() {
        this.$nextTick(() => this.setupInView());
    },
    beforeUnmount() {
        this.destroyed = true;
        if (this.ioCleanup) {
            this.ioCleanup();
            this.ioCleanup = null;
        }
        this.teardownLottie();
    },
    methods: {
        setupInView() {
            const el = this.$refs.stickerRoot;
            if (!el) {
                return;
            }
            this.ioCleanup = attachInView(el, (entry) => {
                this.inView = entry.isIntersecting;
            });
        },
        onInViewChanged() {
            if (this.isVideo) {
                this.syncVideoPlayback();
            }
            if (this.isAnimated) {
                if (this.inView && !this.lottieAnim && !this.destroyed) {
                    this.$nextTick(() => this.mountLottie());
                } else {
                    this.syncLottiePlayback();
                }
            }
        },
        syncVideoPlayback() {
            const v = this.$refs.videoEl;
            if (!v || !this.isVideo) {
                return;
            }
            if (this.inView) {
                v.play?.().catch(() => {});
            } else {
                v.pause?.();
            }
        },
        syncLottiePlayback() {
            if (!this.lottieAnim || !this.isAnimated) {
                return;
            }
            try {
                if (this.inView) {
                    this.lottieAnim.play();
                } else {
                    this.lottieAnim.pause();
                }
            } catch (e) {
                console.warn(e);
            }
        },
        async mountLottie() {
            if (!this.$refs.lottieMount || !this.src || !this.inView) {
                return;
            }
            this.teardownLottie();
            try {
                const lottie = await import("lottie-web/build/player/lottie_light.js");
                const lib = lottie.default || lottie;
                const response = await fetch(this.src);
                const buf = await response.arrayBuffer();
                const data = await decodeTgsBuffer(buf);
                if (this.destroyed || !this.inView) {
                    return;
                }
                this.lottieAnim = lib.loadAnimation({
                    container: this.$refs.lottieMount,
                    renderer: "svg",
                    loop: true,
                    autoplay: false,
                    animationData: data,
                });
                this.syncLottiePlayback();
            } catch (e) {
                console.error("Failed to render TGS sticker", e);
                this.$emit("error", e);
            }
        },
        teardownLottie() {
            if (this.lottieAnim) {
                try {
                    this.lottieAnim.destroy();
                } catch (e) {
                    console.warn(e);
                }
                this.lottieAnim = null;
            }
        },
        onError(e) {
            this.$emit("error", e);
        },
    },
};
</script>

<style scoped>
.sticker-view {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    line-height: 0;
}
.sticker-view--auto {
    width: 100%;
    height: 100%;
}
.sticker-view--xs {
    width: 32px;
    height: 32px;
}
.sticker-view--sm {
    width: 56px;
    height: 56px;
}
.sticker-view--md {
    width: 96px;
    height: 96px;
}
.sticker-view--lg {
    width: 192px;
    height: 192px;
}
.sticker-media {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
}
</style>
