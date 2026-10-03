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
                        <MaterialDesignIcon icon-name="note-edit" class="size-5 text-sem-warning" />
                        Edit Note
                    </h3>
                    <button
                        class="p-2 text-sem-fg-muted hover:bg-sem-surface-muted rounded-full transition-colors"
                        @click="$emit('close')"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-4">
                    <textarea
                        :value="text"
                        class="w-full h-40 p-4 text-base bg-sem-surface-muted border border-sem-border rounded-xl focus:ring-2 focus:ring-sem-warning focus:border-transparent outline-hidden resize-none text-sem-fg"
                        placeholder="Type your note here..."
                        autofocus
                        @input="$emit('update:text', $event.target.value)"
                    ></textarea>
                </div>
                <div class="p-4 bg-sem-surface-muted/50 flex justify-between gap-3">
                    <button
                        class="flex-1 px-4 py-3 text-sm font-bold text-sem-danger hover:bg-sem-danger/15 dark:hover:bg-sem-danger/15 rounded-xl transition-colors flex items-center justify-center gap-2"
                        @click="$emit('delete')"
                    >
                        <MaterialDesignIcon icon-name="trash-can-outline" class="size-5" />
                        Delete
                    </button>
                    <button
                        class="flex-2 px-4 py-3 text-sm font-bold bg-sem-warning text-white hover:bg-sem-warning rounded-xl shadow-lg shadow-amber-500/30 transition-colors"
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
