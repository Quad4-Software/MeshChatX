<template>
    <button type="button" class="context-item" :class="itemClass" :disabled="disabled" @click="$emit('click', $event)">
        <slot />
    </button>
</template>

<script>
export default {
    name: "ContextMenuItem",
    props: {
        itemClass: {
            type: String,
            default: "",
        },
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    emits: ["click"],
};
</script>
