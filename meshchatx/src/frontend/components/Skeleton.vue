<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div :class="rootClasses" :aria-hidden="true" role="presentation" />
</template>

<script setup lang="ts">
import { computed } from "vue";

const VARIANT_CLASSES: Record<string, string> = {
    line: "h-3 w-full rounded-md",
    row: "h-10 w-full rounded-xl",
    avatar: "size-10 rounded-full shrink-0",
    card: "h-24 w-full rounded-2xl",
};

const props = withDefaults(
    defineProps<{
        variant?: string;
        rootClass?: string;
    }>(),
    {
        variant: "line",
        rootClass: "",
    }
);

const rootClasses = computed(() => {
    const base = VARIANT_CLASSES[props.variant] || VARIANT_CLASSES.line;
    return ["bg-sem-surface-muted animate-pulse motion-reduce:animate-none", base, props.rootClass];
});
</script>
