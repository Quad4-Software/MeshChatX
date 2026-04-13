const { ipcRenderer, contextBridge } = require("electron");

// forward logs received from exe to web console
ipcRenderer.on("log", (event, message) => console.log(message));

contextBridge.exposeInMainWorld("electron", {
    // allow fetching app version in electron browser window
    appVersion: async function () {
        return await ipcRenderer.invoke("app-version");
    },

    // allow fetching electron version
    electronVersion: function () {
        return process.versions.electron;
    },

    // allow fetching chrome version
    chromeVersion: function () {
        return process.versions.chrome;
    },

    // allow fetching node version
    nodeVersion: function () {
        return process.versions.node;
    },

    // show an alert dialog in electron browser window, this fixes a bug where alert breaks input fields on windows
    alert: async function (message) {
        return await ipcRenderer.invoke("alert", message);
    },

    // show a confirm dialog in electron browser window, this fixes a bug where confirm breaks input fields on windows
    confirm: async function (message) {
        return await ipcRenderer.invoke("confirm", message);
    },

    // add support for using "prompt" in electron browser window
    prompt: async function (message) {
        return await ipcRenderer.invoke("prompt", message);
    },

    // allow relaunching app in electron browser window
    relaunch: async function () {
        return await ipcRenderer.invoke("relaunch");
    },

    // allow relaunching app in emergency mode
    relaunchEmergency: async function () {
        return await ipcRenderer.invoke("relaunch-emergency");
    },

    // allow shutting down app in electron browser window
    shutdown: async function () {
        return await ipcRenderer.invoke("shutdown");
    },

    // allow getting memory usage in electron browser window
    getMemoryUsage: async function () {
        return await ipcRenderer.invoke("get-memory-usage");
    },

    // allow showing a file path in os file manager
    showPathInFolder: async function (path) {
        return await ipcRenderer.invoke("showPathInFolder", path);
    },
    // allow checking hardware acceleration status
    isHardwareAccelerationEnabled: async function () {
        return await ipcRenderer.invoke("is-hardware-acceleration-enabled");
    },
    // allow checking integrity status
    getIntegrityStatus: async function () {
        return await ipcRenderer.invoke("get-integrity-status");
    },
    // allow showing a native notification
    showNotification: function (title, body, silent = false) {
        ipcRenderer.invoke("show-notification", { title, body, silent });
    },
    // allow controlling power save blocker
    setPowerSaveBlocker: async function (enabled) {
        return await ipcRenderer.invoke("set-power-save-blocker", enabled);
    },
    // listen for protocol links
    onProtocolLink: function (callback) {
        ipcRenderer.on("open-protocol-link", (event, url) => callback(url));
    },
    // true when backend was started with --no-https (probe HTTP first in loading.html)
    backendHttpOnly: async function () {
        return await ipcRenderer.invoke("backend-http-only");
    },
});
