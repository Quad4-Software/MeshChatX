<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <label class="block text-[11px] text-sem-fg-muted space-y-1">
            <span>{{ $t("map.data_display_name") }}</span>
            <input
                v-model="displayName"
                type="text"
                maxlength="32"
                class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[12px]"
                @blur="saveConfig"
            />
        </label>
        <label class="flex items-center gap-2 text-[11px] text-sem-fg-muted">
            <input v-model="announceEnabled" type="checkbox" :disabled="!published.length" @change="saveConfig" />
            {{ $t("map.data_announce") }}
        </label>
        <p v-if="!published.length" class="text-[10px] text-sem-fg-muted">
            {{ $t("map.data_announce_needs_publish") }}
        </p>
        <label class="block text-[11px] text-sem-fg-muted space-y-1">
            <span>{{ $t("map.data_interval") }}</span>
            <input
                v-model.number="announceInterval"
                type="number"
                min="900"
                class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[12px]"
                @blur="saveConfig"
            />
        </label>
        <div class="flex gap-2">
            <button
                type="button"
                class="flex-1 py-2 text-[10px] font-semibold uppercase rounded-lg bg-sem-action-primary text-sem-action-primary-text disabled:opacity-40"
                :disabled="publishing"
                @click="pickFile"
            >
                {{ $t("map.data_publish") }}
            </button>
            <button
                type="button"
                class="flex-1 py-2 text-[10px] font-semibold uppercase rounded-lg border border-sem-border disabled:opacity-40"
                :disabled="announcing || !published.length"
                @click="announceNow"
            >
                {{ $t("map.data_announce_now") }}
            </button>
        </div>
        <input ref="fileInput" type="file" accept=".geojson,.json,.kml,.kmz" class="hidden" @change="onFile" />
        <p v-if="strippedPreview.length" class="text-[10px] text-sem-warning">
            {{ $t("map.data_stripped") }}: {{ strippedPreview.join(", ") }}
        </p>
        <div v-if="!published.length" class="text-[11px] text-sem-fg-muted">{{ $t("map.data_no_published") }}</div>
        <div
            v-for="row in published"
            :key="row.map_id"
            class="rounded-lg border border-sem-border p-2 flex items-center justify-between gap-2"
        >
            <div class="min-w-0">
                <div class="text-[12px] font-semibold truncate">{{ row.name }}</div>
                <div class="text-[9px] text-sem-fg-muted">
                    {{ row.format }} · {{ $t("map.data_published_size", { size: formatSize(row.size) }) }}
                </div>
            </div>
            <button type="button" class="text-[10px] text-sem-danger font-semibold" @click="unpublish(row.map_id)">
                {{ $t("map.data_unpublish") }}
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import ToastUtils from "../../../js/ToastUtils";
import { apiPath } from "../../../js/constants";
import { useTranslateUi } from "../../../js/localeLoader";

defineOptions({ name: "MapPublishPanel" });

defineProps<{
    drawSource?: object | null;
}>();

interface PublishedMap {
    map_id: string;
    name: string;
    format: string;
    size: number;
}

function fileToB64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const buf = reader.result as ArrayBuffer;
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

function hintedFormat(name: string): string {
    const lower = String(name || "").toLowerCase();
    if (lower.endsWith(".kmz")) {
        return "kmz";
    }
    if (lower.endsWith(".kml")) {
        return "kml";
    }
    return "geojson";
}

const t = useTranslateUi();

const displayName = ref("Maps");
const announceEnabled = ref(false);
const announceInterval = ref(21600);
const published = ref<PublishedMap[]>([]);
const strippedPreview = ref<string[]>([]);
const publishing = ref(false);
const announcing = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

function formatSize(n: number): string {
    const v = Number(n) || 0;
    if (v < 1024) {
        return `${v} B`;
    }
    return `${(v / 1024).toFixed(1)} KiB`;
}

async function load() {
    try {
        const status = await window.api.get(apiPath("/map/data/status"));
        const s = status.data || {};
        displayName.value = s.display_name || "Maps";
        announceEnabled.value = Boolean(s.announce_enabled);
        announceInterval.value = s.announce_interval || 21600;
        const listed = await window.api.get(apiPath("/map/data/published"));
        published.value = listed.data.maps || [];
    } catch {
        ToastUtils.error(t("map.data_unavailable"));
    }
}

async function saveConfig() {
    try {
        await window.api.patch(apiPath("/map/data/config"), {
            display_name: displayName.value,
            announce_enabled: announceEnabled.value,
            announce_interval: announceInterval.value,
        });
    } catch {
        ToastUtils.error(t("map.data_unavailable"));
    }
}

function pickFile() {
    fileInput.value?.click();
}

async function onFile(ev: Event) {
    const target = ev.target as HTMLInputElement;
    const file = target.files && target.files[0];
    target.value = "";
    if (!file) {
        return;
    }
    publishing.value = true;
    strippedPreview.value = [];
    try {
        const dataB64 = await fileToB64(file);
        const response = await window.api.post(apiPath("/map/data/publish"), {
            name: file.name.replace(/\.[^.]+$/, "") || "map",
            format: hintedFormat(file.name),
            data_b64: dataB64,
        });
        strippedPreview.value = response.data.stripped || [];
        ToastUtils.success(t("map.data_publish_ok"));
        await load();
    } catch (e: any) {
        const code = e.response?.data?.error;
        if (code === "file_too_large") {
            ToastUtils.error(t("map.data_file_too_large"));
        } else if (code === "remote_content" || code === "dtd_forbidden" || code === "unsafe_kmz_entry") {
            ToastUtils.error(t("map.data_sanitize_reject"));
        } else {
            ToastUtils.error(t("map.data_publish_failed"));
        }
    } finally {
        publishing.value = false;
    }
}

async function announceNow() {
    if (!published.value.length) {
        ToastUtils.warning(t("map.data_announce_needs_publish"));
        return;
    }
    announcing.value = true;
    try {
        await window.api.post(apiPath("/map/data/announce"));
        ToastUtils.success(t("map.data_announce_ok"));
    } catch (e: any) {
        const code = e.response?.data?.error;
        if (code === "nothing_published") {
            ToastUtils.warning(t("map.data_announce_needs_publish"));
        } else {
            ToastUtils.error(t("map.data_unavailable"));
        }
    } finally {
        announcing.value = false;
    }
}

async function unpublish(mapId: string) {
    try {
        await window.api.delete(apiPath(`/map/data/published/${mapId}`));
        ToastUtils.success(t("map.data_unpublish_ok"));
        await load();
    } catch {
        ToastUtils.error(t("map.data_unavailable"));
    }
}

onMounted(load);
</script>
