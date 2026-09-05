<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import { formatProgressLabel } from "../lib/filesyncFormat.js";
    import type { FilesyncProgressPayload, FilesyncStatus } from "../lib/types.js";

    interface Props {
        status: FilesyncStatus;
        syncDirectory: string;
        announceInterval: number;
        monitor: boolean;
        busy: boolean;
        lastProgress: FilesyncProgressPayload | null;
        onOpenBrowser: () => void;
        onUseSharedFolder: () => void;
        onOpenFolder: () => void;
        onStart: () => void;
        onStop: () => void;
        onAnnounce: () => void;
        onRefresh: () => void;
    }

    let {
        status,
        syncDirectory = $bindable(""),
        announceInterval = $bindable(300),
        monitor = $bindable(true),
        busy,
        lastProgress,
        onOpenBrowser,
        onUseSharedFolder,
        onOpenFolder,
        onStart,
        onStop,
        onAnnounce,
        onRefresh,
    }: Props = $props();

    const progressLabel = $derived(formatProgressLabel(lastProgress));

    async function copyHash(hash: string): Promise<void> {
        try {
            await navigator.clipboard.writeText(hash);
            ToastUtils.success(t("rns_filesync.copied"));
        } catch {
            ToastUtils.error(t("rns_filesync.error"));
        }
    }
</script>

<div class="space-y-4">
    <div class="rounded-xl border border-sem-border bg-sem-surface-muted/40 p-4 space-y-4">
        <div class="flex flex-wrap items-center gap-2">
            <span
                class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold {status.running
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                    : 'bg-sem-surface-muted text-sem-fg-muted'}"
            >
                <span class="size-1.5 rounded-full {status.running ? 'bg-emerald-500' : 'bg-sem-fg-muted'}"></span>
                {status.running ? t("rns_filesync.status_syncing") : t("rns_filesync.status_stopped")}
            </span>
            <span class="text-xs text-sem-fg-muted">
                {t("rns_filesync.peers_count")}:
                <strong class="text-sem-fg">{status.peers || 0}</strong>
            </span>
            <span class="text-xs text-sem-fg-muted">
                {t("rns_filesync.files_count")}:
                <strong class="text-sem-fg">{status.files || 0}</strong>
            </span>
        </div>

        <div>
            <label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1" for="rns-filesync-sync-dir"
                >{t("rns_filesync.sync_directory")}</label
            >
            <div class="flex gap-2">
                <input
                    id="rns-filesync-sync-dir"
                    bind:value={syncDirectory}
                    type="text"
                    class="input-field flex-1 min-w-0 font-mono text-sm"
                    disabled={status.running}
                    placeholder={t("rns_filesync.sync_directory_placeholder")}
                />
                <button
                    type="button"
                    class="secondary-chip px-3 py-2 text-xs shrink-0"
                    disabled={busy || status.running}
                    title={t("rns_filesync.browse_folder")}
                    onclick={onOpenBrowser}
                >
                    <MaterialDesignIcon iconName="folder-open-outline" class="w-4 h-4" />
                    <span class="hidden sm:inline">{t("rns_filesync.browse_folder")}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip px-3 py-2 text-xs shrink-0"
                    disabled={busy || status.running}
                    title={t("rns_filesync.use_shared_folder")}
                    onclick={onUseSharedFolder}
                >
                    <MaterialDesignIcon iconName="folder-account-outline" class="w-4 h-4" />
                    <span class="hidden sm:inline">{t("rns_filesync.use_shared_folder")}</span>
                </button>
                <button
                    type="button"
                    class="secondary-chip px-3 py-2 text-xs shrink-0"
                    disabled={busy || !syncDirectory}
                    title={t("rns_filesync.open_folder")}
                    onclick={onOpenFolder}
                >
                    <MaterialDesignIcon iconName="folder" class="w-4 h-4" />
                    <span class="hidden sm:inline">{t("rns_filesync.open_folder")}</span>
                </button>
            </div>
            <p class="mt-1.5 text-xs text-sem-fg-muted">
                {t("rns_filesync.sync_directory_help")}
            </p>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
            <div>
                <label
                    class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1"
                    for="rns-filesync-announce-interval">{t("rns_filesync.announce_interval")}</label
                >
                <input
                    id="rns-filesync-announce-interval"
                    bind:value={announceInterval}
                    type="number"
                    min="10"
                    class="input-field w-full"
                />
                <p class="mt-1 text-xs text-sem-fg-muted">
                    {t("rns_filesync.announce_interval_help")}
                </p>
            </div>
            <div class="flex items-end">
                <label class="flex items-center gap-2 text-sm text-sem-fg pb-2 cursor-pointer">
                    <input bind:checked={monitor} type="checkbox" class="rounded" />
                    {t("rns_filesync.monitor")}
                </label>
            </div>
        </div>

        <div class="flex flex-wrap gap-2">
            {#if !status.running}
                <button type="button" class="primary-chip px-4 py-2 text-sm" disabled={busy} onclick={onStart}>
                    <MaterialDesignIcon iconName="play" class="w-4 h-4" />
                    {t("rns_filesync.start")}
                </button>
            {:else}
                <button
                    type="button"
                    class="secondary-chip px-4 py-2 text-sm text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/50"
                    disabled={busy}
                    onclick={onStop}
                >
                    <MaterialDesignIcon iconName="stop" class="w-4 h-4" />
                    {t("rns_filesync.stop")}
                </button>
            {/if}
            <button
                type="button"
                class="secondary-chip px-4 py-2 text-sm"
                disabled={busy || !status.running}
                onclick={onAnnounce}
            >
                <MaterialDesignIcon iconName="bullhorn" class="w-4 h-4" />
                {t("rns_filesync.announce")}
            </button>
            <button type="button" class="secondary-chip px-4 py-2 text-sm" disabled={busy} onclick={onRefresh}>
                <MaterialDesignIcon iconName="refresh" class="w-4 h-4" />
                {t("rns_filesync.refresh")}
            </button>
        </div>
    </div>

    {#if status.destination_hash}
        <div class="rounded-xl border border-sem-border p-4 space-y-2">
            <div class="text-sm font-semibold text-sem-fg">
                {t("rns_filesync.share_id")}
            </div>
            <p class="text-xs text-sem-fg-muted">{t("rns_filesync.share_id_help")}</p>
            <button
                type="button"
                class="w-full text-left font-mono text-xs break-all rounded-lg border border-sem-border bg-sem-surface-muted/50 px-3 py-2 hover:border-emerald-500 cursor-pointer"
                onclick={() => copyHash(status.destination_hash || "")}
            >
                {status.destination_hash}
            </button>
        </div>
    {/if}

    {#if progressLabel}
        <div class="rounded-lg border border-sem-border px-3 py-2 text-xs text-sem-fg-muted">
            {t("rns_filesync.last_progress")}: {progressLabel}
        </div>
    {/if}
</div>
