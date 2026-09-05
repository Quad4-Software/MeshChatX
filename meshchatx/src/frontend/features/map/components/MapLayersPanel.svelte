<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MapVectorExchangePanel from "./MapVectorExchangePanel.svelte";
    import MapRemoteOverlayPanel from "./MapRemoteOverlayPanel.svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        disabled?: boolean;
        hasFeatures?: boolean;
        mapReady?: boolean;
        announceListenEnabled?: boolean;
        announceListenBusy?: boolean;
        onImportFeatures?: (detail: { features: any[]; merge: boolean }) => void;
        onImportError?: (err: any) => void;
        onExportGeojson?: () => void;
        onExportKml?: () => void;
        onExportKmz?: () => void;
        onExportGpx?: () => void;
        onOverlaysChanged?: (overlays?: any[]) => void;
        onExportOverlay?: (detail: { id: string | number; format: string }) => void;
        onCopyOverlayToDrawings?: (overlay: any) => void;
        onError?: (err: any) => void;
        onToggleAnnounceListen?: (val: boolean) => void;
    }

    let {
        disabled = false,
        hasFeatures = false,
        mapReady = false,
        announceListenEnabled = false,
        announceListenBusy = false,
        onImportFeatures,
        onImportError,
        onExportGeojson,
        onExportKml,
        onExportKmz,
        onExportGpx,
        onOverlaysChanged,
        onExportOverlay,
        onCopyOverlayToDrawings,
        onError,
        onToggleAnnounceListen,
    }: Props = $props();
</script>

<div class="space-y-3">
    <div class="rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3 space-y-2">
        <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
            {t("map.data_listen_title")}
        </div>
        <p class="text-[10px] text-sem-fg-muted leading-snug">
            {t("map.data_listen_hint")}
        </p>
        <label class="flex items-center gap-2 text-[11px] text-sem-fg cursor-pointer select-none">
            <input
                type="checkbox"
                class="rounded-sm border-gray-300 dark:border-zinc-600"
                checked={announceListenEnabled}
                disabled={announceListenBusy}
                onchange={(e) => onToggleAnnounceListen?.((e.target as HTMLInputElement).checked)}
            />
            {announceListenEnabled ? t("map.data_listen_enabled") : t("map.data_listen_enable")}
        </label>
    </div>
    <MapVectorExchangePanel
        {disabled}
        {hasFeatures}
        {onImportFeatures}
        {onImportError}
        {onExportGeojson}
        {onExportKml}
        {onExportKmz}
        {onExportGpx}
    />
    <details class="rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3">
        <summary class="cursor-pointer text-[11px] font-semibold text-sem-fg-muted">
            {t("map.data_advanced_source")}
        </summary>
        <div class="mt-3">
            <MapRemoteOverlayPanel
                disabled={!mapReady}
                {onOverlaysChanged}
                {onExportOverlay}
                {onCopyOverlayToDrawings}
                {onError}
            />
        </div>
    </details>
</div>
