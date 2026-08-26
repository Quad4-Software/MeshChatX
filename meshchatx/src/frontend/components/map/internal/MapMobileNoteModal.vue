<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <transition name="fade">
        <div
            v-if="show"
            class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
            @click.self="$emit('close')"
        >
            <div
                class="bg-sem-surface w-full max-w-lg rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden animate-slide-up sm:animate-fade-in"
            >
                <div class="p-4 border-b border-sem-border flex items-center justify-between">
                    <h3 class="text-lg font-bold text-sem-fg flex items-center gap-2">
                        <MaterialDesignIcon icon-name="note-edit" class="size-5 text-amber-500" />
                        Edit Note
                    </h3>
                    <button
                        class="p-2 text-gray-400 hover:bg-sem-surface-muted rounded-full transition-colors"
                        @click="$emit('close')"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-4">
                    <textarea
                        :value="text"
                        class="w-full h-40 p-4 text-base bg-gray-50 dark:bg-zinc-800 border border-sem-border rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-hidden resize-none text-sem-fg"
                        placeholder="Type your note here..."
                        autofocus
                        @input="$emit('update:text', $event.target.value)"
                    ></textarea>
                </div>
                <div class="p-4 bg-gray-50 dark:bg-zinc-800/50 flex justify-between gap-3">
                    <button
                        class="flex-1 px-4 py-3 text-sm font-bold text-red-500 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-xl transition-colors flex items-center justify-center gap-2"
                        @click="$emit('delete')"
                    >
                        <MaterialDesignIcon icon-name="trash-can-outline" class="size-5" />
                        Delete
                    </button>
                    <button
                        class="flex-2 px-4 py-3 text-sm font-bold bg-amber-500 text-white hover:bg-amber-600 rounded-xl shadow-lg shadow-amber-500/30 transition-colors"
                        @click="$emit('save')"
                    >
                        Save Note
                    </button>
                </div>
            </div>
        </div>
    </transition>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapMobileNoteModal",
    components: {
        MaterialDesignIcon,
    },
    props: {
        show: {
            type: Boolean,
            default: false,
        },
        text: {
            type: String,
            default: "",
        },
    },
    emits: ["close", "save", "delete", "update:text"],
};
</script>
