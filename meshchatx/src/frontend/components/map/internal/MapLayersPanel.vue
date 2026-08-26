<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <MapVectorExchangePanel
            :disabled="disabled"
            :has-features="hasFeatures"
            @import-features="$emit('import-features', $event)"
            @import-error="$emit('import-error', $event)"
            @export-geojson="$emit('export-geojson')"
            @export-kml="$emit('export-kml')"
            @export-kmz="$emit('export-kmz')"
        />
        <details class="rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3">
            <summary class="cursor-pointer text-[11px] font-semibold text-sem-fg-muted">
                {{ $t("map.data_advanced_source") }}
            </summary>
            <div class="mt-3">
                <MapRemoteOverlayPanel
                    :disabled="!mapReady"
                    @overlays-changed="$emit('overlays-changed')"
                    @export-overlay="$emit('export-overlay', $event)"
                    @copy-overlay-to-drawings="$emit('copy-overlay-to-drawings', $event)"
                    @error="$emit('error', $event)"
                />
            </div>
        </details>
    </div>
</template>

<script>
import MapVectorExchangePanel from "./MapVectorExchangePanel.vue";
import MapRemoteOverlayPanel from "./MapRemoteOverlayPanel.vue";

export default {
    name: "MapLayersPanel",
    components: {
        MapVectorExchangePanel,
        MapRemoteOverlayPanel,
    },
    props: {
        disabled: { type: Boolean, default: false },
        hasFeatures: { type: Boolean, default: false },
        mapReady: { type: Boolean, default: false },
    },
    emits: [
        "import-features",
        "import-error",
        "export-geojson",
        "export-kml",
        "export-kmz",
        "overlays-changed",
        "export-overlay",
        "copy-overlay-to-drawings",
        "error",
    ],
};
</script>
