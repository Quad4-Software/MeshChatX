<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute bottom-4 right-4 z-10 hidden sm:flex items-center gap-2 px-4 py-2 rounded-full border border-gray-200/50 dark:border-zinc-800/50 bg-white/70 dark:bg-zinc-900/70 backdrop-blur-xl"
    >
        <div class="flex items-center gap-1.5">
            <div class="w-3 h-3 rounded-full border-2 border-emerald-500 bg-emerald-500/20"></div>
            <span class="text-[10px] font-bold text-gray-600 dark:text-zinc-400 uppercase">Direct</span>
        </div>
        <div class="w-px h-3 bg-gray-200 dark:bg-zinc-800 mx-1"></div>
        <div class="flex items-center gap-1.5">
            <div class="w-3 h-3 rounded-full border-2 border-blue-500/50 bg-blue-500/10"></div>
            <span class="text-[10px] font-bold text-gray-600 dark:text-zinc-400 uppercase">Multi-Hop</span>
        </div>
        <div
            v-if="showDiscoveredInterfaces && discoveredCount > 0"
            class="w-px h-3 bg-gray-200 dark:bg-zinc-800 mx-1"
        ></div>
        <div v-if="showDiscoveredInterfaces && discoveredCount > 0" class="flex items-center gap-1.5">
            <div class="w-3 h-3 rounded-full border-2 border-cyan-500/50 bg-cyan-500/10"></div>
            <span class="text-[10px] font-bold text-gray-600 dark:text-zinc-400 uppercase"
                >Discovered ({{ discoveredCount }})</span
            >
        </div>
    </div>
</template>

<script>
export default {
    name: "NetworkVisualiserLegend",
    props: {
        showDiscoveredInterfaces: { type: Boolean, default: false },
        discoveredCount: { type: Number, default: 0 },
    },
};
</script>
