<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <AppModal
        :model-value="modelValue"
        :max-width="maxWidth"
        persistent
        @update:model-value="$emit('update:modelValue', $event)"
    >
        <template #header>
            <h2 class="min-w-0 flex-1 text-lg font-semibold text-sem-fg">{{ title }}</h2>
        </template>

        <div class="space-y-3 px-4 py-4 text-sm text-sem-fg-muted sm:px-5">
            <p v-if="description">{{ description }}</p>
            <slot />
            <p v-if="busy && busyText" class="text-center text-xs text-sem-fg-muted">
                {{ busyText }}
            </p>
        </div>

        <template #actions>
            <div class="flex w-full flex-col gap-2 sm:flex-row sm:justify-end">
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
            </div>
        </template>
    </AppModal>
</template>

<script>
import AppModal from "./AppModal.vue";

export default {
    name: "AppUpdatePrompt",
    components: {
        AppModal,
    },
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
