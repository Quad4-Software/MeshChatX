<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
    >
        <div
            v-if="url"
            ref="imageModalOverlay"
            tabindex="0"
            class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 dark:bg-black/90 backdrop-blur-xs p-4 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(1rem,env(safe-area-inset-bottom))] outline-hidden"
            @click="$emit('close')"
            @keydown.left.prevent="$emit('navigate', -1)"
            @keydown.right.prevent="$emit('navigate', 1)"
            @keydown.escape.prevent="$emit('close')"
        >
            <div class="relative max-w-7xl max-h-full group/image-modal" @click.stop>
                <button
                    type="button"
                    class="absolute -top-12 left-0 inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 dark:bg-zinc-900/10 hover:bg-white/20 dark:hover:bg-zinc-900/20 text-white transition-colors opacity-0 group-hover/image-modal:opacity-100 focus:opacity-100"
                    :title="$t('messages.save_image_to_device')"
                    @click="$emit('download')"
                >
                    <MaterialDesignIcon icon-name="download" class="size-5" />
                </button>
                <button
                    type="button"
                    class="absolute -top-12 right-0 inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 dark:bg-zinc-900/10 hover:bg-white/20 dark:hover:bg-zinc-900/20 text-white transition-colors"
                    @click="$emit('close')"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
                <button
                    v-if="gallery && gallery.length > 1"
                    type="button"
                    class="absolute left-0 top-1/2 z-10 -translate-y-1/2 inline-flex items-center justify-center w-11 h-11 rounded-full bg-black/40 hover:bg-black/55 text-white transition-colors"
                    aria-label="Previous image"
                    @click.stop="$emit('navigate', -1)"
                >
                    <MaterialDesignIcon icon-name="chevron-left" class="size-7" />
                </button>
                <button
                    v-if="gallery && gallery.length > 1"
                    type="button"
                    class="absolute right-0 top-1/2 z-10 -translate-y-1/2 inline-flex items-center justify-center w-11 h-11 rounded-full bg-black/40 hover:bg-black/55 text-white transition-colors"
                    aria-label="Next image"
                    @click.stop="$emit('navigate', 1)"
                >
                    <MaterialDesignIcon icon-name="chevron-right" class="size-7" />
                </button>
                <div
                    v-if="gallery && gallery.length > 1"
                    class="pointer-events-none absolute bottom-2 left-1/2 z-10 -translate-x-1/2 rounded-full bg-black/50 px-3 py-1 text-xs font-medium text-white"
                >
                    {{ index + 1 }} / {{ gallery.length }}
                </div>
                <img
                    :src="url"
                    class="max-w-full max-h-[90vh] rounded-xl shadow-2xl"
                    alt="Image preview"
                    @contextmenu.prevent.stop="$emit('contextmenu', $event)"
                />
            </div>
        </div>
    </Transition>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "ConversationImageModal",
    components: {
        MaterialDesignIcon,
    },
    props: {
        url: {
            type: String,
            default: "",
        },
        gallery: {
            type: Array,
            default: null,
        },
        index: {
            type: Number,
            default: 0,
        },
    },
    emits: ["close", "navigate", "download", "contextmenu"],
    methods: {
        focusOverlay() {
            this.$nextTick(() => {
                this.$refs.imageModalOverlay?.focus?.();
            });
        },
    },
};
</script>
