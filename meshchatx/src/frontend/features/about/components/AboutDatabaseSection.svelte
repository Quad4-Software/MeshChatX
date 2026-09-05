<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Snippet } from "svelte";
    import Utils from "../../../js/Utils.js";
    import { t } from "../../../js/i18n.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import type { DatabaseHealth } from "../lib/types.js";

    interface Props {
        databaseHealth?: DatabaseHealth | null;
        databaseActionInProgress?: boolean;
        healthLoading?: boolean;
        backupInProgress?: boolean;
        restoreInProgress?: boolean;
        onrefreshhealth?: () => void;
        onvacuum?: () => void;
        onautorecover?: () => void;
        onrecovery?: () => void;
        onbackup?: () => void;
        onrestorefile?: (file: File) => void;
        children?: Snippet;
    }

    let {
        databaseHealth = null,
        databaseActionInProgress = false,
        healthLoading = false,
        backupInProgress = false,
        restoreInProgress = false,
        onrefreshhealth,
        onvacuum,
        onautorecover,
        onrecovery,
        onbackup,
        onrestorefile,
        children,
    }: Props = $props();

    let fileInputEl: HTMLInputElement | null = $state(null);

    function onFileInputChange(event: Event): void {
        const input = event.target as HTMLInputElement | null;
        const files = input?.files;
        if (files && files[0]) {
            onrestorefile?.(files[0]);
        }
        if (input) {
            input.value = "";
        }
    }
</script>

<div class="w-full border-b border-gray-200/60 dark:border-zinc-800/60 py-6 sm:py-8 last:border-0">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-8">
        <div class="text-xs font-black text-blue-500 uppercase tracking-[0.2em] flex items-center gap-2">
            <MaterialDesignIcon iconName="database-cog" class="size-3.5" />
            {t("about.database_health_maintenance")}
        </div>
        <div class="flex flex-wrap gap-2 w-full md:w-auto">
            <button
                type="button"
                class="secondary-chip px-4! py-1.5! text-xs! min-h-[44px] sm:min-h-0"
                disabled={databaseActionInProgress || healthLoading}
                onclick={onrefreshhealth}
            >
                <MaterialDesignIcon iconName="refresh" class="size-3.5 shrink-0" />
                {#if healthLoading}
                    <span>{t("common.loading")}</span>
                {:else}
                    <span>{t("common.refresh")}</span>
                {/if}
            </button>
            <button
                type="button"
                class="primary-chip px-4! py-1.5! text-xs!"
                disabled={databaseActionInProgress}
                onclick={onvacuum}
            >
                <MaterialDesignIcon iconName="broom" class="size-3.5 shrink-0" />
                {t("common.vacuum")}
            </button>
            <button
                type="button"
                class="primary-chip px-4! py-1.5! text-xs!"
                disabled={databaseActionInProgress}
                onclick={onautorecover}
            >
                <MaterialDesignIcon iconName="auto-fix" class="size-3.5 shrink-0" />
                {t("common.auto_recover")}
            </button>
            <button
                type="button"
                class="danger-chip px-4! py-1.5! text-xs!"
                disabled={databaseActionInProgress}
                onclick={onrecovery}
            >
                <MaterialDesignIcon iconName="medical-bag" class="size-3.5 shrink-0" />
                {t("about.recovery")}
            </button>
        </div>
    </div>

    {#if databaseHealth}
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6 lg:gap-8 mb-8">
            <div class="py-3 px-2 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/60 md:border md:rounded-xl">
                <div
                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                >
                    {t("about.integrity")}
                </div>
                <div
                    class="text-lg font-black uppercase tracking-tight {databaseHealth.quick_check === 'ok'
                        ? 'text-emerald-500'
                        : 'text-red-500'}"
                >
                    {databaseHealth.quick_check}
                </div>
            </div>
            <div class="py-3 px-2 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/60 md:border md:rounded-xl">
                <div
                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                >
                    {t("about.journal_short")}
                </div>
                <div class="text-lg font-black uppercase text-blue-500 tracking-tight">
                    {databaseHealth.journal_mode}
                </div>
            </div>
            <div class="py-3 px-2 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/60 md:border md:rounded-xl">
                <div
                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                >
                    {t("about.page_count_label")}
                </div>
                <div class="text-lg font-black font-mono tracking-tight tabular-nums">
                    {databaseHealth.page_count}
                </div>
            </div>
            <div class="py-3 px-2 sm:p-4 border-b border-gray-200/60 dark:border-zinc-800/60 md:border md:rounded-xl">
                <div
                    class="text-[9px] font-black text-gray-400 dark:text-zinc-600 uppercase tracking-[0.2em] mb-2 leading-none"
                >
                    {t("about.free_space")}
                </div>
                <div class="text-lg font-black text-amber-500 tracking-tight tabular-nums">
                    {Utils.formatBytes(databaseHealth.estimated_free_bytes ?? 0)}
                </div>
            </div>
        </div>
    {/if}

    <div id="about-database-backups" class="border-t border-zinc-100 dark:border-zinc-800 pt-8 space-y-8">
        <!-- Backups -->
        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div class="space-y-1">
                <div class="font-black text-sem-fg text-sm tracking-tight flex items-center gap-2">
                    <MaterialDesignIcon iconName="content-save-all" class="size-4 text-blue-500" />
                    {t("about.database_backups_title")}
                </div>
                <div class="text-xs text-gray-500">
                    {t("about.database_backups_desc")}
                </div>
            </div>
            <div class="flex flex-col sm:flex-row gap-2 shrink-0">
                <button
                    type="button"
                    class="primary-chip px-5! py-2.5! text-sm"
                    disabled={backupInProgress}
                    onclick={onbackup}
                >
                    <MaterialDesignIcon iconName="download" class="size-4 shrink-0" />
                    {#if backupInProgress}
                        <span>{t("about.downloading")}</span>
                    {:else}
                        <span>{t("about.download_backup")}</span>
                    {/if}
                </button>
                <button
                    type="button"
                    class="secondary-chip px-5! py-2.5! text-sm"
                    disabled={restoreInProgress}
                    onclick={() => fileInputEl?.click()}
                >
                    <MaterialDesignIcon iconName="upload" class="size-4 shrink-0" />
                    {#if restoreInProgress}
                        <span>{t("about.restoring")}</span>
                    {:else}
                        <span>{t("about.restore_from_file")}</span>
                    {/if}
                </button>
                <input
                    bind:this={fileInputEl}
                    type="file"
                    accept=".zip,application/zip"
                    class="hidden"
                    onchange={onFileInputChange}
                />
            </div>
        </div>

        {#if children}
            {@render children()}
        {/if}
    </div>
</div>
