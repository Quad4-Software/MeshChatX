<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="space-y-3">
        <div
            v-if="!listenEnabled"
            class="rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3 space-y-2"
        >
            <p class="text-[11px] text-sem-fg-muted leading-snug">{{ $t("map.data_listen_off") }}</p>
            <button
                type="button"
                class="w-full py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-blue-500 hover:bg-blue-600 text-white"
                @click="$emit('enable-listen')"
            >
                {{ $t("map.data_listen_enable") }}
            </button>
        </div>
        <template v-else>
            <input
                v-model="search"
                type="search"
                class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[12px]"
                :placeholder="$t('map.data_search')"
                @input="reload"
            />
            <p v-if="error" class="text-[11px] text-amber-600 dark:text-amber-400">{{ error }}</p>
            <div v-if="!announces.length && !loading" class="text-[11px] text-sem-fg-muted">
                {{ $t("map.data_empty") }}
            </div>
            <div
                v-for="item in announces"
                :key="item.destination_hash"
                class="rounded-lg border border-sem-border p-2 space-y-1.5"
            >
                <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                        <div class="text-[12px] font-semibold text-sem-fg truncate">
                            {{ item.map_name || $t("map.data_heard_hash") }}
                        </div>
                        <div class="text-[10px] font-mono text-gray-500 truncate">{{ item.destination_hash }}</div>
                        <div class="text-[10px] text-gray-500">
                            {{ $t("map.data_maps_count", { count: item.map_count || 0 }) }}
                        </div>
                    </div>
                    <button
                        type="button"
                        class="text-[10px] font-semibold text-sem-accent shrink-0 disabled:opacity-40"
                        :disabled="busyHash === item.destination_hash"
                        @click="openCatalog(item)"
                    >
                        {{
                            busyHash === item.destination_hash
                                ? $t("map.data_catalog_loading")
                                : $t("map.data_fetch_catalog")
                        }}
                    </button>
                </div>
                <div v-if="catalogLoaded(item.destination_hash)" class="space-y-1 border-t border-sem-border pt-1">
                    <p v-if="!(catalogs[item.destination_hash] || []).length" class="text-[10px] text-sem-fg-muted">
                        {{ $t("map.data_catalog_empty") }}
                    </p>
                    <div
                        v-for="entry in catalogs[item.destination_hash]"
                        :key="entry.id"
                        class="flex items-center justify-between gap-2"
                    >
                        <div class="min-w-0">
                            <div class="text-[11px] truncate">{{ entry.name }}</div>
                            <div class="text-[9px] text-gray-500">
                                {{ entry.format }} · {{ formatSize(entry.size) }}
                            </div>
                        </div>
                        <button
                            type="button"
                            class="text-[10px] font-semibold bg-blue-500 text-white rounded px-2 py-1 disabled:opacity-40"
                            :disabled="busyHash === item.destination_hash + entry.id"
                            @click="addOverlay(item.destination_hash, entry.id)"
                        >
                            {{ $t("map.data_add_overlay") }}
                        </button>
                    </div>
                </div>
            </div>
        </template>
    </div>
</template>

<script>
import ToastUtils from "../../../js/ToastUtils";
import { onWsEvent, offWsEvent } from "../../../js/registries/wsEventRegistry.js";

function errorMessage(t, code) {
    if (code === "missing_path") {
        return t("map.data_missing_path");
    }
    if (code === "unavailable" || code === "link_unavailable") {
        return t("map.data_unavailable");
    }
    if (code === "request_failed" || code === "empty_response") {
        return t("map.data_request_failed");
    }
    if (code === "job_timeout") {
        return t("map.data_job_timeout");
    }
    if (code === "invalid_catalog" || code === "invalid_response") {
        return t("map.data_invalid_catalog");
    }
    if (code === "link_failed") {
        return t("map.data_link_failed");
    }
    return t("map.remote_overlays_error");
}

export default {
    name: "MapDiscoverPanel",
    props: {
        listenEnabled: { type: Boolean, default: false },
    },
    emits: ["overlays-changed", "enable-listen"],
    data() {
        return {
            search: "",
            announces: [],
            catalogs: {},
            loading: false,
            error: "",
            busyHash: "",
            reloadTimer: null,
        };
    },
    watch: {
        listenEnabled: {
            immediate: true,
            handler(enabled) {
                if (enabled) {
                    this.reload();
                } else {
                    this.announces = [];
                    this.catalogs = {};
                    this.error = "";
                }
            },
        },
    },
    mounted() {
        this.onAnnounce = (payload) => {
            if (!this.listenEnabled) {
                return;
            }
            const aspect = payload?.announce?.aspect;
            if (aspect === "map-data-v1") {
                this.reload();
            }
        };
        onWsEvent("announce", this.onAnnounce);
    },
    beforeUnmount() {
        offWsEvent("announce", this.onAnnounce);
        if (this.reloadTimer) {
            clearTimeout(this.reloadTimer);
        }
    },
    methods: {
        catalogLoaded(hash) {
            return Object.prototype.hasOwnProperty.call(this.catalogs, hash);
        },
        catalogToastKey(hash) {
            return `map-catalog-${hash}`;
        },
        formatSize(n) {
            const v = Number(n) || 0;
            if (v < 1024) {
                return `${v} B`;
            }
            return `${(v / 1024).toFixed(1)} KiB`;
        },
        reload() {
            if (this.reloadTimer) {
                clearTimeout(this.reloadTimer);
            }
            this.reloadTimer = setTimeout(() => this.loadHeard(), 200);
        },
        async loadHeard() {
            if (!this.listenEnabled) {
                this.announces = [];
                this.loading = false;
                return;
            }
            this.loading = true;
            this.error = "";
            try {
                const response = await window.api.get("/api/v1/map/data/heard", {
                    params: { search: this.search || undefined, limit: 250 },
                });
                this.announces = response.data.announces || [];
            } catch (e) {
                this.error = errorMessage(this.$t.bind(this), e.response?.data?.error);
            } finally {
                this.loading = false;
            }
        },
        async openCatalog(item) {
            const hash = item.destination_hash;
            this.busyHash = hash;
            this.error = "";
            const toastKey = this.catalogToastKey(hash);
            ToastUtils.loading(this.$t("map.data_catalog_loading"), 0, toastKey);
            try {
                const response = await window.api.post("/api/v1/map/data/catalog", {
                    destination_hash: hash,
                });
                const maps = response.data.maps || [];
                this.catalogs = {
                    ...this.catalogs,
                    [hash]: maps,
                };
                ToastUtils.dismiss(toastKey);
                if (maps.length) {
                    ToastUtils.success(this.$t("map.data_catalog_ok", { count: maps.length }));
                } else {
                    ToastUtils.info(this.$t("map.data_catalog_empty"));
                }
            } catch (e) {
                ToastUtils.dismiss(toastKey);
                const code = e.response?.data?.error;
                this.error = errorMessage(this.$t.bind(this), code);
                ToastUtils.warning(this.error);
            } finally {
                this.busyHash = "";
            }
        },
        async addOverlay(destinationHash, mapId) {
            this.busyHash = destinationHash + mapId;
            try {
                await window.api.post("/api/v1/map/data/add-overlay", {
                    destination_hash: destinationHash,
                    map_id: mapId,
                });
                ToastUtils.success(this.$t("map.remote_overlays_copied"));
                this.$emit("overlays-changed");
            } catch (e) {
                const code = e.response?.data?.error;
                const msg = errorMessage(this.$t.bind(this), code);
                ToastUtils.error(msg);
            } finally {
                this.busyHash = "";
            }
        },
    },
};
</script>
