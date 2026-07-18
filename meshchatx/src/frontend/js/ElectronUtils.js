import { copyTextToClipboard as copyTextToClipboardWeb } from "./clipboardUtils.js";

class ElectronUtils {
    static isElectron() {
        return window.electron != null;
    }

    static relaunch() {
        if (window.electron) {
            window.electron.relaunch();
        }
    }

    static shutdown() {
        if (window.electron) {
            window.electron.shutdown();
        }
    }

    static async getCloseSettings() {
        if (window.electron?.getCloseSettings) {
            return await window.electron.getCloseSettings();
        }
        return null;
    }

    static async setCloseSettings(partial) {
        if (window.electron?.setCloseSettings) {
            return await window.electron.setCloseSettings(partial);
        }
        return null;
    }

    static getPlatform() {
        if (typeof window.electron?.getPlatform === "function") {
            return window.electron.getPlatform();
        }
        return null;
    }

    static isWindowsElectron() {
        return ElectronUtils.isElectron() && ElectronUtils.getPlatform() === "win32";
    }

    static async getScreenSecuritySettings() {
        if (window.electron?.getScreenSecuritySettings) {
            return await window.electron.getScreenSecuritySettings();
        }
        return null;
    }

    static async setScreenSecurityEnabled(enabled) {
        if (window.electron?.setScreenSecurityEnabled) {
            return await window.electron.setScreenSecurityEnabled(enabled === true);
        }
        return null;
    }

    static async getMemoryUsage() {
        if (window.electron) {
            return await window.electron.getMemoryUsage();
        }
        return null;
    }

    static async getBatteryStatus() {
        if (!window.electron?.getBatteryStatus) {
            return null;
        }
        try {
            return await window.electron.getBatteryStatus();
        } catch {
            return null;
        }
    }

    static showPathInFolder(path) {
        if (window.electron) {
            window.electron.showPathInFolder(path);
        }
    }

    static async openPath(path) {
        if (window.electron?.openPath) {
            return await window.electron.openPath(path);
        }
        return null;
    }

    static async pickFile() {
        if (window.electron?.pickFile) {
            return await window.electron.pickFile();
        }
        return null;
    }

    static async pickDirectory() {
        if (window.electron?.pickDirectory) {
            return await window.electron.pickDirectory();
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
        if (ElectronUtils.isElectron()) {
            ElectronUtils.showPathInFolder(path);
            return true;
        }
        const ok = await ElectronUtils.copyTextToClipboard(path);
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
        if (ElectronUtils.isElectron() && window.electron?.openPath) {
            await window.electron.openPath(dirPath);
            return true;
        }
        const ok = await ElectronUtils.copyTextToClipboard(dirPath);
        if (ok) {
            if (typeof onCopiedWeb === "function") {
                onCopiedWeb();
            }
            return true;
        }
        return false;
    }

    static showNotification(title, body, silent = false) {
        if (window.electron?.showNotification) {
            window.electron.showNotification(title, body, silent);
        }
    }
}

export default ElectronUtils;
