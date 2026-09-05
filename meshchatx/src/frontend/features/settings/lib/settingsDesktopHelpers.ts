// SPDX-License-Identifier: 0BSD

import ElectronUtils from "../../../js/ElectronUtils.js";
import DialogUtils from "../../../js/DialogUtils.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";

export async function fetchDesktopCloseSettings(): Promise<{ trayEnabled?: boolean; closeBehavior?: string } | null> {
    if (typeof ElectronUtils.getCloseSettings !== "function") return null;
    try {
        const settings = await ElectronUtils.getCloseSettings();
        if (settings && typeof settings === "object") {
            return {
                closeBehavior: settings.closeBehavior || "ask",
                trayEnabled: settings.trayEnabled !== false,
            };
        }
    } catch (e) {
        console.log(e);
    }
    return null;
}

export async function fetchScreenSecuritySettings(): Promise<boolean | null> {
    const show = typeof ElectronUtils.isWindowsElectron === "function" && ElectronUtils.isWindowsElectron();
    if (!show || typeof ElectronUtils.getScreenSecuritySettings !== "function") {
        return null;
    }
    try {
        const settings = await ElectronUtils.getScreenSecuritySettings();
        return settings?.enabled === true;
    } catch (e) {
        console.log(e);
        return null;
    }
}

export async function applyScreenSecurityChange(value: boolean): Promise<boolean | null> {
    const enabled = value === true;
    if (!enabled) {
        const confirmed = await DialogUtils.confirm(t("app.screen_security_disable_confirm"));
        if (!confirmed) {
            return null;
        }
    }
    try {
        const settings = await ElectronUtils.setScreenSecurityEnabled(enabled);
        const result = settings?.enabled === true;
        ToastUtils.success(result ? t("app.screen_security_enabled_toast") : t("app.screen_security_disabled_toast"));
        return result;
    } catch (e) {
        console.log(e);
        ToastUtils.error(t("common.save_failed"));
        return !enabled;
    }
}

export async function applyDesktopTrayEnabledChange(
    value: boolean,
    currentCloseBehavior = "ask"
): Promise<{ trayEnabled?: boolean; closeBehavior?: string } | null> {
    try {
        const settings = await ElectronUtils.setCloseSettings({ trayEnabled: value === true });
        if (settings && typeof settings === "object") {
            return {
                closeBehavior: settings.closeBehavior || currentCloseBehavior,
                trayEnabled: settings.trayEnabled !== false,
            };
        }
    } catch (e) {
        console.log(e);
    }
    return null;
}

export async function applyDesktopCloseBehaviorChange(
    value: string,
    _currentTrayEnabled = true
): Promise<{ trayEnabled?: boolean; closeBehavior?: string } | null> {
    try {
        const settings = await ElectronUtils.setCloseSettings({ closeBehavior: value });
        if (settings && typeof settings === "object") {
            return {
                closeBehavior: settings.closeBehavior || value,
                trayEnabled: settings.trayEnabled !== false,
            };
        }
    } catch (e) {
        console.log(e);
    }
    return null;
}
