<template>
    <div
        v-if="show"
        class="context-menu-panel"
        :class="panelClass"
        :style="{ top: y + 'px', left: x + 'px' }"
        v-bind="$attrs"
    >
        <slot name="header" />
        <slot />
    </div>
</template>

<script>
export default {
    name: "ContextMenuPanel",
    inheritAttrs: false,
    props: {
        show: {
            type: Boolean,
            required: true,
        },
        x: {
            type: Number,
            required: true,
        },
        y: {
            type: Number,
            required: true,
        },
        panelClass: {
            type: String,
            default: "",
        },
    },
};
</script>
