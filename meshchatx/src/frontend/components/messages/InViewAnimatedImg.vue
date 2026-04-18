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
            @click="$emit('click', $event)"
        />
        <div v-else :class="placeholderClassComputed" aria-hidden="true" />
    </div>
</template>

<script>
import { attachInView } from "../../js/inViewObserver.js";

export default {
    name: "InViewAnimatedImg",
    props: {
        src: { type: String, required: true },
        imgClass: { type: String, default: "" },
        fitParent: { type: Boolean, default: false },
        alt: { type: String, default: "" },
        loading: { type: String, default: "lazy" },
        decoding: { type: String, default: "async" },
    },
    emits: ["click"],
    data() {
        return {
            show: false,
            ioCleanup: null,
        };
    },
    computed: {
        wrapClass() {
            return this.fitParent ? "absolute inset-0 overflow-hidden" : "relative w-full";
        },
        placeholderClassComputed() {
            if (this.fitParent) {
                return "absolute inset-0 bg-zinc-200/30 dark:bg-white/10";
            }
            return "min-h-[8rem] w-full rounded-2xl bg-gray-100/90 dark:bg-zinc-800/60";
        },
    },
    mounted() {
        this.$nextTick(() => {
            const el = this.$refs.wrap;
            if (!el) {
                return;
            }
            this.ioCleanup = attachInView(el, (entry) => {
                this.show = entry.isIntersecting;
            });
        });
    },
    beforeUnmount() {
        if (this.ioCleanup) {
            this.ioCleanup();
        }
    },
};
</script>
