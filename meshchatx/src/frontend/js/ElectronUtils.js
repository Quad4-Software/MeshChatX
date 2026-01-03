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
}

export default ElectronUtils;
