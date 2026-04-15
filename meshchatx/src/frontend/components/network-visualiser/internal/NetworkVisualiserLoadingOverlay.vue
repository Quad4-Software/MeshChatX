<template>
    <div
        v-if="isLoading"
        class="absolute inset-0 z-20 flex items-center justify-center bg-zinc-950/10 backdrop-blur-[2px] transition-all duration-300"
    >
        <div
            class="bg-white/90 dark:bg-zinc-900/90 border border-gray-200 dark:border-zinc-800 rounded-2xl px-6 py-4 flex flex-col items-center gap-3"
        >
            <div class="relative">
                <div class="w-12 h-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
                <div class="absolute inset-0 flex items-center justify-center">
                    <div
                        class="w-6 h-6 border-4 border-emerald-500/20 border-b-emerald-500 rounded-full animate-spin-reverse"
                    ></div>
                </div>
            </div>
            <div class="text-sm font-medium text-gray-900 dark:text-zinc-100">{{ loadingStatus }}</div>
            <div v-if="totalNodesToLoad > 0" class="w-48 space-y-2">
                <div class="h-1.5 bg-gray-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                    <div
                        class="h-full bg-blue-500 transition-all duration-300 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                        :style="{ width: `${(loadedNodesCount / totalNodesToLoad) * 100}%` }"
                    ></div>
                </div>
                <div
                    v-if="totalBatches > 0"
                    class="flex justify-between items-center text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider"
                >
                    <span>{{ $t("visualiser.batch") }} {{ currentBatch }} / {{ totalBatches }}</span>
                    <span>{{ Math.round((loadedNodesCount / totalNodesToLoad) * 100) }}%</span>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "NetworkVisualiserLoadingOverlay",
    props: {
        isLoading: { type: Boolean, default: false },
        loadingStatus: { type: String, default: "" },
        totalNodesToLoad: { type: Number, default: 0 },
        loadedNodesCount: { type: Number, default: 0 },
        currentBatch: { type: Number, default: 0 },
        totalBatches: { type: Number, default: 0 },
    },
};
</script>
