const path = require("node:path");
const { spawn: defaultSpawn } = require("child_process");

const { verifyBackendIntegrity } = require("./backendIntegrity");
const {
    clearCrashReport,
    getDiagnosticPaths,
    getLogsDir,
    loadCrashReport,
    persistCrashReport,
} = require("./backendCrashReport");
const { killOrphanBackendProcesses } = require("./backendProcessOrphans");

const LOG_LINE_CAP = 200;

function createInitialRuntimeState() {
    return {
        started: false,
        running: false,
        pid: null,
        lastExitCode: null,
        lastError: "",
        lastEventAt: null,
    };
}

function createBackendProcessManager(deps) {
    const {
        log,
        getDefaultStorageDir,
        getDefaultReticulumConfigDir,
        getMainWindowPageKind,
        notifyRenderer,
        showCrashPage,
        spawn: spawnFn = defaultSpawn,
    } = deps;

    let childProcess = null;
    let runtimeState = createInitialRuntimeState();
    let logBuffers = { stdout: [], stderr: [] };
    let lastCrash = null;
    let resolvedExePath = null;
    let userProvidedArguments = [];

    const storageDir = () => getDefaultStorageDir();
    const reticulumConfigDir = () => getDefaultReticulumConfigDir();

    function hydratePersistedCrash() {
        const persisted = loadCrashReport(storageDir());
        if (persisted) {
            lastCrash = persisted;
        }
    }
    hydratePersistedCrash();

    function isRunning() {
        return !!childProcess && childProcess.exitCode === null && childProcess.signalCode === null;
    }

    function getRuntimeState() {
        return {
            ...runtimeState,
            running: isRunning() && runtimeState.started,
        };
    }

    function pushLogLine(buffer, line) {
        buffer.push(line);
        if (buffer.length > LOG_LINE_CAP) {
            buffer.shift();
        }
    }

    function getJoinedLogs() {
        return {
            stdout: logBuffers.stdout.join(""),
            stderr: logBuffers.stderr.join(""),
        };
    }

    function getLastCrash() {
        return lastCrash;
    }

    function getStartupDiagnostics() {
        const paths = getDiagnosticPaths(storageDir(), reticulumConfigDir());
        return {
            runtime: getRuntimeState(),
            crash: lastCrash,
            paths,
        };
    }

    function setUserProvidedArguments(args) {
        userProvidedArguments = Array.isArray(args) ? args : [];
    }

    function resolveExecutablePath(findExePath) {
        resolvedExePath = findExePath();
        return resolvedExePath;
    }

    function recordCrash(code) {
        const logs = getJoinedLogs();
        lastCrash = {
            code,
            stdout: logs.stdout,
            stderr: logs.stderr,
            at: Date.now(),
            pid: runtimeState.pid,
            platform: process.platform,
        };
        try {
            persistCrashReport(storageDir(), lastCrash);
        } catch (error) {
            log(`Failed to persist backend crash report: ${error && error.message ? error.message : error}`);
        }
    }

    function notifyStartupFailure(code) {
        const paths = getDiagnosticPaths(storageDir(), reticulumConfigDir());
        notifyRenderer("backend-startup-failed", {
            code,
            at: lastCrash?.at ?? Date.now(),
            stdout: lastCrash?.stdout || "",
            stderr: lastCrash?.stderr || "",
            paths,
        });
        notifyRenderer("backend-process-exited", { code, at: lastCrash?.at ?? Date.now() });
    }

    function attachChildHandlers(proc) {
        logBuffers = { stdout: [], stderr: [] };

        proc.stdout.setEncoding("utf8");
        proc.stdout.on("data", (data) => {
            const text = data.toString();
            log(text);
            pushLogLine(logBuffers.stdout, text);
        });

        proc.stderr.setEncoding("utf8");
        proc.stderr.on("data", (data) => {
            const text = data.toString();
            log(text);
            pushLogLine(logBuffers.stderr, text);
        });

        proc.on("error", (error) => {
            log(error);
            runtimeState.lastError = error && error.message ? error.message : String(error);
            runtimeState.lastEventAt = Date.now();
        });

        proc.on("exit", async (code) => {
            runtimeState.running = false;
            runtimeState.lastExitCode = code;
            runtimeState.lastEventAt = Date.now();
            childProcess = null;

            if (code == null || deps.isQuiting()) {
                return;
            }

            recordCrash(code);

            const page = getMainWindowPageKind();
            if (page === "loading") {
                notifyStartupFailure(code);
                return;
            }

            notifyRenderer("backend-process-exited", { code, at: lastCrash.at });

            if (page === "app") {
                return;
            }

            if (page === "crash") {
                return;
            }

            await showCrashPage(lastCrash);
        });
    }

    function buildSpawnEnv() {
        const logsDir = getLogsDir(storageDir());
        return {
            ...process.env,
            MESHCHAT_LOG_DIR: logsDir,
            MESHCHAT_STORAGE_DIR: storageDir(),
            MESHCHAT_RETICULUM_CONFIG_DIR: reticulumConfigDir(),
        };
    }

    function shouldUseAppContainerLauncher() {
        if (process.platform !== "win32") {
            return false;
        }
        const raw = process.env.MESHCHAT_APPCONTAINER;
        if (raw !== undefined && raw !== null && String(raw).trim() !== "") {
            const val = String(raw).trim().toLowerCase();
            if (["false", "0", "no", "off"].includes(val)) {
                return false;
            }
            if (["true", "1", "yes", "on"].includes(val)) {
                return true;
            }
        }
        // Opt-in only: set MESHCHAT_APPCONTAINER=1 to use the AppContainer launcher.
        return false;
    }

    function buildSpawnArgs(extraArgs = []) {
        const backendArgs = buildBackendArgs(extraArgs);
        if (!shouldUseAppContainerLauncher()) {
            return backendArgs;
        }
        return ["--meshchatx-run-module", "meshchatx.src.backend.appcontainer_launcher", ...backendArgs];
    }

    async function spawnBackend(exePath, integrityStatusRef) {
        if (!exePath) {
            throw new Error("Backend executable path is not set.");
        }
        if (isRunning()) {
            return { ok: true, alreadyRunning: true };
        }

        const removed = killOrphanBackendProcesses(null);
        if (removed > 0) {
            log(`Removed ${removed} orphan backend process(es) before startup.`);
        }

        resolvedExePath = exePath;
        const exeDir = path.dirname(exePath);
        integrityStatusRef.backend = verifyBackendIntegrity(exeDir);
        if (
            integrityStatusRef.backend.ok &&
            integrityStatusRef.backend.issues.length === 1 &&
            integrityStatusRef.backend.issues[0] === "Manifest missing"
        ) {
            log("Backend integrity manifest missing, skipping check.");
        }
        if (!integrityStatusRef.backend.ok) {
            log(
                `INTEGRITY WARNING: Backend tampering detected! Issues: ${integrityStatusRef.backend.issues.join(", ")}`
            );
        }

        if (shouldUseAppContainerLauncher()) {
            log("Starting Windows backend via AppContainer launcher.");
        }

        const proc = spawnFn(exePath, buildSpawnArgs(), {
            env: buildSpawnEnv(),
            windowsHide: true,
        });
        if (!proc || !proc.pid) {
            throw new Error("Failed to start backend process (no PID).");
        }

        childProcess = proc;
        runtimeState = {
            started: true,
            running: true,
            pid: proc.pid,
            lastExitCode: null,
            lastError: "",
            lastEventAt: Date.now(),
        };
        attachChildHandlers(proc);
        return { ok: true, pid: proc.pid };
    }

    function getChildProcess() {
        return childProcess;
    }

    function killChild(signal) {
        if (!childProcess) {
            return;
        }
        if (childProcess.exitCode !== null || childProcess.signalCode !== null) {
            return;
        }
        if (process.platform === "win32") {
            try {
                const { execFileSync } = require("node:child_process");
                execFileSync("taskkill", ["/F", "/T", "/PID", String(childProcess.pid)], {
                    stdio: "ignore",
                    windowsHide: true,
                });
            } catch (error) {
                log(error);
            }
            return;
        }
        childProcess.kill(signal);
    }

    async function restartBackend(integrityStatusRef) {
        if (!resolvedExePath) {
            return { ok: false, error: "Backend executable is not configured." };
        }
        if (isRunning()) {
            return { ok: false, error: "Backend is already running." };
        }
        try {
            const result = await spawnBackend(resolvedExePath, integrityStatusRef);
            return { ok: true, pid: result.pid };
        } catch (error) {
            return { ok: false, error: error && error.message ? error.message : String(error) };
        }
    }

    function buildBackendArgs(extraArgs = []) {
        const requiredArguments = ["--headless", "--port", "9337"];
        if (!userProvidedArguments.includes("--reticulum-config-dir")) {
            requiredArguments.push("--reticulum-config-dir", reticulumConfigDir());
        }
        if (!userProvidedArguments.includes("--storage-dir")) {
            requiredArguments.push("--storage-dir", storageDir());
        }
        return [...requiredArguments, ...userProvidedArguments, ...extraArgs];
    }

    async function runMaintenanceTask(extraArgs) {
        if (!resolvedExePath) {
            return { ok: false, error: "Backend executable is not configured." };
        }
        if (isRunning()) {
            killChild("SIGTERM");
            await new Promise((resolve) => setTimeout(resolve, 400));
        }

        return await new Promise((resolve) => {
            const stdoutChunks = [];
            const stderrChunks = [];
            const proc = spawnFn(resolvedExePath, buildSpawnArgs(extraArgs), {
                env: buildSpawnEnv(),
                windowsHide: true,
            });
            if (!proc || !proc.pid) {
                resolve({ ok: false, error: "Failed to start backend maintenance task." });
                return;
            }

            proc.stdout?.on("data", (chunk) => {
                stdoutChunks.push(String(chunk));
            });
            proc.stderr?.on("data", (chunk) => {
                stderrChunks.push(String(chunk));
            });
            proc.on("error", (error) => {
                resolve({
                    ok: false,
                    error: error && error.message ? error.message : String(error),
                    stdout: stdoutChunks.join(""),
                    stderr: stderrChunks.join(""),
                });
            });
            proc.on("exit", (code) => {
                const stdout = stdoutChunks.join("");
                const stderr = stderrChunks.join("");
                if (code === 0) {
                    resolve({ ok: true, exitCode: code, stdout, stderr });
                    return;
                }
                resolve({
                    ok: false,
                    exitCode: code,
                    error: `Maintenance task exited with code ${code}`,
                    stdout,
                    stderr,
                });
            });
        });
    }

    function getResolvedExecutablePath() {
        return resolvedExePath;
    }

    async function openCrashReport(showCrashPageFn) {
        if (!lastCrash) {
            return { ok: false, error: "No backend crash report is available." };
        }
        await showCrashPageFn(lastCrash);
        return { ok: true };
    }

    function markBackendHealthy() {
        runtimeState.lastExitCode = null;
        runtimeState.lastError = "";
        clearCrashReport(storageDir());
        lastCrash = null;
    }

    return {
        createInitialRuntimeState,
        setUserProvidedArguments,
        resolveExecutablePath,
        spawnBackend,
        restartBackend,
        openCrashReport,
        getRuntimeState,
        getLastCrash,
        getStartupDiagnostics,
        markBackendHealthy,
        getChildProcess,
        isRunning,
        killChild,
        getJoinedLogs,
        runMaintenanceTask,
        getResolvedExecutablePath,
    };
}

module.exports = {
    createBackendProcessManager,
};
