<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute top-2 left-1/2 -translate-x-1/2 z-20 flex flex-col gap-2 transform-gpu w-max max-w-[98vw] sm:top-2"
    >
        <div
            class="bg-sem-surface rounded-2xl shadow-2xl overflow-hidden flex flex-row items-center p-0.5 sm:p-1 gap-0 sm:gap-0.5 border-0"
        >
            <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-gray-400">{{
                $t("map.toolbar_draw")
            }}</span>
            <button
                v-for="tool in tools"
                :key="tool.type"
                class="p-1.5 sm:p-2 rounded-xl transition-all hover:scale-110 active:scale-90"
                :class="
                    drawType === tool.type && !measuring && !bearingMode
                        ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                        : 'hover:bg-sem-surface-muted text-sem-fg-muted'
                "
                :title="$t(`map.tool_${tool.type.toLowerCase()}`)"
                @click="$emit('toggle-draw', tool.type)"
            >
                <MaterialDesignIcon :icon-name="tool.icon" class="size-[18px] sm:size-5!" />
            </button>
            <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
            <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-gray-400">{{
                $t("map.toolbar_measure")
            }}</span>
            <button
                class="p-1.5 sm:p-2 rounded-xl transition-all hover:scale-110 active:scale-90"
                :class="
                    measuring && !bearingMode
                        ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/30'
                        : 'hover:bg-sem-surface-muted text-sem-fg-muted'
                "
                :title="$t('map.tool_measure')"
                @click="$emit('toggle-measure')"
            >
                <MaterialDesignIcon icon-name="ruler" class="size-[18px] sm:size-5!" />
            </button>
            <button
                class="p-1.5 sm:p-2 rounded-xl transition-all hover:scale-110 active:scale-90"
                :class="
                    bearingMode
                        ? 'bg-teal-600 text-white shadow-lg shadow-teal-600/30'
                        : 'hover:bg-sem-surface-muted text-sem-fg-muted'
                "
                :title="$t('map.tool_bearing')"
                @click="$emit('toggle-bearing')"
            >
                <MaterialDesignIcon icon-name="compass-outline" class="size-[18px] sm:size-5!" />
            </button>
            <button
                class="p-1.5 sm:p-2 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 transition-all hover:scale-110 active:scale-90"
                :title="$t('map.tool_clear')"
                @click="$emit('clear')"
            >
                <MaterialDesignIcon icon-name="trash-can-outline" class="size-[18px] sm:size-5!" />
            </button>
            <button
                v-if="selectedFeature"
                class="p-1.5 sm:p-2 rounded-xl bg-blue-100 dark:bg-blue-900/30 text-blue-600 transition-all hover:scale-110 active:scale-90"
                :title="$t('map.edit_note')"
                @click="$emit('edit-note', selectedFeature)"
            >
                <MaterialDesignIcon icon-name="note-edit-outline" class="size-[18px] sm:size-5!" />
            </button>
            <button
                v-if="selectedFeature && !selectedFeature.get('telemetry')"
                class="p-1.5 sm:p-2 rounded-xl bg-red-100 dark:bg-red-900/30 text-red-600 transition-all hover:scale-110 active:scale-90 animate-pulse"
                :title="$t('map.delete_selected')"
                @click="$emit('delete-feature')"
            >
                <MaterialDesignIcon icon-name="selection-remove" class="size-[18px] sm:size-5!" />
            </button>
            <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
            <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-gray-400">{{
                $t("map.toolbar_files")
            }}</span>
            <button
                class="p-1.5 sm:p-2 rounded-xl hover:bg-sem-surface-muted text-gray-600 dark:text-gray-400 transition-all hover:scale-110 active:scale-90"
                :title="$t('map.save_drawing')"
                @click="$emit('save')"
            >
                <MaterialDesignIcon icon-name="content-save-outline" class="size-[18px] sm:size-5!" />
            </button>
            <button
                class="p-1.5 sm:p-2 rounded-xl hover:bg-sem-surface-muted text-gray-600 dark:text-gray-400 transition-all hover:scale-110 active:scale-90"
                :title="$t('map.load_drawing')"
                @click="$emit('load')"
            >
                <MaterialDesignIcon icon-name="folder-open-outline" class="size-[18px] sm:size-5!" />
            </button>
            <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
            <button
                class="p-1.5 sm:p-2 rounded-xl hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-500 transition-all hover:scale-110 active:scale-90"
                :title="$t('map.go_to_my_location')"
                @click="$emit('locate')"
            >
                <MaterialDesignIcon icon-name="crosshairs-gps" class="size-[18px] sm:size-5!" />
            </button>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../../MaterialDesignIcon.vue";

export default {
    name: "MapDrawingToolbar",
    components: {
        MaterialDesignIcon,
    },
    props: {
        tools: { type: Array, required: true },
        drawType: { type: String, default: null },
        measuring: { type: Boolean, default: false },
        bearingMode: { type: Boolean, default: false },
        bearingFromGps: { type: Boolean, default: false },
        exportMode: { type: Boolean, default: false },
        selectedFeature: { type: Object, default: null },
    },
    emits: [
        "toggle-draw",
        "toggle-measure",
        "toggle-bearing",
        "clear",
        "edit-note",
        "delete-feature",
        "save",
        "load",
        "locate",
    ],
};
</script>
