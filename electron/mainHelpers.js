"use strict";

const path = require("node:path");

const IGNORED_CLI_ARGUMENTS = new Set([
    "--no-sandbox",
    "--ozone-platform-hint=auto",
    "--disable-gpu",
    "--disable-gpu-sandbox",
    "--disable-gpu-compositing",
    "--disable-software-rasterizer",
    "--enable-logging",
    "--enable-logging=stderr",
]);

// URL-like argv entries (lxmf://..., rns://...) arrive from cold-start deep
// links. The backend runs argparse in strict mode, so forwarding them would
// exit the backend with code 2.
const URL_SCHEME_ARG_PATTERN = /^\w[\w+.-]*:\/\//;

// Deep link schemes this app registers via setAsDefaultProtocolClient and the
// packaged CFBundleURLTypes / desktop file.
const PROTOCOL_URL_ARG_PATTERN = /^(?:lxmf|rns):\/\//i;

/**
 * Arguments after argv[0], excluding known Chromium/Electron noise flags and
 * URL-scheme deep link arguments that the backend parser would reject.
 * @param {string[]} argv Typically process.argv
 * @returns {string[]}
 */
function getUserProvidedArguments(argv) {
    const list = Array.isArray(argv) ? argv : [];
    return list.slice(1).filter((arg) => !IGNORED_CLI_ARGUMENTS.has(arg) && !URL_SCHEME_ARG_PATTERN.test(arg));
}

/**
 * First deep link URL in argv (lxmf:// or rns://), or null.
 * @param {string[]} argv
 * @returns {string | null}
 */
function findProtocolUrlArg(argv) {
    const list = Array.isArray(argv) ? argv : [];
    for (const arg of list) {
        if (typeof arg === "string" && PROTOCOL_URL_ARG_PATTERN.test(arg)) {
            return arg;
        }
    }
    return null;
}

/**
 * Whether argv contains "--flag" or "--flag=value" for flagName.
 * @param {string[]} argv
 * @param {string} flagName
 * @returns {boolean}
 */
function hasArgvFlag(argv, flagName) {
    const list = Array.isArray(argv) ? argv : [];
    const prefix = `${flagName}=`;
    return list.some((arg) => arg === flagName || (typeof arg === "string" && arg.startsWith(prefix)));
}

/**
 * Read a flag value from argv. Supports both "--flag value" and "--flag=value"
 * forms so Electron resolves the same paths the backend argparse accepts.
 * @param {string[]} argv
 * @param {string} flagName
 * @returns {string | null}
 */
function parseArgvFlag(argv, flagName) {
    const list = Array.isArray(argv) ? argv : [];
    const prefix = `${flagName}=`;
    for (const arg of list) {
        if (typeof arg === "string" && arg.startsWith(prefix)) {
            const value = arg.slice(prefix.length);
            return value ? value : null;
        }
    }
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

const {
    isLocalBackendUrl,
    isTrustedBlobUrl,
    isTrustedShellFileUrl,
    isTrustedShellOrigin,
    isTrustedIpcEvent,
    senderUrlFromIpcEvent,
    shouldOpenInElectronWindow,
    shouldAllowInWindowNavigation,
} = require("./shellOrigin");

module.exports = {
    getUserProvidedArguments,
    findProtocolUrlArg,
    hasArgvFlag,
    parseArgvFlag,
    resolvePortableStorageRoots,
    formatRenderProcessGoneDetails,
    isLocalBackendUrl,
    isTrustedBlobUrl,
    isTrustedShellFileUrl,
    isTrustedShellOrigin,
    isTrustedIpcEvent,
    senderUrlFromIpcEvent,
    shouldOpenInElectronWindow,
    shouldAllowInWindowNavigation,
};
