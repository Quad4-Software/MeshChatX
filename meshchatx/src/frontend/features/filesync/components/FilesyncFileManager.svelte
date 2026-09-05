<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import DownloadUtils from "../../../js/DownloadUtils.js";
    import DialogUtils from "../../../js/DialogUtils.js";
    import { t } from "../../../js/i18n.js";
    import {
        deleteFilesyncEntry,
        fetchFilesyncContent,
        fetchFilesyncTree,
        mkdirFilesyncFolder,
        uploadFilesyncFile,
    } from "../lib/filesyncApi.js";
    import { formatFileSize, joinPath } from "../lib/filesyncFormat.js";
    import type { FilesyncTreeEntry } from "../lib/types.js";

    interface Props {
        syncDirectory?: string;
        onOpenFolder?: () => void;
    }

    let { syncDirectory = "", onOpenFolder }: Props = $props();

    let busy = $state(false);
    let currentPath = $state("");
    let parentPath = $state<string | null>(null);
    let entries = $state<FilesyncTreeEntry[]>([]);
    let newFolderName = $state("");
    let fileInput = $state<HTMLInputElement | null>(null);

    const breadcrumbLabel = $derived.by(() => {
        if (!currentPath) {
            return t("rns_filesync.manager_root");
        }
        return currentPath;
    });

    let prevSyncDir = "";
    $effect(() => {
        if (syncDirectory !== prevSyncDir) {
            prevSyncDir = syncDirectory;
            currentPath = "";
            void refresh();
        }
    });

    export async function refresh(): Promise<void> {
        busy = true;
        try {
            const data = await fetchFilesyncTree(currentPath || undefined);
            entries = data.entries;
            currentPath = data.current;
            parentPath = data.parent;
        } catch (err: unknown) {
            const error = err as { response?: { data?: { message?: string } }; message?: string };
            entries = [];
            ToastUtils.error(error?.response?.data?.message || error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    function enterDir(path: string): void {
        currentPath = String(path || "");
        void refresh();
    }

    function goUp(): void {
        if (parentPath === null || parentPath === undefined) {
            return;
        }
        currentPath = parentPath === "" ? "" : String(parentPath);
        void refresh();
    }

    function triggerUpload(): void {
        fileInput?.click();
    }

    async function onUploadSelected(event: Event): Promise<void> {
        const target = event.target as HTMLInputElement | null;
        const file = target?.files?.[0];
        if (!file) {
            return;
        }
        busy = true;
        try {
            const formData = new FormData();
            formData.append("file", file);
            if (currentPath) {
                formData.append("path", currentPath);
            }
            await uploadFilesyncFile(formData);
            ToastUtils.success(t("rns_filesync.upload_done"));
            await refresh();
        } catch (err: unknown) {
            const error = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(error?.response?.data?.message || error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
            if (target) {
                target.value = "";
            }
        }
    }

    async function createFolder(): Promise<void> {
        const name = String(newFolderName || "").trim();
        if (!name) {
            return;
        }
        busy = true;
        try {
            const path = joinPath(currentPath, name);
            await mkdirFilesyncFolder(path);
            ToastUtils.success(t("rns_filesync.browser_created"));
            newFolderName = "";
            await refresh();
        } catch (err: unknown) {
            const error = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(error?.response?.data?.message || error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function downloadEntry(entry: FilesyncTreeEntry): Promise<void> {
        const path = entry?.path;
        if (!path) {
            return;
        }
        busy = true;
        try {
            const response = await fetchFilesyncContent(path);
            await DownloadUtils.downloadFromApiResponse(response, entry.name || "download");
            ToastUtils.success(t("rns_filesync.download_local_done"));
        } catch (err: unknown) {
            const error = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(error?.response?.data?.message || error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    async function deleteEntry(entry: FilesyncTreeEntry): Promise<void> {
        const path = entry?.path;
        if (!path) {
            return;
        }
        const label = entry.name || path;
        if (!(await DialogUtils.confirm(t("rns_filesync.delete_confirm", { name: label })))) {
            return;
        }
        busy = true;
        try {
            await deleteFilesyncEntry(path);
            ToastUtils.success(t("rns_filesync.delete_done"));
            await refresh();
        } catch (err: unknown) {
            const error = err as { response?: { data?: { message?: string } }; message?: string };
            ToastUtils.error(error?.response?.data?.message || error?.message || t("rns_filesync.error"));
        } finally {
            busy = false;
        }
    }

    onMount(() => {
        void refresh();
    });
</script>

<div class="space-y-4">
    <p class="text-sm text-sem-fg-muted">{t("rns_filesync.manager_help")}</p>

    <div class="flex flex-wrap items-center gap-2">
        <button
            type="button"
            class="secondary-chip px-3 py-1.5 text-sm"
            disabled={busy || currentPath === ""}
            title={t("rns_filesync.browser_up")}
            onclick={goUp}
        >
            <MaterialDesignIcon iconName="arrow-up" class="w-4 h-4" />
            {t("rns_filesync.browser_up")}
        </button>
        <button type="button" class="secondary-chip px-3 py-1.5 text-sm" disabled={busy} onclick={refresh}>
            {t("rns_filesync.refresh")}
        </button>
        <button type="button" class="secondary-chip px-3 py-1.5 text-sm" disabled={busy} onclick={triggerUpload}>
            <MaterialDesignIcon iconName="upload" class="w-4 h-4" />
            {t("rns_filesync.upload")}
        </button>
        <button
            type="button"
            class="secondary-chip px-3 py-1.5 text-sm"
            disabled={busy || !syncDirectory}
            onclick={onOpenFolder}
        >
            <MaterialDesignIcon iconName="folder-open-outline" class="w-4 h-4" />
            {t("rns_filesync.open_folder")}
        </button>
        <input bind:this={fileInput} type="file" class="hidden" onchange={onUploadSelected} />
    </div>

    <div class="input-field py-2! font-mono text-xs truncate" title={breadcrumbLabel}>
        {breadcrumbLabel}
    </div>

    <div class="flex flex-col sm:flex-row gap-2">
        <input
            bind:value={newFolderName}
            type="text"
            class="input-field flex-1 min-w-0 text-sm"
            placeholder={t("rns_filesync.browser_new_placeholder")}
            disabled={busy}
            onkeydown={(e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    void createFolder();
                }
            }}
        />
        <button
            type="button"
            class="secondary-chip px-3 py-2 text-sm shrink-0"
            disabled={busy || !newFolderName.trim()}
            onclick={createFolder}
        >
            <MaterialDesignIcon iconName="folder-plus-outline" class="w-4 h-4" />
            {t("rns_filesync.browser_new")}
        </button>
    </div>

    {#if busy && entries.length === 0}
        <div class="text-sm text-sem-fg-muted">
            {t("rns_filesync.manager_loading")}
        </div>
    {:else if entries.length === 0}
        <div class="text-sm text-sem-fg-muted">
            {t("rns_filesync.manager_empty")}
        </div>
    {:else}
        <ul class="space-y-2">
            {#each entries as entry (entry.path)}
                <li
                    class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-lg border border-sem-border"
                >
                    {#if entry.type === "dir"}
                        <button
                            type="button"
                            class="min-w-0 flex items-center gap-2 text-left text-sm text-sem-fg hover:text-emerald-600 dark:hover:text-emerald-400"
                            onclick={() => enterDir(entry.path)}
                        >
                            <MaterialDesignIcon
                                iconName="folder"
                                class="w-5 h-5 shrink-0 text-emerald-600 dark:text-emerald-400"
                            />
                            <span class="break-all">{entry.name}</span>
                        </button>
                    {:else}
                        <div class="min-w-0 flex items-center gap-2 text-sm text-sem-fg">
                            <MaterialDesignIcon iconName="file-outline" class="w-5 h-5 shrink-0 text-sem-fg-muted" />
                            <div class="min-w-0">
                                <div class="break-all">{entry.name}</div>
                                <div class="text-xs text-sem-fg-muted mt-0.5">
                                    {formatFileSize(entry.size)}
                                </div>
                            </div>
                        </div>
                    {/if}
                    <div class="flex flex-wrap gap-2 shrink-0">
                        {#if entry.type === "file"}
                            <button
                                type="button"
                                class="secondary-chip px-3 py-1.5 text-sm"
                                disabled={busy}
                                onclick={() => downloadEntry(entry)}
                            >
                                {t("rns_filesync.download_local")}
                            </button>
                        {/if}
                        <button
                            type="button"
                            class="secondary-chip px-3 py-1.5 text-sm text-red-600 dark:text-red-300"
                            disabled={busy}
                            onclick={() => deleteEntry(entry)}
                        >
                            {t("rns_filesync.delete")}
                        </button>
                    </div>
                </li>
            {/each}
        </ul>
    {/if}
</div>
