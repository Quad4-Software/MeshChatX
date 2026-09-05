<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { SnapshotItem } from "../lib/types.js";

    interface Props {
        snapshots?: SnapshotItem[];
        snapshotsTotal?: number;
        snapshotsOffset?: number;
        snapshotsLimit?: number;
        snapshotInProgress?: boolean;
        oncreatesnapshot?: (name: string) => void;
        ondownloadsnapshot?: (name: string) => void;
        onrestoresnapshot?: (path: string) => void;
        ondeletesnapshot?: (name: string) => void;
        onprev?: () => void;
        onnext?: () => void;
    }

    let {
        snapshots = [],
        snapshotsTotal = 0,
        snapshotsOffset = 0,
        snapshotsLimit = 3,
        snapshotInProgress = false,
        oncreatesnapshot,
        ondownloadsnapshot,
        onrestoresnapshot,
        ondeletesnapshot,
        onprev,
        onnext,
    }: Props = $props();

    let snapshotName = $state("");

    function handleCreate(): void {
        const name = snapshotName;
        snapshotName = "";
        oncreatesnapshot?.(name);
    }
</script>

<div class="space-y-6">
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div class="space-y-1">
            <div class="font-black text-sem-fg text-sm tracking-tight flex items-center gap-2">
                <MaterialDesignIcon iconName="camera" class="size-4 text-purple-500" />
                {t("about.local_snapshots_title")}
            </div>
            <div class="text-xs text-gray-500">
                {t("about.local_snapshots_desc")}
            </div>
        </div>
        <div class="flex gap-2 w-full md:w-auto">
            <input
                bind:value={snapshotName}
                type="text"
                placeholder={t("about.snapshot_placeholder")}
                class="bg-zinc-50 dark:bg-zinc-900 px-4 py-2 rounded-xl text-sm border border-zinc-100 dark:border-zinc-800 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 flex-1 md:min-w-[200px]"
            />
            <button type="button" class="primary-chip px-6!" disabled={snapshotInProgress} onclick={handleCreate}>
                {#if snapshotInProgress}
                    <span>{t("about.creating")}</span>
                {:else}
                    <span>{t("about.snapshot_create")}</span>
                {/if}
            </button>
        </div>
    </div>

    {#if snapshots && snapshots.length > 0}
        <div class="space-y-4">
            <div class="grid gap-3 sm:grid-cols-2">
                {#each snapshots as snapshot (snapshot.path)}
                    <div
                        class="flex items-center justify-between gap-2 py-3 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/80 last:border-0 sm:border sm:rounded-lg sm:bg-black/2 dark:sm:bg-white/2 transition-colors"
                    >
                        <div class="flex flex-col min-w-0">
                            <span class="font-black text-sem-fg text-xs truncate">
                                {snapshot.name}
                            </span>
                            <span class="text-[10px] font-bold text-gray-400 mt-1 tabular-nums">
                                {Utils.formatBytes(snapshot.size)} • {Utils.formatTimeAgo(snapshot.created_at)}
                            </span>
                        </div>
                        <div class="flex gap-2 shrink-0">
                            <button
                                type="button"
                                class="primary-chip px-3! py-1! text-[10px]!"
                                onclick={() => ondownloadsnapshot?.(snapshot.name)}
                            >
                                <MaterialDesignIcon iconName="download" class="size-3 shrink-0" />
                                {t("about.snapshot_download")}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip px-3! py-1! text-[10px]!"
                                onclick={() => onrestoresnapshot?.(snapshot.path)}
                            >
                                {t("about.snapshot_restore")}
                            </button>
                            <button
                                type="button"
                                class="danger-chip px-3! py-1! text-[10px]!"
                                aria-label="Delete snapshot"
                                onclick={() => ondeletesnapshot?.(snapshot.name)}
                            >
                                <MaterialDesignIcon iconName="delete" class="size-3" />
                            </button>
                        </div>
                    </div>
                {/each}
            </div>

            <!-- Snapshots Pagination -->
            {#if snapshotsTotal > snapshotsLimit}
                <div class="flex items-center justify-between px-2">
                    <div class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                        {t("about.pagination_page_of", {
                            current: Math.floor(snapshotsOffset / snapshotsLimit) + 1,
                            total: Math.ceil(snapshotsTotal / snapshotsLimit),
                        })}
                    </div>
                    <div class="flex gap-2">
                        <button
                            type="button"
                            class="secondary-chip p-1.5! disabled:opacity-30"
                            disabled={snapshotsOffset === 0}
                            aria-label="Previous snapshots"
                            onclick={onprev}
                        >
                            <MaterialDesignIcon iconName="chevron-left" class="size-4" />
                        </button>
                        <button
                            type="button"
                            class="secondary-chip p-1.5! disabled:opacity-30"
                            disabled={snapshotsOffset + snapshotsLimit >= snapshotsTotal}
                            aria-label="Next snapshots"
                            onclick={onnext}
                        >
                            <MaterialDesignIcon iconName="chevron-right" class="size-4" />
                        </button>
                    </div>
                </div>
            {/if}
        </div>
    {/if}
</div>
