"use strict";

const path = require("node:path");

const IGNORED_CLI_ARGUMENTS = new Set(["--no-sandbox", "--ozone-platform-hint=auto"]);

/**
 * Arguments after argv[0], excluding known Chromium/Electron noise flags.
 * @param {string[]} argv Typically process.argv
 * @returns {string[]}
 */
function getUserProvidedArguments(argv) {
    const list = Array.isArray(argv) ? argv : [];
    return list.slice(1).filter((arg) => !IGNORED_CLI_ARGUMENTS.has(arg));
}

/**
 * Read a "--flag value" pair from argv. Does not match "--flag=value" forms.
 * @param {string[]} argv
 * @param {string} flagName
 * @returns {string | null}
 */
function parseArgvFlag(argv, flagName) {
    const list = Array.isArray(argv) ? argv : [];
    const idx = list.indexOf(flagName);
    if (idx === -1 || idx + 1 >= list.length) {
        return null;
    }
    const value = list[idx + 1];
    if (!value || value.startsWith("--")) {
        return null;
    }
    return value;
}

function firstNonEmpty(...values) {
    for (const value of values) {
        if (typeof value === "string" && value.trim()) {
            return value.trim();
        }
    }
    return null;
}

/**
 * Resolve the storage and Reticulum config roots the backend will use.
 *
 * Mirrors meshchatx.src.path_utils.resolve_meshchat_data_roots precedence so
 * Electron and the CLI agree on portable-mode layout:
 *   1. Explicit --storage-dir / --reticulum-config-dir (argv flag or env var)
 *   2. --data-dir / MESHCHAT_DATA_DIR (fills <root>/storage, <root>/.reticulum)
 *   3. Windows portable executable directory (PORTABLE_EXECUTABLE_DIR)
 *   4. The user home directory
 *
 * @param {object} ctx
 * @param {string[]} ctx.argv Electron process.argv
 * @param {Record<string, string | undefined>} ctx.env
 * @param {string} ctx.homeDir
 * @param {boolean} ctx.isWindows
 * @param {string | null | undefined} [ctx.portableExecutableDir]
 * @returns {{ storageDir: string, reticulumConfigDir: string }}
 */
function resolvePortableStorageRoots(ctx) {
    const { argv, env, homeDir, isWindows, portableExecutableDir } = ctx;
    const userArgv = getUserProvidedArguments(argv);

    let storageDir = firstNonEmpty(parseArgvFlag(userArgv, "--storage-dir"), env && env.MESHCHAT_STORAGE_DIR);
    let reticulumConfigDir = firstNonEmpty(
        parseArgvFlag(userArgv, "--reticulum-config-dir"),
        env && env.MESHCHAT_RETICULUM_CONFIG_DIR
    );

    const dataDir = firstNonEmpty(parseArgvFlag(userArgv, "--data-dir"), env && env.MESHCHAT_DATA_DIR);
    if (dataDir) {
        const root = path.resolve(dataDir);
        if (!storageDir) {
            storageDir = path.join(root, "storage");
        }
        if (!reticulumConfigDir) {
            reticulumConfigDir = path.join(root, ".reticulum");
        }
    }

    if (isWindows && portableExecutableDir) {
        if (!storageDir) {
            storageDir = path.join(portableExecutableDir, ".reticulum-meshchatx");
        }
        if (!reticulumConfigDir) {
            reticulumConfigDir = path.join(portableExecutableDir, ".reticulum");
        }
    }

    if (!storageDir) {
        storageDir = path.join(homeDir, ".reticulum-meshchatx");
    }
    if (!reticulumConfigDir) {
        reticulumConfigDir = path.join(homeDir, ".reticulum");
    }

    return { storageDir, reticulumConfigDir };
}

/**
 * @param {unknown} details Electron render-process-gone details
 * @returns {string}
 */
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

/**
 * Whether the URL is the MeshChatX local backend origin (loading / API checks).
 * @param {unknown} url
 * @returns {boolean}
 */
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

/**
 * Whether window.open should create a child Electron window instead of the OS browser.
 * Local backend popouts and call.html must stay in Electron so they keep the app session.
 * @param {unknown} url
 * @returns {boolean}
 */
function shouldOpenInElectronWindow(url) {
    if (!url || typeof url !== "string") {
        return false;
    }
    if (url.startsWith("blob:")) {
        return true;
    }
    if (!isLocalBackendUrl(url)) {
        return false;
    }
    if (url.includes("/call.html")) {
        return true;
    }
    return url.includes("#/popout/");
}

/**
 * Whether the main frame may navigate to this URL inside Electron (local app shell).
 * External http(s) links must open in the system browser instead.
 * @param {unknown} url
 * @returns {boolean}
 */
function shouldAllowInWindowNavigation(url) {
    if (!url || typeof url !== "string") {
        return false;
    }
    if (url.startsWith("blob:")) {
        return true;
    }
    return isLocalBackendUrl(url);
}

module.exports = {
    getUserProvidedArguments,
    parseArgvFlag,
    resolvePortableStorageRoots,
    formatRenderProcessGoneDetails,
    isLocalBackendUrl,
    shouldOpenInElectronWindow,
    shouldAllowInWindowNavigation,
};
