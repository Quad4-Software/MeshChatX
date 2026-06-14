"use strict";

const fs = require("node:fs");
const path = require("node:path");

const REPORT_FILENAME = "last-backend-crash.json";

/**
 * @param {string} storageDir
 * @returns {string}
 */
function getLogsDir(storageDir) {
    return path.join(storageDir, "logs");
}

/**
 * @param {string} storageDir
 * @returns {string}
 */
function getCrashReportPath(storageDir) {
    return path.join(getLogsDir(storageDir), REPORT_FILENAME);
}

/**
 * @param {string} storageDir
 * @returns {string}
 */
function getBackendLogPath(storageDir) {
    return path.join(getLogsDir(storageDir), "meshchatx.log");
}

/**
 * @param {string} text
 * @returns {string}
 */
function tailText(text, maxChars = 12000) {
    if (!text || typeof text !== "string") {
        return "";
    }
    if (text.length <= maxChars) {
        return text;
    }
    return text.slice(-maxChars);
}

/**
 * @param {object} crash
 * @returns {object}
 */
function normalizeCrash(crash) {
    if (!crash || typeof crash !== "object") {
        return null;
    }
    const code = crash.code != null ? Number(crash.code) : null;
    const stdout = tailText(crash.stdout || "");
    const stderr = tailText(crash.stderr || "");
    const at = crash.at != null ? Number(crash.at) : Date.now();
    return {
        code,
        stdout,
        stderr,
        at,
        platform: crash.platform || process.platform,
        pid: crash.pid != null ? Number(crash.pid) : null,
    };
}

/**
 * @param {string} storageDir
 * @param {object} crash
 */
function persistCrashReport(storageDir, crash) {
    if (!storageDir) {
        return null;
    }
    const normalized = normalizeCrash(crash);
    if (!normalized) {
        return null;
    }
    const logsDir = getLogsDir(storageDir);
    fs.mkdirSync(logsDir, { recursive: true });
    const reportPath = getCrashReportPath(storageDir);
    const payload = {
        ...normalized,
        savedAt: Date.now(),
        reportPath,
        backendLogPath: getBackendLogPath(storageDir),
    };
    fs.writeFileSync(reportPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
    return payload;
}

/**
 * @param {string} storageDir
 * @returns {object|null}
 */
function loadCrashReport(storageDir) {
    if (!storageDir) {
        return null;
    }
    try {
        const raw = fs.readFileSync(getCrashReportPath(storageDir), "utf8");
        const parsed = JSON.parse(raw);
        return normalizeCrash(parsed);
    } catch {
        return null;
    }
}

/**
 * @param {string} storageDir
 */
function clearCrashReport(storageDir) {
    if (!storageDir) {
        return;
    }
    try {
        fs.unlinkSync(getCrashReportPath(storageDir));
    } catch {
        /* already absent */
    }
}

/**
 * @param {string} text
 * @returns {object|null}
 */
function parseMemoryLogLine(text) {
    if (!text || typeof text !== "string") {
        return null;
    }
    for (const rawLine of text.split(/\r?\n/)) {
        const line = rawLine.trim();
        if (!line.startsWith("MESHCHAT_MEMORY:")) {
            continue;
        }
        const parsed = {};
        const payload = line.slice("MESHCHAT_MEMORY:".length).trim();
        for (const token of payload.split(/\s+/)) {
            const idx = token.indexOf("=");
            if (idx <= 0) {
                continue;
            }
            const key = token.slice(0, idx);
            const value = token.slice(idx + 1);
            if (key === "total_mb" || key === "available_mb" || key === "percent_used") {
                const num = Number(value);
                if (Number.isFinite(num)) {
                    parsed[key] = num;
                }
            } else {
                parsed[key] = value;
            }
        }
        return Object.keys(parsed).length > 0 ? parsed : null;
    }
    return null;
}

/**
 * @param {string} stderr
 * @param {string} stdout
 * @param {number|null} exitCode
 * @returns {{ category: string, summary: string, hints: string[] }}
 */
function diagnoseBackendCrash(stderr, stdout, exitCode) {
    const combined = `${stdout || ""}\n${stderr || ""}`.toLowerCase();
    const rawCombined = `${stdout || ""}\n${stderr || ""}`;
    const hints = [];
    const memoryLine = parseMemoryLogLine(rawCombined);

    if (memoryLine) {
        const available = Number(memoryLine.available_mb);
        const action = String(memoryLine.action || "");
        if (action === "abort" || (Number.isFinite(available) && available < 200)) {
            hints.push("Close other applications to free RAM, then relaunch.");
            hints.push("On low-memory devices, try Emergency Mode from the crash screen.");
            return {
                category: "memory",
                summary: Number.isFinite(available)
                    ? `The backend reported critically low memory (${available.toFixed(0)} MB available).`
                    : "The backend aborted startup due to critically low memory.",
                hints,
            };
        }
        if (action === "warn") {
            hints.push("Emergency Mode reduces startup memory use on 4 GB devices.");
            return {
                category: "memory",
                summary: Number.isFinite(available)
                    ? `The backend detected limited memory (${available.toFixed(0)} MB available).`
                    : "The backend detected limited system memory during startup.",
                hints,
            };
        }
    }

    if (
        combined.includes("memoryerror") ||
        combined.includes("out of memory") ||
        combined.includes("cannot allocate memory") ||
        combined.includes("oom")
    ) {
        hints.push("Close other applications to free RAM, then relaunch.");
        hints.push("On low-memory devices, try Emergency Mode from the crash screen.");
        return {
            category: "memory",
            summary: "The backend likely ran out of memory during startup.",
            hints,
        };
    }

    if (
        combined.includes("eacces") ||
        combined.includes("eperm") ||
        combined.includes("permission denied") ||
        combined.includes("access is denied")
    ) {
        hints.push("Check that MeshChatX can write to its data folder.");
        hints.push("Avoid running from protected locations; portable installs should stay on a writable drive.");
        return {
            category: "permission",
            summary: "The backend could not read or write a required file or folder.",
            hints,
        };
    }

    if (
        combined.includes("address already in use") ||
        combined.includes("eaddrinuse") ||
        combined.includes("only one usage of each socket") ||
        combined.includes("port 9337")
    ) {
        hints.push(
            "Another backend copy may still be running. End ReticulumMeshChatX.exe in Task Manager, then relaunch."
        );
        return {
            category: "port-conflict",
            summary: "Port 9337 is already in use by another process.",
            hints,
        };
    }

    if (
        combined.includes("dll load failed") ||
        combined.includes("vcruntime") ||
        combined.includes("api-ms-win") ||
        combined.includes("the specified module could not be found")
    ) {
        hints.push("Install the latest Microsoft Visual C++ Redistributable (x64), then relaunch.");
        return {
            category: "runtime",
            summary: "A required Windows runtime library may be missing.",
            hints,
        };
    }

    if (combined.includes("database") && (combined.includes("corrupt") || combined.includes("malformed"))) {
        hints.push("Try Emergency Mode, or rename the storage folder after backing it up.");
        return {
            category: "database",
            summary: "The local database may be corrupted.",
            hints,
        };
    }

    if (combined.includes("!!! application crash detected !!!")) {
        hints.push("Open the saved crash report and meshchatx.log for the full diagnostic trace.");
        return {
            category: "python-crash",
            summary: "The Python backend crash recovery system captured a fatal error.",
            hints,
        };
    }

    if (exitCode === 3221226505 || combined.includes("access violation") || combined.includes("segfault")) {
        hints.push(
            "This can happen on older GPUs or low-memory systems. Try creating a disable-gpu file in the data folder."
        );
        return {
            category: "native-crash",
            summary: "The backend process crashed natively (access violation).",
            hints,
        };
    }

    if (exitCode != null && exitCode !== 0) {
        hints.push("Open the logs folder below and send meshchatx.log plus the crash report when asking for support.");
        return {
            category: "exit-code",
            summary: `The backend exited with code ${exitCode}.`,
            hints,
        };
    }

    return {
        category: "unknown",
        summary: "The backend stopped before the UI could connect.",
        hints: ["Review the saved crash report and meshchatx.log for details."],
    };
}

/**
 * @param {string} storageDir
 * @param {string} reticulumConfigDir
 * @returns {object}
 */
function getDiagnosticPaths(storageDir, reticulumConfigDir) {
    const logsDir = storageDir ? getLogsDir(storageDir) : null;
    return {
        storageDir: storageDir || null,
        reticulumConfigDir: reticulumConfigDir || null,
        logsDir,
        backendLogPath: storageDir ? getBackendLogPath(storageDir) : null,
        crashReportPath: storageDir ? getCrashReportPath(storageDir) : null,
    };
}

module.exports = {
    REPORT_FILENAME,
    clearCrashReport,
    diagnoseBackendCrash,
    getBackendLogPath,
    getCrashReportPath,
    getDiagnosticPaths,
    getLogsDir,
    loadCrashReport,
    normalizeCrash,
    parseMemoryLogLine,
    persistCrashReport,
    tailText,
};
