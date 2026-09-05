<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import MiniChat from "./MiniChat.svelte";
    import { getDiscoveredIconName } from "../lib/discoveredIcons.js";
    import { formatCoordinate } from "../../../js/mapGeoCoords.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        marker: Record<string, any>;
        miniChatOpen?: boolean;
        coordinateFormat?: string;
        geoWasmEpoch?: number;
        refLon?: number;
        refLat?: number;
        onclose?: () => void;
        ontoggletracking?: (hash: string) => void;
        ontoggleminichat?: () => void;
    }

    let {
        marker,
        miniChatOpen = false,
        coordinateFormat = "wgs84",
        geoWasmEpoch = 0,
        refLon = 0,
        refLat = 0,
        onclose,
        ontoggletracking,
        ontoggleminichat,
    }: Props = $props();

    let telemetryLocation = $derived.by(() => {
        const loc = marker?.telemetry?.telemetry?.location;
        if (!loc || typeof loc !== "object") return null;
        if (loc.latitude == null || loc.longitude == null) return null;
        return loc;
    });

    let formattedTelemetryCoords = $derived.by(() => {
        void geoWasmEpoch;
        const loc = telemetryLocation;
        if (!loc) return "";
        const res = formatCoordinate(loc.longitude, loc.latitude, coordinateFormat, {
            hasRef: true,
            refLat,
            refLon,
        });
        return res?.text || `${formatFixed(loc.latitude, 6)}, ${formatFixed(loc.longitude, 6)}`;
    });

    function shortHash(hash: string | undefined): string {
        const h = String(hash || "");
        return h ? h.substring(0, 8) : "Peer";
    }

    function formatFixed(value: any, digits: number): string {
        const n = Number(value);
        if (!Number.isFinite(n)) return "-";
        return n.toFixed(digits);
    }

    function formatTimestamp(ts: any): string {
        if (ts == null || !Number.isFinite(Number(ts))) return "-";
        return new Date(Number(ts) * 1000).toLocaleString();
    }
</script>

<div
    class="absolute bottom-4 left-4 right-4 sm:left-4 sm:right-auto sm:w-80 md:max-lg:w-72 lg:w-80 z-20 bg-sem-surface rounded-xl shadow-2xl border border-sem-border overflow-hidden text-sem-fg"
>
    <div class="p-4 border-b border-sem-border flex items-center justify-between">
        <div class="flex items-center gap-3">
            {#if marker.telemetry || marker.peer}
                <div
                    class="size-8 rounded-full flex items-center justify-center border-2"
                    style="color: {marker.peer?.lxmf_user_icon?.foreground_colour || '#3b82f6'}; border-color: {marker
                        .peer?.lxmf_user_icon?.foreground_colour || '#3b82f6'}; background-color: {marker.peer
                        ?.lxmf_user_icon?.background_colour || '#ffffff'};"
                >
                    <MaterialDesignIcon
                        iconName={marker.peer?.lxmf_user_icon?.icon_name || "account"}
                        class="size-[18px]"
                    />
                </div>
            {:else if marker.discovered}
                <div
                    class="size-8 rounded-full flex items-center justify-center border-2 border-emerald-500 bg-emerald-50 text-emerald-600"
                >
                    <MaterialDesignIcon iconName={getDiscoveredIconName(marker.discovered)} class="size-[18px]" />
                </div>
            {/if}
            <div>
                <h3 class="font-bold text-sem-fg truncate w-40">
                    {marker.discovered?.name ||
                        marker.peer?.display_name ||
                        shortHash(marker.telemetry?.destination_hash)}
                </h3>
                {#if marker.telemetry}
                    <div class="text-[10px] font-mono text-gray-500 uppercase tracking-tighter">
                        {marker.telemetry.destination_hash || ""}
                    </div>
                {:else if marker.discovered}
                    <div class="text-[10px] font-mono text-gray-500 uppercase tracking-tighter">
                        Discovered Interface
                    </div>
                {/if}
            </div>
        </div>
        <div class="flex items-center gap-1">
            {#if marker.telemetry}
                <button
                    type="button"
                    class="p-2 rounded-full transition-colors cursor-pointer {marker.telemetry.is_tracking
                        ? 'text-blue-500 bg-sem-surface-muted'
                        : 'text-sem-fg-muted hover:text-sem-fg'}"
                    title={marker.telemetry.is_tracking ? "Stop Tracking" : "Live Track Peer"}
                    onclick={() => ontoggletracking?.(marker.telemetry.destination_hash)}
                >
                    <MaterialDesignIcon
                        iconName={marker.telemetry.is_tracking ? "radar" : "crosshairs"}
                        class="size-5"
                    />
                </button>
            {/if}
            <button
                type="button"
                class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300 p-1 cursor-pointer"
                onclick={() => onclose?.()}
            >
                <MaterialDesignIcon iconName="close" class="size-5" />
            </button>
        </div>
    </div>
    <div class="p-4 space-y-3">
        {#if marker.discovered}
            <div class="space-y-3">
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Latitude</div>
                        <div class="tabular-nums">{formatFixed(marker.discovered.latitude, 6)}</div>
                    </div>
                    <div>
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Longitude</div>
                        <div class="tabular-nums">{formatFixed(marker.discovered.longitude, 6)}</div>
                    </div>
                </div>

                <div class="pt-2 border-t border-sem-border space-y-2">
                    {#if marker.discovered.interface}
                        <div class="flex justify-between items-center">
                            <span class="text-[10px] font-bold text-gray-400 uppercase">Interface</span>
                            <span class="text-xs font-mono">{marker.discovered.interface}</span>
                        </div>
                    {/if}
                    {#if marker.discovered.via}
                        <div class="flex justify-between items-center">
                            <span class="text-[10px] font-bold text-gray-400 uppercase">Via</span>
                            <span class="text-xs font-mono">{marker.discovered.via}</span>
                        </div>
                    {/if}
                    {#if marker.discovered.hops != null}
                        <div class="flex justify-between items-center">
                            <span class="text-[10px] font-bold text-gray-400 uppercase">Hops</span>
                            <span class="text-xs">{marker.discovered.hops}</span>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}

        {#if marker.telemetry}
            <div class="space-y-3">
                {#if telemetryLocation}
                    <div class="space-y-2 text-sm">
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                {t("map.coordinate_format")}
                            </div>
                            <div class="tabular-nums break-all">{formattedTelemetryCoords}</div>
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                    {t("map.coord_lat")}
                                </div>
                                <div class="tabular-nums">{formatFixed(telemetryLocation.latitude, 6)}</div>
                            </div>
                            <div>
                                <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                    {t("map.coord_lon")}
                                </div>
                                <div class="tabular-nums">{formatFixed(telemetryLocation.longitude, 6)}</div>
                            </div>
                            <div>
                                <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                    Altitude
                                </div>
                                <div class="tabular-nums">{formatFixed(telemetryLocation.altitude, 1)}m</div>
                            </div>
                            <div>
                                <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                    Speed
                                </div>
                                <div class="tabular-nums">{formatFixed(telemetryLocation.speed, 1)}km/h</div>
                            </div>
                        </div>
                    </div>
                {:else}
                    <div class="text-[11px] text-sem-fg-muted">Location unavailable</div>
                {/if}

                {#if marker.telemetry.physical_link}
                    <div class="pt-2 border-t border-sem-border">
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Signal</div>
                        <div class="flex gap-4 text-xs font-mono">
                            <span>RSSI: {marker.telemetry.physical_link.rssi}</span>
                            <span>SNR: {marker.telemetry.physical_link.snr}</span>
                            <span>Q: {marker.telemetry.physical_link.q}%</span>
                        </div>
                    </div>
                {/if}

                <div class="pt-2 text-[10px] text-gray-400 flex items-center gap-1">
                    <MaterialDesignIcon iconName="clock-outline" class="size-3" />
                    Updated: {formatTimestamp(marker.telemetry.timestamp)}
                </div>

                <div class="border-t border-sem-border pt-3">
                    <button
                        type="button"
                        class="w-full py-2 bg-gray-100 hover:bg-gray-200 dark:bg-zinc-800 hover:bg-sem-surface-muted text-sem-fg-muted rounded-lg font-bold transition-all text-sm flex items-center justify-center gap-2 mb-2 cursor-pointer"
                        onclick={() => ontoggleminichat?.()}
                    >
                        <MaterialDesignIcon iconName={miniChatOpen ? "chevron-up" : "message-text"} class="size-4" />
                        {miniChatOpen ? "Hide Mini-Chat" : "Show Mini-Chat"}
                    </button>
                    {#if miniChatOpen && marker.telemetry.destination_hash}
                        <MiniChat destinationHash={marker.telemetry.destination_hash} />
                    {/if}
                </div>
            </div>
        {/if}
    </div>
</div>
