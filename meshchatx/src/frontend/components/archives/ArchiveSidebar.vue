<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex h-full shrink-0 flex-col overflow-hidden border-r border-sem-border bg-sem-canvas">
        <div class="flex items-center justify-between gap-2 border-b border-sem-border px-3 py-2.5">
            <h2 class="flex items-center gap-2 text-sm font-semibold text-sem-fg">
                <MaterialDesignIcon icon-name="server-network" class="size-4 text-sem-accent" />
                {{ $t("archives.nodes_title") }}
            </h2>
            <span class="rounded-full bg-sem-surface-muted px-2 py-0.5 text-xs font-medium text-sem-fg-muted">
                {{ nodes.length }}
            </span>
        </div>

        <div class="border-b border-sem-border p-2">
            <div class="relative">
                <MaterialDesignIcon
                    icon-name="magnify"
                    class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-sem-fg-muted"
                />
                <input
                    v-model="searchQuery"
                    type="text"
                    :placeholder="$t('archives.search_nodes_placeholder')"
                    class="w-full rounded-lg border border-sem-border bg-sem-canvas py-1.5 pl-9 pr-8 text-sm text-sem-fg placeholder:text-sem-fg-muted focus:border-sem-accent focus:outline-hidden focus:ring-2 focus:ring-sem-accent/20"
                    @input="$emit('update:search-query', searchQuery)"
                />
                <button
                    v-if="searchQuery"
                    type="button"
                    class="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-sem-fg-muted hover:text-sem-fg"
                    @click="clearSearch"
                >
                    <MaterialDesignIcon icon-name="close-circle" class="size-3.5" />
                </button>
            </div>
        </div>

        <div class="flex-1 overflow-y-auto">
            <div v-if="nodes.length === 0" class="flex flex-col items-center justify-center gap-2 p-8 text-center">
                <MaterialDesignIcon icon-name="archive-outline" class="size-10 text-sem-fg-muted opacity-40" />
                <p class="text-sm text-sem-fg-muted">
                    {{ searchQuery ? $t("archives.no_results") : $t("archives.no_archives") }}
                </p>
            </div>

            <button
                v-for="node in nodes"
                :key="node.destination_hash"
                type="button"
                class="flex w-full flex-col gap-1 border-b border-sem-border/50 px-3 py-2.5 text-left transition-colors hover:bg-sem-surface/50"
                :class="{
                    'bg-sem-surface/70 ring-1 ring-inset ring-sem-accent/30':
                        selectedNodeHash === node.destination_hash,
                }"
                @click="$emit('select-node', node)"
            >
                <div class="flex items-center justify-between gap-2">
                    <span
                        class="truncate text-sm font-medium"
                        :class="selectedNodeHash === node.destination_hash ? 'text-sem-accent' : 'text-sem-fg'"
                    >
                        {{ node.node_name || "Unknown Node" }}
                    </span>
                    <span class="shrink-0 text-xs text-sem-fg-muted">{{ node.archives.length }}</span>
                </div>
                <p class="truncate font-mono text-xs text-sem-fg-muted">{{ node.destination_hash }}</p>
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "ArchiveSidebar",
    components: {
        MaterialDesignIcon,
    },
    props: {
        nodes: {
            type: Array,
            required: true,
        },
        selectedNodeHash: {
            type: String,
            default: null,
        },
        initialSearchQuery: {
            type: String,
            default: "",
        },
    },
    emits: ["update:search-query", "select-node"],
    data() {
        return {
            searchQuery: this.initialSearchQuery,
        };
    },
    methods: {
        clearSearch() {
            this.searchQuery = "";
            this.$emit("update:search-query", "");
        },
    },
};
</script>
