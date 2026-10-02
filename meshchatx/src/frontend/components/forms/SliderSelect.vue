<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="slider-select">
        <input
            :value="indexOfValue"
            type="range"
            min="0"
            :max="options.length - 1"
            step="1"
            class="range-input w-full"
            :aria-label="label"
            @input="onInput"
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

<script>
export default {
    name: "SliderSelect",
    props: {
        modelValue: { type: String, required: true },
        options: { type: Array, required: true },
        label: { type: String, default: "" },
    },
    emits: ["update:modelValue", "change"],
    computed: {
        indexOfValue() {
            const i = this.options.findIndex((o) => o.value === this.modelValue);
            return i >= 0 ? i : 0;
        },
    },
    methods: {
        onInput(e) {
            this.selectIndex(Number(e.target.value));
        },
        selectIndex(i) {
            const opt = this.options[i];
            if (!opt) return;
            this.$emit("update:modelValue", opt.value);
            this.$emit("change", opt.value);
        },
    },
};
</script>
