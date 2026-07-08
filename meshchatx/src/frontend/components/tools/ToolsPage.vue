<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
            <div class="border-b border-gray-200 dark:border-zinc-800 px-4 py-4 md:px-6 md:py-5">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between lg:gap-6">
                    <div class="space-y-2 min-w-0 flex-1">
                        <div class="text-2xl md:text-3xl font-black text-gray-900 dark:text-white tracking-tight">
                            {{ $t("tools.power_tools") }}
                        </div>
                        <div class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed max-w-xl">
                            {{ $t("tools.diagnostics_description") }}
                        </div>
                    </div>

                    <div class="w-full lg:max-w-sm shrink-0">
                        <div class="relative group">
                            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <MaterialDesignIcon
                                    icon-name="magnify"
                                    class="size-5 text-gray-400 group-focus-within:text-blue-500 transition-colors"
                                />
                            </div>
                            <input
                                v-model="searchQuery"
                                type="text"
                                :placeholder="$t('common.search')"
                                class="w-full pl-10 pr-10 py-3 bg-gray-50 dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 text-sm"
                            />
                            <button
                                v-if="searchQuery"
                                class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                                type="button"
                                @click="searchQuery = ''"
                            >
                                <MaterialDesignIcon icon-name="close-circle" class="size-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="p-4 md:p-6 xl:p-8 w-full max-w-6xl xl:max-w-7xl 2xl:max-w-384 mx-auto">
                <div
                    class="rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950"
                >
                    <div
                        class="grid grid-cols-1 lg:grid-cols-2 divide-y divide-gray-200 dark:divide-zinc-800 divide-x-0 lg:divide-x lg:divide-y"
                    >
                        <RouterLink
                            v-for="tool in filteredTools"
                            :key="tool.name"
                            :to="tool.comingSoon ? '' : tool.route"
                            :class="
                                [
                                    'tool-row',
                                    tool.customClass,
                                    tool.comingSoon ? 'opacity-60 grayscale-[0.5] cursor-default' : '',
                                ].filter(Boolean)
                            "
                            @click="tool.comingSoon ? $event.preventDefault() : null"
                        >
                            <div :class="tool.iconBg">
                                <MaterialDesignIcon v-if="tool.icon" :icon-name="tool.icon" class="w-6 h-6" />
                                <img
                                    v-else-if="tool.image"
                                    :src="tool.image"
                                    :class="tool.imageClass"
                                    :alt="tool.imageAlt"
                                />
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2 flex-wrap">
                                    <div class="tool-card__title">{{ tool.title }}</div>
                                    <span
                                        v-if="tool.alpha"
                                        class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 rounded-sm border border-violet-200 dark:border-violet-800"
                                    >
                                        {{ $t("tools.alpha_badge") }}
                                    </span>
                                    <span
                                        v-if="tool.beta"
                                        class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-sm border border-amber-200 dark:border-amber-800"
                                    >
                                        {{ $t("tools.beta_badge") }}
                                    </span>
                                    <span
                                        v-if="tool.comingSoon"
                                        class="px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-gray-100 dark:bg-zinc-800 text-gray-500 dark:text-gray-400 rounded-sm border border-gray-200 dark:border-zinc-700"
                                    >
                                        Soon
                                    </span>
                                </div>
                                <div class="tool-card__description">
                                    {{ tool.description }}
                                </div>
                            </div>
                            <div v-if="!tool.comingSoon" class="shrink-0 flex items-center gap-1">
                                <div v-if="tool.extraAction" class="flex items-center gap-2">
                                    <a
                                        :href="tool.extraAction.href"
                                        :target="tool.extraAction.target"
                                        class="p-2 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-lg transition-colors text-gray-400 hover:text-blue-500"
                                        @click.stop
                                    >
                                        <MaterialDesignIcon :icon-name="tool.extraAction.icon" class="size-5" />
                                    </a>
                                    <MaterialDesignIcon icon-name="chevron-right" class="tool-card__chevron" />
                                </div>
                                <MaterialDesignIcon v-else icon-name="chevron-right" class="tool-card__chevron" />
                            </div>
                        </RouterLink>
                    </div>
                </div>

                <div
                    v-if="filteredTools.length === 0"
                    class="mt-6 rounded-lg border border-dashed border-gray-300 dark:border-zinc-700 px-4 py-12 text-center"
                >
                    <MaterialDesignIcon icon-name="magnify" class="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    <div class="text-gray-600 dark:text-gray-400">{{ $t("common.no_results") }}</div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import { listTools } from "../../js/registries/toolsRegistry.js";

export default {
    name: "ToolsPage",
    components: {
        MaterialDesignIcon,
    },
    data() {
        return {
            rnodeLogoPath: "/rnode-flasher/reticulum_logo_512.png",
            searchQuery: "",
        };
    },
    computed: {
        tools() {
            return listTools();
        },
        filteredTools() {
            const toolsWithTranslations = this.tools.map((tool) => ({
                ...tool,
                title: tool.title || (tool.titleKey ? this.$t(tool.titleKey) : ""),
                description: tool.description || (tool.descriptionKey ? this.$t(tool.descriptionKey) : ""),
            }));

            if (!this.searchQuery.trim()) {
                return toolsWithTranslations;
            }

            const query = this.searchQuery.toLowerCase().trim();
            return toolsWithTranslations.filter((tool) => {
                return (
                    tool.title.toLowerCase().includes(query) ||
                    tool.description.toLowerCase().includes(query) ||
                    tool.name.toLowerCase().includes(query)
                );
            });
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.tool-row {
    @apply flex items-start sm:items-center gap-3 sm:gap-4 px-4 py-3.5 min-h-17 transition-colors;
    @apply hover:bg-gray-50 dark:hover:bg-zinc-900/80 active:bg-gray-100 dark:active:bg-zinc-800/80;
}
.tool-card__icon {
    @apply w-11 h-11 sm:w-12 sm:h-12 rounded-xl flex items-center justify-center shrink-0;
}
.tool-card__title {
    @apply text-base sm:text-lg font-semibold text-gray-900 dark:text-white;
}
.tool-card__description {
    @apply text-sm text-gray-600 dark:text-gray-300 mt-0.5 line-clamp-2 sm:line-clamp-none;
}
.tool-card__chevron {
    @apply w-5 h-5 text-gray-400 shrink-0;
}
</style>
