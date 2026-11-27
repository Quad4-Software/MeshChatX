<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="flex flex-wrap items-center gap-x-2 gap-y-1.5 pl-1.5 pr-3 sm:pl-2 sm:pr-4 md:pl-4 md:pr-6 py-1.5 sm:py-2 border-b border-sem-border bg-sem-canvas shrink-0 min-w-0"
    >
        <RouterLink
            :to="backTo"
            class="inline-flex items-center justify-center gap-0.5 sm:gap-1 rounded-lg pl-0 pr-1.5 sm:pr-2 py-1.5 min-h-8 min-w-8 sm:min-w-0 text-sm font-medium text-sem-fg-muted hover:bg-sem-surface-muted transition-colors shrink-0 order-first"
            :aria-label="`${$t('tools.back_to_tools')}: ${resolvedBackLabel}`"
        >
            <MaterialDesignIcon icon-name="chevron-left" class="size-5 shrink-0" />
            <span class="hidden sm:inline truncate max-w-[8rem]">{{ resolvedBackLabel }}</span>
        </RouterLink>

        <div class="flex items-center gap-2 min-w-0 flex-1 basis-0">
            <div class="p-1.5 rounded-lg shrink-0" :class="iconWrapClass">
                <MaterialDesignIcon :icon-name="icon" class="size-4 sm:size-5" :class="iconClass" />
            </div>
            <div class="min-w-0">
                <p v-if="eyebrow" class="text-[11px] leading-tight uppercase tracking-wide text-sem-fg-muted truncate">
                    {{ eyebrow }}
                </p>
                <h1 class="text-base sm:text-lg font-bold text-sem-fg leading-snug truncate">
                    {{ title }}
                </h1>
                <p v-if="description" class="text-xs text-sem-fg-muted leading-snug line-clamp-1 sm:line-clamp-2">
                    {{ description }}
                </p>
            </div>
        </div>

        <div v-if="$slots.actions" class="flex items-center gap-2 shrink-0 ml-auto">
            <slot name="actions" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import { translateUi } from "../../js/localeLoader.js";

const ACCENT = {
    blue: {
        wrap: "bg-sem-info/15",
        icon: "text-sem-accent",
    },
    indigo: {
        wrap: "bg-sem-info/15 dark:bg-sem-info/15",
        icon: "text-sem-info dark:text-sem-info",
    },
    teal: {
        wrap: "bg-sem-success/15 dark:bg-sem-success/15",
        icon: "text-sem-success dark:text-sem-success",
    },
    purple: {
        wrap: "bg-purple-100 dark:bg-purple-900/30",
        icon: "text-purple-600 text-sem-info",
    },
    green: {
        wrap: "bg-sem-success/15",
        icon: "text-sem-success",
    },
    orange: {
        wrap: "bg-sem-warning/15",
        icon: "text-sem-warning",
    },
    cyan: {
        wrap: "bg-sem-info/15 dark:bg-sem-info/15",
        icon: "text-sem-info dark:text-sem-info",
    },
    rose: {
        wrap: "bg-rose-100 dark:bg-rose-900/30",
        icon: "text-rose-600 text-sem-info",
    },
    violet: {
        wrap: "bg-sem-info/15 dark:bg-sem-info/15",
        icon: "text-sem-info dark:text-sem-info",
    },
    amber: {
        wrap: "bg-sem-warning/15",
        icon: "text-sem-warning",
    },
    sky: {
        wrap: "bg-sem-info/15",
        icon: "text-sem-info",
    },
    zinc: {
        wrap: "bg-sem-surface-muted",
        icon: "text-sem-fg-secondary text-sem-fg-muted",
    },
};

const props = withDefaults(
    defineProps<{
        icon: string;
        title: string;
        description?: string;
        eyebrow?: string;
        accent?: string;
        backTo?: string | Record<string, any>;
        backLabel?: string;
    }>(),
    {
        description: "",
        eyebrow: "",
        accent: "blue",
        backTo: "/tools",
        backLabel: "",
    }
);

const palette = computed(() => (ACCENT as Record<string, any>)[props.accent] || (ACCENT as Record<string, any>).blue);
const iconWrapClass = computed(() => palette.value.wrap);
const iconClass = computed(() => palette.value.icon);
const resolvedBackLabel = computed(() => props.backLabel || translateUi("app.tools"));
</script>
