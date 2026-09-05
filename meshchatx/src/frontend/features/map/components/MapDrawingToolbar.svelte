<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface DrawingTool {
        type: string;
        icon: string;
    }

    interface Props {
        tools: DrawingTool[];
        drawType?: string | null;
        measuring?: boolean;
        bearingMode?: boolean;
        bearingFromGps?: boolean;
        exportMode?: boolean;
        selectedFeature?: any;
        ontoggledraw?: (type: string) => void;
        ontogglemeasure?: () => void;
        ontogglebearing?: () => void;
        onclear?: () => void;
        oneditnote?: (feat: any) => void;
        ondeletefeature?: () => void;
        onsave?: () => void;
        onload?: () => void;
        onlocate?: () => void;
    }

    let {
        tools,
        drawType = null,
        measuring = false,
        bearingMode = false,
        bearingFromGps: _bearingFromGps = false,
        exportMode: _exportMode = false,
        selectedFeature = null,
        ontoggledraw,
        ontogglemeasure,
        ontogglebearing,
        onclear,
        oneditnote,
        ondeletefeature,
        onsave,
        onload,
        onlocate,
    }: Props = $props();
</script>

<div
    class="absolute top-2 left-1/2 -translate-x-1/2 z-20 flex flex-col gap-2 transform-gpu w-max max-w-[98vw] sm:top-2"
>
    <div
        class="bg-sem-surface rounded-2xl shadow-2xl overflow-hidden flex flex-row items-center p-0.5 sm:p-1 gap-0 sm:gap-0.5 border-0"
    >
        <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-gray-400">
            {t("map.toolbar_draw")}
        </span>
        {#each tools as tool (tool.type)}
            <button
                type="button"
                class="p-1.5 sm:p-2 rounded-xl transition-all hover:scale-110 active:scale-90 cursor-pointer {drawType ===
                    tool.type &&
                !measuring &&
                !bearingMode
                    ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                    : 'hover:bg-sem-surface-muted text-sem-fg-muted'}"
                title={t(`map.tool_${tool.type.toLowerCase()}`)}
                onclick={() => ontoggledraw?.(tool.type)}
            >
                <MaterialDesignIcon iconName={tool.icon} class="size-[18px] sm:size-5!" />
            </button>
        {/each}
        <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
        <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-gray-400">
            {t("map.toolbar_measure")}
        </span>
        <button
            type="button"
            class="p-1.5 sm:p-2 rounded-xl transition-all hover:scale-110 active:scale-90 cursor-pointer {measuring &&
            !bearingMode
                ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/30'
                : 'hover:bg-sem-surface-muted text-sem-fg-muted'}"
            title={t("map.tool_measure")}
            onclick={() => ontogglemeasure?.()}
        >
            <MaterialDesignIcon iconName="ruler" class="size-[18px] sm:size-5!" />
        </button>
        <button
            type="button"
            class="p-1.5 sm:p-2 rounded-xl transition-all hover:scale-110 active:scale-90 cursor-pointer {bearingMode
                ? 'bg-teal-600 text-white shadow-lg shadow-teal-600/30'
                : 'hover:bg-sem-surface-muted text-sem-fg-muted'}"
            title={t("map.tool_bearing")}
            onclick={() => ontogglebearing?.()}
        >
            <MaterialDesignIcon iconName="compass-outline" class="size-[18px] sm:size-5!" />
        </button>
        <button
            type="button"
            class="p-1.5 sm:p-2 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 transition-all hover:scale-110 active:scale-90 cursor-pointer"
            title={t("map.tool_clear")}
            onclick={() => onclear?.()}
        >
            <MaterialDesignIcon iconName="trash-can-outline" class="size-[18px] sm:size-5!" />
        </button>
        {#if selectedFeature}
            <button
                type="button"
                class="p-1.5 sm:p-2 rounded-xl bg-blue-100 dark:bg-blue-900/30 text-blue-600 transition-all hover:scale-110 active:scale-90 cursor-pointer"
                title={t("map.edit_note")}
                onclick={() => oneditnote?.(selectedFeature)}
            >
                <MaterialDesignIcon iconName="note-edit-outline" class="size-[18px] sm:size-5!" />
            </button>
        {/if}
        {#if selectedFeature && typeof selectedFeature.get === "function" && !selectedFeature.get("telemetry")}
            <button
                type="button"
                class="p-1.5 sm:p-2 rounded-xl bg-red-100 dark:bg-red-900/30 text-red-600 transition-all hover:scale-110 active:scale-90 animate-pulse cursor-pointer"
                title={t("map.delete_selected")}
                onclick={() => ondeletefeature?.()}
            >
                <MaterialDesignIcon iconName="selection-remove" class="size-[18px] sm:size-5!" />
            </button>
        {/if}
        <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
        <span class="hidden md:inline px-1 text-[9px] font-semibold uppercase tracking-wide text-gray-400">
            {t("map.toolbar_files")}
        </span>
        <button
            type="button"
            class="p-1.5 sm:p-2 rounded-xl hover:bg-sem-surface-muted text-gray-600 dark:text-gray-400 transition-all hover:scale-110 active:scale-90 cursor-pointer"
            title={t("map.save_drawing")}
            onclick={() => onsave?.()}
        >
            <MaterialDesignIcon iconName="content-save-outline" class="size-[18px] sm:size-5!" />
        </button>
        <button
            type="button"
            class="p-1.5 sm:p-2 rounded-xl hover:bg-sem-surface-muted text-gray-600 dark:text-gray-400 transition-all hover:scale-110 active:scale-90 cursor-pointer"
            title={t("map.load_drawing")}
            onclick={() => onload?.()}
        >
            <MaterialDesignIcon iconName="folder-open-outline" class="size-[18px] sm:size-5!" />
        </button>
        <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
        <button
            type="button"
            class="p-1.5 sm:p-2 rounded-xl hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-500 transition-all hover:scale-110 active:scale-90 cursor-pointer"
            title={t("map.go_to_my_location")}
            onclick={() => onlocate?.()}
        >
            <MaterialDesignIcon iconName="crosshairs-gps" class="size-[18px] sm:size-5!" />
        </button>
    </div>
</div>
