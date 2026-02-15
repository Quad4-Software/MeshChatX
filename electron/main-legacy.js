const {
    app,
    BrowserWindow,
    dialog,
    ipcMain,
    shell,
    systemPreferences,
    Notification,
    powerSaveBlocker,
} = require("electron");
const electronPrompt = require("electron-prompt");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("node:path");
const crypto = require("crypto");

// remember main window
var mainWindow = null;

// power save blocker id
var activePowerSaveBlockerId = null;

// remember child process for exe so we can kill it when app exits
var exeChildProcess = null;

// store integrity status
var integrityStatus = {
    backend: { ok: true, issues: [] },
    data: { ok: true, issues: [] },
};

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
    // New in Electron 39, fallback for legacy
    if (typeof app.isHardwareAccelerationEnabled === "function") {
        return app.isHardwareAccelerationEnabled();
    }
    return true; // Assume true for older versions
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
    app.relaunch();
    app.exit();
});

ipcMain.handle("relaunch-emergency", () => {
    app.relaunch({ args: process.argv.slice(1).concat(["--emergency"]) });
    app.exit();
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

app.whenReady().then(async () => {
    // get arguments passed to application, and remove the provided application path
    const ignoredArguments = ["--no-sandbox", "--ozone-platform-hint=auto"];
    const userProvidedArguments = process.argv.slice(1).filter((arg) => !ignoredArguments.includes(arg));
    const shouldLaunchHeadless = userProvidedArguments.includes("--headless");

    if (!shouldLaunchHeadless) {
        // create browser window
        mainWindow = new BrowserWindow({
            width: 1500,
            height: 800,
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

    // when packaged, extraFiles are placed at resources/app/electron/build/exe
    // when packaged with asar, unpacked files are in app.asar.unpacked/ directory
    // app.getAppPath() returns the path to app.asar, so unpacked is at the same level
    const possiblePaths = [
        // packaged app - extraFiles location (resources/app/electron/build/exe)
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
        exeChildProcess = await spawn(exe, [
            ...requiredArguments, // always provide required arguments
            ...userProvidedArguments, // also include any user provided arguments
        ]);

        // log stdout
        var stdoutLines = [];
        exeChildProcess.stdout.setEncoding("utf8");
        exeChildProcess.stdout.on("data", function (data) {
            // log
            log(data.toString());

            // keep track of last 10 stdout lines
            stdoutLines.push(data.toString());
            if (stdoutLines.length > 10) {
                stdoutLines.shift();
            }
        });

        // log stderr
        var stderrLines = [];
        exeChildProcess.stderr.setEncoding("utf8");
        exeChildProcess.stderr.on("data", function (data) {
            // log
            log(data.toString());

            // keep track of last 10 stderr lines
            stderrLines.push(data.toString());
            if (stderrLines.length > 10) {
                stderrLines.shift();
            }
        });

        // log errors
        exeChildProcess.on("error", function (error) {
            log(error);
        });

        // quit electron app if exe dies
        exeChildProcess.on("exit", async function (code) {
            // if no exit code provided, we wanted exit to happen, so do nothing
            if (code == null) {
                return;
            }

            // tell user that Visual C++ redistributable needs to be installed on Windows
            if (code === 3221225781 && process.platform === "win32") {
                await dialog.showMessageBox(mainWindow, {
                    message: "Microsoft Visual C++ redistributable must be installed to run this application.",
                });
                app.quit();
                return;
            }

            // show crash log
            const stdout = stdoutLines.join("");
            const stderr = stderrLines.join("");
            await dialog.showMessageBox(mainWindow, {
                message: [
                    "MeshChat Crashed!",
                    "",
                    `Exit Code: ${code}`,
                    "",
                    `----- stdout -----`,
                    "",
                    stdout,
                    `----- stderr -----`,
                    "",
                    stderr,
                ].join("\n"),
            });

            // quit after dismissing error dialog
            app.quit();
        });
    } catch (e) {
        log(e);
    }
});

function quit() {
    // kill python process
    if (exeChildProcess) {
        exeChildProcess.kill("SIGKILL");
    }

    // quit electron app
    app.quit();
}

// quit electron if all windows are closed
app.on("window-all-closed", () => {
    quit();
});

// make sure child process is killed if app is quiting
app.on("quit", () => {
    quit();
});
