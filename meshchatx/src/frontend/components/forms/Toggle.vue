<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <label
        :for="id"
        class="relative inline-flex w-auto shrink-0 items-center gap-3"
        :class="disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'"
    >
        <input
            :id="id"
            type="checkbox"
            :checked="modelValue"
            :disabled="disabled"
            class="sr-only peer"
            @change="!disabled && $emit('update:modelValue', $event.target.checked)"
        />
        <div
            class="toggle-track relative h-6 w-11 shrink-0 bg-sem-surface-muted border border-sem-border-strong peer-focus:outline-hidden peer-focus:ring-4 peer-focus:ring-sem-focus/40 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-px after:left-px after:bg-sem-surface after:border after:border-sem-border-strong after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-sem-action-primary peer-checked:border-transparent"
        ></div>
        <span v-if="label" class="min-w-0 text-sm font-medium leading-snug text-sem-fg">{{ label }}</span>
    </label>
</template>

<script>
export default {
    name: "Toggle",
    props: {
        id: {
            type: String,
            default: null,
        },
        modelValue: {
            type: Boolean,
            default: false,
        },
        label: {
            type: String,
            default: null,
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["update:modelValue"],
};
</script>
