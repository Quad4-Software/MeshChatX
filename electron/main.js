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
    session,
    clipboard,
} = require("electron");
const electronPrompt = require("electron-prompt");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("node:path");

const crypto = require("crypto");

// remember main window
var mainWindow = null;

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

// remember child process for exe so we can kill it when app exits
var exeChildProcess = null;
var backendRuntimeState = {
    started: false,
    running: false,
    pid: null,
    lastExitCode: null,
    lastError: "",
    lastEventAt: null,
};

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

function verifyBackendIntegrity(exeDir) {
    const manifestPath = path.join(exeDir, "backend-manifest.json");
    if (!fs.existsSync(manifestPath)) {
        log("Backend integrity manifest missing, skipping check.");
        return { ok: true, issues: ["Manifest missing"] };
    }

    try {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
        const issues = [];

        const filesToVerify = manifest.files || manifest;
        const metadata = manifest._metadata || {};

        // The exeDir is build/exe when running or unpacked
        // we only care about files in the manifest
        for (const [relPath, expectedHash] of Object.entries(filesToVerify)) {
            const fullPath = path.join(exeDir, relPath);
            if (!fs.existsSync(fullPath)) {
                issues.push(`Missing: ${relPath}`);
                continue;
            }

            const fileBuffer = fs.readFileSync(fullPath);
            const actualHash = crypto.createHash("sha256").update(fileBuffer).digest("hex");
            if (actualHash !== expectedHash) {
                issues.push(`Modified: ${relPath}`);
            }
        }

        if (issues.length > 0 && metadata.date && metadata.time) {
            issues.unshift(`Backend build timestamp: ${metadata.date} ${metadata.time}`);
        }

        return {
            ok: issues.length === 0,
            issues: issues,
        };
    } catch (error) {
        log(`Backend integrity check failed: ${error.message}`);
        return { ok: false, issues: [error.message] };
    }
}

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
ipcMain.handle("show-notification", (event, { title, body, silent }) => {
    const notification = new Notification({
        title: title,
        body: body,
        silent: silent,
    });
    notification.show();

    notification.on("click", () => {
        if (mainWindow) {
            mainWindow.show();
            mainWindow.focus();
        }
    });
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

function getUserProvidedArguments() {
    const ignoredArguments = ["--no-sandbox", "--ozone-platform-hint=auto"];
    return process.argv.slice(1).filter((arg) => !ignoredArguments.includes(arg));
}

ipcMain.handle("backend-http-only", () => {
    return getUserProvidedArguments().includes("--no-https");
});

ipcMain.handle("backend-runtime-state", () => {
    const isRunning =
        !!exeChildProcess &&
        exeChildProcess.exitCode === null &&
        exeChildProcess.signalCode === null &&
        backendRuntimeState.started;
    return {
        ...backendRuntimeState,
        running: isRunning,
    };
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
ipcMain.handle("prompt", async (event, message) => {
    return await electronPrompt({
        title: message,
        label: "",
        value: "",
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

ipcMain.handle("shutdown", () => {
    quit();
});

ipcMain.handle("get-memory-usage", async () => {
    return process.getProcessMemoryInfo();
});

// allow showing a file path in os file manager
ipcMain.handle("showPathInFolder", (event, path) => {
    shell.showItemInFolder(path);
});

ipcMain.handle("open-path", (event, p) => {
    return shell.openPath(p);
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
                    shell.openExternal(params.linkURL);
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

function formatRenderProcessGoneDetails(details) {
    if (!details) {
        return "no details";
    }
    return JSON.stringify(
        {
            reason: details.reason || "unknown",
            exitCode: details.exitCode,
        },
        null,
        2
    );
}

function getDefaultStorageDir() {
    // if we are running a windows portable exe, we want to use .reticulum-meshchat in the portable exe dir
    // e.g if we launch "E:\Some\Path\MeshChat.exe" we want to use "E:\Some\Path\.reticulum-meshchat"
    const portableExecutableDir = process.env.PORTABLE_EXECUTABLE_DIR;
    if (process.platform === "win32" && portableExecutableDir != null) {
        return path.join(portableExecutableDir, ".reticulum-meshchat");
    }

    // otherwise, we will fall back to putting the storage dir in the users home directory
    // e.g: ~/.reticulum-meshchat
    return path.join(app.getPath("home"), ".reticulum-meshchat");
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

function isLocalBackendUrl(url) {
    if (!url || typeof url !== "string") {
        return false;
    }
    return (
        url.startsWith("http://127.0.0.1:9337") ||
        url.startsWith("https://127.0.0.1:9337") ||
        url.startsWith("http://localhost:9337") ||
        url.startsWith("https://localhost:9337")
    );
}

function createTray() {
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

app.whenReady().then(async () => {
    app.on("browser-window-created", (event, browserWindow) => {
        attachDefaultContextMenu(browserWindow);
    });

    // Security: Enforce CSP for all requests as a shell-level fallback
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
        const responseHeaders = { ...details.responseHeaders };

        // Define a robust fallback CSP that matches our backend's policy
        const fallbackCsp = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://*.cartocdn.com",
            "font-src 'self' data:",
            "connect-src 'self' http://127.0.0.1:9337 https://127.0.0.1:9337 http://localhost:9337 https://localhost:9337 ws://127.0.0.1:* wss://127.0.0.1:* ws://localhost:* wss://localhost:* blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://nominatim.openstreetmap.org https://git.quad4.io https://*.cartocdn.com",
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

    // Create system tray
    createTray();

    // get arguments passed to application, and remove the provided application path
    const userProvidedArguments = getUserProvidedArguments();
    const shouldLaunchHeadless = userProvidedArguments.includes("--headless");

    if (!shouldLaunchHeadless) {
        const appIconPath = getAppIconPath();
        // create browser window
        mainWindow = new BrowserWindow({
            width: 1500,
            height: 800,
            icon: appIconPath,
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

        // minimize to tray behavior
        mainWindow.on("close", (event) => {
            if (!isQuiting) {
                event.preventDefault();
                mainWindow.hide();
                return false;
            }
        });

        // open external links in default web browser instead of electron
        mainWindow.webContents.setWindowOpenHandler(({ url }) => {
            var shouldShowInNewElectronWindow = false;

            // we want to open call.html in a new electron window
            // but all other target="_blank" links should open in the system web browser
            // we don't want /rnode-flasher/index.html to open in electron, otherwise user can't select usb devices...
            if (
                (url.startsWith("http://localhost") || url.startsWith("https://localhost")) &&
                url.includes("/call.html")
            ) {
                shouldShowInNewElectronWindow = true;
            }

            // we want to open blob urls in a new electron window
            else if (url.startsWith("blob:")) {
                shouldShowInNewElectronWindow = true;
            }

            // open in new electron window
            if (shouldShowInNewElectronWindow) {
                return {
                    action: "allow",
                    overrideBrowserWindowOptions: {
                        autoHideMenuBar: true,
                        webPreferences: {
                            preload: path.join(__dirname, "preload.js"),
                            nodeIntegration: false,
                            contextIsolation: true,
                            sandbox: true,
                            enableRemoteModule: false,
                        },
                    },
                };
            }

            // fallback to opening any other url in external browser
            shell.openExternal(url);
            return {
                action: "deny",
            };
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

    // when packaged, extraResources are placed at resources/backend
    // when packaged with extraFiles, they were at resources/app/electron/build/exe
    // when packaged with asar, unpacked files are in app.asar.unpacked/ directory
    // app.getAppPath() returns the path to app.asar, so unpacked is at the same level
    const possiblePaths = [
        // packaged app - extraResources location (resources/backend)
        path.join(resourcesPath, "backend", exeName),
        // electron-forge extraResource location (resources/exe)
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

    // Verify backend integrity before spawning
    const exeDir = path.dirname(exe);
    integrityStatus.backend = verifyBackendIntegrity(exeDir);
    if (!integrityStatus.backend.ok) {
        log(`INTEGRITY WARNING: Backend tampering detected! Issues: ${integrityStatus.backend.issues.join(", ")}`);
    }

    try {
        // arguments we always want to pass in
        const requiredArguments = [
            "--headless", // reticulum meshchatx usually launches default web browser, we don't want this when using electron
            "--port",
            "9337",
            // '--test-exception-message', 'Test Exception Message', // uncomment to test the crash dialog
        ];

        // if user didn't provide reticulum config dir, we should provide it
        if (!userProvidedArguments.includes("--reticulum-config-dir")) {
            requiredArguments.push("--reticulum-config-dir", getDefaultReticulumConfigDir());
        }

        // if user didn't provide storage dir, we should provide it
        if (!userProvidedArguments.includes("--storage-dir")) {
            requiredArguments.push("--storage-dir", getDefaultStorageDir());
        }

        // spawn executable
        exeChildProcess = spawn(exe, [
            ...requiredArguments, // always provide required arguments
            ...userProvidedArguments, // also include any user provided arguments
        ]);

        if (!exeChildProcess || !exeChildProcess.pid) {
            throw new Error("Failed to start backend process (no PID).");
        }
        backendRuntimeState = {
            started: true,
            running: true,
            pid: exeChildProcess.pid,
            lastExitCode: null,
            lastError: "",
            lastEventAt: Date.now(),
        };

        // log stdout
        var stdoutLines = [];
        exeChildProcess.stdout.setEncoding("utf8");
        exeChildProcess.stdout.on("data", function (data) {
            // log
            log(data.toString());

            // keep track of last 100 stdout lines
            stdoutLines.push(data.toString());
            if (stdoutLines.length > 100) {
                stdoutLines.shift();
            }
        });

        // log stderr
        var stderrLines = [];
        exeChildProcess.stderr.setEncoding("utf8");
        exeChildProcess.stderr.on("data", function (data) {
            // log
            log(data.toString());

            // keep track of last 100 stderr lines
            stderrLines.push(data.toString());
            if (stderrLines.length > 100) {
                stderrLines.shift();
            }
        });

        // log errors
        exeChildProcess.on("error", function (error) {
            log(error);
            backendRuntimeState.lastError = error && error.message ? error.message : String(error);
            backendRuntimeState.lastEventAt = Date.now();
        });

        // quit electron app if exe dies
        exeChildProcess.on("exit", async function (code) {
            backendRuntimeState.running = false;
            backendRuntimeState.lastExitCode = code;
            backendRuntimeState.lastEventAt = Date.now();
            // if no exit code provided, we wanted exit to happen, so do nothing
            if (code == null) {
                return;
            }

            // show crash log
            const stdout = stdoutLines.join("");
            const stderr = stderrLines.join("");

            // Base64 encode for safe URL passing
            const stdoutBase64 = Buffer.from(stdout).toString("base64");
            const stderrBase64 = Buffer.from(stderr).toString("base64");

            // Load crash page if main window exists
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.show(); // Ensure visible
                mainWindow.focus();
                await mainWindow.loadFile(path.join(__dirname, "crash.html"), {
                    query: {
                        code: code.toString(),
                        stdout: stdoutBase64,
                        stderr: stderrBase64,
                    },
                });
            } else {
                // Fallback for cases where window is gone
                await dialog.showMessageBox({
                    type: "error",
                    title: "MeshChatX Crashed",
                    message: `Backend exited with code: ${code}\n\nSTDOUT: ${stdout.slice(-500)}\n\nSTDERR: ${stderr.slice(-500)}`,
                });
                app.quit();
            }
        });
    } catch (e) {
        log(e);
    }
});

app.on("render-process-gone", (_event, webContents, details) => {
    const wcId = webContents ? webContents.id : "unknown";
    log(`render-process-gone for webContents ${wcId}: ${formatRenderProcessGoneDetails(details)}`);
});

function quit() {
    if (!exeChildProcess) {
        app.quit();
        return;
    }
    if (exeChildProcess.exitCode !== null || exeChildProcess.signalCode !== null) {
        app.quit();
        return;
    }
    try {
        exeChildProcess.kill("SIGTERM");
    } catch (e) {
        log(e);
        try {
            exeChildProcess.kill("SIGKILL");
        } catch (e2) {
            log(e2);
        }
        app.quit();
        return;
    }
    const timeoutMs = 5000;
    const timeout = setTimeout(() => {
        try {
            if (exeChildProcess && exeChildProcess.exitCode === null && exeChildProcess.signalCode === null) {
                exeChildProcess.kill("SIGKILL");
            }
        } catch (e) {
            log(e);
        }
        app.quit();
    }, timeoutMs);
    exeChildProcess.once("exit", () => {
        clearTimeout(timeout);
        app.quit();
    });
}

// quit electron if all windows are closed
app.on("window-all-closed", () => {
    quit();
});
