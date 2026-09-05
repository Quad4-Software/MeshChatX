<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        :class="rootClasses"
        :aria-hidden="true"
        role="presentation"
    />
</template>

<script>
const VARIANT_CLASSES = {
    line: "h-3 w-full rounded-md",
    row: "h-10 w-full rounded-xl",
    avatar: "size-10 rounded-full shrink-0",
    card: "h-24 w-full rounded-2xl",
};

export default {
    name: "Skeleton",
    props: {
        variant: {
            type: String,
            default: "line",
            validator: (value) => Object.prototype.hasOwnProperty.call(VARIANT_CLASSES, value),
        },
        rootClass: {
            type: String,
            default: "",
        },
    },
    computed: {
        rootClasses() {
            const base = VARIANT_CLASSES[this.variant] || VARIANT_CLASSES.line;
            return [
                "bg-sem-surface-muted animate-pulse motion-reduce:animate-none",
                base,
                this.rootClass,
            ];
        },
    },
};
</script>
