<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div :class="tool.iconBg">
        <MaterialDesignIcon v-if="tool.icon" :icon-name="tool.icon" class="w-6 h-6" />
        <img v-else-if="tool.image" :src="tool.image" :class="tool.imageClass" :alt="tool.imageAlt" />
    </div>
    <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
            <div class="tool-card__title">{{ tool.title }}</div>
            <span
                v-if="tool.alpha"
                class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-sem-info/15 dark:bg-sem-info/15 text-sem-info dark:text-sem-info rounded-sm border border-sem-info dark:border-sem-info"
            >
                {{ $t("tools.alpha_badge") }}
            </span>
            <span
                v-if="tool.beta"
                class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-sem-warning/15 text-sem-warning rounded-sm border border-sem-warning dark:border-sem-warning"
            >
                {{ $t("tools.beta_badge") }}
            </span>
            <span
                v-if="tool.comingSoon"
                class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-sem-surface-muted text-sem-fg-muted rounded-sm border border-sem-border"
            >
                {{ $t("tools.coming_soon_badge") }}
            </span>
        </div>
        <div class="tool-card__description">{{ tool.description }}</div>
    </div>
    <div v-if="!tool.comingSoon" class="shrink-0 flex items-center gap-1">
        <div v-if="tool.extraAction" class="flex items-center gap-2">
            <a
                :href="tool.extraAction.href"
                :target="tool.extraAction.target"
                class="p-2 hover:bg-sem-surface-muted rounded-lg transition-colors text-sem-fg-muted hover:text-sem-info"
                @click.stop
            >
                <MaterialDesignIcon :icon-name="tool.extraAction.icon" class="size-5" />
            </a>
            <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
        </div>
        <MaterialDesignIcon v-else icon-name="chevron-right" class="tool-card__chevron" />
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "ToolListRow",
    components: {
        MaterialDesignIcon,
    },
    props: {
        tool: {
            type: Object,
            required: true,
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.tool-card__icon {
    @apply w-11 h-11 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center shrink-0;
}
.tool-card__title {
    @apply text-base sm:text-lg font-semibold text-sem-fg;
}
.tool-card__description {
    @apply text-sm text-sem-fg-muted mt-0.5 line-clamp-2 sm:line-clamp-none;
}
.tool-card__chevron {
    @apply w-5 h-5 text-sem-fg-muted shrink-0;
}
</style>
