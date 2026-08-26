<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="text-center"
        :class="[
            plain ? 'px-2 py-3' : 'rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 px-4 py-12',
            rootClass,
        ]"
    >
        <MaterialDesignIcon
            v-if="icon"
            :icon-name="icon"
            :class="plain ? 'w-8 h-8 mx-auto mb-2 text-gray-400' : 'w-12 h-12 mx-auto mb-4 text-gray-400'"
        />
        <div v-if="title" class="text-base font-semibold text-sem-fg">{{ title }}</div>
        <p v-if="description" class="mt-2 text-sm text-gray-600 dark:text-gray-400 max-w-md mx-auto">
            {{ description }}
        </p>
        <div v-if="$slots.action" class="flex justify-center" :class="plain ? 'mt-3' : 'mt-4'">
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
        plain: {
            type: Boolean,
            default: false,
        },
    },
};
</script>
