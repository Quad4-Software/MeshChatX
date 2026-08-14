const { ipcRenderer, contextBridge } = require("electron");
const { isTrustedShellOrigin } = require("./shellOrigin");

function originAllowed() {
    if (typeof location === "undefined") {
        return false;
    }
    return isTrustedShellOrigin(location.href);
}

function invokeTrusted(channel, ...args) {
    if (!originAllowed()) {
        return Promise.reject(new Error("MeshChatX IPC blocked for this origin"));
    }
    return ipcRenderer.invoke(channel, ...args);
}

function onTrusted(channel, listener) {
    ipcRenderer.on(channel, (event, ...payload) => {
        if (!originAllowed()) {
            return;
        }
        listener(event, ...payload);
    });
}

onTrusted("log", (event, message) => console.log(message));

contextBridge.exposeInMainWorld("electron", {
    appVersion: async function () {
        return await invokeTrusted("app-version");
    },

    electronVersion: function () {
        if (!originAllowed()) {
            return "";
        }
        return process.versions.electron;
    },

    chromeVersion: function () {
        if (!originAllowed()) {
            return "";
        }
        return process.versions.chrome;
    },

    nodeVersion: function () {
        if (!originAllowed()) {
            return "";
        }
        return process.versions.node;
    },

    alert: async function (message) {
        return await invokeTrusted("alert", message);
    },

    confirm: async function (message) {
        return await invokeTrusted("confirm", message);
    },

    prompt: async function (message, defaultValue = "") {
        return await invokeTrusted("prompt", message, defaultValue);
    },

    relaunch: async function () {
        return await invokeTrusted("relaunch");
    },

    relaunchEmergency: async function () {
        return await invokeTrusted("relaunch-emergency");
    },

    relaunchAutoRecover: async function () {
        return await invokeTrusted("relaunch-auto-recover");
    },

    getCrashRecoveryInfo: async function () {
        return await invokeTrusted("crash-recovery-info");
    },

    restoreDatabaseBackup: async function (backupPath) {
        return await invokeTrusted("restore-database-backup", backupPath);
    },

    pickDatabaseBackup: async function () {
        return await invokeTrusted("pick-database-backup");
    },

    shutdown: async function () {
        return await invokeTrusted("shutdown");
    },

    getCloseSettings: async function () {
        return await invokeTrusted("get-close-settings");
    },

    setCloseSettings: async function (partial) {
        return await invokeTrusted("set-close-settings", partial);
    },

    getPlatform: function () {
        if (!originAllowed()) {
            return "";
        }
        return process.platform;
    },

    getScreenSecuritySettings: async function () {
        return await invokeTrusted("get-screen-security-settings");
    },

    setScreenSecurityEnabled: async function (enabled) {
        return await invokeTrusted("set-screen-security-enabled", enabled === true);
    },

    getMemoryUsage: async function () {
        return await invokeTrusted("get-memory-usage");
    },

    getBatteryStatus: async function () {
        return await invokeTrusted("get-battery-status");
    },

    showPathInFolder: async function (path) {
        return await invokeTrusted("showPathInFolder", path);
    },
    openPath: async function (path) {
        return await invokeTrusted("open-path", path);
    },
    pickFile: async function () {
        return await invokeTrusted("pick-file");
    },
    pickDirectory: async function () {
        return await invokeTrusted("pick-directory");
    },
    isHardwareAccelerationEnabled: async function () {
        return await invokeTrusted("is-hardware-acceleration-enabled");
    },
    getIntegrityStatus: async function () {
        return await invokeTrusted("get-integrity-status");
    },
    showNotification: function (title, body, silent = false, destinationHash = null) {
        invokeTrusted("show-notification", { title, body, silent, destinationHash });
    },
    closeMessageNotifications: function (destinationHash = null) {
        return invokeTrusted("close-message-notifications", destinationHash);
    },
    setPowerSaveBlocker: async function (enabled) {
        return await invokeTrusted("set-power-save-blocker", enabled);
    },
    onProtocolLink: function (callback) {
        onTrusted("open-protocol-link", (event, url) => callback(url));
    },
    backendHttpOnly: async function () {
        return await invokeTrusted("backend-http-only");
    },
    backendRuntimeState: async function () {
        return await invokeTrusted("backend-runtime-state");
    },
    backendStartupDiagnostics: async function () {
        return await invokeTrusted("backend-startup-diagnostics");
    },
    markBackendHealthy: async function () {
        return await invokeTrusted("mark-backend-healthy");
    },
    restartBackend: async function () {
        return await invokeTrusted("restart-backend");
    },
    openBackendCrashReport: async function () {
        return await invokeTrusted("open-backend-crash-report");
    },
    onBackendProcessExited: function (callback) {
        if (typeof callback !== "function") {
            return;
        }
        onTrusted("backend-process-exited", (_event, payload) => callback(payload));
    },
    onBackendStartupFailed: function (callback) {
        if (typeof callback !== "function") {
            return;
        }
        onTrusted("backend-startup-failed", (_event, payload) => callback(payload));
    },
});
