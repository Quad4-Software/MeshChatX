<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import MapSidePanel from "./MapSidePanel.svelte";
    import { t } from "../../../js/i18n.js";
    import type { MBTilesEntry } from "../lib/types.js";

    interface Props {
        isOpen?: boolean;
        drawSource?: any;
        hasVectorDrawFeatures?: boolean;
        mapReady?: boolean;
        offlineEnabled?: boolean;
        cachingEnabled?: boolean;
        mbtilesList?: MBTilesEntry[];
        mbtilesDir?: string;
        hasOfflineMap?: boolean;
        announceListenEnabled?: boolean;
        announceListenBusy?: boolean;
        ontoggleoffline?: (val: boolean) => void;
        ontogglecaching?: (val: boolean) => void;
        onsetactivembtiles?: (name: string) => void;
        ondeletembtiles?: (name: string) => void;
        onsavembtilesdir?: (dir: string) => void;
        onclearcache?: () => void;
        onexportregion?: () => void;
        onstartexport?: () => void;
        onrestorestarter?: () => void;
        onuploadmbtiles?: () => void;
        onimportfeatures?: (detail: { features: any[]; merge: boolean }) => void;
        onimporterror?: (err: any) => void;
        onexportgeojson?: () => void;
        onexportkml?: () => void;
        onexportkmz?: () => void;
        onexportgpx?: () => void;
        onoverlayschanged?: (overlays?: any[]) => void;
        onexportoverlay?: (detail: { id: string | number; format: string }) => void;
        oncopyoverlaytodrawings?: (overlay: any) => void;
        onoverlayerror?: (err: any) => void;
        ontoggleannouncelisten?: (val: boolean) => void;
        onclose?: () => void;
    }

    let {
        isOpen = false,
        drawSource = null,
        hasVectorDrawFeatures = false,
        mapReady = false,
        offlineEnabled = false,
        cachingEnabled = true,
        mbtilesList = [],
        mbtilesDir = "",
        hasOfflineMap = false,
        announceListenEnabled = false,
        announceListenBusy = false,
        ontoggleoffline,
        ontogglecaching,
        onsetactivembtiles,
        ondeletembtiles,
        onsavembtilesdir,
        onclearcache,
        onexportregion,
        onstartexport: _onstartexport,
        onrestorestarter,
        onuploadmbtiles,
        onimportfeatures,
        onimporterror,
        onexportgeojson,
        onexportkml,
        onexportkmz,
        onexportgpx,
        onoverlayschanged,
        onexportoverlay,
        oncopyoverlaytodrawings,
        onoverlayerror,
        ontoggleannouncelisten,
        onclose,
    }: Props = $props();
</script>

{#if isOpen}
    <div
        class="absolute z-20 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xs rounded-xl shadow-2xl border border-sem-border overflow-hidden flex flex-col min-h-0 top-14 right-4 w-96 max-h-[min(36rem,calc(100%-4rem))]"
    >
        <div class="p-3 border-b border-sem-border flex items-center justify-between shrink-0">
            <h3 class="font-bold text-sem-fg text-xs uppercase tracking-widest">
                {t("map.side_panel")}
            </h3>
            <button
                type="button"
                class="p-1 hover:bg-gray-200 dark:hover:bg-zinc-800 rounded-lg cursor-pointer"
                onclick={onclose}
            >
                <MaterialDesignIcon iconName="close" class="size-4" />
            </button>
        </div>
        <div class="flex-1 min-h-0 overflow-y-auto">
            <MapSidePanel
                {drawSource}
                {hasVectorDrawFeatures}
                {mapReady}
                {offlineEnabled}
                {cachingEnabled}
                {mbtilesList}
                {mbtilesDir}
                {hasOfflineMap}
                {announceListenEnabled}
                {announceListenBusy}
                onOverlaysChanged={onoverlayschanged}
                onImportFeatures={onimportfeatures}
                onImportError={onimporterror}
                onExportGeojson={onexportgeojson}
                onExportKml={onexportkml}
                onExportKmz={onexportkmz}
                onExportGpx={onexportgpx}
                onExportOverlay={onexportoverlay}
                onCopyOverlayToDrawings={oncopyoverlaytodrawings}
                onOverlayError={onoverlayerror}
                onToggleOffline={ontoggleoffline}
                onToggleCaching={ontogglecaching}
                onUploadMbtiles={onuploadmbtiles}
                onSetActiveMbtiles={onsetactivembtiles}
                onDeleteMbtiles={ondeletembtiles}
                onSaveMbtilesDir={onsavembtilesdir}
                onClearCache={onclearcache}
                onExportRegion={onexportregion}
                onRestoreStarter={onrestorestarter}
                onToggleAnnounceListen={ontoggleannouncelisten}
            />
        </div>
    </div>
{/if}
