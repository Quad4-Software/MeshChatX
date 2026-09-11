<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <div class="flex-1 overflow-y-auto w-full pb-[max(1rem,env(safe-area-inset-bottom))]">
            <div class="border-b border-sem-border px-4 py-4 md:px-6 md:py-5">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between lg:gap-6">
                    <div class="space-y-2 min-w-0 flex-1">
                        <div class="text-2xl md:text-3xl font-black text-sem-fg tracking-tight">
                            {{ $t("tools.power_tools") }}
                        </div>
                        <div class="text-sm text-sem-fg-muted leading-relaxed max-w-xl">
                            {{ $t("tools.diagnostics_description") }}
                        </div>
                    </div>

                    <div class="w-full lg:max-w-sm shrink-0">
                        <SearchInput v-model="searchQuery" :placeholder="$t('common.search')" />
                    </div>
                </div>
            </div>

            <div class="p-4 md:p-6 xl:p-8 w-full max-w-6xl xl:max-w-7xl 2xl:max-w-384 mx-auto">
                <template v-if="groupedToolSections">
                    <div
                        v-for="section in groupedToolSections"
                        :key="section.id"
                        class="mb-6 rounded-lg overflow-hidden border border-sem-border bg-sem-surface"
                    >
                        <button
                            type="button"
                            class="flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-xs font-bold uppercase tracking-widest text-sem-fg-muted transition-colors hover:bg-sem-surface-muted/60"
                            :aria-expanded="!isGroupCollapsed(section.id)"
                            @click="toggleGroup(section.id)"
                        >
                            <span class="flex items-center gap-2">
                                {{ $t(`tools.group.${section.id}`) }}
                                <span
                                    class="rounded-full bg-sem-surface-muted px-1.5 py-0.5 text-[10px] font-semibold normal-case tracking-normal"
                                    >{{ section.tools.length }}</span
                                >
                            </span>
                            <MaterialDesignIcon
                                icon-name="chevron-down"
                                class="size-4 shrink-0 transition-transform"
                                :class="{ '-rotate-90': isGroupCollapsed(section.id) }"
                            />
                        </button>
                        <div
                            v-show="!isGroupCollapsed(section.id)"
                            class="border-t border-sem-border grid grid-cols-1 lg:grid-cols-2 divide-y divide-sem-border divide-x-0 lg:divide-x lg:divide-y"
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
                    class="rounded-lg overflow-hidden border border-sem-border bg-sem-surface"
                >
                    <div
                        class="grid grid-cols-1 lg:grid-cols-2 divide-y divide-sem-border divide-x-0 lg:divide-x lg:divide-y"
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
import SearchInput from "../SearchInput.vue";
import EmptyState from "../EmptyState.vue";
import ToolListRow from "./ToolListRow.vue";
import { listTools } from "../../js/registries/toolsRegistry.js";

const TOOL_GROUP_ORDER = ["diagnostics", "transfer", "messaging", "network", "other"];
const COLLAPSED_GROUPS_KEY = "meshchatx.tools.collapsedGroups";

function loadCollapsedGroups() {
    try {
        const raw = localStorage.getItem(COLLAPSED_GROUPS_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        return new Set(Array.isArray(parsed) ? parsed : []);
    } catch {
        return new Set();
    }
}

export default {
    name: "ToolsPage",
    components: {
        MaterialDesignIcon,
        SearchInput,
        EmptyState,
        ToolListRow,
    },
    data() {
        return {
            searchQuery: "",
            collapsedGroups: loadCollapsedGroups(),
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
        isGroupCollapsed(groupId) {
            return this.collapsedGroups.has(groupId);
        },
        toggleGroup(groupId) {
            const next = new Set(this.collapsedGroups);
            if (next.has(groupId)) {
                next.delete(groupId);
            } else {
                next.add(groupId);
            }
            this.collapsedGroups = next;
            try {
                localStorage.setItem(COLLAPSED_GROUPS_KEY, JSON.stringify([...next]));
            } catch {
                /* storage unavailable */
            }
        },
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
    @apply hover:bg-sem-surface-muted active:bg-sem-surface-muted;
}
</style>
