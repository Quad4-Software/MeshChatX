<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="slider-select">
        <input
            :value="indexOfValue"
            type="range"
            min="0"
            :max="options.length - 1"
            step="1"
            class="range-input w-full touch-pan-x"
            :aria-label="label"
            @input="onInput"
            @change="onChange"
        />
        <div class="flex mt-1" :style="`padding: 0 ${100 / options.length / 2}%`">
            <button
                v-for="(opt, i) in options"
                :key="opt.value"
                type="button"
                class="flex-1 text-center text-[10px] font-medium transition-colors"
                :class="i === indexOfValue ? 'text-sem-accent font-semibold' : 'text-sem-fg-muted hover:text-sem-fg'"
                @click="selectIndex(i)"
            >
                {{ $t(opt.label) }}
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface SliderOption {
    value: string;
    label: string;
}

const props = withDefaults(
    defineProps<{
        modelValue: string;
        options: SliderOption[];
        label?: string;
    }>(),
    {
        label: "",
    }
);

const emit = defineEmits<{
    "update:modelValue": [value: string];
    change: [value: string];
}>();

const indexOfValue = computed(() => {
    const i = props.options.findIndex((o) => o.value === props.modelValue);
    return i >= 0 ? i : 0;
});

function selectIndex(i: number) {
    const opt = props.options[i];
    if (!opt) return;
    emit("update:modelValue", opt.value);
    emit("change", opt.value);
}

function onInput(event: Event) {
    selectIndex(Number((event.target as HTMLInputElement).value));
}

function onChange(event: Event) {
    selectIndex(Number((event.target as HTMLInputElement).value));
}
</script>
