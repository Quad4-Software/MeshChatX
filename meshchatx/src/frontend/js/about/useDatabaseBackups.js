// @ts-check

import { ref } from "vue";

import DialogUtils from "../DialogUtils.js";
import DownloadUtils from "../DownloadUtils.js";
import ToastUtils from "../ToastUtils.js";
import * as databaseApi from "../api/database.js";
import { apiPath } from "../constants.js";

/**
 * Database snapshot and auto-backup state for AboutPage: listing,
 * pagination, download, delete, and snapshot creation.
 *
 * options.t is the host i18n function so toasts and confirm dialogs keep
 * the component locale.
 */
export function useDatabaseBackups(options = {}) {
    const t = options.t || ((key) => key);

    const snapshotName = ref("");
    /** @type {import("vue").Ref<any[]>} */
    const snapshots = ref([]);
    const snapshotsTotal = ref(0);
    const snapshotsOffset = ref(0);
    const snapshotsLimit = ref(3);
    const snapshotInProgress = ref(false);
    const snapshotMessage = ref("");
    const snapshotError = ref("");
    /** @type {import("vue").Ref<any[]>} */
    const autoBackups = ref([]);
    const autoBackupsTotal = ref(0);
    const autoBackupsOffset = ref(0);
    const autoBackupsLimit = ref(4);

    async function listSnapshots() {
        try {
            const response = await databaseApi.listSnapshots({
                params: {
                    limit: snapshotsLimit.value,
                    offset: snapshotsOffset.value,
                },
            });
            snapshots.value = response.data.snapshots;
            snapshotsTotal.value = response.data.total;
        } catch (e) {
            console.log("Failed to list snapshots", e);
        }
    }

    async function listAutoBackups() {
        try {
            const response = await databaseApi.listBackups({
                params: {
                    limit: autoBackupsLimit.value,
                    offset: autoBackupsOffset.value,
                },
            });
            autoBackups.value = response.data.backups;
            autoBackupsTotal.value = response.data.total;
        } catch {
            console.log("Failed to list auto-backups");
        }
    }

    async function downloadSnapshot(filename) {
        try {
            const downloadName = filename.endsWith(".zip") ? filename : `${filename}.zip`;
            const response = await databaseApi.downloadSnapshots(filename, null, {
                responseType: "arraybuffer",
            });
            await DownloadUtils.downloadFromApiResponse(response, downloadName);
            ToastUtils.success(t("about.snapshot_downloaded"));
        } catch {
            ToastUtils.error(t("about.snapshot_download_failed"));
        }
    }

    async function downloadBackupFile(filename) {
        try {
            const response = await databaseApi.downloadBackups(filename, null, {
                responseType: "arraybuffer",
            });
            await DownloadUtils.downloadFromApiResponse(response, filename);
            ToastUtils.success(t("about.backup_downloaded"));
        } catch {
            ToastUtils.error(t("about.backup_download_failed"));
        }
    }

    async function deleteSnapshot(filename) {
        if (!(await DialogUtils.confirm(t("about.delete_snapshot_confirm")))) return;
        try {
            await window.api.delete(apiPath(`/database/snapshots/${filename}`));
            ToastUtils.success(t("about.snapshot_deleted"));
            await listSnapshots();
        } catch {
            ToastUtils.error(t("about.failed_delete_snapshot"));
        }
    }

    async function deleteBackup(filename) {
        if (!(await DialogUtils.confirm(t("about.delete_backup_confirm")))) return;
        try {
            await window.api.delete(apiPath(`/database/backups/${filename}`));
            ToastUtils.success(t("about.backup_deleted"));
            await listAutoBackups();
        } catch {
            ToastUtils.error(t("about.failed_delete_backup"));
        }
    }

    async function nextSnapshots() {
        if (snapshotsOffset.value + snapshotsLimit.value < snapshotsTotal.value) {
            snapshotsOffset.value += snapshotsLimit.value;
            await listSnapshots();
        }
    }

    async function prevSnapshots() {
        if (snapshotsOffset.value > 0) {
            snapshotsOffset.value = Math.max(0, snapshotsOffset.value - snapshotsLimit.value);
            await listSnapshots();
        }
    }

    async function nextBackups() {
        if (autoBackupsOffset.value + autoBackupsLimit.value < autoBackupsTotal.value) {
            autoBackupsOffset.value += autoBackupsLimit.value;
            await listAutoBackups();
        }
    }

    async function prevBackups() {
        if (autoBackupsOffset.value > 0) {
            autoBackupsOffset.value = Math.max(0, autoBackupsOffset.value - autoBackupsLimit.value);
            await listAutoBackups();
        }
    }

    async function createSnapshot() {
        if (snapshotInProgress.value) return;
        snapshotInProgress.value = true;
        snapshotMessage.value = "";
        snapshotError.value = "";
        try {
            await window.api.post(apiPath("/database/snapshot"), {
                name: snapshotName.value || `snapshot-${Math.floor(Date.now() / 1000)}`,
            });
            snapshotMessage.value = "Snapshot created successfully";
            snapshotName.value = "";
            await listSnapshots();
        } catch {
            snapshotError.value = "Failed to create snapshot";
        } finally {
            snapshotInProgress.value = false;
        }
    }

    return {
        snapshotName,
        snapshots,
        snapshotsTotal,
        snapshotsOffset,
        snapshotsLimit,
        snapshotInProgress,
        snapshotMessage,
        snapshotError,
        autoBackups,
        autoBackupsTotal,
        autoBackupsOffset,
        autoBackupsLimit,
        listSnapshots,
        listAutoBackups,
        downloadSnapshot,
        downloadBackupFile,
        deleteSnapshot,
        deleteBackup,
        nextSnapshots,
        prevSnapshots,
        nextBackups,
        prevBackups,
        createSnapshot,
    };
}
