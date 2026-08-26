<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="theme-preset-swatch inline-grid shrink-0 overflow-hidden rounded-md border border-sem-border shadow-xs"
        :class="sizeClass"
        aria-hidden="true"
    >
        <span class="theme-preset-swatch__band" :style="{ backgroundColor: colors.canvas }" />
        <span class="theme-preset-swatch__band" :style="{ backgroundColor: colors.surface }" />
        <span class="theme-preset-swatch__band" :style="{ backgroundColor: colors.accent }" />
        <span class="theme-preset-swatch__band" :style="{ backgroundColor: colors.border }" />
    </div>
</template>

<script>
export default {
    name: "ThemePresetSwatch",
    props: {
        colors: {
            type: Object,
            required: true,
        },
        size: {
            type: String,
            default: "md",
            validator: (value) => ["sm", "md", "lg"].includes(value),
        },
    },
    computed: {
        sizeClass() {
            if (this.size === "sm") {
                return "h-7 w-7";
            }
            if (this.size === "lg") {
                return "h-10 w-10";
            }
            return "h-8 w-8";
        },
    },
};
</script>

<style scoped>
.theme-preset-swatch {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.theme-preset-swatch__band {
    min-height: 100%;
}
</style>
