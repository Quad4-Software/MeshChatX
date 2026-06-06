const path = require("node:path");
const { spawn: defaultSpawn } = require("child_process");

const { verifyBackendIntegrity } = require("./backendIntegrity");

const LOG_LINE_CAP = 100;

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

    function setUserProvidedArguments(args) {
        userProvidedArguments = Array.isArray(args) ? args : [];
    }

    function resolveExecutablePath(findExePath) {
        resolvedExePath = findExePath();
        return resolvedExePath;
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

            const logs = getJoinedLogs();
            lastCrash = {
                code,
                stdout: logs.stdout,
                stderr: logs.stderr,
                at: Date.now(),
            };

            notifyRenderer("backend-process-exited", { code, at: lastCrash.at });

            const page = getMainWindowPageKind();
            if (page === "loading" || page === "app") {
                return;
            }

            if (page === "crash") {
                return;
            }

            await showCrashPage(lastCrash);
        });
    }

    async function spawnBackend(exePath, integrityStatusRef) {
        if (!exePath) {
            throw new Error("Backend executable path is not set.");
        }
        if (isRunning()) {
            return { ok: true, alreadyRunning: true };
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

        const requiredArguments = ["--headless", "--port", "9337"];
        if (!userProvidedArguments.includes("--reticulum-config-dir")) {
            requiredArguments.push("--reticulum-config-dir", getDefaultReticulumConfigDir());
        }
        if (!userProvidedArguments.includes("--storage-dir")) {
            requiredArguments.push("--storage-dir", getDefaultStorageDir());
        }

        const proc = spawnFn(exePath, [...requiredArguments, ...userProvidedArguments]);
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

    async function openCrashReport(showCrashPageFn) {
        if (!lastCrash) {
            return { ok: false, error: "No backend crash report is available." };
        }
        await showCrashPageFn(lastCrash);
        return { ok: true };
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
        getChildProcess,
        isRunning,
        killChild,
        getJoinedLogs,
    };
}

module.exports = {
    createBackendProcessManager,
};
