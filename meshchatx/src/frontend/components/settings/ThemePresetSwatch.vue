<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="theme-preset-swatch inline-grid shrink-0 overflow-hidden border border-sem-border shadow-xs"
        :class="[sizeClass, round ? 'rounded-full' : 'rounded-md']"
        aria-hidden="true"
    >
        <span class="theme-preset-swatch__band" :style="{ backgroundColor: colors.canvas }" />
        <span class="theme-preset-swatch__band" :style="{ backgroundColor: colors.surface }" />
        <span class="theme-preset-swatch__band" :style="{ backgroundColor: colors.accent }" />
        <span class="theme-preset-swatch__band" :style="{ backgroundColor: colors.border }" />
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface SwatchColors {
    canvas: string;
    surface: string;
    accent: string;
    border: string;
}

const props = withDefaults(
    defineProps<{
        colors: SwatchColors;
        size?: "sm" | "md" | "lg";
        round?: boolean;
    }>(),
    {
        size: "md",
        round: false,
    }
);

const sizeClass = computed(() => {
    if (props.size === "sm") {
        return "h-7 w-7";
    }
    if (props.size === "lg") {
        return "h-10 w-10";
    }
    return "h-8 w-8";
});
</script>

<style scoped>
.theme-preset-swatch {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

.theme-preset-swatch__band {
    min-height: 100%;
}
</style>
