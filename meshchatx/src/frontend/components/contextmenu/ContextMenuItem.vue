<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <button type="button" class="context-item" :class="itemClass" :disabled="disabled" @click="emit('click', $event)">
        <slot />
    </button>
</template>

<script setup lang="ts">
defineProps<{
    itemClass?: string;
    disabled?: boolean;
}>();

const emit = defineEmits<{
    click: [event: MouseEvent];
}>();
</script>
