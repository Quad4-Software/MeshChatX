<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute top-0 mt-14 left-1/2 -translate-x-1/2 z-20 w-80 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden text-gray-900 dark:text-zinc-100"
    >
        <div class="p-4 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between">
            <h3 class="font-semibold text-gray-900 dark:text-zinc-100">{{ $t("map.export_area") }}</h3>
            <button class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300" @click="$emit('cancel')">
                <MaterialDesignIcon icon-name="close" class="size-5" />
            </button>
        </div>
        <div class="p-4 space-y-4">
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{ $t("map.min_zoom") }}</label>
                    <input
                        :value="minZoom"
                        type="number"
                        min="0"
                        max="20"
                        class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm dark:text-zinc-100"
                        @input="$emit('update:minZoom', Number($event.target.value))"
                    />
                </div>
                <div>
                    <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{ $t("map.max_zoom") }}</label>
                    <input
                        :value="maxZoom"
                        type="number"
                        min="0"
                        max="20"
                        class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm dark:text-zinc-100"
                        @input="$emit('update:maxZoom', Number($event.target.value))"
                    />
                </div>
            </div>
            <div class="flex justify-between items-center text-sm">
                <span class="text-gray-600 dark:text-zinc-400">{{ $t("map.tile_count") }}:</span>
                <span class="font-bold text-blue-600">{{ estimatedTiles }}</span>
            </div>
            <p v-if="tileLimitExceeded" class="text-xs text-red-600 dark:text-red-400 font-semibold">
                {{ $t("map.export_tile_limit_exceeded") }}
            </p>
            <div class="flex gap-2">
                <button
                    :disabled="exporting"
                    class="flex-1 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-zinc-700 dark:hover:bg-zinc-600 disabled:bg-gray-100 dark:disabled:bg-zinc-800 text-gray-900 dark:text-zinc-100 rounded-lg font-bold transition-colors"
                    @click="$emit('cancel')"
                >
                    {{ $t("common.cancel") }}
                </button>
                <button
                    :disabled="exporting || tileLimitExceeded"
                    class="flex-1 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg font-bold transition-colors shadow-md"
                    @click="$emit('start')"
                >
                    {{ $t("map.start_export") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapExportConfigPanel",
    components: { MaterialDesignIcon },
    props: {
        minZoom: { type: Number, required: true },
        maxZoom: { type: Number, required: true },
        estimatedTiles: { type: [Number, String], default: 0 },
        exporting: { type: Boolean, default: false },
        tileLimitExceeded: { type: Boolean, default: false },
    },
    emits: ["cancel", "start", "update:minZoom", "update:maxZoom"],
};
</script>
