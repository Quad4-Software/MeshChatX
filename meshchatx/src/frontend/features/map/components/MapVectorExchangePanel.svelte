<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { readGeoJsonToFeatures } from "../../../js/mapExchange/geoJsonCodec.js";
    import { readKmlToFeatures } from "../../../js/mapExchange/kmlCodec.js";
    import { readKmzToFeatures } from "../../../js/mapExchange/kmzCodec.js";
    import { readGpxToFeatures } from "../../../js/mapExchange/gpxCodec.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        disabled?: boolean;
        hasFeatures?: boolean;
        onImportFeatures?: (detail: { features: any[]; merge: boolean }) => void;
        onExportGeojson?: () => void;
        onExportKml?: () => void;
        onExportKmz?: () => void;
        onExportGpx?: () => void;
        onImportError?: (err: any) => void;
    }

    let {
        disabled = false,
        hasFeatures = false,
        onImportFeatures,
        onExportGeojson,
        onExportKml,
        onExportKmz,
        onExportGpx,
        onImportError,
    }: Props = $props();

    let mergeImport = $state(true);
    let geojsonInput = $state<HTMLInputElement | null>(null);
    let kmlInput = $state<HTMLInputElement | null>(null);
    let kmzInput = $state<HTMLInputElement | null>(null);
    let gpxInput = $state<HTMLInputElement | null>(null);

    function triggerGeoJsonPick() {
        geojsonInput?.click();
    }

    function triggerKmlPick() {
        kmlInput?.click();
    }

    function triggerKmzPick() {
        kmzInput?.click();
    }

    function triggerGpxPick() {
        gpxInput?.click();
    }

    async function readFileText(file: File): Promise<string> {
        return new Promise((resolve, reject) => {
            const r = new FileReader();
            r.onload = () => resolve(String(r.result || ""));
            r.onerror = () => reject(new Error("read failed"));
            r.readAsText(file);
        });
    }

    async function readFileArrayBuffer(file: File): Promise<ArrayBuffer> {
        return new Promise((resolve, reject) => {
            const r = new FileReader();
            r.onload = () => resolve(r.result as ArrayBuffer);
            r.onerror = () => reject(new Error("read failed"));
            r.readAsArrayBuffer(file);
        });
    }

    async function onGeojsonFile(ev: Event) {
        const input = ev.target as HTMLInputElement;
        const file = input.files && input.files[0];
        input.value = "";
        if (!file) return;
        try {
            const text = await readFileText(file);
            const features = readGeoJsonToFeatures(text, "EPSG:3857");
            onImportFeatures?.({ features, merge: mergeImport });
        } catch (e) {
            onImportError?.(e);
        }
    }

    async function onKmlFile(ev: Event) {
        const input = ev.target as HTMLInputElement;
        const file = input.files && input.files[0];
        input.value = "";
        if (!file) return;
        try {
            const text = await readFileText(file);
            const features = readKmlToFeatures(text, "EPSG:3857");
            onImportFeatures?.({ features, merge: mergeImport });
        } catch (e) {
            onImportError?.(e);
        }
    }

    async function onKmzFile(ev: Event) {
        const input = ev.target as HTMLInputElement;
        const file = input.files && input.files[0];
        input.value = "";
        if (!file) return;
        try {
            const buf = await readFileArrayBuffer(file);
            const features = await readKmzToFeatures(buf, "EPSG:3857");
            onImportFeatures?.({ features, merge: mergeImport });
        } catch (e) {
            onImportError?.(e);
        }
    }

    async function onGpxFile(ev: Event) {
        const input = ev.target as HTMLInputElement;
        const file = input.files && input.files[0];
        input.value = "";
        if (!file) return;
        try {
            const text = await readFileText(file);
            const features = readGpxToFeatures(text, "EPSG:3857");
            onImportFeatures?.({ features, merge: mergeImport });
        } catch (e) {
            onImportError?.(e);
        }
    }
</script>

<div class="space-y-3 rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3">
    <div class="flex items-center justify-between gap-2">
        <span class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
            {t("map.vector_exchange_title")}
        </span>
    </div>
    <label class="flex items-center gap-2 text-[10px] text-sem-fg-muted cursor-pointer select-none">
        <input type="checkbox" bind:checked={mergeImport} class="rounded-sm border-gray-300 dark:border-zinc-600" />
        {t("map.vector_exchange_merge")}
    </label>
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <button
            type="button"
            class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-sem-surface border border-sem-border text-sem-fg hover:bg-sem-surface-muted disabled:opacity-40 cursor-pointer"
            {disabled}
            onclick={triggerGeoJsonPick}
        >
            {t("map.vector_import_geojson")}
        </button>
        <button
            type="button"
            class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-sem-surface border border-sem-border text-sem-fg hover:bg-sem-surface-muted disabled:opacity-40 cursor-pointer"
            {disabled}
            onclick={triggerKmlPick}
        >
            {t("map.vector_import_kml")}
        </button>
        <button
            type="button"
            class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-sem-surface border border-sem-border text-sem-fg hover:bg-sem-surface-muted disabled:opacity-40 cursor-pointer"
            {disabled}
            onclick={triggerKmzPick}
        >
            {t("map.vector_import_kmz")}
        </button>
        <button
            type="button"
            class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-sem-surface border border-sem-border text-sem-fg hover:bg-sem-surface-muted disabled:opacity-40 cursor-pointer"
            {disabled}
            onclick={triggerGpxPick}
        >
            {t("map.vector_import_gpx")}
        </button>
        <button
            type="button"
            class="flex items-center justify-center px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            disabled={disabled || !hasFeatures}
            onclick={() => onExportGeojson?.()}
        >
            {t("map.vector_export_geojson")}
        </button>
        <button
            type="button"
            class="flex items-center justify-center px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            disabled={disabled || !hasFeatures}
            onclick={() => onExportKml?.()}
        >
            {t("map.vector_export_kml")}
        </button>
        <button
            type="button"
            class="flex items-center justify-center px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            disabled={disabled || !hasFeatures}
            onclick={() => onExportKmz?.()}
        >
            {t("map.vector_export_kmz")}
        </button>
        <button
            type="button"
            class="flex items-center justify-center px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            disabled={disabled || !hasFeatures}
            onclick={() => onExportGpx?.()}
        >
            {t("map.vector_export_gpx")}
        </button>
    </div>
    <p class="text-[9px] text-sem-fg-muted leading-snug">
        {t("map.vector_exchange_hint")}
    </p>
    <input
        bind:this={geojsonInput}
        type="file"
        accept=".geojson,.json,application/geo+json,application/json"
        class="hidden"
        onchange={onGeojsonFile}
    />
    <input
        bind:this={kmlInput}
        type="file"
        accept=".kml,.xml,text/xml,application/vnd.google-earth.kml+xml"
        class="hidden"
        onchange={onKmlFile}
    />
    <input
        bind:this={kmzInput}
        type="file"
        accept=".kmz,application/vnd.google-earth.kmz,application/zip"
        class="hidden"
        onchange={onKmzFile}
    />
    <input
        bind:this={gpxInput}
        type="file"
        accept=".gpx,application/gpx+xml,application/xml,text/xml"
        class="hidden"
        onchange={onGpxFile}
    />
</div>
