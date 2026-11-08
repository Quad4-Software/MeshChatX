import { copyTextToClipboard as copyTextToClipboardWeb } from "./clipboardUtils.js";

class DesktopUtils {
    static isDesktop() {
        return window.desktop != null;
    }

    static relaunch() {
        if (window.desktop) {
            window.desktop.relaunch();
        }
    }

    static shutdown() {
        if (window.desktop) {
            window.desktop.shutdown();
        }
    }

    static async getCloseSettings() {
        if (window.desktop?.getCloseSettings) {
            return await window.desktop.getCloseSettings();
        }
        return null;
    }

    static async setCloseSettings(partial) {
        if (window.desktop?.setCloseSettings) {
            return await window.desktop.setCloseSettings(partial);
        }
        return null;
    }

    static getPlatform() {
        if (typeof window.desktop?.getPlatform === "function") {
            return window.desktop.getPlatform();
        }
        return null;
    }

    static isWindowsDesktop() {
        return DesktopUtils.isDesktop() && DesktopUtils.getPlatform() === "win32";
    }

    static async getScreenSecuritySettings() {
        if (window.desktop?.getScreenSecuritySettings) {
            return await window.desktop.getScreenSecuritySettings();
        }
        return null;
    }

    static async setScreenSecurityEnabled(enabled) {
        if (window.desktop?.setScreenSecurityEnabled) {
            return await window.desktop.setScreenSecurityEnabled(enabled === true);
        }
        return null;
    }

    static async getMemoryUsage() {
        if (window.desktop) {
            return await window.desktop.getMemoryUsage();
        }
        return null;
    }

    static async getBatteryStatus() {
        if (!window.desktop?.getBatteryStatus) {
            return null;
        }
        try {
            return await window.desktop.getBatteryStatus();
        } catch {
            return null;
        }
    }

    static showPathInFolder(path) {
        if (window.desktop) {
            window.desktop.showPathInFolder(path);
        }
    }

    static async openPath(path) {
        if (window.desktop?.openPath) {
            return await window.desktop.openPath(path);
        }
        return null;
    }

    static async pickFile() {
        if (window.desktop?.pickFile) {
            return await window.desktop.pickFile();
        }
        return null;
    }

    static async pickDirectory() {
        if (window.desktop?.pickDirectory) {
            return await window.desktop.pickDirectory();
        }
        return null;
    }

    static async copyTextToClipboard(text) {
        return copyTextToClipboardWeb(text);
    }

    static async revealPathInFolderOrCopy(path, onCopiedWeb) {
        if (!path) {
            return false;
        }
        if (DesktopUtils.isDesktop()) {
            DesktopUtils.showPathInFolder(path);
            return true;
        }
        const ok = await DesktopUtils.copyTextToClipboard(path);
        if (ok) {
            if (typeof onCopiedWeb === "function") {
                onCopiedWeb();
            }
            return true;
        }
        return false;
    }

    static async openDirectoryOrCopy(dirPath, onCopiedWeb) {
        if (!dirPath) {
            return false;
        }
        if (DesktopUtils.isDesktop() && window.desktop?.openPath) {
            await window.desktop.openPath(dirPath);
            return true;
        }
        const ok = await DesktopUtils.copyTextToClipboard(dirPath);
        if (ok) {
            if (typeof onCopiedWeb === "function") {
                onCopiedWeb();
            }
            return true;
        }
        return false;
    }

    static showNotification(title, body, silent = false) {
        if (window.desktop?.showNotification) {
            window.desktop.showNotification(title, body, silent);
        }
    }
}

export default DesktopUtils;
