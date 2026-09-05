<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MapDiscoverPanel from "./MapDiscoverPanel.svelte";
    import MapPublishPanel from "./MapPublishPanel.svelte";
    import MapLayersPanel from "./MapLayersPanel.svelte";
    import MapOfflinePanel from "./MapOfflinePanel.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        drawSource?: any;
        hasVectorDrawFeatures?: boolean;
        mapReady?: boolean;
        offlineEnabled?: boolean;
        cachingEnabled?: boolean;
        mbtilesList?: any[];
        mbtilesDir?: string;
        hasOfflineMap?: boolean;
        initialTab?: string;
        announceListenEnabled?: boolean;
        announceListenBusy?: boolean;
        onOverlaysChanged?: (overlays?: any[]) => void;
        onImportFeatures?: (detail: { features: any[]; merge: boolean }) => void;
        onImportError?: (err: any) => void;
        onExportGeojson?: () => void;
        onExportKml?: () => void;
        onExportKmz?: () => void;
        onExportGpx?: () => void;
        onExportOverlay?: (detail: { id: string | number; format: string }) => void;
        onCopyOverlayToDrawings?: (overlay: any) => void;
        onOverlayError?: (err: any) => void;
        onToggleOffline?: (val: boolean) => void;
        onToggleCaching?: (val: boolean) => void;
        onUploadMbtiles?: () => void;
        onSetActiveMbtiles?: (name: string) => void;
        onDeleteMbtiles?: (name: string) => void;
        onSaveMbtilesDir?: (dir: string) => void;
        onClearCache?: () => void;
        onExportRegion?: () => void;
        onRestoreStarter?: () => void;
        onToggleAnnounceListen?: (val: boolean) => void;
    }

    let {
        drawSource = null,
        hasVectorDrawFeatures = false,
        mapReady = false,
        offlineEnabled = false,
        cachingEnabled = true,
        mbtilesList = [],
        mbtilesDir = "",
        hasOfflineMap = false,
        initialTab = "discover",
        announceListenEnabled = false,
        announceListenBusy = false,
        onOverlaysChanged,
        onImportFeatures,
        onImportError,
        onExportGeojson,
        onExportKml,
        onExportKmz,
        onExportGpx,
        onExportOverlay,
        onCopyOverlayToDrawings,
        onOverlayError,
        onToggleOffline,
        onToggleCaching,
        onUploadMbtiles,
        onSetActiveMbtiles,
        onDeleteMbtiles,
        onSaveMbtilesDir,
        onClearCache,
        onExportRegion,
        onRestoreStarter,
        onToggleAnnounceListen,
    }: Props = $props();

    let activeTab = $state(initialTab || "discover");

    const tabs = [
        { id: "discover", labelKey: "map.tab_discover" },
        { id: "publish", labelKey: "map.tab_publish" },
        { id: "layers", labelKey: "map.tab_layers" },
        { id: "offline", labelKey: "map.tab_offline" },
    ] as const;
</script>

<div class="flex flex-col h-full min-h-0">
    <div class="flex border-b border-sem-border shrink-0">
        {#each tabs as tab (tab.id)}
            <button
                type="button"
                class="flex-1 px-2 py-2 text-[11px] font-semibold transition-colors cursor-pointer {activeTab === tab.id
                    ? 'text-sem-accent border-b-2 border-blue-500'
                    : 'text-sem-fg-muted hover:text-sem-fg'}"
                onclick={() => {
                    activeTab = tab.id;
                }}
            >
                {t(tab.labelKey)}
            </button>
        {/each}
    </div>
    <div class="flex-1 min-h-0 overflow-y-auto p-3">
        {#if activeTab === "discover"}
            <MapDiscoverPanel
                listenEnabled={announceListenEnabled}
                onoverlayschanged={onOverlaysChanged}
                onenablelisten={() => onToggleAnnounceListen?.(true)}
            />
        {:else if activeTab === "publish"}
            <MapPublishPanel {drawSource} />
        {:else if activeTab === "layers"}
            <MapLayersPanel
                disabled={!drawSource}
                hasFeatures={hasVectorDrawFeatures}
                {mapReady}
                {announceListenEnabled}
                {announceListenBusy}
                {onImportFeatures}
                {onImportError}
                {onExportGeojson}
                {onExportKml}
                {onExportKmz}
                {onExportGpx}
                {onOverlaysChanged}
                {onExportOverlay}
                {onCopyOverlayToDrawings}
                onError={onOverlayError}
                {onToggleAnnounceListen}
            />
        {:else if activeTab === "offline"}
            <MapOfflinePanel
                {offlineEnabled}
                {cachingEnabled}
                {mbtilesList}
                {mbtilesDir}
                {hasOfflineMap}
                {onToggleOffline}
                {onToggleCaching}
                onUpload={onUploadMbtiles}
                onSetActive={onSetActiveMbtiles}
                onDeleteFile={onDeleteMbtiles}
                onSaveDir={onSaveMbtilesDir}
                {onClearCache}
                {onExportRegion}
                {onRestoreStarter}
            />
        {/if}
    </div>
</div>
