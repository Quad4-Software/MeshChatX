// SPDX-License-Identifier: 0BSD

import DownloadUtils from "../../../js/DownloadUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import DialogUtils from "../../../js/DialogUtils.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import {
    loadNomadFavouritesLayout,
    normalizeNomadFavouritesLayout,
    saveNomadFavouritesLayout,
    type NomadFavouritesLayout,
} from "../../../js/nomadFavouritesLayoutStore.js";
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
        const response = await api.get("/api/v1/maintenance/messages/export");
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
            const response = await api.post("/api/v1/maintenance/messages/import", data);
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

type NomadFavouritesImportParsed =
    { kind: "full"; layout: NomadFavouritesLayout } | { kind: "section"; payload: Record<string, unknown> };

function parseNomadnetFavouritesImportData(data: unknown): NomadFavouritesImportParsed | null {
    if (!data || typeof data !== "object" || Array.isArray(data)) {
        return null;
    }
    const raw = data as Record<string, unknown>;
    if (raw.format === "meshchatx/nomadnet_favourites/v1" && raw.layout && typeof raw.layout === "object") {
        const layout = normalizeNomadFavouritesLayout(raw.layout);
        return layout ? { kind: "full", layout } : null;
    }
    if (raw.format === "meshchatx/nomadnet_favourites_section/v1") {
        const sec = raw.section;
        if (!sec || typeof sec !== "object" || Array.isArray(sec) || typeof (sec as { id?: unknown }).id !== "string") {
            return null;
        }
        return { kind: "section", payload: raw };
    }
    const layout = normalizeNomadFavouritesLayout(raw);
    return layout ? { kind: "full", layout } : null;
}

async function mergeNomadnetFavouritesSectionImport(payload: Record<string, unknown>, api = window.api): Promise<void> {
    const sec = payload.section as { id: string; name?: string; collapsed?: boolean };
    const hashes = Array.isArray(payload.destination_hashes)
        ? payload.destination_hashes.filter((h): h is string => typeof h === "string")
        : [];
    const loaded = await loadNomadFavouritesLayout(api);
    const base = loaded || { sections: [], sectionOrder: [], favouritesBySection: {} };
    const sections = [...base.sections];
    const sectionOrder = [...base.sectionOrder];
    const favouritesBySection = { ...base.favouritesBySection };
    const idx = sections.findIndex((s) => s.id === sec.id);
    const sectionObj = {
        id: sec.id,
        name: typeof sec.name === "string" && sec.name.trim() !== "" ? sec.name : t("nomadnet.favourites"),
        collapsed: sec.collapsed === true,
    };
    if (idx === -1) {
        sections.push(sectionObj);
        if (!sectionOrder.includes(sec.id)) {
            sectionOrder.push(sec.id);
        }
    } else {
        sections[idx] = { ...sections[idx], ...sectionObj };
    }
    favouritesBySection[sec.id] = hashes;
    const merged = normalizeNomadFavouritesLayout({
        sections,
        sectionOrder,
        favouritesBySection,
    });
    if (!merged) {
        throw new Error("invalid layout");
    }
    await saveNomadFavouritesLayout(api, merged);
}

/**
 * Exports nomadnet favourites layout plus favourite records as JSON
 */
export async function exportNomadnetFavouritesLayout(api = window.api): Promise<void> {
    let layout: NomadFavouritesLayout = { sections: [], sectionOrder: [], favouritesBySection: {} };
    try {
        const loaded = await loadNomadFavouritesLayout(api);
        if (loaded) {
            layout = loaded;
        }
    } catch {
        // keep empty layout
    }
    let favourites: unknown[] = [];
    try {
        const response = await api.get("/api/v1/favourites");
        favourites = response.data.favourites || [];
    } catch {
        // continue without favourite records
    }
    const body = {
        format: "meshchatx/nomadnet_favourites/v1",
        exported_at: new Date().toISOString(),
        favourites,
        layout,
    };
    try {
        await DownloadUtils.downloadFile(
            `meshchat_nomadnet_favourites_${new Date().toISOString().slice(0, 10)}.json`,
            new Blob([JSON.stringify(body, null, 2)], { type: "application/json" })
        );
        ToastUtils.success(t("maintenance.nomadnet_favourites_exported"));
    } catch {
        ToastUtils.error(t("maintenance.nomadnet_favourites_export_failed"));
    }
}

/**
 * Imports nomadnet favourites layout (and optional favourites list) from JSON
 */
export function importNomadnetFavouritesFile(file: File, api = window.api): void {
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const data = JSON.parse(String(e.target?.result || ""));
            const parsed = parseNomadnetFavouritesImportData(data);
            if (!parsed) {
                throw new Error("invalid file");
            }
            if (Array.isArray(data.favourites) && data.favourites.length > 0) {
                await api.post("/api/v1/favourites/import", {
                    favourites: data.favourites,
                });
            }
            if (parsed.kind === "full") {
                await saveNomadFavouritesLayout(api, parsed.layout);
            } else if (parsed.kind === "section") {
                await mergeNomadnetFavouritesSectionImport(parsed.payload, api);
            } else {
                throw new Error("invalid file");
            }
            GlobalEmitter.emit("nomadnet-favourites-layout-imported");
            GlobalEmitter.emit("nomadnet-favourites-changed");
            ToastUtils.success(t("maintenance.nomadnet_favourites_imported"));
        } catch {
            ToastUtils.error(t("maintenance.nomadnet_favourites_import_failed"));
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
