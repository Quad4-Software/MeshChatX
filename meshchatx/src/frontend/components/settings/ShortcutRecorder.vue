<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex items-center gap-2">
        <div
            class="flex-1 flex flex-wrap gap-1.5 p-2 bg-sem-surface border border-sem-border rounded-xl min-h-[44px]"
            :class="{ 'ring-2 ring-blue-500 border-blue-500': isRecording }"
        >
            <template v-if="keys.length > 0">
                <kbd
                    v-for="key in keys"
                    :key="key"
                    class="px-2 py-1 bg-sem-surface-muted border border-sem-border rounded-lg text-xs font-bold text-sem-fg-muted shadow-xs uppercase"
                >
                    {{ formatKey(key) }}
                </kbd>
            </template>
            <span v-else class="text-sem-fg-muted text-sm my-auto px-1">
                {{ isRecording ? "Press keys..." : "No shortcut" }}
            </span>
        </div>

        <button
            type="button"
            class="px-4 py-2 rounded-xl font-bold transition-all shadow-xs flex items-center gap-2"
            :class="[
                isRecording
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-sem-surface-muted text-sem-fg-muted hover:bg-gray-200 hover:bg-sem-surface-muted',
            ]"
            @click="toggleRecording"
        >
            <MaterialDesignIcon :icon-name="isRecording ? 'check' : 'record-circle-outline'" class="size-5" />
            {{ isRecording ? "Done" : "Record" }}
        </button>

        <button
            v-if="keys.length > 0 && !isRecording"
            type="button"
            class="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-xl transition-all"
            title="Clear Shortcut"
            @click="clearShortcut"
        >
            <MaterialDesignIcon icon-name="trash-can-outline" class="size-5" />
        </button>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import KeyboardShortcuts from "../../js/KeyboardShortcuts";

export default {
    name: "ShortcutRecorder",
    components: { MaterialDesignIcon },
    props: {
        modelValue: {
            type: Array,
            default: () => [],
        },
        action: {
            type: String,
            required: true,
        },
    },
    emits: ["update:modelValue", "save", "delete"],
    data() {
        return {
            isRecording: false,
            keys: [...this.modelValue],
        };
    },
    watch: {
        modelValue(newVal) {
            this.keys = [...newVal];
        },
    },
    methods: {
        formatKey(key) {
            if (key === "control") return "Ctrl";
            if (key === "alt") return "Alt";
            if (key === "shift") return "Shift";
            if (key === "meta") return "⌘";
            if (key === " ") return "Space";
            return key;
        },
        toggleRecording() {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        },
        startRecording() {
            this.isRecording = true;
            this.keys = [];
            KeyboardShortcuts.startRecording((keys) => {
                this.keys = keys;
            });
        },
        stopRecording() {
            this.isRecording = false;
            KeyboardShortcuts.stopRecording();
            this.$emit("update:modelValue", this.keys);
            this.$emit("save", this.keys);
        },
        clearShortcut() {
            this.keys = [];
            this.$emit("update:modelValue", []);
            this.$emit("delete");
        },
    },
};
</script>
