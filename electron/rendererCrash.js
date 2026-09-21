const fs = require("fs");
const path = require("node:path");

// Reasons where the renderer is gone for good and the window shows a dead
// page. clean-exit and killed are intentional exits and get no dialog.
const RECOVERABLE_REASONS = new Set(["crashed", "launch-failed", "abnormal-exit", "oom", "integrity-failure"]);

const BUTTON_RELAUNCH = 0;
const BUTTON_RELAUNCH_NO_GPU = 1;
const BUTTON_OPEN_DUMPS = 2;
const BUTTON_QUIT = 3;

// A GPU process that crashes this many times inside the window is in a
// crash loop and takes the renderers down with it (the renderer then dies
// with the same exit code). Hardware acceleration is disabled and the app
// relaunches once instead of leaving the window dead.
const GPU_STORM_THRESHOLD = 3;
const GPU_STORM_WINDOW_MS = 20000;

function disableGpuMarkerPath(storageDir) {
    return path.join(storageDir, "disable-gpu");
}

function writeDisableGpuMarker(storageDir) {
    fs.mkdirSync(storageDir, { recursive: true });
    fs.writeFileSync(
        disableGpuMarkerPath(storageDir),
        "written by renderer crash recovery; delete this file to re-enable GPU\n",
        "utf8"
    );
}

function describeExitCode(exitCode) {
    if (exitCode == null) {
        return "unknown";
    }
    const unsigned = exitCode >>> 0;
    return `${exitCode} (0x${unsigned.toString(16).toUpperCase().padStart(8, "0")})`;
}

function createRendererCrashHandler(deps) {
    const {
        dialog,
        shell,
        log,
        getMainWindow,
        isQuiting,
        getStorageDir,
        getCrashDumpsDir,
        isHardwareAccelerationEnabled = () => true,
        now = () => Date.now(),
        defer = (fn) => setImmediate(fn),
        showMessageBox = (parent, options) => dialog.showMessageBox(parent, options),
    } = deps;

    let handling = false;
    let gpuCrashTimes = [];
    let gpuAutoRecovering = false;

    function disableGpuMarkerExists() {
        try {
            return fs.existsSync(disableGpuMarkerPath(getStorageDir()));
        } catch {
            return false;
        }
    }

    function gpuAccelerationActive() {
        try {
            return Boolean(isHardwareAccelerationEnabled());
        } catch {
            return false;
        }
    }

    function gpuCrashRecoveryAvailable() {
        // No window means headless mode, and an existing marker means the
        // fallback was already attempted; relaunching again would loop.
        const win = getMainWindow();
        if (!win || win.isDestroyed() || isQuiting()) {
            return false;
        }
        return gpuAccelerationActive() && !disableGpuMarkerExists();
    }

    function gpuStormActive() {
        const nowTs = now();
        gpuCrashTimes = gpuCrashTimes.filter((t) => nowTs - t <= GPU_STORM_WINDOW_MS);
        return gpuCrashTimes.length >= GPU_STORM_THRESHOLD;
    }

    function autoRecoverGpu(source) {
        if (gpuAutoRecovering) {
            return;
        }
        gpuAutoRecovering = true;
        try {
            writeDisableGpuMarker(getStorageDir());
        } catch (error) {
            log(`Failed to write disable-gpu marker: ${error && error.message ? error.message : error}`);
        }
        log(
            `GPU process crashed ${gpuCrashTimes.length} times in ${GPU_STORM_WINDOW_MS / 1000}s (${source}); ` +
                "disabling hardware acceleration and relaunching"
        );
        deps.relaunch();
    }

    function handleChildProcessGone(details) {
        if (!details || details.type !== "GPU" || details.reason !== "crashed") {
            return;
        }
        // Count crashes even before the window exists so a startup storm is
        // already detected when the first renderer dies.
        if (!gpuAccelerationActive() || disableGpuMarkerExists()) {
            return;
        }
        const nowTs = now();
        gpuCrashTimes = gpuCrashTimes.filter((t) => nowTs - t <= GPU_STORM_WINDOW_MS);
        gpuCrashTimes.push(nowTs);
        if (gpuStormActive() && gpuCrashRecoveryAvailable()) {
            autoRecoverGpu("child-process-gone");
        }
    }

    function isRecoverableCrash(webContents, details) {
        if (!webContents || isQuiting()) {
            return false;
        }
        const win = getMainWindow();
        if (!win || win.isDestroyed() || win.webContents !== webContents) {
            return false;
        }
        return RECOVERABLE_REASONS.has(details && details.reason);
    }

    function buildDialogOptions(details) {
        const reason = (details && details.reason) || "unknown";
        const exitCode = describeExitCode(details && details.exitCode);
        const dumpsDir = getCrashDumpsDir();
        const detailLines = [
            `Reason: ${reason}`,
            `Exit code: ${exitCode}`,
            "",
            "A minidump was written to the crash dumps folder and can be shared for diagnosis:",
            dumpsDir,
            "",
            "If relaunching keeps crashing, the usual causes on Windows are the GPU driver,",
            "antivirus or overlay software injecting into the renderer, or corrupted GPU",
            "and code caches. Relaunch without GPU acceleration to rule the driver out.",
        ];
        return {
            type: "error",
            title: "MeshChatX window crashed",
            message: "The MeshChatX window crashed",
            detail: detailLines.join("\n"),
            buttons: ["Relaunch", "Relaunch without GPU acceleration", "Open crash dumps folder", "Quit"],
            defaultId: BUTTON_RELAUNCH,
            cancelId: BUTTON_QUIT,
            noLink: true,
        };
    }

    async function promptRecovery(details) {
        const win = getMainWindow();
        const parent = win && !win.isDestroyed() ? win : null;
        const options = buildDialogOptions(details);
        for (;;) {
            const { response } = await showMessageBox(parent, options);
            if (response === BUTTON_OPEN_DUMPS) {
                try {
                    await shell.openPath(getCrashDumpsDir());
                } catch (error) {
                    log(`Failed to open crash dumps folder: ${error && error.message ? error.message : error}`);
                }
                continue;
            }
            return response;
        }
    }

    async function applyRecoveryChoice(response) {
        if (response === BUTTON_RELAUNCH) {
            deps.relaunch();
            return;
        }
        if (response === BUTTON_RELAUNCH_NO_GPU) {
            try {
                writeDisableGpuMarker(getStorageDir());
            } catch (error) {
                log(`Failed to write disable-gpu marker: ${error && error.message ? error.message : error}`);
            }
            deps.relaunch();
            return;
        }
        deps.requestQuit();
    }

    function handle(webContents, details) {
        if (handling || gpuAutoRecovering || !isRecoverableCrash(webContents, details)) {
            return;
        }
        // The renderer died while the GPU process was crash-looping. Skip the
        // dialog and fall back to software rendering directly.
        if (gpuStormActive() && gpuCrashRecoveryAvailable()) {
            defer(() => autoRecoverGpu("render-process-gone"));
            return;
        }
        handling = true;
        // Defer one task: reacting synchronously inside render-process-gone
        // re-enters renderer launch bookkeeping and can CHECK-crash the
        // browser process (electron#51900).
        defer(() => {
            void promptRecovery(details)
                .then((response) => applyRecoveryChoice(response))
                .catch((error) => {
                    log(`Renderer crash recovery failed: ${error && error.message ? error.message : error}`);
                })
                .finally(() => {
                    handling = false;
                });
        });
    }

    return { handle, handleChildProcessGone, isRecoverableCrash };
}

module.exports = {
    createRendererCrashHandler,
    disableGpuMarkerPath,
    describeExitCode,
    RECOVERABLE_REASONS,
    GPU_STORM_THRESHOLD,
    GPU_STORM_WINDOW_MS,
};
