<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="flex flex-col items-center justify-center px-4 py-10 text-center"
        :class="rootClass"
        role="status"
        aria-live="polite"
        aria-busy="true"
    >
        <MaterialDesignIcon
            icon-name="loading"
            class="size-8 animate-spin text-sem-accent motion-reduce:animate-none"
        />
        <p v-if="message" class="mt-3 text-sm text-sem-fg-muted">{{ message }}</p>
    </div>
</template>

<script setup lang="ts">
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

withDefaults(
    defineProps<{
        message?: string;
        rootClass?: string;
    }>(),
    {
        message: "",
        rootClass: "",
    }
);
</script>
