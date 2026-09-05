<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";

    interface Props {
        drawSource?: any;
    }

    let { drawSource: _drawSource = null }: Props = $props();

    let displayName = $state("Maps");
    let announceEnabled = $state(false);
    let announceInterval = $state(900);
    let published = $state<any[]>([]);
    let strippedPreview = $state<string[]>([]);
    let publishing = $state(false);
    let announcing = $state(false);
    let fileInput = $state<HTMLInputElement | null>(null);

    async function fileToB64(file: File): Promise<string> {
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

    function hintedFormat(name: string) {
        const lower = String(name || "").toLowerCase();
        if (lower.endsWith(".kmz")) return "kmz";
        if (lower.endsWith(".kml")) return "kml";
        return "geojson";
    }

    function formatSize(n: number | string) {
        const v = Number(n) || 0;
        if (v < 1024) return `${v} B`;
        return `${(v / 1024).toFixed(1)} KiB`;
    }

    export async function load() {
        const api = (window as any).api;
        if (!api) return;
        try {
            const status = await api.get("/api/v1/map/data/status");
            const s = status.data || {};
            displayName = s.display_name || "Maps";
            announceEnabled = Boolean(s.announce_enabled);
            announceInterval = s.announce_interval || 900;
            const listed = await api.get("/api/v1/map/data/published");
            published = listed.data?.maps || [];
        } catch {
            ToastUtils.error(t("map.data_unavailable"));
        }
    }

    export async function saveConfig() {
        const api = (window as any).api;
        if (!api) return;
        try {
            await api.patch("/api/v1/map/data/config", {
                display_name: displayName,
                announce_enabled: announceEnabled,
                announce_interval: announceInterval,
            });
        } catch {
            ToastUtils.error(t("map.data_unavailable"));
        }
    }

    function pickFile() {
        fileInput?.click();
    }

    async function onFile(ev: Event) {
        const input = ev.target as HTMLInputElement;
        const file = input.files && input.files[0];
        input.value = "";
        if (!file) return;
        publishing = true;
        strippedPreview = [];
        const api = (window as any).api;
        if (!api) return;
        try {
            const dataB64 = await fileToB64(file);
            const response = await api.post("/api/v1/map/data/publish", {
                name: file.name.replace(/\.[^.]+$/, "") || "map",
                format: hintedFormat(file.name),
                data_b64: dataB64,
            });
            strippedPreview = response.data?.stripped || [];
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
            publishing = false;
        }
    }

    export async function announceNow() {
        if (!published.length) {
            ToastUtils.warning(t("map.data_announce_needs_publish"));
            return;
        }
        announcing = true;
        const api = (window as any).api;
        if (!api) return;
        try {
            await api.post("/api/v1/map/data/announce");
            ToastUtils.success(t("map.data_announce_ok"));
        } catch (e: any) {
            const code = e.response?.data?.error;
            if (code === "nothing_published") {
                ToastUtils.warning(t("map.data_announce_needs_publish"));
            } else {
                ToastUtils.error(t("map.data_unavailable"));
            }
        } finally {
            announcing = false;
        }
    }

    export async function unpublish(mapId: string) {
        const api = (window as any).api;
        if (!api) return;
        try {
            await api.delete(`/api/v1/map/data/published/${mapId}`);
            ToastUtils.success(t("map.data_unpublish_ok"));
            await load();
        } catch {
            ToastUtils.error(t("map.data_unavailable"));
        }
    }

    onMount(() => {
        load();
    });
</script>

<div class="space-y-3">
    <label class="block text-[11px] text-sem-fg-muted space-y-1">
        <span>{t("map.data_display_name")}</span>
        <input
            bind:value={displayName}
            type="text"
            maxlength={32}
            class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[12px] text-sem-fg"
            onblur={saveConfig}
        />
    </label>
    <label class="flex items-center gap-2 text-[11px] text-sem-fg-muted cursor-pointer">
        <input type="checkbox" bind:checked={announceEnabled} disabled={!published.length} onchange={saveConfig} />
        {t("map.data_announce")}
    </label>
    {#if !published.length}
        <p class="text-[10px] text-sem-fg-muted">
            {t("map.data_announce_needs_publish")}
        </p>
    {/if}
    <label class="block text-[11px] text-sem-fg-muted space-y-1">
        <span>{t("map.data_interval")}</span>
        <input
            bind:value={announceInterval}
            type="number"
            min="10"
            class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[12px] text-sem-fg"
            onblur={saveConfig}
        />
    </label>
    <div class="flex gap-2">
        <button
            type="button"
            class="flex-1 py-2 text-[10px] font-semibold uppercase rounded-lg bg-blue-500 text-white disabled:opacity-40 cursor-pointer"
            disabled={publishing}
            onclick={pickFile}
        >
            {t("map.data_publish")}
        </button>
        <button
            type="button"
            class="flex-1 py-2 text-[10px] font-semibold uppercase rounded-lg border border-sem-border disabled:opacity-40 cursor-pointer"
            disabled={announcing || !published.length}
            onclick={announceNow}
        >
            {t("map.data_announce_now")}
        </button>
    </div>
    <input bind:this={fileInput} type="file" accept=".geojson,.json,.kml,.kmz" class="hidden" onchange={onFile} />
    {#if strippedPreview.length}
        <p class="text-[10px] text-amber-600 dark:text-amber-400">
            {t("map.data_stripped")}: {strippedPreview.join(", ")}
        </p>
    {/if}
    {#if !published.length}
        <div class="text-[11px] text-gray-500">{t("map.data_no_published")}</div>
    {/if}
    {#each published as row (row.map_id)}
        <div class="rounded-lg border border-sem-border p-2 flex items-center justify-between gap-2">
            <div class="min-w-0">
                <div class="text-[12px] font-semibold truncate text-sem-fg">{row.name}</div>
                <div class="text-[9px] text-gray-500">
                    {row.format} · {t("map.data_published_size", { size: formatSize(row.size) })}
                </div>
            </div>
            <button
                type="button"
                class="text-[10px] text-red-500 font-semibold cursor-pointer"
                onclick={() => unpublish(row.map_id)}
            >
                {t("map.data_unpublish")}
            </button>
        </div>
    {/each}
</div>
