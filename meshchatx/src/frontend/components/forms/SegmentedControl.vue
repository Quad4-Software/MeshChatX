<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="inline-flex gap-1 rounded-xl border border-sem-border bg-sem-surface-muted p-1"
        role="radiogroup"
        :aria-label="label"
    >
        <button
            v-for="opt in options"
            :key="opt.value"
            type="button"
            role="radio"
            :aria-checked="modelValue === opt.value"
            class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors whitespace-nowrap"
            :class="
                modelValue === opt.value
                    ? 'bg-sem-surface text-sem-fg shadow-xs font-semibold'
                    : 'text-sem-fg-muted hover:text-sem-fg'
            "
            :title="opt.hint ? $t(opt.hint) : undefined"
            @click="select(opt.value)"
        >
            <MaterialDesignIcon v-if="opt.icon" :icon-name="opt.icon" class="size-4 shrink-0" />
            <span>{{ $t(opt.label) }}</span>
        </button>
    </div>
</template>

<script setup lang="ts">
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

interface SegmentOption {
    value: string;
    label: string;
    icon?: string;
    hint?: string;
}

defineProps<{
    modelValue: string;
    options: SegmentOption[];
    label?: string;
}>();

const emit = defineEmits<{
    "update:modelValue": [value: string];
    change: [value: string];
}>();

function select(value: string) {
    emit("update:modelValue", value);
    emit("change", value);
}
</script>
