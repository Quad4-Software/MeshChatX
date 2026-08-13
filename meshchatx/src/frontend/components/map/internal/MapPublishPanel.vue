<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <label class="block text-[11px] text-gray-600 dark:text-zinc-400 space-y-1">
            <span>{{ $t("map.data_display_name") }}</span>
            <input
                v-model="displayName"
                type="text"
                maxlength="32"
                class="w-full rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 py-1.5 text-[12px]"
                @blur="saveConfig"
            />
        </label>
        <label class="flex items-center gap-2 text-[11px] text-gray-600 dark:text-zinc-400">
            <input v-model="announceEnabled" type="checkbox" @change="saveConfig" />
            {{ $t("map.data_announce") }}
        </label>
        <label class="block text-[11px] text-gray-600 dark:text-zinc-400 space-y-1">
            <span>{{ $t("map.data_interval") }}</span>
            <input
                v-model.number="announceInterval"
                type="number"
                min="10"
                class="w-full rounded-lg border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 py-1.5 text-[12px]"
                @blur="saveConfig"
            />
        </label>
        <div class="flex gap-2">
            <button
                type="button"
                class="flex-1 py-2 text-[10px] font-semibold uppercase rounded-lg bg-blue-500 text-white disabled:opacity-40"
                :disabled="publishing"
                @click="pickFile"
            >
                {{ $t("map.data_publish") }}
            </button>
            <button
                type="button"
                class="flex-1 py-2 text-[10px] font-semibold uppercase rounded-lg border border-gray-200 dark:border-zinc-700 disabled:opacity-40"
                :disabled="announcing"
                @click="announceNow"
            >
                {{ $t("map.data_announce_now") }}
            </button>
        </div>
        <input ref="fileInput" type="file" accept=".geojson,.json,.kml,.kmz" class="hidden" @change="onFile" />
        <p v-if="strippedPreview.length" class="text-[10px] text-amber-600 dark:text-amber-400">
            {{ $t("map.data_stripped") }}: {{ strippedPreview.join(", ") }}
        </p>
        <div v-if="!published.length" class="text-[11px] text-gray-500">{{ $t("map.data_no_published") }}</div>
        <div
            v-for="row in published"
            :key="row.map_id"
            class="rounded-lg border border-gray-200 dark:border-zinc-800 p-2 flex items-center justify-between gap-2"
        >
            <div class="min-w-0">
                <div class="text-[12px] font-semibold truncate">{{ row.name }}</div>
                <div class="text-[9px] text-gray-500">
                    {{ row.format }} · {{ $t("map.data_published_size", { size: formatSize(row.size) }) }}
                </div>
            </div>
            <button type="button" class="text-[10px] text-red-500 font-semibold" @click="unpublish(row.map_id)">
                {{ $t("map.data_unpublish") }}
            </button>
        </div>
    </div>
</template>

<script>
import ToastUtils from "../../../js/ToastUtils";

function fileToB64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const buf = reader.result;
            const bytes = new Uint8Array(buf);
            let binary = "";
            for (let i = 0; i < bytes.length; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            resolve(btoa(binary));
        };
        reader.onerror = () => reject(reader.error);
        reader.readAsArrayBuffer(file);
    });
}

function hintedFormat(name) {
    const lower = String(name || "").toLowerCase();
    if (lower.endsWith(".kmz")) {
        return "kmz";
    }
    if (lower.endsWith(".kml")) {
        return "kml";
    }
    return "geojson";
}

export default {
    name: "MapPublishPanel",
    props: {
        drawSource: { type: Object, default: null },
    },
    data() {
        return {
            displayName: "Maps",
            announceEnabled: true,
            announceInterval: 900,
            published: [],
            strippedPreview: [],
            publishing: false,
            announcing: false,
        };
    },
    mounted() {
        this.load();
    },
    methods: {
        formatSize(n) {
            const v = Number(n) || 0;
            if (v < 1024) {
                return `${v} B`;
            }
            return `${(v / 1024).toFixed(1)} KiB`;
        },
        async load() {
            try {
                const status = await window.api.get("/api/v1/map/data/status");
                const s = status.data || {};
                this.displayName = s.display_name || "Maps";
                this.announceEnabled = Boolean(s.announce_enabled);
                this.announceInterval = s.announce_interval || 900;
                const listed = await window.api.get("/api/v1/map/data/published");
                this.published = listed.data.maps || [];
            } catch {
                ToastUtils.error(this.$t("map.data_unavailable"));
            }
        },
        async saveConfig() {
            try {
                await window.api.patch("/api/v1/map/data/config", {
                    display_name: this.displayName,
                    announce_enabled: this.announceEnabled,
                    announce_interval: this.announceInterval,
                });
            } catch {
                ToastUtils.error(this.$t("map.data_unavailable"));
            }
        },
        pickFile() {
            this.$refs.fileInput?.click();
        },
        async onFile(ev) {
            const file = ev.target.files && ev.target.files[0];
            ev.target.value = "";
            if (!file) {
                return;
            }
            this.publishing = true;
            this.strippedPreview = [];
            try {
                const dataB64 = await fileToB64(file);
                const response = await window.api.post("/api/v1/map/data/publish", {
                    name: file.name.replace(/\.[^.]+$/, "") || "map",
                    format: hintedFormat(file.name),
                    data_b64: dataB64,
                });
                this.strippedPreview = response.data.stripped || [];
                ToastUtils.success(this.$t("map.data_publish_ok"));
                await this.load();
            } catch (e) {
                const code = e.response?.data?.error;
                if (code === "file_too_large") {
                    ToastUtils.error(this.$t("map.data_file_too_large"));
                } else if (code === "remote_content" || code === "dtd_forbidden" || code === "unsafe_kmz_entry") {
                    ToastUtils.error(this.$t("map.data_sanitize_reject"));
                } else {
                    ToastUtils.error(this.$t("map.data_publish_failed"));
                }
            } finally {
                this.publishing = false;
            }
        },
        async announceNow() {
            this.announcing = true;
            try {
                await window.api.post("/api/v1/map/data/announce");
                ToastUtils.success(this.$t("map.data_announce_ok"));
            } catch {
                ToastUtils.error(this.$t("map.data_unavailable"));
            } finally {
                this.announcing = false;
            }
        },
        async unpublish(mapId) {
            try {
                await window.api.delete(`/api/v1/map/data/published/${mapId}`);
                ToastUtils.success(this.$t("map.data_unpublish_ok"));
                await this.load();
            } catch {
                ToastUtils.error(this.$t("map.data_unavailable"));
            }
        },
    },
};
</script>
