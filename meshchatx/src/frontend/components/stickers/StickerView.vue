<template>
    <div ref="stickerRoot" :class="['sticker-view', sizeClass]">
        <video v-if="isVideo" ref="videoEl" :src="src" class="sticker-media" loop muted playsinline @error="onError" />
        <div
            v-else-if="isAnimated"
            class="w-full h-full flex items-center justify-center bg-gray-200/80 dark:bg-zinc-700/50 text-gray-500 dark:text-zinc-400"
            :title="alt || 'TGS'"
            :aria-label="alt || 'Animated sticker'"
        >
            <MaterialDesignIcon icon-name="animation-outline" class="w-[42%] h-[42%] opacity-70" />
        </div>
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
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "StickerView",
    components: { MaterialDesignIcon },
    props: {
        src: { type: String, required: true },
        imageType: { type: String, default: "" },
        alt: { type: String, default: "" },
        size: { type: String, default: "auto" },
    },
    emits: ["error"],
    data() {
        return {
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
            if (this.isVideo) {
                this.$nextTick(() => this.syncVideoPlayback());
            }
        },
        imageType() {
            if (this.isVideo) {
                this.$nextTick(() => this.syncVideoPlayback());
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
