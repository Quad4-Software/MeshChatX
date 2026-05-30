<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="flex flex-wrap items-center gap-x-2 gap-y-2 pl-1.5 pr-3 sm:pl-2 sm:pr-4 md:pl-4 md:pr-6 py-3 sm:py-4 border-b border-gray-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-950 shrink-0 min-w-0"
    >
        <RouterLink
            :to="backTo"
            class="inline-flex items-center justify-center gap-0.5 sm:gap-1 rounded-lg pl-0 pr-1.5 sm:pr-2 py-2 min-h-9 min-w-9 sm:min-w-0 text-sm font-medium text-gray-600 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-800/80 transition-colors shrink-0 order-first"
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
                <p v-if="eyebrow" class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 truncate">
                    {{ eyebrow }}
                </p>
                <h1 class="text-lg sm:text-xl font-bold text-gray-900 dark:text-white truncate">
                    {{ title }}
                </h1>
                <p
                    v-if="description"
                    class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 line-clamp-2 sm:line-clamp-none"
                >
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
        wrap: "bg-blue-100 dark:bg-blue-900/30",
        icon: "text-blue-600 dark:text-blue-400",
    },
    indigo: {
        wrap: "bg-indigo-100 dark:bg-indigo-900/30",
        icon: "text-indigo-600 dark:text-indigo-400",
    },
    teal: {
        wrap: "bg-teal-100 dark:bg-teal-900/30",
        icon: "text-teal-600 dark:text-teal-400",
    },
    purple: {
        wrap: "bg-purple-100 dark:bg-purple-900/30",
        icon: "text-purple-600 dark:text-purple-400",
    },
    green: {
        wrap: "bg-green-100 dark:bg-green-900/30",
        icon: "text-green-600 dark:text-green-400",
    },
    orange: {
        wrap: "bg-orange-100 dark:bg-orange-900/30",
        icon: "text-orange-600 dark:text-orange-400",
    },
    cyan: {
        wrap: "bg-cyan-100 dark:bg-cyan-900/30",
        icon: "text-cyan-600 dark:text-cyan-400",
    },
    rose: {
        wrap: "bg-rose-100 dark:bg-rose-900/30",
        icon: "text-rose-600 dark:text-rose-400",
    },
    violet: {
        wrap: "bg-violet-100 dark:bg-violet-900/30",
        icon: "text-violet-600 dark:text-violet-400",
    },
    amber: {
        wrap: "bg-amber-100 dark:bg-amber-900/30",
        icon: "text-amber-600 dark:text-amber-400",
    },
    sky: {
        wrap: "bg-sky-100 dark:bg-sky-900/30",
        icon: "text-sky-600 dark:text-sky-400",
    },
    zinc: {
        wrap: "bg-zinc-100 dark:bg-zinc-800",
        icon: "text-zinc-600 dark:text-zinc-400",
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
