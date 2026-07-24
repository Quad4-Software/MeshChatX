// SPDX-License-Identifier: 0BSD

/**
 * Broken-pipe (EPIPE) guards for Electron AppImage / launcher sessions where
 * stdout or stderr is closed while the main process still logs.
 */

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
 * uncaughtException dialogs when console.log writes after the pipe closes.
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

module.exports = {
    isBrokenPipeError,
    installBrokenPipeGuards,
    safeConsoleLog,
};
