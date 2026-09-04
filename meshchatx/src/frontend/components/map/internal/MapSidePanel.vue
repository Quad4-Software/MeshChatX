<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col h-full min-h-0">
        <div class="flex border-b border-sem-border shrink-0">
            <button
                v-for="tab in tabs"
                :key="tab.id"
                type="button"
                class="flex-1 px-2 py-2 text-[11px] font-semibold transition-colors"
                :class="
                    activeTab === tab.id
                        ? 'text-sem-accent border-b-2 border-blue-500'
                        : 'text-sem-fg-muted hover:text-gray-800 hover:text-sem-fg'
                "
                @click="activeTab = tab.id"
            >
                {{ $t(tab.labelKey) }}
            </button>
        </div>
        <div class="flex-1 min-h-0 overflow-y-auto p-3">
            <MapDiscoverPanel
                v-show="activeTab === 'discover'"
                :listen-enabled="announceListenEnabled"
                @overlays-changed="$emit('overlays-changed')"
                @enable-listen="$emit('toggle-announce-listen', true)"
            />
            <MapPublishPanel v-if="activeTab === 'publish'" :draw-source="drawSource" />
            <MapLayersPanel
                v-else-if="activeTab === 'layers'"
                :disabled="!drawSource"
                :has-features="hasVectorDrawFeatures"
                :map-ready="mapReady"
                :announce-listen-enabled="announceListenEnabled"
                :announce-listen-busy="announceListenBusy"
                @import-features="$emit('import-features', $event)"
                @import-error="$emit('import-error', $event)"
                @export-geojson="$emit('export-geojson')"
                @export-kml="$emit('export-kml')"
                @export-kmz="$emit('export-kmz')"
                @export-gpx="$emit('export-gpx')"
                @overlays-changed="$emit('overlays-changed')"
                @export-overlay="$emit('export-overlay', $event)"
                @copy-overlay-to-drawings="$emit('copy-overlay-to-drawings', $event)"
                @error="$emit('overlay-error', $event)"
                @toggle-announce-listen="$emit('toggle-announce-listen', $event)"
            />
            <MapOfflinePanel
                v-else-if="activeTab === 'offline'"
                :offline-enabled="offlineEnabled"
                :caching-enabled="cachingEnabled"
                :mbtiles-list="mbtilesList"
                :mbtiles-dir="mbtilesDir"
                :has-offline-map="hasOfflineMap"
                @toggle-offline="$emit('toggle-offline', $event)"
                @toggle-caching="$emit('toggle-caching', $event)"
                @upload="$emit('upload-mbtiles')"
                @set-active="$emit('set-active-mbtiles', $event)"
                @delete-file="$emit('delete-mbtiles', $event)"
                @save-dir="$emit('save-mbtiles-dir', $event)"
                @clear-cache="$emit('clear-cache')"
                @export-region="$emit('export-region')"
                @restore-starter="$emit('restore-starter')"
            />
        </div>
    </div>
</template>

<script>
import MapDiscoverPanel from "./MapDiscoverPanel.vue";
import MapPublishPanel from "./MapPublishPanel.vue";
import MapLayersPanel from "./MapLayersPanel.vue";
import MapOfflinePanel from "./MapOfflinePanel.vue";

export default {
    name: "MapSidePanel",
    components: {
        MapDiscoverPanel,
        MapPublishPanel,
        MapLayersPanel,
        MapOfflinePanel,
    },
    props: {
        drawSource: { type: Object, default: null },
        hasVectorDrawFeatures: { type: Boolean, default: false },
        mapReady: { type: Boolean, default: false },
        offlineEnabled: { type: Boolean, default: false },
        cachingEnabled: { type: Boolean, default: true },
        mbtilesList: { type: Array, default: () => [] },
        mbtilesDir: { type: String, default: "" },
        hasOfflineMap: { type: Boolean, default: false },
        initialTab: { type: String, default: "discover" },
        announceListenEnabled: { type: Boolean, default: false },
        announceListenBusy: { type: Boolean, default: false },
    },
    emits: [
        "overlays-changed",
        "import-features",
        "import-error",
        "export-geojson",
        "export-kml",
        "export-kmz",
        "export-gpx",
        "export-overlay",
        "copy-overlay-to-drawings",
        "overlay-error",
        "toggle-offline",
        "toggle-caching",
        "upload-mbtiles",
        "set-active-mbtiles",
        "delete-mbtiles",
        "save-mbtiles-dir",
        "clear-cache",
        "export-region",
        "restore-starter",
        "toggle-announce-listen",
    ],
    data() {
        return {
            activeTab: this.initialTab || "discover",
            tabs: [
                { id: "discover", labelKey: "map.tab_discover" },
                { id: "publish", labelKey: "map.tab_publish" },
                { id: "layers", labelKey: "map.tab_layers" },
                { id: "offline", labelKey: "map.tab_offline" },
            ],
        };
    },
};
</script>
