// SPDX-License-Identifier: 0BSD

/**
 * Main-process log policy for Electron.
 *
 * Desktop launchers (AppImage, .desktop) often start MeshChatX with stdout
 * attached to a pipe that later closes. Writing console.log then raises EPIPE.
 * Prefer a durable file under the storage logs dir, and only mirror to stdout
 * when it is still a TTY (or when forced via env).
 */

const fs = require("node:fs");
const path = require("node:path");

const ELECTRON_LOG_PREFIX = "[electron] ";

function isBrokenPipeError(err) {
    if (!err || typeof err !== "object") {
        return false;
    }
    if (err.code === "EPIPE" || err.errno === "EPIPE") {
        return true;
    }
    const message = typeof err.message === "string" ? err.message : "";
    return /\bEPIPE\b/i.test(message);
}

/**
 * Attach no-op error listeners so closed stdout/stderr do not become
 * uncaughtException dialogs when a write races the pipe close.
 * @param {{ stdout?: NodeJS.WritableStream, stderr?: NodeJS.WritableStream } | null | undefined} [proc]
 */
function installBrokenPipeGuards(proc = process) {
    const attach = (stream) => {
        if (!stream || typeof stream.on !== "function") {
            return;
        }
        if (stream.__meshchatxBrokenPipeGuarded) {
            return;
        }
        stream.__meshchatxBrokenPipeGuarded = true;
        stream.on("error", (err) => {
            if (isBrokenPipeError(err)) {
                return;
            }
        });
    };
    attach(proc?.stdout);
    attach(proc?.stderr);
}

/**
 * True when stdout is a live terminal, or MESHCHAT_FORCE_STDOUT_LOG=1.
 * Packaged AppImage / desktop launches usually have isTTY false.
 * @param {{ stdout?: { isTTY?: boolean } } | null | undefined} [proc]
 * @param {NodeJS.ProcessEnv} [env]
 */
function shouldMirrorStdout(proc = process, env = process.env) {
    if (env?.MESHCHAT_DISABLE_STDOUT_LOG === "1") {
        return false;
    }
    if (env?.MESHCHAT_FORCE_STDOUT_LOG === "1") {
        return true;
    }
    return Boolean(proc?.stdout && proc.stdout.isTTY);
}

/**
 * console.log that never throws on a closed stdout pipe.
 * @param {...unknown} args
 */
function safeConsoleLog(...args) {
    try {
        console.log(...args);
    } catch (err) {
        if (!isBrokenPipeError(err)) {
            throw err;
        }
    }
}

/**
 * @param {string} message
 * @returns {string}
 */
function formatElectronLogLine(message) {
    const text = String(message ?? "").replace(/\s+$/u, "");
    return `${new Date().toISOString()} ${ELECTRON_LOG_PREFIX}${text}\n`;
}

/**
 * Create a durable main-process logger that appends to meshchatx.log.
 * @param {{
 *   getLogsDir: () => string | null | undefined,
 *   appendFileSync?: typeof fs.appendFileSync,
 *   mkdirSync?: typeof fs.mkdirSync,
 *   now?: () => Date,
 * }} options
 */
function createMainProcessLogger(options) {
    const getLogsDir = options.getLogsDir;
    const appendFileSync = options.appendFileSync || fs.appendFileSync.bind(fs);
    const mkdirSync = options.mkdirSync || fs.mkdirSync.bind(fs);
    const pending = [];
    let disabled = false;

    function resolveLogPath() {
        let logsDir;
        try {
            logsDir = getLogsDir?.();
        } catch {
            return null;
        }
        if (!logsDir || typeof logsDir !== "string") {
            return null;
        }
        return path.join(logsDir, "meshchatx.log");
    }

    function flushPending() {
        if (!pending.length) {
            return;
        }
        const logPath = resolveLogPath();
        if (!logPath) {
            return;
        }
        const chunk = pending.splice(0, pending.length).join("");
        try {
            mkdirSync(path.dirname(logPath), { recursive: true });
            appendFileSync(logPath, chunk, { encoding: "utf8" });
        } catch {
            disabled = true;
        }
    }

    function writeToFile(message) {
        if (disabled) {
            return;
        }
        const line = formatElectronLogLine(message);
        const logPath = resolveLogPath();
        if (!logPath) {
            pending.push(line);
            return;
        }
        flushPending();
        try {
            mkdirSync(path.dirname(logPath), { recursive: true });
            appendFileSync(logPath, line, { encoding: "utf8" });
        } catch {
            disabled = true;
        }
    }

    /**
     * Durable file write plus best-effort stdout when a TTY is present.
     * @param {unknown} message
     * @param {{ mirrorStdout?: boolean, proc?: NodeJS.Process, env?: NodeJS.ProcessEnv }} [opts]
     */
    function write(message, opts = {}) {
        writeToFile(message);
        const mirror =
            opts.mirrorStdout !== undefined
                ? opts.mirrorStdout
                : shouldMirrorStdout(opts.proc || process, opts.env || process.env);
        if (mirror) {
            safeConsoleLog(message);
        }
    }

    return {
        write,
        flushPending,
        _pendingForTests: pending,
        _formatLineForTests: formatElectronLogLine,
    };
}

module.exports = {
    isBrokenPipeError,
    installBrokenPipeGuards,
    safeConsoleLog,
    shouldMirrorStdout,
    formatElectronLogLine,
    createMainProcessLogger,
    ELECTRON_LOG_PREFIX,
};
