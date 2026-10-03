<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="flex flex-wrap items-center gap-x-2 gap-y-2 pl-1.5 pr-3 sm:pl-2 sm:pr-4 md:pl-4 md:pr-6 py-3 sm:py-4 border-b border-sem-border bg-sem-canvas shrink-0 min-w-0"
    >
        <RouterLink
            :to="backTo"
            class="inline-flex items-center justify-center gap-0.5 sm:gap-1 rounded-lg pl-0 pr-1.5 sm:pr-2 py-2 min-h-9 min-w-9 sm:min-w-0 text-sm font-medium text-sem-fg-muted hover:bg-sem-surface-muted transition-colors shrink-0 order-first"
            :aria-label="$t('tools.back_to_tools')"
        >
            <MaterialDesignIcon icon-name="chevron-left" class="size-6 sm:size-5 shrink-0" />
            <span class="hidden sm:inline truncate max-w-[8rem]">{{ resolvedBackLabel }}</span>
        </RouterLink>

        <div class="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 basis-0">
            <div class="p-2 rounded-lg shrink-0" :class="iconWrapClass">
                <MaterialDesignIcon :icon-name="icon" class="size-5 sm:size-6" :class="iconClass" />
            </div>
            <div class="min-w-0">
                <p v-if="eyebrow" class="text-xs uppercase tracking-wide text-sem-fg-muted truncate">
                    {{ eyebrow }}
                </p>
                <h1 class="text-lg sm:text-xl font-bold text-sem-fg truncate">
                    {{ title }}
                </h1>
                <p v-if="description" class="text-xs sm:text-sm text-sem-fg-muted line-clamp-2 sm:line-clamp-none">
                    {{ description }}
                </p>
            </div>
        </div>

        <div v-if="$slots.actions" class="flex items-center gap-2 shrink-0 ml-auto">
            <slot name="actions" />
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

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

export default {
    name: "ToolsPageHeader",
    components: { MaterialDesignIcon },
    props: {
        icon: { type: String, required: true },
        title: { type: String, required: true },
        description: { type: String, default: "" },
        eyebrow: { type: String, default: "" },
        accent: {
            type: String,
            default: "blue",
            validator: (v) => Object.prototype.hasOwnProperty.call(ACCENT, v),
        },
        backTo: { type: [String, Object], default: "/tools" },
        backLabel: { type: String, default: "" },
    },
    computed: {
        palette() {
            return ACCENT[this.accent] || ACCENT.blue;
        },
        iconWrapClass() {
            return this.palette.wrap;
        },
        iconClass() {
            return this.palette.icon;
        },
        resolvedBackLabel() {
            return this.backLabel || this.$t("app.tools");
        },
    },
};
</script>
