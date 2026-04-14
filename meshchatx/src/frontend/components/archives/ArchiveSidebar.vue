<template>
    <div
        class="flex h-full shrink-0 flex-col overflow-hidden border-r border-gray-200 bg-white dark:border-zinc-800 dark:bg-zinc-950"
    >
        <!-- Sidebar Header -->
        <div class="flex items-center justify-between border-b border-gray-200 p-4 dark:border-zinc-800">
            <h2
                class="text-xs font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest flex items-center gap-2"
            >
                <MaterialDesignIcon icon-name="server-network" class="size-4" />
                Nodes
            </h2>
            <div class="text-[10px] font-bold text-gray-400 dark:text-zinc-500">
                {{ nodes.length }}
            </div>
        </div>

        <!-- Search Bar -->
        <div class="border-b border-gray-200 bg-white p-2 dark:border-zinc-800 dark:bg-zinc-950">
            <div class="relative">
                <MaterialDesignIcon
                    icon-name="magnify"
                    class="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-gray-400 dark:text-zinc-500 pointer-events-none"
                />
                <input
                    v-model="searchQuery"
                    type="text"
                    placeholder="Search nodes or content..."
                    class="w-full pl-9 pr-3 py-1.5 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg text-xs text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                    @input="$emit('update:search-query', searchQuery)"
                />
                <button
                    v-if="searchQuery"
                    class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:text-zinc-500 dark:hover:text-zinc-300 p-0.5"
                    @click="clearSearch"
                >
                    <MaterialDesignIcon icon-name="close-circle" class="size-3.5" />
                </button>
            </div>
        </div>

        <!-- Node List -->
        <div class="flex-1 overflow-y-auto">
            <div v-if="nodes.length === 0" class="p-8 text-center">
                <p class="text-xs text-gray-500 dark:text-gray-400">
                    {{ searchQuery ? "No results found" : "No archives" }}
                </p>
            </div>

            <button
                v-for="node in nodes"
                :key="node.destination_hash"
                class="w-full text-left px-4 py-3 border-b border-gray-50 dark:border-zinc-800/50 hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors group"
                :class="{ 'bg-blue-50 dark:bg-blue-900/20': selectedNodeHash === node.destination_hash }"
                @click="$emit('select-node', node)"
            >
                <div class="flex items-center justify-between mb-1">
                    <span
                        class="text-sm font-bold text-gray-900 dark:text-white truncate"
                        :class="{ 'text-blue-600 dark:text-blue-400': selectedNodeHash === node.destination_hash }"
                    >
                        {{ node.node_name || "Unknown Node" }}
                    </span>
                    <span class="text-[10px] font-bold text-gray-400 dark:text-zinc-500">
                        {{ node.archives.length }}
                    </span>
                </div>
                <p class="text-[10px] font-mono text-gray-500 dark:text-zinc-500 truncate">
                    {{ node.destination_hash }}
                </p>
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
