<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute bottom-4 left-4 right-4 sm:left-4 sm:right-auto sm:w-80 md:max-lg:w-72 lg:w-80 z-20 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden text-gray-900 dark:text-zinc-100"
    >
        <div class="p-4 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div
                    class="size-8 rounded-full flex items-center justify-center bg-blue-600 text-white text-sm font-bold"
                >
                    {{ cluster.count }}
                </div>
                <div>
                    <h3 class="font-bold text-gray-900 dark:text-zinc-100">{{ cluster.count }} interfaces here</h3>
                    <div class="text-[10px] font-mono text-gray-500 uppercase tracking-tighter">
                        Tap an item to focus
                    </div>
                </div>
            </div>
            <button
                class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300 p-1"
                title="Close"
                @click="$emit('close')"
            >
                <v-icon icon="mdi-close" size="20"></v-icon>
            </button>
        </div>
        <div class="max-h-72 overflow-y-auto divide-y divide-gray-100 dark:divide-zinc-800">
            <button
                v-for="(item, idx) in cluster.items"
                :key="idx"
                class="w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors"
                @click="$emit('select', item)"
            >
                <div
                    v-if="item.kind === 'discovered'"
                    class="size-7 rounded-full flex items-center justify-center border-2 border-emerald-500 bg-emerald-50 text-emerald-600 shrink-0"
                >
                    <MaterialDesignIcon :icon-name="getDiscoveredIconName(item.iconKey)" class="size-[14px]" />
                </div>
                <div
                    v-else-if="item.kind === 'telemetry'"
                    class="size-7 rounded-full flex items-center justify-center border-2 border-blue-500 bg-blue-50 text-blue-600 shrink-0"
                >
                    <v-icon :icon="'mdi-' + (item.peer?.lxmf_user_icon?.icon_name || 'account')" size="14"></v-icon>
                </div>
                <div
                    v-else
                    class="size-7 rounded-full flex items-center justify-center border-2 border-gray-400 bg-gray-50 text-gray-500 shrink-0"
                >
                    <v-icon icon="mdi-help" size="14"></v-icon>
                </div>
                <div class="min-w-0 flex-1">
                    <div class="text-sm font-medium truncate">{{ item.label }}</div>
                    <div v-if="item.identifier" class="text-[10px] font-mono text-gray-500 truncate">
                        {{ item.identifier }}
                    </div>
                </div>
                <v-icon icon="mdi-chevron-right" size="16" class="text-gray-400 shrink-0"></v-icon>
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";
import { getDiscoveredIconName } from "./discoveredIcons.js";

export default {
    name: "MapClusterPanel",
    components: { MaterialDesignIcon },
    props: {
        cluster: {
            type: Object,
            required: true,
        },
    },
    emits: ["close", "select"],
    methods: {
        getDiscoveredIconName,
    },
};
</script>
