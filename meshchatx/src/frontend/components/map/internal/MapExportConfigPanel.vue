<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute top-0 mt-14 left-1/2 -translate-x-1/2 z-20 w-80 bg-sem-surface rounded-xl shadow-2xl border border-sem-border overflow-hidden text-sem-fg"
    >
        <div class="p-4 border-b border-sem-border flex items-center justify-between">
            <h3 class="font-semibold text-sem-fg">{{ $t("map.export_area") }}</h3>
            <button
                class="text-sem-fg-muted hover:text-sem-fg dark:hover:text-sem-fg-secondary"
                @click="$emit('cancel')"
            >
                <MaterialDesignIcon icon-name="close" class="size-5" />
            </button>
        </div>
        <div class="p-4 space-y-4">
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-sem-fg-muted uppercase mb-1">{{
                        $t("map.min_zoom")
                    }}</label>
                    <input
                        :value="minZoom"
                        type="number"
                        min="0"
                        max="20"
                        class="w-full bg-sem-surface-muted border border-sem-border rounded-lg px-3 py-2 text-sm text-sem-fg"
                        @input="$emit('update:minZoom', Number($event.target.value))"
                    />
                </div>
                <div>
                    <label class="block text-xs font-bold text-sem-fg-muted uppercase mb-1">{{
                        $t("map.max_zoom")
                    }}</label>
                    <input
                        :value="maxZoom"
                        type="number"
                        min="0"
                        max="20"
                        class="w-full bg-sem-surface-muted border border-sem-border rounded-lg px-3 py-2 text-sm text-sem-fg"
                        @input="$emit('update:maxZoom', Number($event.target.value))"
                    />
                </div>
            </div>
            <div class="flex justify-between items-center text-sm">
                <span class="text-sem-fg-muted">{{ $t("map.tile_count") }}:</span>
                <span class="font-bold text-sem-info">{{ estimatedTiles }}</span>
            </div>
            <p v-if="tileLimitExceeded" class="text-xs text-sem-danger font-semibold">
                {{ $t("map.export_tile_limit_exceeded") }}
            </p>
            <div class="flex gap-2">
                <button
                    :disabled="exporting"
                    class="flex-1 py-2 bg-sem-surface-muted hover:bg-gray-300 bg-sem-surface dark:hover:bg-zinc-600 disabled:bg-gray-100 dark:disabled:bg-sem-surface text-sem-fg rounded-lg font-bold transition-colors"
                    @click="$emit('cancel')"
                >
                    {{ $t("common.cancel") }}
                </button>
                <button
                    :disabled="exporting || tileLimitExceeded"
                    class="flex-1 py-2 bg-sem-info hover:bg-sem-action-primary disabled:bg-blue-300 text-sem-action-primary-text rounded-lg font-bold transition-colors shadow-md"
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
