<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="inline-flex">
        <button
            v-if="isRecordingAudioAttachment"
            type="button"
            class="my-auto inline-flex items-center gap-x-1 rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 shadow-sm hover:border-red-400 transition dark:border-red-500/40 dark:bg-red-900/30 dark:text-red-100"
            @click="stopRecordingAudioAttachment"
        >
            <MaterialDesignIcon icon-name="microphone" class="w-4 h-4" />
            <span class="ml-1">
                <slot />
            </span>
        </button>

        <button
            v-else
            type="button"
            class="my-auto inline-flex items-center gap-x-1 rounded-full border border-gray-200 dark:border-zinc-700 bg-white/90 dark:bg-zinc-900/80 px-3 py-1.5 text-xs font-semibold text-gray-800 dark:text-gray-100 shadow-sm hover:border-blue-400 dark:hover:border-blue-500 transition"
            @click="showMenu"
        >
            <MaterialDesignIcon icon-name="microphone-plus" class="w-4 h-4" />
            <span class="hidden xl:inline-block whitespace-nowrap">Add Voice</span>
        </button>

        <div class="relative block">
            <Transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="transform opacity-0 scale-95"
                enter-to-class="transform opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="transform opacity-100 scale-100"
                leave-to-class="transform opacity-0 scale-95"
            >
                <div
                    v-if="isShowingMenu"
                    v-click-outside="hideMenu"
                    class="absolute bottom-0 -ml-11 sm:right-0 sm:ml-0 z-10 mb-10 rounded-xl bg-white dark:bg-zinc-900 shadow-lg ring-1 ring-gray-200 dark:ring-zinc-800 focus:outline-none"
                >
                    <div class="py-1">
                        <button
                            type="button"
                            class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-800 whitespace-nowrap"
                            @click="startRecordingCodec2('1200')"
                        >
                            Low Quality - Codec2 (1200)
                        </button>
                        <button
                            type="button"
                            class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-800 whitespace-nowrap"
                            @click="startRecordingCodec2('3200')"
                        >
                            Medium Quality - Codec2 (3200)
                        </button>
                        <button
                            type="button"
                            class="w-full block text-left px-4 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-800 whitespace-nowrap"
                            @click="startRecordingOpus()"
                        >
                            High Quality - OPUS
                        </button>
                    </div>
                </div>
            </Transition>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
export default {
    name: "AddAudioButton",
    components: {
        MaterialDesignIcon,
    },
    props: {
        isRecordingAudioAttachment: Boolean,
    },
    emits: ["start-recording", "stop-recording"],
    data() {
        return {
            isShowingMenu: false,
        };
    },
    methods: {
        showMenu() {
            this.isShowingMenu = true;
        },
        hideMenu() {
            this.isShowingMenu = false;
        },
        startRecordingAudioAttachment(args) {
            this.isShowingMenu = false;
            this.$emit("start-recording", args);
        },
        startRecordingCodec2(mode) {
            this.startRecordingAudioAttachment({
                codec: "codec2",
                mode: mode,
            });
        },
        startRecordingOpus() {
            this.startRecordingAudioAttachment({
                codec: "opus",
            });
        },
        stopRecordingAudioAttachment() {
            this.isShowingMenu = false;
            this.$emit("stop-recording");
        },
    },
};
</script>
