// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import ElectronUtils from "../../../js/ElectronUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import type { ActiveSession, AppInfo, DatabaseHealth, DatabaseRecoveryAction } from "./types.js";

/**
 * Fetch application info from backend
 */
export async function fetchAppInfo(): Promise<AppInfo | null> {
    try {
        const response = await window.api.get("/api/v1/app/info");
        return (response?.data?.app_info as AppInfo) || null;
    } catch (e) {
        console.log("Failed to fetch app info", e);
        return null;
    }
}

/**
 * Fetch active sessions list and count
 */
export async function fetchActiveSessions(): Promise<{ count: number; sessions: ActiveSession[] }> {
    try {
        const response = await window.api.get("/api/v1/app/sessions");
        const data = response?.data;
        const sessions = Array.isArray(data?.sessions) ? (data.sessions as ActiveSession[]) : [];
        const count = Number(data?.count);
        return {
            count: Number.isFinite(count) ? count : sessions.length,
            sessions,
        };
    } catch (e) {
        console.log("Failed to fetch active sessions", e);
        return { count: 0, sessions: [] };
    }
}

/**
 * Acknowledge and reset integrity warning
 */
export async function acknowledgeIntegrity(): Promise<boolean> {
    if (!(await DialogUtils.confirm(t("about.integrity_acknowledge_confirm")))) {
        return false;
    }
    try {
        await window.api.post("/api/v1/app/integrity/acknowledge");
        ToastUtils.success(t("about.integrity_acknowledged"));
        return true;
    } catch {
        ToastUtils.error(t("about.failed_acknowledge_integrity"));
        return false;
    }
}

/**
 * Reload Reticulum stack
 */
export async function reloadRns(): Promise<boolean> {
    try {
        ToastUtils.loading(t("app.reloading_rns"), 0, "about-rns-reload");
        const response = await window.api.post("/api/v1/reticulum/reload");
        ToastUtils.success(response?.data?.message || t("app.reloaded_rns"));
        return true;
    } catch (e: any) {
        ToastUtils.error(e?.response?.data?.error || t("settings.failed_reload_reticulum"));
        return false;
    } finally {
        ToastUtils.dismiss("about-rns-reload");
    }
}

/**
 * Shutdown the application
 */
export async function shutdownApp(isElectron: boolean): Promise<void> {
    if (!(await DialogUtils.confirm(t("about.shutdown_confirm")))) {
        return;
    }
    try {
        await window.api.post("/api/v1/app/shutdown");
    } catch {
        // Backend might terminate before responding
    }

    if (isElectron) {
        ElectronUtils.shutdown();
    } else if (
        typeof window !== "undefined" &&
        (window as unknown as { MeshChatXAndroid?: { exitApp: () => void } }).MeshChatXAndroid?.exitApp
    ) {
        try {
            (window as unknown as { MeshChatXAndroid: { exitApp: () => void } }).MeshChatXAndroid.exitApp();
        } catch {
            ToastUtils.success(t("about.shutdown_sent"));
        }
    } else {
        ToastUtils.success(t("about.shutdown_sent"));
    }
}

/**
 * Fetch database health statistics
 */
export async function fetchDatabaseHealth(): Promise<DatabaseHealth | null> {
    try {
        const response = await window.api.get("/api/v1/database/health");
        return (response.data.database as DatabaseHealth) || null;
    } catch (e) {
        console.log("Failed to fetch database health", e);
        return null;
    }
}

/**
 * Vacuum the database
 */
export async function vacuumDatabase(): Promise<{
    success: boolean;
    health?: DatabaseHealth;
    message?: string;
    error?: string;
}> {
    try {
        const response = await window.api.post("/api/v1/database/vacuum");
        const health = response.data.database?.health as DatabaseHealth | undefined;
        const msg = (response.data.message as string) || t("about.vacuum_complete");
        ToastUtils.success(t("about.vacuum_complete"));
        return { success: true, health, message: msg };
    } catch (e: any) {
        const detail = e?.response?.data?.message;
        const err = detail || t("about.vacuum_failed");
        ToastUtils.error(err);
        return { success: false, error: err };
    }
}

/**
 * Run automated database recovery routine
 */
export async function runAutoRecover(): Promise<{
    success: boolean;
    strategy?: string;
    requiresRelaunch?: boolean;
    health?: DatabaseHealth;
    actions?: DatabaseRecoveryAction[];
    message?: string;
    error?: string;
}> {
    if (!(await DialogUtils.confirm(t("about.auto_recover_confirm")))) {
        return { success: false };
    }
    try {
        const response = await window.api.post("/api/v1/database/auto-recover", { relaunch: true });
        const strategy = response.data?.strategy as string | undefined;
        const msg = response.data?.message as string | undefined;
        if (strategy === "restore_backup") {
            ToastUtils.success(msg || t("about.auto_recover_backup"));
            return {
                success: true,
                strategy,
                requiresRelaunch: Boolean(response.data?.requires_relaunch),
                message: msg,
            };
        } else if (strategy === "sqlite_recovery") {
            const health = response.data.database?.health as DatabaseHealth | undefined;
            const actions = response.data.database?.actions as DatabaseRecoveryAction[] | undefined;
            ToastUtils.success(msg || t("about.recovery_complete"));
            return { success: true, strategy, health, actions, message: msg };
        }
        const errMsg = msg || t("about.auto_recover_failed");
        ToastUtils.error(errMsg);
        return { success: false, error: errMsg };
    } catch (e: any) {
        const detail = e?.response?.data?.message || e?.response?.data?.error;
        const errMsg = detail || t("about.auto_recover_failed");
        ToastUtils.error(errMsg);
        return { success: false, error: errMsg };
    }
}

/**
 * Run manual database recovery routine
 */
export async function runRecovery(): Promise<{
    success: boolean;
    health?: DatabaseHealth;
    actions?: DatabaseRecoveryAction[];
    message?: string;
    error?: string;
}> {
    if (!(await DialogUtils.confirm(t("about.recovery_confirm")))) {
        return { success: false };
    }
    try {
        const response = await window.api.post("/api/v1/database/recover");
        const health = response.data.database?.health as DatabaseHealth | undefined;
        const actions = response.data.database?.actions as DatabaseRecoveryAction[] | undefined;
        const msg = (response.data.message as string) || t("about.recovery_complete");
        ToastUtils.success(t("about.recovery_complete"));
        return { success: true, health, actions, message: msg };
    } catch (e: any) {
        const detail = e?.response?.data?.message;
        const errMsg = detail || t("about.recovery_failed");
        ToastUtils.error(errMsg);
        return { success: false, error: errMsg };
    }
}

/**
 * Reveal path in file manager or copy to clipboard
 */
export async function revealPath(path: string | null | undefined): Promise<void> {
    if (!path) return;
    const ok = await ElectronUtils.revealPathInFolderOrCopy(path, () => ToastUtils.success(t("common.copied")));
    if (!ok) {
        DialogUtils.alert(path);
    }
}
