/**
 * Thin wrapper over the MeshChatXAndroid JS bridge for download progress,
 * completion notifications, and transfer wake sessions. Every call no-ops
 * cleanly when the bridge or method is absent (browser, Electron, older APK).
 */

function bridge() {
    return typeof window !== "undefined" ? window.MeshChatXAndroid : null;
}

function call(method, ...args) {
    const b = bridge();
    if (b && typeof b[method] === "function") {
        try {
            return b[method](...args);
        } catch {
            return undefined;
        }
    }
    return undefined;
}

export const AndroidDownloadBridge = {
    isAvailable() {
        return bridge() != null;
    },

    supportsChunkedSave() {
        const b = bridge();
        return (
            b != null &&
            typeof b.saveDownloadBegin === "function" &&
            typeof b.saveDownloadAppend === "function" &&
            typeof b.saveDownloadFinish === "function"
        );
    },

    supportsTrackedSave() {
        const b = bridge();
        return b != null && typeof b.saveDownloadWithId === "function";
    },

    sessionStart(sessionId) {
        if (sessionId == null) return;
        call("downloadSessionStart", String(sessionId));
    },

    sessionEnd(sessionId) {
        if (sessionId == null) return;
        call("downloadSessionEnd", String(sessionId));
    },

    notifyProgress(downloadId, fileName, percent) {
        if (downloadId == null) return;
        let value = -1;
        if (typeof percent === "number" && Number.isFinite(percent)) {
            value = Math.max(0, Math.min(100, Math.round(percent)));
        }
        call("showDownloadProgress", String(downloadId), String(fileName || "download"), value);
    },

    notifyFailed(downloadId, fileName) {
        if (downloadId == null) return;
        call("downloadFailed", String(downloadId), String(fileName || "download"));
    },

    cancelNotification(downloadId) {
        if (downloadId == null) return;
        call("cancelDownloadNotification", String(downloadId));
    },
};

export default AndroidDownloadBridge;
