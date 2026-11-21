<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        class="absolute top-2 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2 transform-gpu w-max max-w-[calc(100%-7rem)]"
    >
        <div
            class="bg-sem-surface rounded-2xl shadow-2xl max-w-full flex flex-row flex-wrap items-center justify-center p-0.5 sm:p-1 gap-0 sm:gap-0.5 border-0"
        >
            <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-sem-fg-muted">{{
                $t("map.toolbar_draw")
            }}</span>
            <button
                v-for="tool in tools"
                :key="tool.type"
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center transition-all hover:scale-110 active:scale-90"
                :class="
                    drawType === tool.type && !measuring && !bearingMode
                        ? 'bg-sem-action-primary text-sem-action-primary-text shadow-lg shadow-sem-action-primary/30'
                        : 'hover:bg-sem-surface-muted text-sem-fg-muted'
                "
                :title="$t(`map.tool_${tool.type.toLowerCase()}`)"
                @click="$emit('toggle-draw', tool.type)"
            >
                <MaterialDesignIcon :icon-name="tool.icon" class="size-[18px] sm:size-5!" />
            </button>
            <div class="w-px h-6 bg-sem-surface-muted my-auto mx-0.5 sm:mx-1"></div>
            <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-sem-fg-muted">{{
                $t("map.toolbar_measure")
            }}</span>
            <button
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center transition-all hover:scale-110 active:scale-90"
                :class="
                    measuring && !bearingMode
                        ? 'bg-sem-action-primary text-sem-action-primary-text shadow-lg shadow-sem-action-primary/30'
                        : 'hover:bg-sem-surface-muted text-sem-fg-muted'
                "
                :title="$t('map.tool_measure')"
                @click="$emit('toggle-measure')"
            >
                <MaterialDesignIcon icon-name="ruler" class="size-[18px] sm:size-5!" />
            </button>
            <button
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center transition-all hover:scale-110 active:scale-90"
                :class="
                    bearingMode
                        ? 'bg-sem-success text-white shadow-lg shadow-teal-600/30'
                        : 'hover:bg-sem-surface-muted text-sem-fg-muted'
                "
                :title="$t('map.tool_bearing')"
                @click="$emit('toggle-bearing')"
            >
                <MaterialDesignIcon icon-name="compass-outline" class="size-[18px] sm:size-5!" />
            </button>
            <button
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center hover:bg-sem-danger/15 dark:hover:bg-sem-danger/15 text-sem-danger transition-all hover:scale-110 active:scale-90"
                :title="$t('map.tool_clear')"
                @click="$emit('clear')"
            >
                <MaterialDesignIcon icon-name="trash-can-outline" class="size-[18px] sm:size-5!" />
            </button>
            <button
                v-if="selectedFeature"
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center bg-sem-info/15 text-sem-info transition-all hover:scale-110 active:scale-90"
                :title="$t('map.edit_note')"
                @click="$emit('edit-note', selectedFeature)"
            >
                <MaterialDesignIcon icon-name="note-edit-outline" class="size-[18px] sm:size-5!" />
            </button>
            <button
                v-if="selectedFeature && !selectedFeature.get('telemetry')"
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center bg-sem-danger/15 text-sem-danger transition-all hover:scale-110 active:scale-90 animate-pulse"
                :title="$t('map.delete_selected')"
                @click="$emit('delete-feature')"
            >
                <MaterialDesignIcon icon-name="selection-remove" class="size-[18px] sm:size-5!" />
            </button>
            <div class="w-px h-6 bg-sem-surface-muted my-auto mx-0.5 sm:mx-1"></div>
            <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-sem-fg-muted">{{
                $t("map.toolbar_files")
            }}</span>
            <button
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center hover:bg-sem-surface-muted text-sem-fg-muted transition-all hover:scale-110 active:scale-90"
                :title="$t('map.save_drawing')"
                @click="$emit('save')"
            >
                <MaterialDesignIcon icon-name="content-save-outline" class="size-[18px] sm:size-5!" />
            </button>
            <button
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center hover:bg-sem-surface-muted text-sem-fg-muted transition-all hover:scale-110 active:scale-90"
                :title="$t('map.load_drawing')"
                @click="$emit('load')"
            >
                <MaterialDesignIcon icon-name="folder-open-outline" class="size-[18px] sm:size-5!" />
            </button>
            <div class="w-px h-6 bg-sem-surface-muted my-auto mx-0.5 sm:mx-1"></div>
            <button
                class="min-h-11 min-w-11 p-1.5 sm:p-2 rounded-xl inline-flex items-center justify-center hover:bg-sem-info/15 dark:hover:bg-sem-info/15 text-sem-info transition-all hover:scale-110 active:scale-90"
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
