<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <v-dialog
        :model-value="modelValue"
        persistent
        :max-width="maxWidth"
        scrollable
        @update:model-value="$emit('update:modelValue', $event)"
    >
        <v-card class="bg-white dark:bg-zinc-950 border border-gray-200 dark:border-zinc-800">
            <v-card-title class="text-lg font-semibold text-gray-900 dark:text-zinc-100 pt-5 px-5 pb-2">
                {{ title }}
            </v-card-title>
            <v-card-text class="px-5 pb-2 text-sm text-gray-600 dark:text-zinc-400 space-y-3">
                <p v-if="description">{{ description }}</p>
                <slot />
                <p v-if="busy && busyText" class="text-xs text-center text-gray-500 dark:text-zinc-500">
                    {{ busyText }}
                </p>
            </v-card-text>
            <v-card-actions class="px-5 pb-5 pt-2 flex flex-col sm:flex-row gap-2 sm:justify-end">
                <button
                    v-if="secondaryLabel"
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-secondary w-full sm:w-auto"
                    :disabled="busy"
                    @click="$emit('secondary')"
                >
                    {{ secondaryLabel }}
                </button>
                <button
                    v-if="primaryLabel"
                    type="button"
                    class="tutorial-action-btn tutorial-action-btn-primary w-full sm:w-auto"
                    :disabled="busy || primaryDisabled"
                    @click="$emit('primary')"
                >
                    {{ primaryLabel }}
                </button>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script>
export default {
    name: "AppUpdatePrompt",
    props: {
        modelValue: { type: Boolean, default: false },
        title: { type: String, required: true },
        description: { type: String, default: "" },
        primaryLabel: { type: String, default: "" },
        secondaryLabel: { type: String, default: "" },
        busy: { type: Boolean, default: false },
        busyText: { type: String, default: "" },
        primaryDisabled: { type: Boolean, default: false },
        maxWidth: { type: [Number, String], default: 520 },
    },
    emits: ["update:modelValue", "primary", "secondary"],
};
</script>
