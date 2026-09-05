// SPDX-License-Identifier: 0BSD

import DownloadUtils from "../../../js/DownloadUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import DialogUtils from "../../../js/DialogUtils.js";
import { t } from "../../../js/i18n.js";
import * as maintenanceClient from "../../../js/settings/settingsMaintenanceClient.js";

/**
 * Exports old messages archive as a downloaded JSON file
 */
export async function exportOldMessagesArchive(
    params: { older_than_days?: number; before?: string } | null,
    api = window.api
): Promise<void> {
    if (!params) {
        ToastUtils.warning(t("maintenance.purge_filter_invalid"));
        return;
    }
    const bundle = await maintenanceClient.exportMessagesBundle(api, params);
    const dataStr = JSON.stringify(bundle, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const stamp = params.before || (params.older_than_days != null ? `${params.older_than_days}d` : "filtered");
    const exportFileDefaultName = `meshchat_messages_archive_${stamp}_${new Date().toISOString().slice(0, 10)}.json`;
    await DownloadUtils.downloadFile(exportFileDefaultName, blob);
    ToastUtils.success(t("maintenance.export_old_archive_done"));
}

/**
 * Confirms and purges messages older than specified criteria
 */
export async function purgeOldMessages(
    params: { older_than_days?: number; before?: string } | null,
    api = window.api
): Promise<boolean> {
    if (!params) {
        ToastUtils.warning(t("maintenance.purge_filter_invalid"));
        return false;
    }
    if (!(await DialogUtils.confirm(t("maintenance.purge_old_confirm")))) return false;
    const { deleted } = await maintenanceClient.purgeMessagesByAge(api, params);
    ToastUtils.success(t("maintenance.purge_old_done", { count: deleted }));
    return true;
}

/**
 * Clears all messages after confirmation
 */
export async function handleClearMessages(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearMessages(api);
        ToastUtils.success(t("maintenance.messages_cleared"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears duplicate messages after confirmation
 */
export async function handleClearDuplicates(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_duplicates_confirm")))) return;
    try {
        const { deleted } = await maintenanceClient.clearDuplicateMessages(api);
        ToastUtils.success(t("maintenance.clear_duplicates_done", { count: deleted }));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears announces after confirmation
 */
export async function handleClearAnnounces(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearAnnounces(api);
        ToastUtils.success(t("maintenance.announces_cleared"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears nomadnet favorites after confirmation
 */
export async function handleClearNomadnetFavorites(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearNomadnetFavorites(api);
        ToastUtils.success(t("maintenance.favourites_cleared"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears lxmf icons after confirmation
 */
export async function handleClearLxmfIcons(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearLxmfIcons(api);
        ToastUtils.success(t("maintenance.lxmf_icons_cleared"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears stickers after confirmation
 */
export async function handleClearStickers(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearStickers(api);
        ToastUtils.success(t("maintenance.stickers_cleared"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears gifs after confirmation
 */
export async function handleClearGifs(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearGifs(api);
        ToastUtils.success(t("maintenance.gifs_cleared"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears archives after confirmation
 */
export async function handleClearArchives(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearArchives(api);
        ToastUtils.success(t("maintenance.clear_archives_desc"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears reticulum docs after confirmation
 */
export async function handleClearReticulumDocs(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearReticulumDocs(api);
        ToastUtils.success(t("maintenance.clear_reticulum_docs_desc"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Clears path table after confirmation
 */
export async function handleClearPathTable(api = window.api): Promise<void> {
    if (!(await DialogUtils.confirm(t("maintenance.clear_confirm")))) return;
    try {
        await maintenanceClient.clearPathTable(api);
        ToastUtils.success(t("maintenance.clear_path_table_desc"));
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

/**
 * Exports all messages as JSON file
 */
export async function exportMessages(api = window.api): Promise<void> {
    try {
        const response = await api.get("/api/v1/messages/export");
        const dataStr = JSON.stringify(response.data, null, 2);
        const exportFileDefaultName = `meshchat_messages_${new Date().toISOString().slice(0, 10)}.json`;
        await DownloadUtils.downloadFile(exportFileDefaultName, new Blob([dataStr], { type: "application/json" }));
        ToastUtils.success(t("maintenance.export_done"));
    } catch {
        ToastUtils.error(t("maintenance.import_failed"));
    }
}

/**
 * Imports messages from a JSON file
 */
export function importMessagesFile(file: File, api = window.api): void {
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(e.target?.result as string);
            const response = await api.post("/api/v1/messages/import", data);
            ToastUtils.success(t("maintenance.import_success", { count: response.data.imported }));
        } catch {
            ToastUtils.error(t("maintenance.import_failed"));
        }
    };
    reader.readAsText(file);
}

/**
 * Exports folders as JSON file
 */
export async function exportFolders(api = window.api): Promise<void> {
    try {
        const response = await api.get("/api/v1/lxmf/folders/export");
        const dataStr = JSON.stringify(response.data, null, 2);
        const exportFileDefaultName = `meshchat_folders_${new Date().toISOString().slice(0, 10)}.json`;
        await DownloadUtils.downloadFile(exportFileDefaultName, new Blob([dataStr], { type: "application/json" }));
        ToastUtils.success(t("maintenance.export_done"));
    } catch {
        ToastUtils.error(t("maintenance.import_failed"));
    }
}

/**
 * Imports folders from a JSON file
 */
export function importFoldersFile(file: File, api = window.api): void {
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(e.target?.result as string);
            const response = await api.post("/api/v1/lxmf/folders/import", data);
            ToastUtils.success(t("maintenance.import_success", { count: response.data.imported ?? 0 }));
        } catch {
            ToastUtils.error(t("maintenance.import_failed"));
        }
    };
    reader.readAsText(file);
}

/**
 * Exports nomadnet favourites layout as JSON file
 */
export async function exportNomadnetFavouritesLayout(api = window.api): Promise<void> {
    try {
        const response = await api.get("/api/v1/favourites/export/nomadnet");
        const dataStr = JSON.stringify(response.data, null, 2);
        const exportFileDefaultName = `meshchat_nomadnet_favourites_${new Date().toISOString().slice(0, 10)}.json`;
        await DownloadUtils.downloadFile(exportFileDefaultName, new Blob([dataStr], { type: "application/json" }));
        ToastUtils.success(t("maintenance.export_done"));
    } catch {
        ToastUtils.error(t("maintenance.import_failed"));
    }
}

/**
 * Imports nomadnet favourites layout from a JSON file
 */
export function importNomadnetFavouritesFile(file: File, api = window.api): void {
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(e.target?.result as string);
            const response = await api.post("/api/v1/favourites/import/nomadnet", data);
            ToastUtils.success(t("maintenance.import_success", { count: response.data?.imported ?? 0 }));
        } catch {
            ToastUtils.error(t("maintenance.import_failed"));
        }
    };
    reader.readAsText(file);
}

export async function exportStickers(api = window.api): Promise<void> {
    try {
        const response = await api.get("/api/v1/stickers/export");
        const dataStr = JSON.stringify(response.data, null, 2);
        const exportFileDefaultName = `meshchat_stickers_${new Date().toISOString().slice(0, 10)}.json`;
        await DownloadUtils.downloadFile(exportFileDefaultName, new Blob([dataStr], { type: "application/json" }));
        ToastUtils.success(t("stickers.export_done"));
    } catch {
        ToastUtils.error(t("stickers.import_failed"));
    }
}

export function importStickersFile(file: File, replaceDuplicates: boolean, api = window.api): void {
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(e.target?.result as string);
            const response = await api.post("/api/v1/stickers/import", {
                ...data,
                replace_duplicates: replaceDuplicates,
            });
            const r = response.data || {};
            ToastUtils.success(
                t("stickers.import_success", {
                    imported: r.imported ?? 0,
                    skipped_duplicates: r.skipped_duplicates ?? 0,
                    skipped_invalid: r.skipped_invalid ?? 0,
                })
            );
        } catch {
            ToastUtils.error(t("stickers.import_failed"));
        }
    };
    reader.readAsText(file);
}

export async function exportGifs(api = window.api): Promise<void> {
    try {
        const response = await api.get("/api/v1/gifs/export");
        const dataStr = JSON.stringify(response.data, null, 2);
        const exportFileDefaultName = `meshchat_gifs_${new Date().toISOString().slice(0, 10)}.json`;
        await DownloadUtils.downloadFile(exportFileDefaultName, new Blob([dataStr], { type: "application/json" }));
        ToastUtils.success(t("gifs.export_done"));
    } catch {
        ToastUtils.error(t("gifs.import_failed"));
    }
}

export function importGifsFile(file: File, replaceDuplicates: boolean, api = window.api): void {
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(e.target?.result as string);
            const response = await api.post("/api/v1/gifs/import", {
                ...data,
                replace_duplicates: replaceDuplicates,
            });
            const r = response.data || {};
            ToastUtils.success(
                t("gifs.import_success", {
                    imported: r.imported ?? 0,
                    skipped_duplicates: r.skipped_duplicates ?? 0,
                    skipped_invalid: r.skipped_invalid ?? 0,
                })
            );
        } catch {
            ToastUtils.error(t("gifs.import_failed"));
        }
    };
    reader.readAsText(file);
}
