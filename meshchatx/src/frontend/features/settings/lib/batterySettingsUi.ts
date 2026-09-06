// SPDX-License-Identifier: 0BSD

import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import {
    loadBatterySaverPrefs,
    saveBatterySaverPrefs,
    type BatterySaverPrefs,
} from "../../../js/settings/batterySaverPrefs.js";
import {
    applyBatterySaverBitrateLimits,
    restoreBatterySaverBitrateLimits,
} from "../../../js/settings/batterySaverBitrateApply.js";

export type BatteryInterfaceRow = {
    name: string;
    type: string;
    bitrate: number | string | null;
};

export function readBatterySaverPrefs(): BatterySaverPrefs {
    const prefs = loadBatterySaverPrefs();
    if (!prefs.interfaceBitrateLimits) {
        prefs.interfaceBitrateLimits = {};
    }
    return prefs;
}

export async function fetchBatteryInterfaceRows(api = window.api): Promise<BatteryInterfaceRow[]> {
    try {
        const response = await api.get("/api/v1/reticulum/interfaces");
        const interfaces = response?.data?.interfaces || {};
        return Object.entries(interfaces)
            .map(([name, iface]) => {
                const row = iface as { type?: string; bitrate?: number | string | null };
                return {
                    name,
                    type: row?.type || "",
                    bitrate: row?.bitrate ?? null,
                };
            })
            .sort((a, b) => a.name.localeCompare(b.name));
    } catch {
        return [];
    }
}

export async function applyBatteryBitrateLimitsNow(): Promise<{ updated: string[] }> {
    return applyBatterySaverBitrateLimits({ reload: true });
}

export async function restoreBatteryBitrateLimitsNow(): Promise<{ updated: string[] }> {
    return restoreBatterySaverBitrateLimits({ reload: true });
}

export function patchBatterySaverPrefs(patch: Partial<BatterySaverPrefs>): BatterySaverPrefs {
    return saveBatterySaverPrefs(patch);
}

export function toastBatteryBitrateApplyResult(result: { updated: string[] }): void {
    if (!result.updated.length) {
        ToastUtils.error(t("settings.battery.bitrates_none_applied"));
        return;
    }
    ToastUtils.success(t("settings.battery.bitrates_applied", { count: result.updated.length }));
}

export function toastBatteryBitrateRestoreResult(result: { updated: string[] }): void {
    if (!result.updated.length) {
        ToastUtils.error(t("settings.battery.bitrates_none_restored"));
        return;
    }
    ToastUtils.success(t("settings.battery.bitrates_restored", { count: result.updated.length }));
}

export function toastBatteryBitrateApplyFailed(): void {
    ToastUtils.error(t("settings.battery.bitrates_apply_failed"));
}

export function toastBatteryBitrateRestoreFailed(): void {
    ToastUtils.error(t("settings.battery.bitrates_restore_failed"));
}
