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
                <template v-if="groupedToolSections">
                    <div
                        v-for="section in groupedToolSections"
                        :key="section.id"
                        class="mb-6 rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950"
                    >
                        <div
                            class="px-4 py-3 border-b border-gray-200 dark:border-zinc-800 text-xs font-bold uppercase tracking-widest text-gray-500 dark:text-zinc-400"
                        >
                            {{ $t(`tools.group.${section.id}`) }}
                        </div>
                        <div
                            class="grid grid-cols-1 lg:grid-cols-2 divide-y divide-gray-200 dark:divide-zinc-800 divide-x-0 lg:divide-x lg:divide-y"
                        >
                            <RouterLink
                                v-for="tool in section.tools"
                                :key="tool.name"
                                :to="tool.comingSoon ? '' : tool.route"
                                :class="toolRowClass(tool)"
                                @click="tool.comingSoon ? $event.preventDefault() : null"
                            >
                                <ToolListRow :tool="tool" />
                            </RouterLink>
                        </div>
                    </div>
                </template>

                <div
                    v-else-if="filteredTools.length > 0"
                    class="rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950"
                >
                    <div
                        class="grid grid-cols-1 lg:grid-cols-2 divide-y divide-gray-200 dark:divide-zinc-800 divide-x-0 lg:divide-x lg:divide-y"
                    >
                        <RouterLink
                            v-for="tool in filteredTools"
                            :key="tool.name"
                            :to="tool.comingSoon ? '' : tool.route"
                            :class="toolRowClass(tool)"
                            @click="tool.comingSoon ? $event.preventDefault() : null"
                        >
                            <ToolListRow :tool="tool" />
                        </RouterLink>
                    </div>
                </div>

                <EmptyState
                    v-if="filteredTools.length === 0"
                    class="mt-6"
                    icon="magnify"
                    :title="$t('common.no_results')"
                />
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import EmptyState from "../EmptyState.vue";
import ToolListRow from "./ToolListRow.vue";
import { listTools } from "../../js/registries/toolsRegistry.js";

const TOOL_GROUP_ORDER = ["diagnostics", "transfer", "messaging", "network", "other"];

export default {
    name: "ToolsPage",
    components: {
        MaterialDesignIcon,
        EmptyState,
        ToolListRow,
    },
    data() {
        return {
            searchQuery: "",
        };
    },
    computed: {
        tools() {
            return listTools();
        },
        toolsWithTranslations() {
            return this.tools.map((tool) => ({
                ...tool,
                title: tool.title || (tool.titleKey ? this.$t(tool.titleKey) : ""),
                description: tool.description || (tool.descriptionKey ? this.$t(tool.descriptionKey) : ""),
            }));
        },
        filteredTools() {
            if (!this.searchQuery.trim()) {
                return this.toolsWithTranslations;
            }

            const query = this.searchQuery.toLowerCase().trim();
            return this.toolsWithTranslations.filter((tool) => {
                return (
                    tool.title.toLowerCase().includes(query) ||
                    tool.description.toLowerCase().includes(query) ||
                    tool.name.toLowerCase().includes(query)
                );
            });
        },
        groupedToolSections() {
            if (this.searchQuery.trim()) {
                return null;
            }
            const groups = {};
            for (const tool of this.filteredTools) {
                const groupId = tool.group || "other";
                if (!groups[groupId]) {
                    groups[groupId] = [];
                }
                groups[groupId].push(tool);
            }
            return TOOL_GROUP_ORDER.filter((groupId) => groups[groupId]?.length).map((groupId) => ({
                id: groupId,
                tools: groups[groupId],
            }));
        },
    },
    methods: {
        toolRowClass(tool) {
            return [
                "tool-row",
                tool.customClass,
                tool.comingSoon ? "opacity-60 grayscale-[0.5] cursor-default" : "",
            ].filter(Boolean);
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
</style>
