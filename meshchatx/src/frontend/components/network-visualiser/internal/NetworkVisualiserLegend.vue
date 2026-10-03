<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute bottom-4 right-4 z-10 hidden sm:flex items-center gap-2 px-4 py-2 rounded-full border border-sem-border dark:border-sem-border bg-sem-surface dark:bg-sem-surface"
    >
        <div class="flex items-center gap-1.5">
            <div class="w-3 h-3 rounded-full border-2 border-sem-success bg-sem-warning/15"></div>
            <span class="text-[10px] font-bold text-sem-fg-muted uppercase">Direct</span>
        </div>
        <div class="w-px h-3 bg-sem-surface-muted mx-1"></div>
        <div class="flex items-center gap-1.5">
            <div class="w-3 h-3 rounded-full border-2 border-blue-500/50 bg-sem-warning/15"></div>
            <span class="text-[10px] font-bold text-sem-fg-muted uppercase">Multi-Hop</span>
        </div>
        <div v-if="showDiscoveredInterfaces && discoveredCount > 0" class="w-px h-3 bg-sem-surface-muted mx-1"></div>
        <div v-if="showDiscoveredInterfaces && discoveredCount > 0" class="flex items-center gap-1.5">
            <div class="w-3 h-3 rounded-full border-2 border-cyan-500/50 bg-sem-warning/15"></div>
            <span class="text-[10px] font-bold text-sem-fg-muted uppercase">Discovered ({{ discoveredCount }})</span>
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
