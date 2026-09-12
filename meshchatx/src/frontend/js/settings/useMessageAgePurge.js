// @ts-check

import { ref } from "vue";

import * as maintenanceClient from "./settingsMaintenanceClient.js";
import DialogUtils from "../DialogUtils.js";
import DownloadUtils from "../DownloadUtils.js";
import ToastUtils from "../ToastUtils.js";

/**
 * Message age-based purge/export state for the maintenance section of
 * SettingsPage: filter params, preview count, and busy/loading flags.
 *
 * options.t is the host i18n function so toasts keep the component locale.
 */
export function useMessageAgePurge(options = {}) {
    const t = options.t || ((key) => key);

    const messageAgePurgeMode = ref("days");
    const messageAgePurgeDays = ref(90);
    const messageAgePurgeBeforeDate = ref("");
    const messageAgePurgePreviewCount = ref(null);
    const messageAgePurgePreviewLoading = ref(false);
    const messageAgePurgeBusy = ref(false);

    function messageAgeFilterParams() {
        return maintenanceClient.buildMessageAgeFilterParams({
            mode: messageAgePurgeMode.value,
            days: messageAgePurgeDays.value,
            beforeDate: messageAgePurgeBeforeDate.value,
        });
    }

    async function refreshMessageAgePurgePreview() {
        const params = messageAgeFilterParams();
        if (!params) {
            messageAgePurgePreviewCount.value = null;
            ToastUtils.warning(t("maintenance.purge_filter_invalid"));
            return;
        }
        messageAgePurgePreviewLoading.value = true;
        try {
            const { count } = await maintenanceClient.previewMessageAgePurge(window.api, params);
            messageAgePurgePreviewCount.value = count;
        } catch {
            messageAgePurgePreviewCount.value = null;
            ToastUtils.error(t("common.error"));
        } finally {
            messageAgePurgePreviewLoading.value = false;
        }
    }

    async function exportOldMessagesArchive() {
        const params = messageAgeFilterParams();
        if (!params) {
            ToastUtils.warning(t("maintenance.purge_filter_invalid"));
            return;
        }
        messageAgePurgeBusy.value = true;
        try {
            const bundle = await maintenanceClient.exportMessagesBundle(window.api, params);
            const dataStr = JSON.stringify(bundle, null, 2);
            const blob = new Blob([dataStr], { type: "application/json" });
            const stamp = params.before || (params.older_than_days != null ? `${params.older_than_days}d` : "filtered");
            const exportFileDefaultName = `meshchat_messages_archive_${stamp}_${new Date().toISOString().slice(0, 10)}.json`;
            await DownloadUtils.downloadFile(exportFileDefaultName, blob);
            ToastUtils.success(t("maintenance.export_old_archive_done"));
        } catch {
            ToastUtils.error(t("common.error"));
        } finally {
            messageAgePurgeBusy.value = false;
        }
    }

    async function purgeOldMessages() {
        const params = messageAgeFilterParams();
        if (!params) {
            ToastUtils.warning(t("maintenance.purge_filter_invalid"));
            return;
        }
        if (!(await DialogUtils.confirm(t("maintenance.purge_old_confirm")))) return;
        messageAgePurgeBusy.value = true;
        try {
            const { deleted } = await maintenanceClient.purgeMessagesByAge(window.api, params);
            messageAgePurgePreviewCount.value = 0;
            ToastUtils.success(t("maintenance.purge_old_done", { count: deleted }));
        } catch {
            ToastUtils.error(t("common.error"));
        } finally {
            messageAgePurgeBusy.value = false;
        }
    }

    return {
        messageAgePurgeMode,
        messageAgePurgeDays,
        messageAgePurgeBeforeDate,
        messageAgePurgePreviewCount,
        messageAgePurgePreviewLoading,
        messageAgePurgeBusy,
        messageAgeFilterParams,
        refreshMessageAgePurgePreview,
        exportOldMessagesArchive,
        purgeOldMessages,
    };
}
