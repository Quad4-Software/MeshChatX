<template>
    <div ref="stickerRoot" :class="['sticker-view', sizeClass]">
        <video v-if="isVideo" ref="videoEl" :src="src" class="sticker-media" loop muted playsinline @error="onError" />
        <div
            v-else-if="isAnimated"
            class="w-full h-full flex items-center justify-center bg-gray-200/80 bg-sem-surface text-sem-fg-muted"
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

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { attachInView } from "../../js/inViewObserver.js";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

const props = withDefaults(
    defineProps<{
        src: string;
        imageType?: string;
        alt?: string;
        size?: string;
    }>(),
    {
        imageType: "",
        alt: "",
        size: "auto",
    }
);

const emit = defineEmits<{
    error: [event: Event];
}>();

let destroyed = false;
const inView = ref(false);
let ioCleanup: (() => void) | null = null;

const stickerRoot = ref<HTMLElement | null>(null);
const videoEl = ref<HTMLVideoElement | null>(null);

const isVideo = computed(() => (props.imageType || "").toLowerCase() === "webm");
const isAnimated = computed(() => (props.imageType || "").toLowerCase() === "tgs");
const sizeClass = computed(() => `sticker-view--${props.size}`);

watch(inView, () => {
    onInViewChanged();
});

watch(
    () => props.src,
    () => {
        if (isVideo.value) {
            nextTick(() => syncVideoPlayback());
        }
    }
);

watch(
    () => props.imageType,
    () => {
        if (isVideo.value) {
            nextTick(() => syncVideoPlayback());
        }
    }
);

onMounted(() => {
    nextTick(() => setupInView());
});

onBeforeUnmount(() => {
    destroyed = true;
    if (ioCleanup) {
        ioCleanup();
        ioCleanup = null;
    }
});

function setupInView() {
    const el = stickerRoot.value;
    if (!el) {
        return;
    }
    ioCleanup = attachInView(el, (entry: IntersectionObserverEntry) => {
        inView.value = entry.isIntersecting;
    });
}

function onInViewChanged() {
    if (isVideo.value) {
        syncVideoPlayback();
    }
}

function syncVideoPlayback() {
    const v = videoEl.value;
    if (!v || !isVideo.value) {
        return;
    }
    if (inView.value) {
        v.play?.().catch(() => {});
    } else {
        v.pause?.();
    }
}

function onError(e: Event) {
    emit("error", e);
}

void destroyed;
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
