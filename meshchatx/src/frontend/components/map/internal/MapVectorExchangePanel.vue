<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3 rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3">
        <div class="flex items-center justify-between gap-2">
            <span class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">{{
                $t("map.vector_exchange_title")
            }}</span>
        </div>
        <label class="flex items-center gap-2 text-[10px] text-sem-fg-muted cursor-pointer select-none">
            <input v-model="mergeImport" type="checkbox" class="rounded-sm border-gray-300 dark:border-zinc-600" />
            {{ $t("map.vector_exchange_merge") }}
        </label>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <button
                type="button"
                class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-sem-surface border border-sem-border text-sem-fg hover:bg-sem-surface-muted disabled:opacity-40"
                :disabled="disabled"
                @click="triggerGeoJsonPick"
            >
                {{ $t("map.vector_import_geojson") }}
            </button>
            <button
                type="button"
                class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-sem-surface border border-sem-border text-sem-fg hover:bg-sem-surface-muted disabled:opacity-40"
                :disabled="disabled"
                @click="triggerKmlPick"
            >
                {{ $t("map.vector_import_kml") }}
            </button>
            <button
                type="button"
                class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-sem-surface border border-sem-border text-sem-fg hover:bg-sem-surface-muted disabled:opacity-40"
                :disabled="disabled"
                @click="triggerKmzPick"
            >
                {{ $t("map.vector_import_kmz") }}
            </button>
            <button
                type="button"
                class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-sem-surface border border-sem-border text-sem-fg hover:bg-sem-surface-muted disabled:opacity-40"
                :disabled="disabled"
                @click="triggerGpxPick"
            >
                {{ $t("map.vector_import_gpx") }}
            </button>
            <button
                type="button"
                class="flex items-center justify-center px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="disabled || !hasFeatures"
                @click="$emit('export-geojson')"
            >
                {{ $t("map.vector_export_geojson") }}
            </button>
            <button
                type="button"
                class="flex items-center justify-center px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="disabled || !hasFeatures"
                @click="$emit('export-kml')"
            >
                {{ $t("map.vector_export_kml") }}
            </button>
            <button
                type="button"
                class="flex items-center justify-center px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="disabled || !hasFeatures"
                @click="$emit('export-kmz')"
            >
                {{ $t("map.vector_export_kmz") }}
            </button>
            <button
                type="button"
                class="flex items-center justify-center px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="disabled || !hasFeatures"
                @click="$emit('export-gpx')"
            >
                {{ $t("map.vector_export_gpx") }}
            </button>
        </div>
        <p class="text-[9px] text-sem-fg-muted leading-snug">
            {{ $t("map.vector_exchange_hint") }}
        </p>
        <input
            ref="geojsonInput"
            type="file"
            accept=".geojson,.json,application/geo+json,application/json"
            class="hidden"
            @change="onGeojsonFile"
        />
        <input
            ref="kmlInput"
            type="file"
            accept=".kml,.xml,text/xml,application/vnd.google-earth.kml+xml"
            class="hidden"
            @change="onKmlFile"
        />
        <input
            ref="kmzInput"
            type="file"
            accept=".kmz,application/vnd.google-earth.kmz,application/zip"
            class="hidden"
            @change="onKmzFile"
        />
        <input
            ref="gpxInput"
            type="file"
            accept=".gpx,application/gpx+xml,application/xml,text/xml"
            class="hidden"
            @change="onGpxFile"
        />
    </div>
</template>

<script>
import { readGeoJsonToFeatures } from "../../../js/mapExchange/geoJsonCodec.js";
import { readKmlToFeatures } from "../../../js/mapExchange/kmlCodec.js";
import { readKmzToFeatures } from "../../../js/mapExchange/kmzCodec.js";
import { readGpxToFeatures } from "../../../js/mapExchange/gpxCodec.js";

export default {
    name: "MapVectorExchangePanel",
    props: {
        disabled: { type: Boolean, default: false },
        hasFeatures: { type: Boolean, default: false },
    },
    emits: ["import-features", "export-geojson", "export-kml", "export-kmz", "export-gpx", "import-error"],
    data() {
        return {
            mergeImport: true,
        };
    },
    methods: {
        triggerGeoJsonPick() {
            this.$refs.geojsonInput?.click();
        },
        triggerKmlPick() {
            this.$refs.kmlInput?.click();
        },
        triggerKmzPick() {
            this.$refs.kmzInput?.click();
        },
        triggerGpxPick() {
            this.$refs.gpxInput?.click();
        },
        async readFileText(file) {
            return new Promise((resolve, reject) => {
                const r = new FileReader();
                r.onload = () => resolve(String(r.result || ""));
                r.onerror = () => reject(new Error("read failed"));
                r.readAsText(file);
            });
        },
        async onGeojsonFile(ev) {
            const input = ev.target;
            const file = input.files && input.files[0];
            input.value = "";
            if (!file) {
                return;
            }
            try {
                const text = await this.readFileText(file);
                const features = readGeoJsonToFeatures(text, "EPSG:3857");
                this.$emit("import-features", { features, merge: this.mergeImport });
            } catch (e) {
                console.error(e);
                this.$emit("import-error", e);
            }
        },
        async onKmlFile(ev) {
            const input = ev.target;
            const file = input.files && input.files[0];
            input.value = "";
            if (!file) {
                return;
            }
            try {
                const text = await this.readFileText(file);
                const features = readKmlToFeatures(text, "EPSG:3857");
                this.$emit("import-features", { features, merge: this.mergeImport });
            } catch (e) {
                console.error(e);
                this.$emit("import-error", e);
            }
        },
        async readFileArrayBuffer(file) {
            return new Promise((resolve, reject) => {
                const r = new FileReader();
                r.onload = () => resolve(/** @type {ArrayBuffer} */ (r.result));
                r.onerror = () => reject(new Error("read failed"));
                r.readAsArrayBuffer(file);
            });
        },
        async onKmzFile(ev) {
            const input = ev.target;
            const file = input.files && input.files[0];
            input.value = "";
            if (!file) {
                return;
            }
            try {
                const buf = await this.readFileArrayBuffer(file);
                const features = await readKmzToFeatures(buf, "EPSG:3857");
                this.$emit("import-features", { features, merge: this.mergeImport });
            } catch (e) {
                console.error(e);
                this.$emit("import-error", e);
            }
        },
        async onGpxFile(ev) {
            const input = ev.target;
            const file = input.files && input.files[0];
            input.value = "";
            if (!file) {
                return;
            }
            try {
                const text = await this.readFileText(file);
                const features = readGpxToFeatures(text, "EPSG:3857");
                this.$emit("import-features", { features, merge: this.mergeImport });
            } catch (e) {
                console.error(e);
                this.$emit("import-error", e);
            }
        },
    },
};
</script>
