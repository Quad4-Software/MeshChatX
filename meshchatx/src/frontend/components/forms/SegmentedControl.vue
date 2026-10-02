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
            @click="
                $emit('update:modelValue', opt.value);
                $emit('change', opt.value);
            "
        >
            <MaterialDesignIcon v-if="opt.icon" :icon-name="opt.icon" class="size-4 shrink-0" />
            <span>{{ $t(opt.label) }}</span>
        </button>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "SegmentedControl",
    components: { MaterialDesignIcon },
    props: {
        modelValue: { type: String, required: true },
        options: { type: Array, required: true },
        label: { type: String, default: "" },
    },
    emits: ["update:modelValue", "change"],
};
</script>
