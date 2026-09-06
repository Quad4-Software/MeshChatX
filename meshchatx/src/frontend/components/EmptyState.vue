<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="text-center"
        :class="[
            plain
                ? 'px-2 py-3'
                : 'rounded-lg border border-dashed border-sem-border px-4 py-12 bg-sem-surface-muted/40',
            rootClass,
        ]"
    >
        <MaterialDesignIcon
            v-if="icon"
            :icon-name="icon"
            :class="plain ? 'w-8 h-8 mx-auto mb-2 text-sem-fg-muted' : 'w-12 h-12 mx-auto mb-4 text-sem-fg-muted'"
        />
        <div v-if="title" class="text-base font-semibold text-sem-fg">{{ title }}</div>
        <p v-if="description" class="mt-2 text-sm text-sem-fg-muted max-w-md mx-auto">
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
