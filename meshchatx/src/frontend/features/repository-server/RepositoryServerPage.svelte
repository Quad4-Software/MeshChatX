<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import DialogUtils from "../../js/DialogUtils.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import { t } from "../../js/i18n.js";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import EmptyState from "../../ui/svelte/EmptyState.svelte";
    import LoadingState from "../../ui/svelte/LoadingState.svelte";
    import { DEFAULT_HTTP_HOST, DEFAULT_HTTP_PORT } from "./lib/constants.js";
    import {
        buildHttpBody,
        computeBrowserRepoUrl,
        deleteRepositoryUpload,
        fetchRepositoryList,
        fetchRepositoryStatus,
        formatBytes,
        restartHttpServer,
        resolveHttpErrorMessage,
        startHttpServer,
        stopHttpServer,
        syncHttpFormFromStatus,
        uploadRepositoryPackage,
    } from "./lib/repositoryServer.js";
    import type { RepositoryEntry, RepositoryServerStatus } from "./lib/types.js";

    let loading = $state(true);
    let httpBusy = $state(false);
    let httpHost = $state(DEFAULT_HTTP_HOST);
    let httpPort = $state(DEFAULT_HTTP_PORT);
    let status = $state<RepositoryServerStatus | null>(null);
    let entries = $state<RepositoryEntry[]>([]);
    let lastUploadError = $state<string | null>(null);

    const httpRunning = $derived(Boolean(status?.http?.running));
    const browserRepoUrl = $derived(computeBrowserRepoUrl(status?.http?.url));

    async function loadAll(): Promise<void> {
        loading = true;
        lastUploadError = null;
        try {
            const [s, list] = await Promise.all([fetchRepositoryStatus(), fetchRepositoryList()]);
            status = s;
            entries = list;
            const synced = syncHttpFormFromStatus(status, httpHost, httpPort);
            httpHost = synced.host;
            httpPort = synced.port;
        } catch (e) {
            ToastUtils.error(t("tools.repository_server.load_failed"));
            console.error(e);
        } finally {
            loading = false;
        }
    }

    async function startHttp(): Promise<void> {
        const built = buildHttpBody(httpHost, httpPort);
        if (built.error === "invalid_port") {
            ToastUtils.error(resolveHttpErrorMessage("invalid_port"));
            return;
        }
        httpBusy = true;
        try {
            const data = await startHttpServer(built.body || {});
            if (!data.ok) {
                ToastUtils.error(resolveHttpErrorMessage(data.error, data.message));
            } else {
                ToastUtils.success(t("tools.repository_server.http_started"));
            }
            await loadAll();
        } catch (e) {
            ToastUtils.error(t("tools.repository_server.http_err_generic"));
            console.error(e);
        } finally {
            httpBusy = false;
        }
    }

    async function stopHttp(): Promise<void> {
        httpBusy = true;
        try {
            await stopHttpServer();
            ToastUtils.success(t("tools.repository_server.http_stopped"));
            await loadAll();
        } catch (e) {
            ToastUtils.error(t("tools.repository_server.http_err_generic"));
            console.error(e);
        } finally {
            httpBusy = false;
        }
    }

    async function restartHttp(): Promise<void> {
        const built = buildHttpBody(httpHost, httpPort);
        if (built.error === "invalid_port") {
            ToastUtils.error(resolveHttpErrorMessage("invalid_port"));
            return;
        }
        httpBusy = true;
        try {
            const data = await restartHttpServer(built.body || {});
            if (!data.ok) {
                ToastUtils.error(resolveHttpErrorMessage(data.error, data.message));
            } else {
                ToastUtils.success(t("tools.repository_server.http_restarted"));
            }
            await loadAll();
        } catch (e) {
            ToastUtils.error(t("tools.repository_server.http_err_generic"));
            console.error(e);
        } finally {
            httpBusy = false;
        }
    }

    async function onUpload(ev: Event): Promise<void> {
        const input = ev.target as HTMLInputElement;
        const file = input.files && input.files[0];
        input.value = "";
        if (!file) return;
        lastUploadError = null;
        try {
            await uploadRepositoryPackage(file);
            ToastUtils.success(t("tools.repository_server.upload_ok"));
            await loadAll();
        } catch (e: any) {
            lastUploadError = e?.response?.data?.error || e?.message || t("tools.repository_server.upload_failed");
            ToastUtils.error(t("tools.repository_server.upload_failed"));
        }
    }

    async function deleteUpload(name: string): Promise<void> {
        if (!(await DialogUtils.confirm(t("tools.repository_server.delete_confirm", { name })))) {
            return;
        }
        try {
            await deleteRepositoryUpload(name);
            ToastUtils.success(t("tools.repository_server.delete_ok"));
            await loadAll();
        } catch (e) {
            ToastUtils.error(t("tools.repository_server.delete_failed"));
            console.error(e);
        }
    }

    onMount(async () => {
        await loadAll();
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas" data-testid="repository-server-page">
    <ToolsPageHeader
        icon="package-variant"
        title={t("tools.repository_server.title")}
        description={t("tools.repository_server.description")}
        accent="sky"
    />
    <div class="flex-1 overflow-y-auto overflow-x-hidden w-full px-3 sm:px-5 md:px-5 lg:px-8 py-3 sm:py-4 min-w-0">
        <div class="space-y-0 w-full max-w-6xl xl:max-w-7xl mx-auto min-w-0">
            <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6 space-y-3">
                <h2 class="text-sm font-semibold text-sem-fg">
                    {t("tools.repository_server.http_heading")}
                </h2>
                <div class="flex flex-wrap gap-3 items-end">
                    <label class="flex flex-col gap-1 text-xs min-w-40">
                        <span class="text-sem-fg-muted">{t("tools.repository_server.host_label")}</span>
                        <input
                            bind:value={httpHost}
                            type="text"
                            autocomplete="off"
                            class="input-field"
                            disabled={httpBusy || loading || httpRunning}
                            title={httpRunning ? t("tools.repository_server.stop_before_edit") : undefined}
                        />
                    </label>
                    <label class="flex flex-col gap-1 text-xs w-24">
                        <span class="text-sem-fg-muted">{t("tools.repository_server.port_label")}</span>
                        <input
                            bind:value={httpPort}
                            type="text"
                            inputmode="numeric"
                            autocomplete="off"
                            class="input-field"
                            disabled={httpBusy || loading || httpRunning}
                            title={httpRunning ? t("tools.repository_server.stop_before_edit") : undefined}
                        />
                    </label>
                    <div class="flex flex-wrap gap-2">
                        <button
                            type="button"
                            class="primary-chip focus-ring-sem disabled:opacity-50 disabled:pointer-events-none"
                            disabled={httpBusy || loading || httpRunning}
                            title={httpRunning ? t("tools.repository_server.already_running") : undefined}
                            onclick={startHttp}
                        >
                            <MaterialDesignIcon iconName="play" class="size-4" />
                            {t("tools.repository_server.start_http")}
                        </button>
                        <button
                            type="button"
                            class="secondary-chip focus-ring-sem disabled:opacity-50 disabled:pointer-events-none"
                            disabled={httpBusy || loading || !httpRunning}
                            title={!httpRunning ? t("tools.repository_server.not_running") : undefined}
                            onclick={stopHttp}
                        >
                            <MaterialDesignIcon iconName="stop" class="size-4" />
                            {t("tools.repository_server.stop_http")}
                        </button>
                        <button
                            type="button"
                            class="secondary-chip focus-ring-sem disabled:opacity-50 disabled:pointer-events-none"
                            disabled={httpBusy || loading}
                            onclick={restartHttp}
                        >
                            <MaterialDesignIcon iconName="restart" class="size-4" />
                            {t("tools.repository_server.restart_http")}
                        </button>
                    </div>
                </div>
                {#if httpRunning && status?.http?.url}
                    <div class="text-xs space-y-1">
                        <div class="text-sem-fg-muted">
                            {t("tools.repository_server.http_listen_label")}
                            <span class="font-mono text-gray-900 text-sem-fg">{status.http.url}</span>
                        </div>
                        {#if browserRepoUrl}
                            <a
                                href={browserRepoUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                class="inline-flex items-center gap-1 text-sky-600 dark:text-sky-400 font-medium hover:underline"
                            >
                                <MaterialDesignIcon iconName="open-in-new" class="size-4" />
                                {t("tools.repository_server.open_http")}
                            </a>
                        {/if}
                    </div>
                {/if}
            </div>

            <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6 space-y-3">
                <h2 class="text-sm font-semibold text-sem-fg">
                    {t("tools.repository_server.upload_heading")}
                </h2>
                <div class="flex flex-wrap items-center gap-3">
                    <label class="primary-chip focus-ring-sem cursor-pointer">
                        <MaterialDesignIcon iconName="upload" class="size-4" />
                        {t("tools.repository_server.choose_file")}
                        <input type="file" class="hidden" onchange={onUpload} />
                    </label>
                    {#if lastUploadError}
                        <p class="text-xs text-red-600 dark:text-red-400">
                            {lastUploadError}
                        </p>
                    {/if}
                </div>
            </div>

            {#if status?.last_refresh_failed && Object.keys(status.last_refresh_failed).length > 0}
                <div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-4 sm:py-6">
                    <div
                        class="rounded-xl border border-amber-200 dark:border-amber-900/40 bg-amber-50 dark:bg-amber-950/30 p-3 text-xs text-amber-900 dark:text-amber-200"
                    >
                        <div class="font-semibold mb-1">{t("tools.repository_server.refresh_partial")}</div>
                        <ul class="list-disc pl-4 space-y-1">
                            {#each Object.entries(status.last_refresh_failed) as [pkg, msg] (pkg)}
                                <li>
                                    <span class="font-mono">{pkg}</span>: {msg}
                                </li>
                            {/each}
                        </ul>
                    </div>
                </div>
            {/if}

            <div class="w-full py-4 sm:py-6 space-y-3">
                <div class="flex items-center justify-between">
                    <h2 class="text-sm font-semibold text-sem-fg">
                        {t("tools.repository_server.files_heading")}
                    </h2>
                    <span class="text-xs text-gray-500">{entries.length}</span>
                </div>
                {#if loading}
                    <div class="py-6">
                        <LoadingState message={t("common.loading")} />
                    </div>
                {:else if entries.length === 0}
                    <div class="py-6">
                        <EmptyState icon="package-variant-closed" title={t("tools.repository_server.empty")} plain />
                    </div>
                {:else}
                    <table class="w-full text-left text-xs">
                        <thead
                            class="text-gray-500 uppercase tracking-wide border-b border-gray-200/60 dark:border-zinc-800/60"
                        >
                            <tr>
                                <th class="px-4 py-2 font-semibold">{t("tools.repository_server.col_name")}</th>
                                <th class="px-4 py-2 font-semibold">{t("tools.repository_server.col_source")}</th>
                                <th class="px-4 py-2 font-semibold text-right">
                                    {t("tools.repository_server.col_size")}
                                </th>
                                <th class="px-4 py-2 font-semibold w-24"></th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100 dark:divide-zinc-800/50 text-sem-fg">
                            {#each entries as row (row.name + row.source)}
                                <tr>
                                    <td class="px-4 py-2 font-mono break-all">{row.name}</td>
                                    <td class="px-4 py-2">{row.source}</td>
                                    <td class="px-4 py-2 text-right tabular-nums">{formatBytes(row.bytes)}</td>
                                    <td class="px-4 py-2 text-right">
                                        {#if row.source === "upload"}
                                            <button
                                                type="button"
                                                class="text-red-600 dark:text-red-400 hover:underline text-xs font-medium"
                                                onclick={() => deleteUpload(row.name)}
                                            >
                                                {t("tools.repository_server.delete")}
                                            </button>
                                        {/if}
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                {/if}
            </div>
        </div>
    </div>
</div>
