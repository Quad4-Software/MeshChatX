<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <label class="setting-toggle" :class="{ 'opacity-50 cursor-not-allowed': disabled }">
        <Toggle
            :id="id"
            :model-value="modelValue"
            :disabled="disabled"
            @update:model-value="$emit('update:modelValue', $event)"
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

<script>
import Toggle from "../forms/Toggle.vue";

export default {
    name: "SettingToggleRow",
    components: {
        Toggle,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        modelValue: {
            type: Boolean,
            default: false,
        },
        title: {
            type: String,
            required: true,
        },
        description: {
            type: String,
            default: "",
        },
        hint: {
            type: String,
            default: "",
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["update:modelValue"],
};
</script>

<style scoped>
@reference "../../style.css";
.setting-toggle {
    @apply relative flex flex-row-reverse items-start gap-3 rounded-2xl border border-gray-200 dark:border-zinc-800 bg-white/70 dark:bg-zinc-900/70 px-3 py-3;
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
    @apply text-sm font-semibold text-gray-900 dark:text-white break-words leading-snug;
}
.setting-toggle__description {
    @apply text-xs sm:text-sm text-gray-600 dark:text-gray-300 break-words leading-snug;
}
.setting-toggle__hint {
    @apply text-xs text-gray-500 dark:text-gray-400 break-words;
}
</style>
