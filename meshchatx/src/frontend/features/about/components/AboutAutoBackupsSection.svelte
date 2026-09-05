<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { AutoBackupItem } from "../lib/types.js";

    interface Props {
        autoBackups?: AutoBackupItem[];
        autoBackupsTotal?: number;
        autoBackupsOffset?: number;
        autoBackupsLimit?: number;
        ondownloadbackup?: (name: string) => void;
        onrestorebackup?: (path: string) => void;
        ondeletebackup?: (name: string) => void;
        onprev?: () => void;
        onnext?: () => void;
    }

    let {
        autoBackups = [],
        autoBackupsTotal = 0,
        autoBackupsOffset = 0,
        autoBackupsLimit = 4,
        ondownloadbackup,
        onrestorebackup,
        ondeletebackup,
        onprev,
        onnext,
    }: Props = $props();

    const hasSuspiciousBackups = $derived(autoBackups.some((b) => b.name.includes("SUSPICIOUS")));
</script>

<div class="space-y-6">
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div class="space-y-1">
            <div class="font-black text-sem-fg text-sm tracking-tight flex items-center gap-2">
                <MaterialDesignIcon iconName="history" class="size-4 text-blue-500" />
                {t("about.automatic_backups_title")}
            </div>
            <div class="text-xs text-gray-500">
                {t("about.automatic_backups_desc")}
            </div>
        </div>
    </div>

    {#if autoBackups && autoBackups.length > 0}
        <div class="space-y-4">
            <div class="grid gap-3 sm:grid-cols-2">
                {#each autoBackups as backup (backup.path)}
                    <div
                        class="flex items-center justify-between gap-2 py-3 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/80 last:border-0 sm:border sm:rounded-lg sm:bg-black/2 dark:sm:bg-white/2 transition-colors"
                    >
                        <div class="flex flex-col min-w-0">
                            <span class="font-black text-sem-fg text-xs truncate">
                                {backup.name}
                            </span>
                            <span class="text-[10px] font-bold text-gray-400 mt-1 tabular-nums">
                                {Utils.formatBytes(backup.size)} • {Utils.formatTimeAgo(backup.created_at)}
                            </span>
                        </div>
                        <div class="flex gap-2 shrink-0">
                            <button
                                type="button"
                                class="primary-chip p-1.5!"
                                aria-label={t("about.snapshot_download")}
                                title={t("about.snapshot_download")}
                                onclick={() => ondownloadbackup?.(backup.name)}
                            >
                                <MaterialDesignIcon iconName="download" class="size-4" />
                            </button>
                            <button
                                type="button"
                                class="secondary-chip px-3! py-1! text-[10px]!"
                                onclick={() => onrestorebackup?.(backup.path)}
                            >
                                {t("about.snapshot_restore")}
                            </button>
                            <button
                                type="button"
                                class="danger-chip px-3! py-1! text-[10px]!"
                                aria-label="Delete backup"
                                onclick={() => ondeletebackup?.(backup.name)}
                            >
                                <MaterialDesignIcon iconName="delete" class="size-3" />
                            </button>
                        </div>
                    </div>
                {/each}
            </div>

            {#if hasSuspiciousBackups}
                <div
                    class="mt-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 text-xs text-amber-700 dark:text-amber-300 flex items-start gap-2"
                >
                    <MaterialDesignIcon iconName="alert" class="size-4 shrink-0 mt-0.5" />
                    <span>
                        Suspicious backups are created when the database size or message count drops unexpectedly
                        compared to the last known baseline, usually after a crash, corruption, or deletion. They are
                        kept automatically so you can inspect or restore from them.
                    </span>
                </div>
            {/if}

            <!-- Backups Pagination -->
            {#if autoBackupsTotal > autoBackupsLimit}
                <div class="flex items-center justify-between px-2">
                    <div class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                        {t("about.pagination_page_of", {
                            current: Math.floor(autoBackupsOffset / autoBackupsLimit) + 1,
                            total: Math.ceil(autoBackupsTotal / autoBackupsLimit),
                        })}
                    </div>
                    <div class="flex gap-2">
                        <button
                            type="button"
                            class="secondary-chip p-1.5! disabled:opacity-30"
                            disabled={autoBackupsOffset === 0}
                            aria-label="Previous backups"
                            onclick={onprev}
                        >
                            <MaterialDesignIcon iconName="chevron-left" class="size-4" />
                        </button>
                        <button
                            type="button"
                            class="secondary-chip p-1.5! disabled:opacity-30"
                            disabled={autoBackupsOffset + autoBackupsLimit >= autoBackupsTotal}
                            aria-label="Next backups"
                            onclick={onnext}
                        >
                            <MaterialDesignIcon iconName="chevron-right" class="size-4" />
                        </button>
                    </div>
                </div>
            {/if}
        </div>
    {:else}
        <div
            class="rounded-xl border border-dashed border-zinc-200 dark:border-zinc-700 px-4 py-6 text-center text-xs text-gray-500"
        >
            {t("about.automatic_backups_empty")}
        </div>
    {/if}
</div>
