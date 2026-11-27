<template>
    <div ref="wrap" :class="wrapClass">
        <img
            v-if="show"
            :src="src"
            :loading="loading"
            :decoding="decoding"
            :class="imgClass"
            :alt="alt"
            draggable="false"
            @click="emit('click', $event)"
        />
        <div v-else :class="placeholderClassComputed" aria-hidden="true" />
    </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { attachInView } from "../../js/inViewObserver.js";

const props = withDefaults(
    defineProps<{
        src: string;
        imgClass?: string;
        fitParent?: boolean;
        alt?: string;
        loading?: string;
        decoding?: string;
    }>(),
    {
        imgClass: "",
        fitParent: false,
        alt: "",
        loading: "lazy",
        decoding: "async",
    }
);

const emit = defineEmits<{
    click: [event: MouseEvent];
}>();

const wrap = ref<HTMLElement | null>(null);
const show = ref(false);
let ioCleanup: (() => void) | null = null;

const wrapClass = computed(() => (props.fitParent ? "absolute inset-0 overflow-hidden" : "relative w-full"));
const placeholderClassComputed = computed(() => {
    if (props.fitParent) {
        return "absolute inset-0 bg-zinc-200/30 dark:bg-white/10";
    }
    return "min-h-32 w-full rounded-2xl bg-sem-surface-muted/80 dark:bg-sem-surface/80";
});

onMounted(() => {
    nextTick(() => {
        const el = wrap.value;
        if (!el) {
            return;
        }
        ioCleanup = attachInView(el, (entry) => {
            // One-way reveal. Toggling hide collapses height and yanks the message list scroll.
            if (entry.isIntersecting) {
                show.value = true;
            }
        });
    });
});

onBeforeUnmount(() => {
    if (ioCleanup) {
        ioCleanup();
    }
});
</script>
