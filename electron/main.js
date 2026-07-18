const {
    app,
    BrowserWindow,
    dialog,
    ipcMain,
    shell,
    systemPreferences,
    Tray,
    Menu,
    Notification,
    powerSaveBlocker,
    powerMonitor,
    session,
    clipboard,
} = require("electron");
const electronPrompt = require("electron-prompt");
const fs = require("fs");
const path = require("node:path");

const { createBackendProcessManager } = require("./backendProcess");
const { getCrashRecoveryInfo } = require("./offlineRecovery");
const {
    getUserProvidedArguments,
    formatRenderProcessGoneDetails,
    isLocalBackendUrl,
    shouldOpenInElectronWindow,
    shouldAllowInWindowNavigation,
} = require("./mainHelpers");
const { isAllowedShellPath } = require("./shellPathGuard");
const { normalizeExternalUrlForOpen } = require("./safeExternalUrl");
const {
    loadCloseSettings,
    saveCloseSettings,
    resolveCloseAction,
    rememberedCloseSettings,
    createCloseRequestGuard,
} = require("./closeBehavior");
const {
    loadDesktopPrivacySettings,
    saveDesktopPrivacySettings,
    isScreenSecurityPlatformSupported,
    applyContentProtection,
    applyContentProtectionToWindows,
} = require("./desktopPrivacySettings");

// remember main window
var mainWindow = null;
var closeSettings = null;
var desktopPrivacySettings = null;
var closeRequestGuard = createCloseRequestGuard();

function getDialogParentWindow() {
    const focused = BrowserWindow.getFocusedWindow();
    if (focused && !focused.isDestroyed()) {
        return focused;
    }
    if (mainWindow && !mainWindow.isDestroyed()) {
        return mainWindow;
    }
    return null;
}

// tray instance
var tray = null;

// power save blocker id
var activePowerSaveBlockerId = null;

// track if we are actually quiting
var isQuiting = false;

// backend child process (managed by backendProcess.js)
var backendManager = null;

// store integrity status
var integrityStatus = {
    backend: { ok: true, issues: [] },
    data: { ok: true, issues: [] },
};

// Check for hardware acceleration preference in storage dir
try {
    const storageDir = getDefaultStorageDir();
    const disableGpuFile = path.join(storageDir, "disable-gpu");
    if (fs.existsSync(disableGpuFile)) {
        app.disableHardwareAcceleration();
        console.log("Hardware acceleration disabled via storage flag.");
    }
} catch {
    // ignore errors reading storage dir this early
}

// Handle hardware acceleration disabling via CLI
if (process.argv.includes("--disable-gpu") || process.argv.includes("--disable-software-rasterizer")) {
    app.disableHardwareAcceleration();
}

if (process.platform === "linux") {
    app.setName("reticulum-meshchatx");
}

// Detect if running in Flatpak sandbox
const isRunningInFlatpak = !!process.env.FLATPAK_ID;
if (isRunningInFlatpak) {
    console.log(`Running in Flatpak sandbox: ${process.env.FLATPAK_ID}`);
}

// Protocol registration
if (process.defaultApp) {
    if (process.argv.length >= 2) {
        app.setAsDefaultProtocolClient("lxmf", process.execPath, [path.resolve(process.argv[1])]);
        app.setAsDefaultProtocolClient("rns", process.execPath, [path.resolve(process.argv[1])]);
    }
} else {
    app.setAsDefaultProtocolClient("lxmf");
    app.setAsDefaultProtocolClient("rns");
}

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
    app.quit();
} else {
    app.on("second-instance", (event, commandLine) => {
        // Someone tried to run a second instance, we should focus our window.
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.show();
            mainWindow.focus();

            // Handle protocol links from second instance
            const url = commandLine.pop();
            if (url && (url.startsWith("lxmf://") || url.startsWith("rns://"))) {
                mainWindow.webContents.send("open-protocol-link", url);
            }
        }
    });
}

// Handle protocol links on macOS
app.on("open-url", (event, url) => {
    event.preventDefault();
    if (mainWindow) {
        mainWindow.show();
        mainWindow.webContents.send("open-protocol-link", url);
    }
});

// allow fetching app version via ipc
ipcMain.handle("app-version", () => {
    return app.getVersion();
});

// allow fetching hardware acceleration status via ipc
ipcMain.handle("is-hardware-acceleration-enabled", () => {
    return app.isHardwareAccelerationEnabled();
});

// allow fetching integrity status
ipcMain.handle("get-integrity-status", () => {
    return integrityStatus;
});

// Native Notification IPC
const {
    trackMessageNotification,
    untrackMessageNotification,
    closeMessageNotificationsFor,
    closeAllMessageNotifications,
} = require("./messageNotifications.js");

ipcMain.handle("show-notification", (event, { title, body, silent, destinationHash }) => {
    const notification = new Notification({
        title: title,
        body: body,
        silent: silent,
    });
    trackMessageNotification(destinationHash, notification);
    notification.on("close", () => {
        untrackMessageNotification(destinationHash, notification);
    });
    notification.show();

    notification.on("click", () => {
        if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
        }
    });
});

ipcMain.handle("close-message-notifications", (_event, destinationHash) => {
    if (destinationHash) {
        return closeMessageNotificationsFor(destinationHash);
    }
    return closeAllMessageNotifications();
});

// Power Management IPC
ipcMain.handle("set-power-save-blocker", (event, enabled) => {
    if (enabled) {
        if (activePowerSaveBlockerId === null) {
            activePowerSaveBlockerId = powerSaveBlocker.start("prevent-app-suspension");
            log("Power save blocker started.");
        }
    } else {
        if (activePowerSaveBlockerId !== null) {
            powerSaveBlocker.stop(activePowerSaveBlockerId);
            activePowerSaveBlockerId = null;
            log("Power save blocker stopped.");
        }
    }
    return activePowerSaveBlockerId !== null;
});

// ignore ssl errors
app.commandLine.appendSwitch("ignore-certificate-errors");

ipcMain.handle("backend-http-only", () => {
    return getUserProvidedArguments(process.argv).includes("--no-https");
});

ipcMain.handle("backend-runtime-state", () => {
    return getBackendManager().getRuntimeState();
});

ipcMain.handle("backend-startup-diagnostics", () => {
    return getBackendManager().getStartupDiagnostics();
});

ipcMain.handle("mark-backend-healthy", () => {
    getBackendManager().markBackendHealthy();
    return { ok: true };
});

ipcMain.handle("restart-backend", async () => {
    return await getBackendManager().restartBackend(integrityStatus);
});

ipcMain.handle("open-backend-crash-report", async () => {
    const lastCrash = getBackendManager().getLastCrash();
    if (!lastCrash) {
        return { ok: false, error: "No backend crash report is available." };
    }
    await loadBackendCrashPage(lastCrash);
    return { ok: true };
});

ipcMain.handle("crash-recovery-info", () => {
    const manager = getBackendManager();
    const lastCrash = manager.getLastCrash() || {};
    const logs = manager.getJoinedLogs();
    return getCrashRecoveryInfo({
        storageDir: getDefaultStorageDir(),
        reticulumConfigDir: getDefaultReticulumConfigDir(),
        platform: process.platform,
        portableExecutableDir: process.env.PORTABLE_EXECUTABLE_DIR || null,
        stderr: lastCrash.stderr || logs.stderr || "",
        stdout: lastCrash.stdout || logs.stdout || "",
        exitCode: lastCrash.code != null ? lastCrash.code : null,
    });
});

ipcMain.handle("restore-database-backup", async (_event, backupPath) => {
    if (!backupPath || typeof backupPath !== "string") {
        return { ok: false, error: "No backup path provided." };
    }
    const ctx = {
        app,
        getDefaultStorageDir,
        getDefaultReticulumConfigDir,
        getUserProvidedArguments,
    };
    const { isAllowedShellPath } = require("./shellPathGuard");
    if (!isAllowedShellPath(backupPath, ctx)) {
        return { ok: false, error: "Backup path is not allowed." };
    }
    if (!fs.existsSync(backupPath)) {
        return { ok: false, error: "Backup file was not found." };
    }
    return await getBackendManager().runMaintenanceTask(["--restore-db", backupPath]);
});

ipcMain.handle("pick-database-backup", async () => {
    const win = getDialogParentWindow();
    if (!win) {
        return null;
    }
    const { canceled, filePaths } = await dialog.showOpenDialog(win, {
        properties: ["openFile"],
        filters: [{ name: "MeshChatX backup", extensions: ["zip"] }],
    });
    if (canceled || !filePaths || filePaths.length === 0) {
        return null;
    }
    return filePaths[0];
});

// add support for showing an alert window via ipc
ipcMain.handle("alert", async (event, message) => {
    return await dialog.showMessageBox(mainWindow, {
        message: message,
    });
});

// add support for showing a confirm window via ipc
ipcMain.handle("confirm", async (event, message) => {
    // show confirm dialog
    const result = await dialog.showMessageBox(mainWindow, {
        type: "question",
        title: "Confirm",
        message: message,
        cancelId: 0, // esc key should press cancel button
        defaultId: 1, // enter key should press ok button
        buttons: [
            "Cancel", // 0
            "OK", // 1
        ],
    });

    // check if user clicked OK
    return result.response === 1;
});

// add support for showing a prompt window via ipc
ipcMain.handle("prompt", async (event, message, defaultValue = "") => {
    return await electronPrompt({
        title: message,
        label: "",
        value: defaultValue == null ? "" : String(defaultValue),
        type: "input",
        inputAttrs: {
            type: "text",
        },
    });
});

// allow relaunching app via ipc
ipcMain.handle("relaunch", () => {
    const relaunchOptions = {};
    if (!process.defaultApp && process.platform === "linux" && process.env.APPIMAGE) {
        relaunchOptions.execPath = process.env.APPIMAGE;
    }
    app.relaunch(relaunchOptions);
    isQuiting = true;
    quit();
});

ipcMain.handle("relaunch-emergency", () => {
    const relaunchOptions = {
        args: process.argv.slice(1).concat(["--emergency"]),
    };
    if (!process.defaultApp && process.platform === "linux" && process.env.APPIMAGE) {
        relaunchOptions.execPath = process.env.APPIMAGE;
    }
    app.relaunch(relaunchOptions);
    isQuiting = true;
    quit();
});

ipcMain.handle("relaunch-auto-recover", () => {
    const relaunchOptions = {
        args: process.argv.slice(1).concat(["--auto-recover"]),
    };
    if (!process.defaultApp && process.platform === "linux" && process.env.APPIMAGE) {
        relaunchOptions.execPath = process.env.APPIMAGE;
    }
    app.relaunch(relaunchOptions);
    isQuiting = true;
    quit();
});

ipcMain.handle("shutdown", () => {
    isQuiting = true;
    quit();
});

ipcMain.handle("get-close-settings", () => {
    return getCloseSettings();
});

ipcMain.handle("set-close-settings", (_event, partial) => {
    return updateCloseSettings(partial || {});
});

ipcMain.handle("get-screen-security-settings", () => {
    return getScreenSecuritySettingsPayload();
});

ipcMain.handle("set-screen-security-enabled", (_event, enabled) => {
    return updateScreenSecurityEnabled(enabled === true);
});

ipcMain.handle("get-memory-usage", async () => {
    return process.getProcessMemoryInfo();
});

ipcMain.handle("get-battery-status", async () => {
    let onBattery = null;
    try {
        if (typeof powerMonitor?.isOnBatteryPower === "function") {
            onBattery = Boolean(powerMonitor.isOnBatteryPower());
        }
    } catch {
        onBattery = null;
    }

    let level = null;
    // Linux sysfs: common laptop BAT0/BAT1 capacity files.
    if (process.platform === "linux") {
        try {
            const powerSupplyDir = "/sys/class/power_supply";
            if (fs.existsSync(powerSupplyDir)) {
                const entries = fs.readdirSync(powerSupplyDir);
                for (const name of entries) {
                    if (!/^BAT\d+$/i.test(name) && name.toUpperCase() !== "BATTERY") {
                        continue;
                    }
                    const capacityPath = path.join(powerSupplyDir, name, "capacity");
                    if (!fs.existsSync(capacityPath)) {
                        continue;
                    }
                    const raw = fs.readFileSync(capacityPath, "utf8").trim();
                    const parsed = Number.parseInt(raw, 10);
                    if (Number.isFinite(parsed) && parsed >= 0 && parsed <= 100) {
                        level = parsed;
                        break;
                    }
                }
            }
        } catch {
            level = null;
        }
    }

    if (level == null && onBattery == null) {
        return null;
    }
    return {
        level,
        charging: onBattery == null ? null : !onBattery,
        on_battery: onBattery,
        source: "electron",
    };
});

// allow showing a file path in os file manager
ipcMain.handle("showPathInFolder", (event, targetPath) => {
    const ctx = {
        app,
        getDefaultStorageDir,
        getDefaultReticulumConfigDir,
        getUserProvidedArguments,
    };
    if (!isAllowedShellPath(targetPath, ctx)) {
        console.warn("showPathInFolder denied (path outside allowed directories)");
        return;
    }
    shell.showItemInFolder(targetPath);
});

ipcMain.handle("open-path", (event, targetPath) => {
    const ctx = {
        app,
        getDefaultStorageDir,
        getDefaultReticulumConfigDir,
        getUserProvidedArguments,
    };
    if (!isAllowedShellPath(targetPath, ctx)) {
        console.warn("open-path denied (path outside allowed directories)");
        return "Path is not allowed";
    }
    return shell.openPath(targetPath);
});

ipcMain.handle("pick-file", async () => {
    const win = getDialogParentWindow();
    if (!win) {
        return null;
    }
    const { canceled, filePaths } = await dialog.showOpenDialog(win, {
        properties: ["openFile"],
    });
    if (canceled || !filePaths || filePaths.length === 0) {
        return null;
    }
    return filePaths[0];
});

ipcMain.handle("pick-directory", async () => {
    const win = getDialogParentWindow();
    if (!win) {
        return null;
    }
    const { canceled, filePaths } = await dialog.showOpenDialog(win, {
        properties: ["openDirectory"],
    });
    if (canceled || !filePaths || filePaths.length === 0) {
        return null;
    }
    return filePaths[0];
});

function getChildBrowserWindowOptions() {
    return {
        autoHideMenuBar: true,
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: true,
            enableRemoteModule: false,
        },
    };
}

function handleWindowOpenRequest(url) {
    if (shouldOpenInElectronWindow(url)) {
        return {
            action: "allow",
            overrideBrowserWindowOptions: getChildBrowserWindowOptions(),
        };
    }

    const safe = normalizeExternalUrlForOpen(url);
    if (safe) {
        shell.openExternal(safe);
    }
    return {
        action: "deny",
    };
}

function attachWindowOpenHandler(browserWindow) {
    browserWindow.webContents.setWindowOpenHandler(({ url }) => handleWindowOpenRequest(url));
}

function attachInWindowNavigationGuard(browserWindow) {
    browserWindow.webContents.on("will-navigate", (event, url) => {
        if (shouldAllowInWindowNavigation(url)) {
            return;
        }
        event.preventDefault();
        const safe = normalizeExternalUrlForOpen(url);
        if (safe) {
            shell.openExternal(safe);
        }
    });
}

function attachDevToolsF12Shortcut(browserWindow) {
    browserWindow.webContents.on("before-input-event", (event, input) => {
        if (input.type !== "keyDown" || input.key !== "F12") {
            return;
        }
        if (browserWindow.isDestroyed()) {
            return;
        }
        browserWindow.webContents.toggleDevTools();
        event.preventDefault();
    });
}

function attachDefaultContextMenu(browserWindow) {
    const webContents = browserWindow.webContents;
    webContents.on("context-menu", (event, params) => {
        const template = [];

        if (params.isEditable) {
            template.push(
                { role: "undo" },
                { role: "redo" },
                { type: "separator" },
                { role: "cut" },
                { role: "copy" },
                { role: "paste" },
                { role: "pasteAndMatchStyle" },
                { type: "separator" },
                { role: "selectAll" }
            );
        } else if (params.selectionText) {
            template.push({ role: "copy" });
        }

        if (params.misspelledWord) {
            const suggestions = params.dictionarySuggestions || [];
            if (suggestions.length > 0) {
                if (template.length > 0) {
                    template.push({ type: "separator" });
                }
                for (const suggestion of suggestions) {
                    template.push({
                        label: suggestion,
                        click: () => {
                            webContents.replaceMisspelling(suggestion);
                        },
                    });
                }
            }
            if (template.length > 0) {
                template.push({ type: "separator" });
            }
            template.push({
                label: "Add to dictionary",
                click: () => {
                    void webContents.session.addWordToSpellCheckerDictionary(params.misspelledWord);
                },
            });
        }

        if (params.linkURL) {
            if (template.length > 0) {
                template.push({ type: "separator" });
            }
            template.push({
                label: "Open link",
                click: () => {
                    const safe = normalizeExternalUrlForOpen(params.linkURL);
                    if (safe) {
                        shell.openExternal(safe);
                    }
                },
            });
            template.push({
                label: "Copy link",
                click: () => {
                    clipboard.writeText(params.linkURL);
                },
            });
        }

        if (template.length === 0) {
            return;
        }

        const menu = Menu.buildFromTemplate(template);
        menu.popup({ window: browserWindow });
    });
}

function log(message) {
    // log to stdout of this process
    console.log(message);

    // make sure main window exists
    if (!mainWindow) {
        return;
    }

    // make sure window is not destroyed
    if (mainWindow.isDestroyed()) {
        return;
    }

    // log to web console
    mainWindow.webContents.send("log", message);
}

function getDefaultStorageDir() {
    const portableExecutableDir = process.env.PORTABLE_EXECUTABLE_DIR;
    if (process.platform === "win32" && portableExecutableDir != null) {
        return path.join(portableExecutableDir, ".reticulum-meshchatx");
    }

    return path.join(app.getPath("home"), ".reticulum-meshchatx");
}

function getDefaultReticulumConfigDir() {
    // if we are running a windows portable exe, we want to use .reticulum in the portable exe dir
    // e.g if we launch "E:\Some\Path\MeshChat.exe" we want to use "E:\Some\Path\.reticulum"
    const portableExecutableDir = process.env.PORTABLE_EXECUTABLE_DIR;
    if (process.platform === "win32" && portableExecutableDir != null) {
        return path.join(portableExecutableDir, ".reticulum");
    }

    // otherwise, we will fall back to using the .reticulum folder in the users home directory
    // e.g: ~/.reticulum
    return path.join(app.getPath("home"), ".reticulum");
}

function getAppIconPath() {
    const iconPath = path.join(__dirname, "build", "icon.png");
    const fallbackIconPath = path.join(__dirname, "assets", "images", "logo.png");
    return fs.existsSync(iconPath) ? iconPath : fallbackIconPath;
}

function getMainWindowPageKind() {
    if (!mainWindow || mainWindow.isDestroyed()) {
        return "none";
    }
    const url = mainWindow.webContents.getURL();
    if (url.includes("loading.html")) {
        return "loading";
    }
    if (url.includes("crash.html")) {
        return "crash";
    }
    if (isLocalBackendUrl(url)) {
        return "app";
    }
    return "other";
}

async function loadBackendCrashPage(crash) {
    const stdoutBase64 = Buffer.from((crash && crash.stdout) || "").toString("base64");
    const stderrBase64 = Buffer.from((crash && crash.stderr) || "").toString("base64");
    const code = crash && crash.code != null ? String(crash.code) : "";
    const paths = getBackendManager().getStartupDiagnostics().paths;

    if (!mainWindow || mainWindow.isDestroyed()) {
        await dialog.showMessageBox({
            type: "error",
            title: "MeshChatX Crashed",
            message: `Backend exited with code: ${code}`,
        });
        app.quit();
        return;
    }

    mainWindow.show();
    mainWindow.focus();
    await mainWindow.loadFile(path.join(__dirname, "crash.html"), {
        query: {
            code: code,
            stdout: stdoutBase64,
            stderr: stderrBase64,
            logPath: paths?.backendLogPath || "",
            crashReportPath: paths?.crashReportPath || "",
        },
    });
}

function getBackendManager() {
    if (!backendManager) {
        backendManager = createBackendProcessManager({
            log,
            getDefaultStorageDir,
            getDefaultReticulumConfigDir,
            getMainWindowPageKind,
            isQuiting: () => quitInitiated,
            notifyRenderer: (channel, payload) => {
                if (mainWindow && !mainWindow.isDestroyed()) {
                    mainWindow.webContents.send(channel, payload);
                }
            },
            showCrashPage: loadBackendCrashPage,
        });
    }
    return backendManager;
}

function getCloseSettings() {
    if (!closeSettings) {
        closeSettings = loadCloseSettings(getDefaultStorageDir());
    }
    return closeSettings;
}

function updateCloseSettings(partial) {
    closeSettings = saveCloseSettings(getDefaultStorageDir(), partial);
    syncTrayWithSettings();
    return closeSettings;
}

function getDesktopPrivacySettings() {
    if (!desktopPrivacySettings) {
        desktopPrivacySettings = loadDesktopPrivacySettings(getDefaultStorageDir());
    }
    return desktopPrivacySettings;
}

function getScreenSecuritySettingsPayload() {
    const settings = getDesktopPrivacySettings();
    const platform = process.platform;
    return {
        platform,
        available: isScreenSecurityPlatformSupported(platform),
        windowsDrm: platform === "win32",
        enabled: settings.screenSecurityEnabled === true,
    };
}

function applyScreenSecurityToWindow(browserWindow, enabled) {
    if (!applyContentProtection(browserWindow, enabled === true)) {
        return;
    }
}

function applyScreenSecurityToAllWindows(enabled) {
    applyContentProtectionToWindows(BrowserWindow.getAllWindows(), enabled === true);
}

function updateScreenSecurityEnabled(enabled) {
    desktopPrivacySettings = saveDesktopPrivacySettings(getDefaultStorageDir(), {
        screenSecurityEnabled: enabled === true,
    });
    applyScreenSecurityToAllWindows(desktopPrivacySettings.screenSecurityEnabled);
    return getScreenSecuritySettingsPayload();
}

function destroyTray() {
    if (tray && !tray.isDestroyed()) {
        tray.destroy();
    }
    tray = null;
}

function createTray() {
    if (tray && !tray.isDestroyed()) {
        return;
    }
    tray = new Tray(getAppIconPath());
    const contextMenu = Menu.buildFromTemplate([
        {
            label: "Show App",
            click: function () {
                if (mainWindow) {
                    mainWindow.show();
                }
            },
        },
        {
            label: "Quit",
            click: function () {
                isQuiting = true;
                quit();
            },
        },
    ]);

    tray.setToolTip("Reticulum MeshChatX");
    tray.setContextMenu(contextMenu);

    tray.on("click", () => {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.hide();
            } else {
                mainWindow.show();
            }
        }
    });
}

function syncTrayWithSettings() {
    const settings = getCloseSettings();
    if (settings.trayEnabled) {
        createTray();
    } else {
        destroyTray();
    }
}

async function promptCloseAction() {
    const settings = getCloseSettings();
    const backgroundLabel = settings.trayEnabled ? "Keep running in background" : "Minimize to taskbar";
    const backgroundDetail = settings.trayEnabled
        ? "Hide the window and keep MeshChatX in the system tray."
        : "Minimize MeshChatX to the taskbar.";
    const result = await dialog.showMessageBox(getDialogParentWindow() || undefined, {
        type: "question",
        title: "Close MeshChatX?",
        message: "Close MeshChatX?",
        detail: `Choose whether to quit the application or keep it running.\n\n${backgroundDetail}`,
        buttons: ["Cancel", "Quit application", backgroundLabel],
        defaultId: 2,
        cancelId: 0,
        checkboxLabel: "Remember my choice",
        checkboxChecked: false,
    });
    if (result.response === 0) {
        return null;
    }
    const action = result.response === 1 ? "quit" : settings.trayEnabled ? "background" : "minimize";
    const remembered = rememberedCloseSettings(action, result.checkboxChecked);
    if (remembered) {
        updateCloseSettings(remembered);
    }
    return action;
}

async function handleWindowCloseRequest(event) {
    if (isQuiting) {
        return;
    }
    event.preventDefault();
    if (!closeRequestGuard.tryEnter()) {
        return;
    }
    try {
        const settings = getCloseSettings();
        let action = resolveCloseAction(settings);
        if (action === "ask") {
            action = await promptCloseAction();
            if (!action) {
                return;
            }
        }
        if (action === "quit") {
            isQuiting = true;
            quit();
            return;
        }
        if (!mainWindow || mainWindow.isDestroyed()) {
            return;
        }
        if (action === "minimize") {
            mainWindow.minimize();
            return;
        }
        mainWindow.hide();
    } finally {
        closeRequestGuard.leave();
    }
}

app.whenReady().then(async () => {
    app.on("browser-window-created", (event, browserWindow) => {
        attachDefaultContextMenu(browserWindow);
        attachDevToolsF12Shortcut(browserWindow);
        attachWindowOpenHandler(browserWindow);
        attachInWindowNavigationGuard(browserWindow);
        const privacy = getDesktopPrivacySettings();
        applyScreenSecurityToWindow(browserWindow, privacy.screenSecurityEnabled === true);
    });

    // Security: Enforce CSP for all requests as a shell-level fallback
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
        const responseHeaders = { ...details.responseHeaders };

        // Define a robust fallback CSP that matches our backend's policy
        const fallbackCsp = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' blob:",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://*.cartocdn.com https://tiles.openfreemap.org https://*.openfreemap.org",
            "font-src 'self' data: https://tiles.openfreemap.org https://*.openfreemap.org",
            "connect-src 'self' http://127.0.0.1:9337 https://127.0.0.1:9337 http://localhost:9337 https://localhost:9337 ws://127.0.0.1:* wss://127.0.0.1:* ws://localhost:* wss://localhost:* blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://nominatim.openstreetmap.org https://github.com https://*.cartocdn.com https://tiles.openfreemap.org https://*.openfreemap.org",
            "media-src 'self' blob:",
            "worker-src 'self' blob:",
            "frame-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
        ].join("; ");

        // If the response doesn't already have a CSP, apply our fallback
        if (!responseHeaders["Content-Security-Policy"] && !responseHeaders["content-security-policy"]) {
            responseHeaders["Content-Security-Policy"] = [fallbackCsp];
        }

        callback({ responseHeaders });
    });

    // Log Hardware Acceleration status (New in Electron 39)
    const isHardwareAccelerationEnabled = app.isHardwareAccelerationEnabled();
    log(`Hardware Acceleration Enabled: ${isHardwareAccelerationEnabled}`);

    // Create system tray when enabled in desktop close settings
    syncTrayWithSettings();

    // get arguments passed to application, and remove the provided application path
    const userProvidedArguments = getUserProvidedArguments(process.argv);
    const shouldLaunchHeadless = userProvidedArguments.includes("--headless");

    if (!shouldLaunchHeadless) {
        const appIconPath = getAppIconPath();
        // create browser window
        mainWindow = new BrowserWindow({
            width: 1500,
            height: 800,
            icon: appIconPath,
            autoHideMenuBar: true,
            webPreferences: {
                // used to inject logging over ipc
                preload: path.join(__dirname, "preload.js"),
                // Security: disable node integration in renderer
                nodeIntegration: false,
                // Security: enable context isolation (default in Electron 12+)
                contextIsolation: true,
                // Security: enable sandbox for additional protection
                sandbox: true,
                // Security: disable remote module (deprecated but explicit)
                enableRemoteModule: false,
            },
        });
        mainWindow.webContents.on("render-process-gone", (_event, details) => {
            log(`Renderer process crashed: ${formatRenderProcessGoneDetails(details)}`);
        });
        mainWindow.webContents.on("unresponsive", () => {
            log("Renderer process became unresponsive.");
        });
        mainWindow.webContents.on(
            "did-fail-load",
            async (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
                if (!isMainFrame || !isLocalBackendUrl(validatedURL)) {
                    return;
                }
                log(`Failed to load backend URL (${errorCode}): ${errorDescription} - ${validatedURL}`);
                if (!mainWindow || mainWindow.isDestroyed()) {
                    return;
                }
                const currentUrl = mainWindow.webContents.getURL();
                if (currentUrl.includes("loading.html")) {
                    return;
                }
                try {
                    await mainWindow.loadFile(path.join(__dirname, "loading.html"), {
                        query: { startup_error: "backend_unreachable" },
                    });
                } catch (error) {
                    log(`Failed to restore loading screen after backend load failure: ${error.message}`);
                }
            }
        );

        // quit / minimize / hide-to-tray based on remembered close settings
        mainWindow.on("close", (event) => {
            void handleWindowCloseRequest(event);
        });

        // navigate to loading page
        await mainWindow.loadFile(path.join(__dirname, "loading.html"));

        // ask mac users for microphone access for audio calls to work
        if (process.platform === "darwin") {
            await systemPreferences.askForMediaAccess("microphone");
        }
    }

    // find path to python/cxfreeze executable (setup.py builds ReticulumMeshChatX)
    const exeName = process.platform === "win32" ? "ReticulumMeshChatX.exe" : "ReticulumMeshChatX";

    // get app path (handles both development and packaged app)
    const appPath = app.getAppPath();
    // get resources path (where extraFiles are placed)
    const resourcesPath = process.resourcesPath || path.join(appPath, "..", "..");
    var exe = null;

    const platformFolder =
        process.platform === "win32" || process.platform === "win"
            ? "win32"
            : process.platform === "darwin"
              ? "darwin"
              : "linux";
    const archSegment = (() => {
        if (process.arch === "arm64") return "arm64";
        if (process.arch === "ia32") return "ia32";
        if (process.arch === "arm") return "armv7l";
        return "x64";
    })();
    const packagedExtraResourceDir = path.join(resourcesPath, `${platformFolder}-${archSegment}`, exeName);

    // when packaged, extraResources are placed at resources/backend
    // when packaged with extraFiles, they were at resources/app/electron/build/exe
    // when packaged with asar, unpacked files are in app.asar.unpacked/ directory
    // app.getAppPath() returns the path to app.asar, so unpacked is at the same level
    const possiblePaths = [
        // packaged app - extraResources location (resources/backend)
        path.join(resourcesPath, "backend", exeName),
        // @electron/packager extraResource: copies build/exe/<platform>-<arch> to resources/<platform>-<arch>/
        packagedExtraResourceDir,
        // legacy electron-forge extraResource location (resources/exe)
        path.join(resourcesPath, "exe", exeName),
        // legacy packaged app - extraFiles location (resources/app/electron/build/exe)
        path.join(resourcesPath, "app", "electron", "build", "exe", exeName),
        // packaged app with asar (unpacked files from asarUnpack)
        path.join(appPath, "..", "app.asar.unpacked", "build", "exe", exeName),
        // packaged app without asar (relative to app path)
        path.join(appPath, "build", "exe", exeName),
        // development mode (relative to electron directory)
        path.join(__dirname, "build", "exe", exeName),
        // development mode (relative to project root)
        path.join(__dirname, "..", "build", "exe", exeName),
    ];

    // find the first path that exists
    for (const possibleExe of possiblePaths) {
        if (fs.existsSync(possibleExe)) {
            exe = possibleExe;
            break;
        }
    }

    // verify executable exists
    if (!exe || !fs.existsSync(exe)) {
        const errorMsg = `Could not find executable: ${exeName}\nChecked paths:\n${possiblePaths.join("\n")}\n\nApp path: ${appPath}\nResources path: ${resourcesPath}`;
        log(errorMsg);
        if (mainWindow) {
            await dialog.showMessageBox(mainWindow, {
                message: errorMsg,
            });
        }
        app.quit();
        return;
    }

    log(`Found executable at: ${exe}`);

    const manager = getBackendManager();
    manager.setUserProvidedArguments(userProvidedArguments);
    try {
        await manager.spawnBackend(exe, integrityStatus);
    } catch (e) {
        log(e);
    }
});

app.on("render-process-gone", (_event, webContents, details) => {
    const wcId = webContents ? webContents.id : "unknown";
    log(`render-process-gone for webContents ${wcId}: ${formatRenderProcessGoneDetails(details)}`);
});

// Track if quit has been initiated to prevent recursion
let quitInitiated = false;
let quitTimeoutId = null;

function quit() {
    if (quitInitiated) {
        return;
    }
    quitInitiated = true;

    const exeChildProcess = getBackendManager().getChildProcess();
    if (!exeChildProcess) {
        app.quit();
        return;
    }
    if (exeChildProcess.exitCode !== null || exeChildProcess.signalCode !== null) {
        app.quit();
        return;
    }
    try {
        getBackendManager().killChild("SIGTERM");
    } catch (e) {
        log(e);
        try {
            getBackendManager().killChild("SIGKILL");
        } catch (e2) {
            log(e2);
        }
        app.quit();
        return;
    }
    const timeoutMs = 5000;
    quitTimeoutId = setTimeout(() => {
        try {
            const proc = getBackendManager().getChildProcess();
            if (proc && proc.exitCode === null && proc.signalCode === null) {
                getBackendManager().killChild("SIGKILL");
            }
        } catch (e) {
            log(e);
        }
        app.quit();
    }, timeoutMs);
    exeChildProcess.once("exit", () => {
        if (quitTimeoutId) {
            clearTimeout(quitTimeoutId);
            quitTimeoutId = null;
        }
        app.quit();
    });
}

// Handle before-quit for additional cleanup
app.on("before-quit", () => {
    if (!isQuiting) {
        isQuiting = true;
    }
    // Ensure tray is destroyed to prevent it from keeping the app alive
    destroyTray();
});

// quit electron if all windows are closed
app.on("window-all-closed", () => {
    quit();
});
