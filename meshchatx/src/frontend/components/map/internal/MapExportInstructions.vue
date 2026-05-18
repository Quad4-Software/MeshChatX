<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="absolute inset-x-0 top-0 mt-14 z-20 flex justify-center px-2 pointer-events-none">
        <div class="flex flex-col items-center gap-2 max-w-[min(100vw-2rem,36rem)] w-full pointer-events-auto">
            <div
                class="px-4 py-2 bg-blue-600 text-white rounded-full shadow-lg font-medium text-sm animate-bounce text-center"
            >
                {{ $t("map.export_instructions") }}
            </div>
            <div v-if="presets && presets.length" class="flex flex-wrap justify-center gap-2 pointer-events-auto">
                <button
                    v-for="p in presets"
                    :key="p.id"
                    type="button"
                    class="px-2 py-1 text-[10px] font-bold uppercase tracking-tight rounded-lg bg-white/95 dark:bg-zinc-900/95 border border-gray-200 dark:border-zinc-700 text-gray-800 dark:text-zinc-100 shadow-xs hover:bg-gray-50 dark:hover:bg-zinc-800"
                    @click="$emit('select-preset', p)"
                >
                    {{ $t(`map.export_region_${p.id}`) }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    name: "MapExportInstructions",
    props: {
        presets: { type: Array, default: () => [] },
    },
    emits: ["select-preset"],
};
</script>
