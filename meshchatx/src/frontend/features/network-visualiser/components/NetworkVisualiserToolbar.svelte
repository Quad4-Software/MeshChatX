<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Toggle from "../../../ui/svelte/Toggle.svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";
    import NetworkVisualiserToolbarEngineSelect from "./NetworkVisualiserToolbarEngineSelect.svelte";
    import NetworkVisualiserToolbarHopFilter from "./NetworkVisualiserToolbarHopFilter.svelte";
    import NetworkVisualiserToolbarStats from "./NetworkVisualiserToolbarStats.svelte";
    import type { EngineMode, PreferredRenderer, ViewMode } from "../lib/types.js";

    interface Props {
        isShowingControls?: boolean;
        isUpdating?: boolean;
        isLoading?: boolean;
        autoReload?: boolean;
        enablePhysics?: boolean;
        hopMaxFilter?: number | null;
        nodeCount?: number;
        edgeCount?: number;
        onlineInterfaceCount?: number;
        offlineInterfaceCount?: number;
        searchQuery?: string;
        preferredRenderer?: PreferredRenderer;
        engineMode?: EngineMode;
        viewMode?: ViewMode;
        fps?: number;
        onmanualupdate?: () => void;
        onupdatehopmaxfilter?: (val: number | null) => void;
        onupdatepreferredrenderer?: (val: PreferredRenderer) => void;
        onupdateviewmode?: (val: ViewMode) => void;
    }

    let {
        isShowingControls = $bindable(true),
        isUpdating = false,
        isLoading = false,
        autoReload = $bindable(false),
        enablePhysics = $bindable(true),
        hopMaxFilter = 4,
        nodeCount = 0,
        edgeCount = 0,
        onlineInterfaceCount = 0,
        offlineInterfaceCount = 0,
        searchQuery = $bindable(""),
        preferredRenderer = "auto",
        engineMode = "checking",
        viewMode = "flat",
        fps = 0,
        onmanualupdate,
        onupdatehopmaxfilter,
        onupdatepreferredrenderer,
        onupdateviewmode,
    }: Props = $props();

    let fpsDisplay = $derived.by(() => {
        const n = Number(fps);
        if (!Number.isFinite(n) || n <= 0) return "--";
        return String(Math.round(n));
    });
</script>

<div
    class="absolute top-2 left-2 right-2 sm:top-4 sm:left-4 sm:right-4 z-10 flex flex-col sm:flex-row gap-2 pointer-events-none"
>
    <div
        class="pointer-events-auto border border-gray-200/50 dark:border-zinc-800/50 bg-white/90 dark:bg-zinc-900/90 rounded-2xl overflow-hidden w-full sm:w-[280px] sm:max-w-[280px] transition-all duration-300"
    >
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
            class="flex items-center px-4 sm:px-5 py-3 sm:py-4 cursor-pointer hover:bg-gray-50/50 dark:hover:bg-zinc-800/50 transition-colors"
            onclick={() => {
                isShowingControls = !isShowingControls;
            }}
        >
            <div class="flex-1 flex flex-col min-w-0 mr-2">
                <span class="font-bold text-sem-fg tracking-tight truncate">{t("visualiser.reticulum_mesh")}</span>
                <span class="text-[10px] uppercase font-bold text-sem-fg-muted tracking-widest truncate"
                    >{t("visualiser.network_visualizer")}</span
                >
            </div>
            <div class="flex items-center gap-2">
                <button
                    type="button"
                    class="inline-flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 text-white transition-all active:scale-95 disabled:opacity-60"
                    disabled={isUpdating || isLoading}
                    aria-label={t("visualiser.refresh")}
                    onclick={(e) => {
                        e.stopPropagation();
                        onmanualupdate?.();
                    }}
                >
                    <MaterialDesignIcon
                        iconName={isLoading ? "loading" : "refresh"}
                        class="w-4 h-4 sm:w-5 sm:h-5 {isLoading ? 'animate-spin' : ''}"
                    />
                </button>
                <div class="w-5 sm:w-6 flex justify-center">
                    <MaterialDesignIcon
                        iconName="chevron-down"
                        class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 transition-transform duration-300 {isShowingControls
                            ? 'rotate-180'
                            : ''}"
                    />
                </div>
            </div>
        </div>

        {#if isShowingControls}
            <div class="px-5 pb-5 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                <div class="h-px bg-linear-to-r from-transparent via-gray-200 dark:via-zinc-800 to-transparent"></div>

                <div class="grid grid-cols-2 gap-2">
                    <NetworkVisualiserToolbarEngineSelect
                        {preferredRenderer}
                        {engineMode}
                        {onupdatepreferredrenderer}
                    />
                    <div
                        class="min-w-0 rounded-xl px-3 py-2 border border-gray-100 dark:border-zinc-700/50 bg-gray-50/60 dark:bg-zinc-800/40"
                    >
                        <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-wider mb-0.5">
                            {t("visualiser.fps")}
                        </div>
                        <div class="text-xs font-bold text-sem-fg tabular-nums">
                            {fpsDisplay}
                        </div>
                    </div>
                </div>

                <div class="flex items-center justify-between">
                    <label for="auto-reload" class="text-sm font-semibold text-sem-fg-muted cursor-pointer">
                        {t("visualiser.auto_update")}
                    </label>
                    <Toggle id="auto-reload" bind:checked={autoReload} />
                </div>

                <div class="flex items-center justify-between">
                    <label for="enable-physics" class="text-sm font-semibold text-sem-fg-muted cursor-pointer">
                        {t("visualiser.live_layout")}
                    </label>
                    <Toggle id="enable-physics" bind:checked={enablePhysics} />
                </div>

                {#if engineMode === "webgl"}
                    <div class="flex items-center justify-between gap-2">
                        <span class="text-sm font-semibold text-sem-fg-muted">{t("visualiser.view_mode")}</span>
                        <div
                            class="inline-flex shrink-0 rounded-lg border border-gray-200 bg-gray-50 p-0.5 dark:border-zinc-700 dark:bg-zinc-800"
                            role="group"
                            aria-label={t("visualiser.view_mode")}
                        >
                            <button
                                id="visualiser-view-flat"
                                type="button"
                                class="rounded-md px-2.5 py-1 text-[11px] font-bold {viewMode === 'flat'
                                    ? 'bg-white text-blue-600 shadow-xs dark:bg-zinc-700 dark:text-blue-300'
                                    : 'text-sem-fg-muted'}"
                                aria-pressed={viewMode === "flat" ? "true" : "false"}
                                onclick={() => onupdateviewmode?.("flat")}
                            >
                                {t("visualiser.view_mode_flat")}
                            </button>
                            <button
                                id="visualiser-view-planet"
                                type="button"
                                class="rounded-md px-2.5 py-1 text-[11px] font-bold {viewMode === 'planet'
                                    ? 'bg-white text-blue-600 shadow-xs dark:bg-zinc-700 dark:text-blue-300'
                                    : 'text-sem-fg-muted'}"
                                aria-pressed={viewMode === "planet" ? "true" : "false"}
                                onclick={() => onupdateviewmode?.("planet")}
                            >
                                {t("visualiser.view_mode_planet")}
                            </button>
                        </div>
                    </div>
                {/if}

                <NetworkVisualiserToolbarHopFilter {hopMaxFilter} {onupdatehopmaxfilter} />

                <NetworkVisualiserToolbarStats {nodeCount} {edgeCount} {onlineInterfaceCount} {offlineInterfaceCount} />
            </div>
        {/if}
    </div>

    <div class="sm:ml-auto w-full sm:w-auto pointer-events-auto">
        <div class="relative group">
            <div
                class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400 group-focus-within:text-sem-accent transition-colors"
            >
                <MaterialDesignIcon iconName="magnify" class="w-4 h-4" />
            </div>
            <input
                bind:value={searchQuery}
                type="text"
                placeholder={t("visualiser.search_nodes_placeholder", { count: nodeCount })}
                class="block w-full sm:w-64 pl-9 pr-10 py-2.5 sm:py-3 bg-white/90 dark:bg-zinc-900/90 border border-gray-200/50 dark:border-zinc-800/50 rounded-2xl text-xs font-semibold focus:outline-hidden focus:ring-2 focus:ring-blue-500/50 sm:focus:w-80 md:max-lg:focus:w-72 lg:focus:w-80 transition-all text-sem-fg shadow-xs"
            />
            {#if searchQuery}
                <button
                    type="button"
                    class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 hover:text-sem-fg transition-colors"
                    aria-label={t("visualiser.clear_search")}
                    onclick={() => {
                        searchQuery = "";
                    }}
                >
                    <MaterialDesignIcon iconName="close" class="w-4 h-4" />
                </button>
            {/if}
        </div>
    </div>
</div>
