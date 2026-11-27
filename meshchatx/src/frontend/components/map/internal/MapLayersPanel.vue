<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <div class="rounded-xl border border-sem-border bg-sem-surface-muted/80 dark:bg-sem-surface p-3 space-y-2">
            <div class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
                {{ $t("map.data_listen_title") }}
            </div>
            <p class="text-[10px] text-sem-fg-muted leading-snug">
                {{ $t("map.data_listen_hint") }}
            </p>
            <label class="flex items-center gap-2 text-[11px] text-sem-fg cursor-pointer select-none">
                <input
                    type="checkbox"
                    class="rounded-sm border-sem-border dark:border-sem-border"
                    :checked="announceListenEnabled"
                    :disabled="announceListenBusy"
                    @change="onToggleListen"
                />
                {{ announceListenEnabled ? $t("map.data_listen_enabled") : $t("map.data_listen_enable") }}
            </label>
        </div>
        <MapVectorExchangePanel
            :disabled="disabled"
            :has-features="hasFeatures"
            @import-features="emit('import-features', $event)"
            @import-error="emit('import-error', $event)"
            @export-geojson="emit('export-geojson')"
            @export-kml="emit('export-kml')"
            @export-kmz="emit('export-kmz')"
            @export-gpx="emit('export-gpx')"
        />
        <details class="rounded-xl border border-sem-border bg-sem-surface-muted/80 dark:bg-sem-surface p-3">
            <summary class="cursor-pointer text-[11px] font-semibold text-sem-fg-muted">
                {{ $t("map.data_advanced_source") }}
            </summary>
            <div class="mt-3">
                <MapRemoteOverlayPanel
                    :disabled="!mapReady"
                    @overlays-changed="emit('overlays-changed')"
                    @export-overlay="emit('export-overlay', $event)"
                    @copy-overlay-to-drawings="emit('copy-overlay-to-drawings', $event)"
                    @error="emit('error', $event)"
                />
            </div>
        </details>
    </div>
</template>

<script setup lang="ts">
import MapVectorExchangePanel from "./MapVectorExchangePanel.vue";
import MapRemoteOverlayPanel from "./MapRemoteOverlayPanel.vue";

withDefaults(
    defineProps<{
        disabled?: boolean;
        hasFeatures?: boolean;
        mapReady?: boolean;
        announceListenEnabled?: boolean;
        announceListenBusy?: boolean;
    }>(),
    {
        disabled: false,
        hasFeatures: false,
        mapReady: false,
        announceListenEnabled: false,
        announceListenBusy: false,
    }
);

const emit = defineEmits<{
    "import-features": [event: any];
    "import-error": [event: any];
    "export-geojson": [];
    "export-kml": [];
    "export-kmz": [];
    "export-gpx": [];
    "overlays-changed": [];
    "export-overlay": [event: any];
    "copy-overlay-to-drawings": [event: any];
    error: [event: any];
    "toggle-announce-listen": [enabled: boolean];
}>();

function onToggleListen(event: Event) {
    emit("toggle-announce-listen", (event.target as HTMLInputElement).checked);
}
</script>
