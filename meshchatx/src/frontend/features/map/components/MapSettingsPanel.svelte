<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import { t } from "../../../js/i18n.js";

    interface TrackedPeer {
        destination_hash: string;
        [key: string]: unknown;
    }

    interface Props {
        show?: boolean;
        offlineEnabled?: boolean;
        clusterMarkersEnabled?: boolean;
        tileServerUrl?: string;
        nominatimApiUrl?: string;
        trackedPeers?: TrackedPeer[];
        peers?: Record<string, any>;
        currentZoom?: number;
        displayCoords?: [number, number];
        formattedDisplayCoords?: string;
        coordinateFormat?: string;
        settingsPanelPos?: { left: number; top: number } | null;
        isMobileScreen?: boolean;
        onclose?: () => void;
        onsetasdefaultview?: () => void;
        ontogglecluster?: (enabled: boolean) => void;
        oncoordinateformatchange?: (format: string) => void;
        onsettileserver?: (styleId: string) => void;
        onsavetileserverurl?: (url: string) => void;
        onsavenominatimurl?: (url: string) => void;
        ontoggletracking?: (hash: string) => void;
        onupdatepanelpos?: (pos: { left: number; top: number }) => void;
    }

    let {
        show = false,
        offlineEnabled = false,
        clusterMarkersEnabled = $bindable(false),
        tileServerUrl = $bindable(""),
        nominatimApiUrl = $bindable(""),
        trackedPeers = [],
        peers = {},
        currentZoom = 0,
        displayCoords = [0, 0],
        formattedDisplayCoords = "",
        coordinateFormat = "wgs84",
        settingsPanelPos = null,
        isMobileScreen = false,
        onclose,
        onsetasdefaultview,
        ontogglecluster,
        oncoordinateformatchange,
        onsettileserver,
        onsavetileserverurl,
        onsavenominatimurl,
        ontoggletracking,
        onupdatepanelpos,
    }: Props = $props();

    let isDragging = $state(false);
    let dragStart = { x: 0, y: 0 };
    let initialPos = { left: 0, top: 0 };

    const tileStyles = [
        { id: "osm", label: "OSM" },
        { id: "openfreemap", label: "OFM" },
        { id: "carto-dark", label: "Dark" },
        { id: "carto-voyager", label: "Voy" },
        { id: "carto-light", label: "Lite" },
    ];

    function onPointerDown(e: PointerEvent) {
        if (isMobileScreen) return;
        isDragging = true;
        dragStart = { x: e.clientX, y: e.clientY };
        initialPos = settingsPanelPos || {
            left: Math.max(16, window.innerWidth - 336),
            top: 56,
        };
        (e.target as HTMLElement)?.setPointerCapture?.(e.pointerId);
    }

    function onPointerMove(e: PointerEvent) {
        if (!isDragging || isMobileScreen) return;
        const dx = e.clientX - dragStart.x;
        const dy = e.clientY - dragStart.y;
        const nextLeft = Math.max(8, Math.min(window.innerWidth - 328, initialPos.left + dx));
        const nextTop = Math.max(8, Math.min(window.innerHeight - 100, initialPos.top + dy));
        onupdatepanelpos?.({ left: nextLeft, top: nextTop });
    }

    function onPointerUp(e: PointerEvent) {
        if (!isDragging) return;
        isDragging = false;
        try {
            (e.target as HTMLElement)?.releasePointerCapture?.(e.pointerId);
        } catch {
            // best effort release
        }
    }
</script>

{#if show}
    <div
        class="absolute z-20 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xs rounded-xl shadow-2xl border border-sem-border overflow-hidden flex flex-col min-h-0 {isMobileScreen
            ? 'left-2 right-2 top-14 bottom-2 w-auto'
            : 'top-14 right-4 w-80 max-h-[min(36rem,calc(100%-4rem))]'}"
        style={!isMobileScreen && settingsPanelPos
            ? `left: ${settingsPanelPos.left}px; top: ${settingsPanelPos.top}px;`
            : undefined}
    >
        <div
            role="toolbar"
            tabindex="0"
            aria-label="Settings panel header"
            class="p-3 border-b border-sem-border flex items-center justify-between shrink-0 bg-gray-50/50 dark:bg-zinc-800/50 touch-none select-none cursor-grab active:cursor-grabbing"
            onpointerdown={onPointerDown}
            onpointermove={onPointerMove}
            onpointerup={onPointerUp}
            onpointercancel={onPointerUp}
        >
            <div class="flex items-center space-x-2">
                <MaterialDesignIcon iconName="cog" class="size-4 text-gray-500 dark:text-gray-300" />
                <h3 class="font-bold text-sem-fg text-xs uppercase tracking-widest">
                    {t("app.settings")}
                </h3>
            </div>
            <button
                type="button"
                class="p-1 hover:bg-gray-200 dark:hover:bg-zinc-800 rounded-lg transition-colors text-gray-500 dark:text-gray-300 cursor-pointer"
                onpointerdown={(e) => e.stopPropagation()}
                onclick={() => onclose?.()}
            >
                <MaterialDesignIcon iconName="close" class="size-4" />
            </button>
        </div>

        <div class="p-3 space-y-4 overflow-y-auto scrollbar-thin flex-1">
            <div class="grid grid-cols-2 gap-2">
                <button
                    type="button"
                    class="flex items-center justify-center space-x-1.5 px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 cursor-pointer"
                    onclick={() => onsetasdefaultview?.()}
                >
                    <MaterialDesignIcon iconName="pin" class="size-3" />
                    <span>{t("map.set_as_default")}</span>
                </button>
                <label
                    class="flex items-center justify-center space-x-1.5 px-2 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-zinc-800 text-sem-fg-muted rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight cursor-pointer select-none"
                >
                    <input
                        bind:checked={clusterMarkersEnabled}
                        type="checkbox"
                        class="rounded-sm"
                        onchange={(e) => ontogglecluster?.((e.target as HTMLInputElement).checked)}
                    />
                    <span>{t("map.cluster_markers")}</span>
                </label>
            </div>

            <details class="space-y-2 group" open={!offlineEnabled}>
                <summary
                    class="flex items-center justify-between cursor-pointer list-none text-[10px] font-bold text-gray-400 uppercase tracking-widest select-none"
                >
                    <span>{t("map.online_sources")}</span>
                    <MaterialDesignIcon
                        iconName="chevron-down"
                        class="size-4 transition-transform group-open:rotate-180"
                    />
                </summary>
                <div class="space-y-2 pt-1">
                    <p class="text-[9px] text-sem-fg-muted leading-snug">
                        {t("map.online_sources_hint")}
                    </p>
                    <div class="grid grid-cols-5 gap-1">
                        {#each tileStyles as style (style.id)}
                            <button
                                type="button"
                                class="py-1.5 text-[8px] font-bold uppercase rounded-md transition-all border leading-tight cursor-pointer {(style.id ===
                                    'openfreemap' &&
                                    tileServerUrl.includes('tiles.openfreemap.org/styles/')) ||
                                (style.id === 'osm' && tileServerUrl.includes('openstreetmap.org')) ||
                                (style.id === 'carto-dark' &&
                                    tileServerUrl.includes('basemaps.cartocdn.com/dark_all')) ||
                                (style.id === 'carto-voyager' && tileServerUrl.includes('rastertiles/voyager')) ||
                                (style.id === 'carto-light' &&
                                    tileServerUrl.includes('basemaps.cartocdn.com/light_all'))
                                    ? 'bg-blue-500 border-blue-600 text-white shadow-xs ring-2 ring-blue-500/20'
                                    : 'bg-sem-surface border-sem-border text-sem-fg-muted hover:bg-sem-surface-muted'}"
                                onclick={() => onsettileserver?.(style.id)}
                            >
                                {style.label}
                            </button>
                        {/each}
                    </div>

                    <div class="space-y-1">
                        <label
                            for="map-tile-url-input"
                            class="text-[9px] font-bold text-sem-fg-muted uppercase flex items-center"
                        >
                            <MaterialDesignIcon iconName="link-variant" class="size-3 mr-1" />
                            Tile Server URL
                        </label>
                        <input
                            id="map-tile-url-input"
                            bind:value={tileServerUrl}
                            type="text"
                            class="w-full bg-gray-50/50 dark:bg-zinc-950/50 border border-sem-border rounded-lg px-2 py-1.5 text-[10px] text-sem-fg font-mono focus:ring-1 focus:ring-blue-500 transition-all outline-hidden"
                            placeholder={t("map.tile_server_url_placeholder")}
                            onblur={() => onsavetileserverurl?.(tileServerUrl)}
                        />
                    </div>

                    <div class="space-y-1">
                        <label
                            for="map-nominatim-url-input"
                            class="text-[9px] font-bold text-sem-fg-muted uppercase flex items-center"
                        >
                            <MaterialDesignIcon iconName="magnify" class="size-3 mr-1" />
                            Geocoder API
                        </label>
                        <input
                            id="map-nominatim-url-input"
                            bind:value={nominatimApiUrl}
                            type="text"
                            class="w-full bg-gray-50/50 dark:bg-zinc-950/50 border border-sem-border rounded-lg px-2 py-1.5 text-[10px] text-sem-fg font-mono focus:ring-1 focus:ring-blue-500 transition-all outline-hidden"
                            placeholder={t("map.nominatim_api_url_placeholder")}
                            onblur={() => onsavenominatimurl?.(nominatimApiUrl)}
                        />
                    </div>
                </div>
            </details>

            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest"> Live Tracking </span>
                    <div class="h-px flex-1 bg-sem-surface-muted ml-3"></div>
                </div>
                {#if trackedPeers.length === 0}
                    <div class="text-[10px] text-gray-500 italic px-2">No peers currently being tracked.</div>
                {:else}
                    <div class="space-y-1">
                        {#each trackedPeers as peer (peer.destination_hash)}
                            <div
                                class="flex items-center justify-between p-2 bg-gray-50 dark:bg-zinc-800/50 rounded-lg group"
                            >
                                <div class="flex flex-col min-w-0">
                                    <span class="text-[10px] font-bold text-sem-fg truncate">
                                        {peers[peer.destination_hash]?.display_name ||
                                            peer.destination_hash.substring(0, 8)}
                                    </span>
                                    <span class="text-[8px] text-gray-500 font-mono">
                                        {peer.destination_hash}
                                    </span>
                                </div>
                                <button
                                    type="button"
                                    class="p-1 text-red-400 hover:text-red-600 transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
                                    title="Stop Tracking"
                                    onclick={() => ontoggletracking?.(peer.destination_hash)}
                                >
                                    <MaterialDesignIcon iconName="close-circle" class="size-3" />
                                </button>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>

        <div class="p-2.5 bg-gray-50 dark:bg-zinc-800/50 border-t border-sem-border shrink-0 space-y-2">
            <label class="flex items-center justify-between gap-2">
                <span class="text-[10px] font-semibold text-sem-fg-muted uppercase tracking-wide">
                    {t("map.coordinate_format")}
                </span>
                <select
                    class="input-field py-1 px-2 text-[11px] min-w-0 max-w-[9rem]"
                    value={coordinateFormat}
                    onchange={(e) => oncoordinateformatchange?.((e.currentTarget as HTMLSelectElement).value)}
                >
                    <option value="wgs84">{t("map.coord_format_wgs84")}</option>
                    <option value="utm">{t("map.coord_format_utm")}</option>
                    <option value="mgrs">{t("map.coord_format_mgrs")}</option>
                    <option value="olc">{t("map.coord_format_olc")}</option>
                </select>
            </label>
            <div class="grid grid-cols-3 gap-2">
                <div class="flex flex-col items-center">
                    <span class="text-[8px] font-black text-gray-400 uppercase tracking-tighter mb-0.5"> Zoom </span>
                    <span class="text-[10px] font-bold text-sem-fg-muted leading-none tabular-nums">
                        {currentZoom.toFixed(1)}
                    </span>
                </div>
                <div class="flex flex-col items-center border-x border-sem-border col-span-2 px-1">
                    <span class="text-[8px] font-black text-gray-400 uppercase tracking-tighter mb-0.5">
                        {t("map.coordinate_format")}
                    </span>
                    <span
                        class="text-[9px] font-bold text-sem-fg-muted leading-tight tabular-nums text-center break-all"
                    >
                        {coordinateFormat === "wgs84"
                            ? `${displayCoords[1].toFixed(4)}, ${displayCoords[0].toFixed(4)}`
                            : formattedDisplayCoords}
                    </span>
                </div>
            </div>
        </div>
    </div>
{/if}
