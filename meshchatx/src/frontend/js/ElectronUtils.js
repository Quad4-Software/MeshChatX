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

    static async getMemoryUsage() {
        if (window.electron) {
            return await window.electron.getMemoryUsage();
        }
        return null;
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
        if (text == null || text === "") {
            return false;
        }
        const s = String(text);
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(s);
                return true;
            }
        } catch {
            // fall through to execCommand
        }
        try {
            const ta = document.createElement("textarea");
            ta.value = s;
            ta.setAttribute("readonly", "");
            ta.style.position = "fixed";
            ta.style.left = "-9999px";
            document.body.appendChild(ta);
            ta.select();
            const ok = document.execCommand("copy");
            document.body.removeChild(ta);
            return ok;
        } catch {
            return false;
        }
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
