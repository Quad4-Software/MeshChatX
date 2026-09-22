// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import DownloadUtils from "../../../js/DownloadUtils.js";
import ElectronUtils from "../../../js/ElectronUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import type { AutoBackupItem, DatabaseHealth, DatabaseRecoveryAction, SnapshotItem } from "./types.js";

/**
 * Schedule relaunch or page reload after database restore
 */
export function scheduleRestoreRelaunch(isElectron: boolean): void {
    if (isElectron) {
        setTimeout(() => ElectronUtils.relaunch(), 2000);
        return;
    }
    setTimeout(() => {
        window.location.reload();
    }, 2000);
}

/**
 * Fetch snapshots list with pagination
 */
export async function listSnapshots(
    offset: number,
    limit: number
): Promise<{ snapshots: SnapshotItem[]; total: number }> {
    try {
        const response = await window.api.get("/api/v1/database/snapshots", {
            params: { limit, offset },
        });
        const snapshots = Array.isArray(response.data?.snapshots) ? (response.data.snapshots as SnapshotItem[]) : [];
        const total = Number(response.data?.total) || 0;
        return { snapshots, total };
    } catch (e) {
        console.log("Failed to list snapshots", e);
        return { snapshots: [], total: 0 };
    }
}

/**
 * Fetch automatic backups list with pagination
 */
export async function listAutoBackups(
    offset: number,
    limit: number
): Promise<{ backups: AutoBackupItem[]; total: number }> {
    try {
        const response = await window.api.get("/api/v1/database/backups", {
            params: { limit, offset },
        });
        const backups = Array.isArray(response.data?.backups) ? (response.data.backups as AutoBackupItem[]) : [];
        const total = Number(response.data?.total) || 0;
        return { backups, total };
    } catch (e) {
        console.log("Failed to list auto-backups", e);
        return { backups: [], total: 0 };
    }
}

/**
 * Create a new database snapshot
 */
export async function createSnapshot(name?: string): Promise<{ success: boolean; error?: string }> {
    try {
        const snapshotName = name || `snapshot-${Math.floor(Date.now() / 1000)}`;
        await window.api.post("/api/v1/database/snapshot", { name: snapshotName });
        return { success: true };
    } catch (e) {
        console.log("Failed to create snapshot", e);
        return { success: false, error: "Failed to create snapshot" };
    }
}

/**
 * Download a database snapshot ZIP
 */
export async function downloadSnapshot(filename: string): Promise<boolean> {
    try {
        const downloadName = filename.endsWith(".zip") ? filename : `${filename}.zip`;
        const response = await window.api.post(`/api/v1/database/snapshots/${filename}/download`, null, {
            responseType: "arraybuffer",
        });
        await DownloadUtils.downloadFromApiResponse(response, downloadName);
        ToastUtils.success(t("about.snapshot_downloaded"));
        return true;
    } catch {
        ToastUtils.error(t("about.snapshot_download_failed"));
        return false;
    }
}

/**
 * Download an automatic backup ZIP
 */
export async function downloadBackupFile(filename: string): Promise<boolean> {
    try {
        const response = await window.api.post(`/api/v1/database/backups/${filename}/download`, null, {
            responseType: "arraybuffer",
        });
        await DownloadUtils.downloadFromApiResponse(response, filename);
        ToastUtils.success(t("about.backup_downloaded"));
        return true;
    } catch {
        ToastUtils.error(t("about.backup_download_failed"));
        return false;
    }
}

/**
 * Delete a database snapshot
 */
export async function deleteSnapshot(filename: string): Promise<boolean> {
    if (!(await DialogUtils.confirm(t("about.delete_snapshot_confirm")))) {
        return false;
    }
    try {
        await window.api.delete(`/api/v1/database/snapshots/${filename}`);
        ToastUtils.success(t("about.snapshot_deleted"));
        return true;
    } catch {
        ToastUtils.error(t("about.failed_delete_snapshot"));
        return false;
    }
}

/**
 * Delete an automatic backup
 */
export async function deleteBackup(filename: string): Promise<boolean> {
    if (!(await DialogUtils.confirm(t("about.delete_backup_confirm")))) {
        return false;
    }
    try {
        await window.api.delete(`/api/v1/database/backups/${filename}`);
        ToastUtils.success(t("about.backup_deleted"));
        return true;
    } catch {
        ToastUtils.error(t("about.failed_delete_backup"));
        return false;
    }
}

/**
 * Restore database from a snapshot path
 */
export async function restoreFromSnapshot(path: string, isElectron: boolean): Promise<boolean> {
    if (!(await DialogUtils.confirm(t("about.restore_snapshot_confirm")))) {
        return false;
    }
    try {
        const response = await window.api.post("/api/v1/database/restore", { path });
        if (response.data.status === "success") {
            ToastUtils.success(t("about.database_restored"));
            scheduleRestoreRelaunch(isElectron);
            return true;
        }
        return false;
    } catch {
        ToastUtils.error(t("about.failed_restore_snapshot"));
        return false;
    }
}

/**
 * Download a full database backup archive
 */
export async function backupDatabase(): Promise<{ success: boolean; message?: string; error?: string }> {
    try {
        const response = await window.api.post("/api/v1/database/backup/download", null, {
            responseType: "arraybuffer",
        });
        const filename =
            response.headers["content-disposition"]?.split("filename=")?.[1]?.replace(/"/g, "") ||
            "meshchatx-backup.zip";
        await DownloadUtils.downloadFromApiResponse(response, filename);
        return { success: true, message: "Backup downloaded" };
    } catch (e) {
        console.log("Failed to backup database", e);
        return { success: false, error: "Backup failed" };
    }
}

/**
 * Restore database from uploaded file
 */
export async function restoreDatabaseFromFile(
    file: File,
    isElectron: boolean
): Promise<{
    success: boolean;
    health?: DatabaseHealth;
    actions?: DatabaseRecoveryAction[];
    message?: string;
    error?: string;
}> {
    if (!(await DialogUtils.confirm(t("about.restore_file_confirm")))) {
        return { success: false };
    }
    try {
        const formData = new FormData();
        formData.append("file", file);
        const response = await window.api.post("/api/v1/database/restore", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        const msg = (response.data.message as string) || t("about.database_restored");
        const health = response.data.database?.health as DatabaseHealth | undefined;
        const actions = response.data.database?.actions as DatabaseRecoveryAction[] | undefined;
        ToastUtils.success(t("about.database_restored"));
        scheduleRestoreRelaunch(isElectron);
        return { success: true, health, actions, message: msg };
    } catch (e: any) {
        console.log("Failed to restore database from file", e);
        ToastUtils.error(t("about.failed_restore_file"));
        return { success: false, error: t("about.failed_restore_file") };
    }
}
