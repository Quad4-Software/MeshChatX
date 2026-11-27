<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <label class="setting-toggle" :class="{ 'opacity-50 cursor-not-allowed': disabled }">
        <Toggle
            :id="id"
            :model-value="modelValue"
            :disabled="disabled"
            @update:model-value="emit('update:modelValue', $event)"
        />
        <span class="setting-toggle__label">
            <span class="setting-toggle__title">{{ title }}</span>
            <span v-if="description" class="setting-toggle__description">
                <slot name="description">{{ description }}</slot>
            </span>
            <span v-if="hint" class="setting-toggle__hint">{{ hint }}</span>
        </span>
    </label>
</template>

<script setup lang="ts">
import Toggle from "../forms/Toggle.vue";

withDefaults(
    defineProps<{
        id: string;
        modelValue?: boolean;
        title: string;
        description?: string;
        hint?: string;
        disabled?: boolean;
    }>(),
    {
        modelValue: false,
        description: "",
        hint: "",
        disabled: false,
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: boolean];
}>();
</script>

<style scoped>
@reference "../../style.css";
.setting-toggle {
    @apply relative flex flex-row-reverse items-start gap-3 rounded-2xl border border-sem-border bg-sem-surface px-3 py-3;
}
.setting-toggle > :deep(label) {
    @apply shrink-0 self-center;
}
.setting-toggle :deep(.sr-only) {
    @apply absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0;
}
.setting-toggle__label {
    @apply flex-1 min-w-0 flex flex-col gap-0.5;
}
.setting-toggle__title {
    @apply text-sm font-semibold text-sem-fg wrap-break-word leading-snug;
}
.setting-toggle__description {
    @apply text-xs sm:text-sm text-sem-fg-muted wrap-break-word leading-snug;
}
.setting-toggle__hint {
    @apply text-xs text-sem-fg-muted wrap-break-word;
}
</style>
