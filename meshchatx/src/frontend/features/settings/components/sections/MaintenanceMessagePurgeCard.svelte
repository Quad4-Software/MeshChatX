<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ToastUtils from "../../../../js/ToastUtils.js";
    import * as maintenanceClient from "../../../../js/settings/settingsMaintenanceClient.js";
    import { t } from "../../../../js/i18n.js";
    import { exportOldMessagesArchive, purgeOldMessages } from "../../lib/maintenanceActions.js";

    let messageAgePurgeMode = $state<"days" | "date">("days");
    let messageAgePurgeDays = $state(90);
    let messageAgePurgeBeforeDate = $state("");
    let messageAgePurgePreviewLoading = $state(false);
    let messageAgePurgePreviewCount = $state<number | null>(null);
    let messageAgePurgeBusy = $state(false);

    function messageAgeFilterParams() {
        return maintenanceClient.buildMessageAgeFilterParams({
            mode: messageAgePurgeMode,
            days: messageAgePurgeDays,
            beforeDate: messageAgePurgeBeforeDate,
        });
    }

    async function refreshMessageAgePurgePreview() {
        const params = messageAgeFilterParams();
        if (!params) {
            messageAgePurgePreviewCount = null;
            ToastUtils.warning(t("maintenance.purge_filter_invalid"));
            return;
        }
        messageAgePurgePreviewLoading = true;
        try {
            const { count } = await maintenanceClient.previewMessageAgePurge(window.api, params);
            messageAgePurgePreviewCount = count;
        } catch {
            messageAgePurgePreviewCount = null;
            ToastUtils.error(t("common.error"));
        } finally {
            messageAgePurgePreviewLoading = false;
        }
    }

    async function handleExportArchive() {
        const params = messageAgeFilterParams();
        if (!params) {
            ToastUtils.warning(t("maintenance.purge_filter_invalid"));
            return;
        }
        messageAgePurgeBusy = true;
        try {
            await exportOldMessagesArchive(params, window.api);
        } catch {
            ToastUtils.error(t("common.error"));
        } finally {
            messageAgePurgeBusy = false;
        }
    }

    async function handlePurgeOldMessages() {
        const params = messageAgeFilterParams();
        if (!params) {
            ToastUtils.warning(t("maintenance.purge_filter_invalid"));
            return;
        }
        messageAgePurgeBusy = true;
        try {
            const success = await purgeOldMessages(params, window.api);
            if (success) {
                messageAgePurgePreviewCount = 0;
            }
        } catch {
            ToastUtils.error(t("common.error"));
        } finally {
            messageAgePurgeBusy = false;
        }
    }
</script>

<div
    class="rounded-2xl border border-amber-200 dark:border-amber-900/40 bg-amber-50/60 dark:bg-amber-950/20 p-4 space-y-3"
>
    <div>
        <div class="text-sm font-bold text-sem-fg">{t("maintenance.purge_old_title")}</div>
        <div class="text-xs text-sem-fg-muted mt-1">{t("maintenance.purge_old_desc")}</div>
    </div>
    <div class="flex flex-wrap gap-2">
        <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer {messageAgePurgeMode ===
            'days'
                ? 'border-amber-500 bg-amber-100 dark:bg-amber-900/40 text-amber-900 dark:text-amber-100'
                : 'border-sem-border text-sem-fg-muted'}"
            onclick={() => (messageAgePurgeMode = "days")}
        >
            {t("maintenance.purge_mode_days")}
        </button>
        <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer {messageAgePurgeMode ===
            'date'
                ? 'border-amber-500 bg-amber-100 dark:bg-amber-900/40 text-amber-900 dark:text-amber-100'
                : 'border-sem-border text-sem-fg-muted'}"
            onclick={() => (messageAgePurgeMode = "date")}
        >
            {t("maintenance.purge_mode_date")}
        </button>
    </div>
    {#if messageAgePurgeMode === "days"}
        <div class="flex flex-wrap items-center gap-2">
            <label class="text-sm text-sem-fg" for="purge-older-days">
                {t("maintenance.purge_older_than_days")}
            </label>
            <input
                id="purge-older-days"
                value={messageAgePurgeDays}
                type="number"
                min="1"
                max="10000"
                class="input-field w-24"
                aria-label={t("maintenance.purge_older_than_days")}
                oninput={(e) => (messageAgePurgeDays = Number((e.target as HTMLInputElement).value))}
                onchange={refreshMessageAgePurgePreview}
            />
        </div>
    {:else}
        <div class="flex flex-wrap items-center gap-2">
            <label class="text-sm text-sem-fg" for="purge-before-date">
                {t("maintenance.purge_before_date")}
            </label>
            <input
                id="purge-before-date"
                value={messageAgePurgeBeforeDate}
                type="date"
                class="input-field"
                aria-label={t("maintenance.purge_before_date")}
                oninput={(e) => (messageAgePurgeBeforeDate = (e.target as HTMLInputElement).value)}
                onchange={refreshMessageAgePurgePreview}
            />
        </div>
    {/if}
    <div class="text-xs text-sem-fg-muted">
        {#if messageAgePurgePreviewLoading}
            <span>{t("maintenance.purge_preview_loading")}</span>
        {:else if messageAgePurgePreviewCount != null}
            <span>{t("maintenance.purge_preview_count", { count: messageAgePurgePreviewCount })}</span>
        {:else}
            <span>{t("maintenance.purge_preview_hint")}</span>
        {/if}
    </div>
    <div class="flex flex-wrap gap-2">
        <button
            type="button"
            class="px-3 py-2 rounded-xl text-sm font-semibold border border-sem-border bg-sem-surface hover:bg-sem-surface-muted disabled:opacity-60 cursor-pointer"
            disabled={messageAgePurgeBusy}
            onclick={refreshMessageAgePurgePreview}
        >
            {t("maintenance.purge_preview")}
        </button>
        <button
            type="button"
            class="px-3 py-2 rounded-xl text-sm font-semibold border border-blue-300 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/40 text-blue-800 dark:text-blue-200 hover:bg-blue-100 dark:hover:bg-blue-900/40 disabled:opacity-60 cursor-pointer"
            disabled={messageAgePurgeBusy}
            onclick={handleExportArchive}
        >
            {t("maintenance.export_old_archive")}
        </button>
        <button
            type="button"
            class="px-3 py-2 rounded-xl text-sm font-semibold border border-red-300 dark:border-red-800 bg-red-600 text-white hover:bg-red-700 disabled:opacity-60 cursor-pointer"
            disabled={messageAgePurgeBusy}
            onclick={handlePurgeOldMessages}
        >
            {t("maintenance.purge_old_confirm_btn")}
        </button>
    </div>
</div>
