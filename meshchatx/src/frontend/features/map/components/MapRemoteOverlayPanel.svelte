<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { t } from "../../../js/i18n.js";

    interface Props {
        disabled?: boolean;
        onOverlaysChanged?: (overlays: any[]) => void;
        onExportOverlay?: (detail: { id: string | number; format: string }) => void;
        onCopyOverlayToDrawings?: (overlay: any) => void;
        onError?: (err: any) => void;
    }

    let { disabled = false, onOverlaysChanged, onExportOverlay, onCopyOverlayToDrawings, onError }: Props = $props();

    let kind = $state("nomadnet_file");
    let url = $state("");
    let pathsText = $state("");
    let refName = $state("HEAD");
    let refreshInterval = $state(0);
    let overlays = $state<any[]>([]);
    let loading = $state(false);
    let importing = $state(false);
    let jobPhase = $state("");
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let jobGeneration = 0;

    function clearPoll() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    export async function reload() {
        loading = true;
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.get("/api/v1/map/overlays");
            overlays = res?.overlays || res?.data?.overlays || [];
            onOverlaysChanged?.(overlays);
        } catch (e) {
            onError?.(e);
        } finally {
            loading = false;
        }
    }

    export async function importSources() {
        const body: Record<string, any> = {
            kind,
            url: url.trim(),
            refresh_interval_seconds: Number(refreshInterval) || 0,
        };
        if (kind === "rngit_files") {
            body.ref = refName || "HEAD";
            body.paths = pathsText
                .split("\n")
                .map((l) => l.trim())
                .filter(Boolean);
        }
        importing = true;
        jobPhase = "queued";
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.post("/api/v1/map/overlays", body);
            overlays = res?.overlays || res?.data?.overlays || overlays;
            onOverlaysChanged?.(overlays);
            const jobId = res?.job_id || res?.data?.job_id;
            if (jobId) {
                watchJob(jobId);
            }
        } catch (e) {
            onError?.(e);
            importing = false;
            jobPhase = "";
        }
    }

    function watchJob(jobId: string) {
        clearPoll();
        const gen = ++jobGeneration;
        const api = (window as any).api;
        pollTimer = setInterval(async () => {
            if (gen !== jobGeneration) return;
            try {
                const res = await api.get(`/api/v1/map/overlays/jobs/${jobId}`);
                const job = res?.data || res;
                if (gen !== jobGeneration) return;
                jobPhase = job?.phase || job?.status || "";
                if (job?.status === "success" || job?.status === "error" || job?.status === "cancelled") {
                    clearPoll();
                    importing = false;
                    await reload();
                    if (job.status !== "success") {
                        onError?.(job.error || job.status);
                    }
                }
            } catch (e) {
                clearPoll();
                importing = false;
                onError?.(e);
            }
        }, 1000);
    }

    export async function refresh(overlay: any) {
        const api = (window as any).api;
        if (!api) return;
        try {
            const res = await api.post(`/api/v1/map/overlays/${overlay.id}/refresh`, {});
            const jobId = res?.job_id || res?.data?.job_id;
            if (jobId) {
                importing = true;
                watchJob(jobId);
            }
        } catch (e) {
            onError?.(e);
        }
    }

    export async function toggleVisible(overlay: any, visible: boolean) {
        const api = (window as any).api;
        if (!api) return;
        try {
            await api.patch(`/api/v1/map/overlays/${overlay.id}`, { visible: Boolean(visible) });
            await reload();
        } catch (e) {
            onError?.(e);
        }
    }

    export async function remove(overlay: any) {
        const api = (window as any).api;
        if (!api) return;
        try {
            await api.delete(`/api/v1/map/overlays/${overlay.id}`);
            await reload();
        } catch (e) {
            onError?.(e);
        }
    }

    onMount(() => {
        reload();
    });

    onDestroy(() => {
        clearPoll();
    });
</script>

<div class="space-y-3 rounded-xl border border-sem-border bg-gray-50/50 dark:bg-zinc-900/40 p-3">
    <div class="flex items-center justify-between gap-2">
        <span class="text-[10px] font-bold text-sem-fg-muted uppercase tracking-widest">
            {t("map.remote_overlays_title")}
        </span>
        <button
            type="button"
            class="text-[10px] font-bold uppercase text-sem-accent disabled:opacity-40 cursor-pointer"
            disabled={loading || disabled}
            onclick={reload}
        >
            {t("map.remote_overlays_reload")}
        </button>
    </div>

    <div class="grid grid-cols-1 gap-2">
        <label class="text-[10px] text-sem-fg-muted space-y-1">
            <span>{t("map.remote_overlays_kind")}</span>
            <select
                bind:value={kind}
                class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px] text-sem-fg"
            >
                <option value="nomadnet_file">NomadNet /file/</option>
                <option value="rngit_files">RNGit sparse</option>
            </select>
        </label>
        <label class="text-[10px] text-sem-fg-muted space-y-1">
            <span>{t("map.remote_overlays_url")}</span>
            <input
                bind:value={url}
                type="text"
                class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px] text-sem-fg"
                placeholder={kind === "rngit_files" ? "rns://hash/group/repo" : "hash:/file/maps/layer.geojson"}
            />
        </label>
        {#if kind === "rngit_files"}
            <label class="text-[10px] text-sem-fg-muted space-y-1">
                <span>{t("map.remote_overlays_paths")}</span>
                <textarea
                    bind:value={pathsText}
                    rows="3"
                    class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px] font-mono text-sem-fg"
                    placeholder="maps/layer.geojson"></textarea>
            </label>
            <label class="text-[10px] text-sem-fg-muted space-y-1">
                <span>{t("map.remote_overlays_ref")}</span>
                <input
                    bind:value={refName}
                    type="text"
                    class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px] text-sem-fg"
                    placeholder="HEAD / tag / commit"
                />
            </label>
        {/if}
        <label class="text-[10px] text-sem-fg-muted space-y-1">
            <span>{t("map.remote_overlays_refresh_interval")}</span>
            <input
                bind:value={refreshInterval}
                type="number"
                min="0"
                class="w-full rounded-lg border border-sem-border bg-sem-surface px-2 py-1.5 text-[11px] text-sem-fg"
            />
        </label>
        <button
            type="button"
            class="py-2 px-2 text-[10px] font-bold uppercase rounded-lg bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-40 cursor-pointer"
            disabled={disabled || importing || !url.trim()}
            onclick={importSources}
        >
            {importing ? t("map.remote_overlays_importing") : t("map.remote_overlays_import")}
        </button>
        {#if jobPhase}
            <p class="text-[9px] text-sem-fg-muted">{jobPhase}</p>
        {/if}
    </div>

    {#if overlays.length}
        <div class="space-y-2 border-t border-sem-border pt-2">
            {#each overlays as overlay (overlay.id)}
                <div class="rounded-lg border border-sem-border bg-sem-surface/60 p-2 space-y-1.5">
                    <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0">
                            <div class="text-[11px] font-semibold text-sem-fg truncate">
                                {overlay.name}
                            </div>
                            <div class="text-[9px] text-sem-fg-muted truncate">
                                {overlay.kind} · {overlay.status}
                                {#if overlay.format}
                                    <span> · {overlay.format}</span>
                                {/if}
                            </div>
                            {#if overlay.last_error}
                                <div class="text-[9px] text-red-500 truncate">
                                    {overlay.last_error}
                                </div>
                            {/if}
                        </div>
                        <label class="flex items-center gap-1 text-[9px] text-gray-500 shrink-0 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={Boolean(overlay.visible)}
                                onchange={(e) => toggleVisible(overlay, (e.target as HTMLInputElement).checked)}
                            />
                            {t("map.remote_overlays_visible")}
                        </label>
                    </div>
                    <div class="flex flex-wrap gap-1">
                        <button
                            type="button"
                            class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted cursor-pointer"
                            {disabled}
                            onclick={() => refresh(overlay)}
                        >
                            {t("map.remote_overlays_refresh")}
                        </button>
                        <button
                            type="button"
                            class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted cursor-pointer"
                            disabled={disabled || overlay.status !== "ready"}
                            onclick={() => onExportOverlay?.({ id: overlay.id, format: "geojson" })}
                        >
                            GeoJSON
                        </button>
                        <button
                            type="button"
                            class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted cursor-pointer"
                            disabled={disabled || overlay.status !== "ready"}
                            onclick={() => onExportOverlay?.({ id: overlay.id, format: "kml" })}
                        >
                            KML
                        </button>
                        <button
                            type="button"
                            class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted cursor-pointer"
                            disabled={disabled || overlay.status !== "ready"}
                            onclick={() => onExportOverlay?.({ id: overlay.id, format: "kmz" })}
                        >
                            KMZ
                        </button>
                        <button
                            type="button"
                            class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-sem-surface-muted cursor-pointer"
                            disabled={disabled || overlay.status !== "ready"}
                            onclick={() => onCopyOverlayToDrawings?.(overlay)}
                        >
                            {t("map.remote_overlays_copy_drawings")}
                        </button>
                        <button
                            type="button"
                            class="px-1.5 py-1 text-[9px] font-bold uppercase rounded bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400 cursor-pointer"
                            {disabled}
                            onclick={() => remove(overlay)}
                        >
                            {t("map.remote_overlays_delete")}
                        </button>
                    </div>
                </div>
            {/each}
        </div>
    {:else}
        <p class="text-[9px] text-sem-fg-muted">{t("map.remote_overlays_empty")}</p>
    {/if}
</div>
