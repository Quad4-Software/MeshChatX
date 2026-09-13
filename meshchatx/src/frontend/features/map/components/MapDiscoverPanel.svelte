<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import { onWsEvent, offWsEvent } from "../../../js/registries/wsEventRegistry.js";
    import { t } from "../../../js/i18n.js";

    interface AnnounceItem {
        destination_hash: string;
        map_name?: string;
        map_count?: number;
        [key: string]: unknown;
    }

    interface CatalogEntry {
        id: string;
        name: string;
        format: string;
        size: number;
        [key: string]: unknown;
    }

    interface Props {
        listenEnabled?: boolean;
        onoverlayschanged?: () => void;
        onenablelisten?: () => void;
    }

    let { listenEnabled = false, onoverlayschanged, onenablelisten }: Props = $props();

    let search = $state("");
    let announces = $state<AnnounceItem[]>([]);
    let catalogs = $state<Record<string, CatalogEntry[]>>({});
    let loading = $state(false);
    let error = $state("");
    let busyHash = $state("");
    let reloadTimer: ReturnType<typeof setTimeout> | null = null;

    function errorMessage(code?: string): string {
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

    function catalogLoaded(hash: string): boolean {
        return Object.prototype.hasOwnProperty.call(catalogs, hash);
    }

    function catalogToastKey(hash: string): string {
        return `map-catalog-${hash}`;
    }

    function formatSize(n: number | string): string {
        const v = Number(n) || 0;
        if (v < 1024) {
            return `${v} B`;
        }
        return `${(v / 1024).toFixed(1)} KiB`;
    }

    export function reload() {
        if (reloadTimer) {
            clearTimeout(reloadTimer);
        }
        reloadTimer = setTimeout(() => loadHeard(), 200);
    }

    async function loadHeard() {
        if (!listenEnabled) {
            announces = [];
            loading = false;
            return;
        }
        loading = true;
        error = "";
        try {
            const response = await window.api.get("/api/v1/map/data/heard", {
                params: { search: search || undefined, limit: 250 },
            });
            const resData = response?.data || response;
            announces = resData?.announces || [];
        } catch (e: any) {
            error = errorMessage(e?.response?.data?.error);
        } finally {
            loading = false;
        }
    }

    async function openCatalog(item: AnnounceItem) {
        const hash = item.destination_hash;
        busyHash = hash;
        error = "";
        const toastKey = catalogToastKey(hash);
        ToastUtils.loading(t("map.data_catalog_loading"), 0, toastKey);
        try {
            const response = await window.api.post("/api/v1/map/data/catalog", {
                destination_hash: hash,
            });
            const resData = response?.data || response;
            const maps = resData?.maps || [];
            catalogs = {
                ...catalogs,
                [hash]: maps,
            };
            ToastUtils.dismiss(toastKey);
            if (maps.length) {
                ToastUtils.success(t("map.data_catalog_ok", { count: maps.length }));
            } else {
                ToastUtils.info(t("map.data_catalog_empty"));
            }
        } catch (e: any) {
            ToastUtils.dismiss(toastKey);
            const code = e?.response?.data?.error;
            error = errorMessage(code);
            ToastUtils.warning(error);
        } finally {
            busyHash = "";
        }
    }

    async function addOverlay(destinationHash: string, mapId: string) {
        busyHash = destinationHash + mapId;
        try {
            await window.api.post("/api/v1/map/data/add-overlay", {
                destination_hash: destinationHash,
                map_id: mapId,
            });
            ToastUtils.success(t("map.remote_overlays_copied"));
            onoverlayschanged?.();
        } catch (e: any) {
            const code = e?.response?.data?.error;
            const msg = errorMessage(code);
            ToastUtils.error(msg);
        } finally {
            busyHash = "";
        }
    }

    function onAnnounce(payload: any) {
        if (!listenEnabled) return;
        const aspect = payload?.announce?.aspect;
        if (aspect === "map-data-v1") {
            reload();
        }
    }

    function onWebsocketReconnected() {
        if (listenEnabled) {
            reload();
        }
    }

    $effect(() => {
        if (listenEnabled) {
            reload();
        } else {
            announces = [];
            catalogs = {};
            error = "";
        }
    });

    onMount(() => {
        onWsEvent("announce", onAnnounce);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);
    });

    onDestroy(() => {
        offWsEvent("announce", onAnnounce);
        GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
        if (reloadTimer) {
            clearTimeout(reloadTimer);
        }
    });
</script>

<div class="space-y-3">
    {#if !listenEnabled}
        <div class="rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3 space-y-2">
            <p class="text-[11px] text-sem-fg-muted leading-snug">{t("map.data_listen_off")}</p>
            <button
                type="button"
                class="w-full py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-blue-500 hover:bg-blue-600 text-white cursor-pointer"
                onclick={() => onenablelisten?.()}
            >
                {t("map.data_listen_enable")}
            </button>
        </div>
    {:else}
        <input
            bind:value={search}
            type="search"
            class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[12px]"
            placeholder={t("map.data_search")}
            oninput={reload}
        />
        {#if error}
            <p class="text-[11px] text-amber-600 dark:text-amber-400">{error}</p>
        {/if}
        {#if !announces.length && !loading}
            <div class="text-[11px] text-sem-fg-muted">
                {t("map.data_empty")}
            </div>
        {/if}
        {#each announces as item (item.destination_hash)}
            <div class="rounded-lg border border-sem-border p-2 space-y-1.5">
                <div class="flex items-start justify-between gap-2">
                    <div class="min-w-0">
                        <div class="text-[12px] font-semibold text-sem-fg truncate">
                            {item.map_name || t("map.data_heard_hash")}
                        </div>
                        <div class="text-[10px] font-mono text-gray-500 truncate">{item.destination_hash}</div>
                        <div class="text-[10px] text-gray-500">
                            {t("map.data_maps_count", { count: item.map_count || 0 })}
                        </div>
                    </div>
                    <button
                        type="button"
                        class="text-[10px] font-semibold text-sem-accent shrink-0 disabled:opacity-40 cursor-pointer"
                        disabled={busyHash === item.destination_hash}
                        onclick={() => openCatalog(item)}
                    >
                        {busyHash === item.destination_hash
                            ? t("map.data_catalog_loading")
                            : t("map.data_fetch_catalog")}
                    </button>
                </div>
                {#if catalogLoaded(item.destination_hash)}
                    <div class="space-y-1 border-t border-sem-border pt-1">
                        {#if !(catalogs[item.destination_hash] || []).length}
                            <p class="text-[10px] text-sem-fg-muted">
                                {t("map.data_catalog_empty")}
                            </p>
                        {/if}
                        {#each catalogs[item.destination_hash] || [] as entry (entry.id)}
                            <div class="flex items-center justify-between gap-2">
                                <div class="min-w-0">
                                    <div class="text-[11px] truncate">{entry.name}</div>
                                    <div class="text-[9px] text-gray-500">
                                        {entry.format} · {formatSize(entry.size)}
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    class="text-[10px] font-semibold bg-blue-500 text-white rounded px-2 py-1 disabled:opacity-40 cursor-pointer"
                                    disabled={busyHash === item.destination_hash + entry.id}
                                    onclick={() => addOverlay(item.destination_hash, entry.id)}
                                >
                                    {t("map.data_add_overlay")}
                                </button>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        {/each}
    {/if}
</div>
