<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 px-4 py-12 text-center"
        :class="rootClass"
    >
        <MaterialDesignIcon v-if="icon" :icon-name="icon" class="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <div v-if="title" class="text-base font-semibold text-gray-800 dark:text-zinc-200">{{ title }}</div>
        <p v-if="description" class="mt-2 text-sm text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            {{ description }}
        </p>
        <div v-if="$slots.action" class="mt-4 flex justify-center">
            <slot name="action" />
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";

export default {
    name: "EmptyState",
    components: {
        MaterialDesignIcon,
    },
    props: {
        icon: {
            type: String,
            default: "",
        },
        title: {
            type: String,
            default: "",
        },
        description: {
            type: String,
            default: "",
        },
        rootClass: {
            type: String,
            default: "",
        },
    },
};
</script>
