"use strict";

const fs = require("fs");
const path = require("node:path");

function parseArgvFlag(argv, flagName) {
    const list = Array.isArray(argv) ? argv : [];
    const idx = list.indexOf(flagName);
    if (idx === -1 || idx + 1 >= list.length) {
        return null;
    }
    const v = list[idx + 1];
    if (!v || v.startsWith("--")) {
        return null;
    }
    return v;
}

function resolveDirForPrefixCheck(dirPath) {
    try {
        if (typeof fs.realpathSync.native === "function") {
            return fs.realpathSync.native(dirPath);
        }
        return fs.realpathSync(dirPath);
    } catch {
        return path.resolve(dirPath);
    }
}

function isResolvedPathUnderRoot(resolvedCandidate, rootPath) {
    const root = resolveDirForPrefixCheck(rootPath);
    const file = path.resolve(resolvedCandidate);
    const rel = path.relative(root, file);
    return rel === "" || (!rel.startsWith(`..${path.sep}`) && rel !== "..");
}

function pairedLegacyStorageDir(defaultStorageDir) {
    const base = path.basename(path.resolve(defaultStorageDir));
    if (base !== ".reticulum-meshchatx") {
        return null;
    }
    return path.join(path.dirname(path.resolve(defaultStorageDir)), ".reticulum-meshchat");
}

/**
 * @param {string} targetPath
 * @param {object} ctx
 * @param {import("electron").App} ctx.app
 * @param {() => string} ctx.getDefaultStorageDir
 * @param {() => string} ctx.getDefaultReticulumConfigDir
 * @param {(argv: string[]) => string[]} ctx.getUserProvidedArguments
 * @returns {boolean}
 */
function isAllowedShellPath(targetPath, ctx) {
    if (typeof targetPath !== "string" || !targetPath.trim()) {
        return false;
    }
    if (targetPath.includes("\0")) {
        return false;
    }
    const resolved = path.resolve(targetPath.trim());
    const roots = [];
    const add = (p) => {
        if (p) {
            roots.push(p);
        }
    };

    add(ctx.getDefaultStorageDir());
    add(pairedLegacyStorageDir(ctx.getDefaultStorageDir()));
    add(ctx.getDefaultReticulumConfigDir());
    add(ctx.app.getPath("userData"));
    add(ctx.app.getPath("temp"));
    // Prefer app-owned exchange folders. Keep parent Downloads/Documents so
    // reveal-in-folder still works for browser saves that landed outside them.
    const downloads = ctx.app.getPath("downloads");
    const documents = ctx.app.getPath("documents");
    add(path.join(downloads, "MeshChatX"));
    add(path.join(documents, "MeshChatX"));
    try {
        add(path.join(ctx.app.getPath("pictures"), "MeshChatX"));
    } catch {
        // pictures may be unavailable in some Electron test fakes
    }
    add(downloads);
    add(documents);

    const portable = process.env.PORTABLE_EXECUTABLE_DIR;
    if (portable) {
        add(portable);
    }

    const userArgv = ctx.getUserProvidedArguments(process.argv);
    add(parseArgvFlag(userArgv, "--storage-dir"));
    add(parseArgvFlag(userArgv, "--reticulum-config-dir"));
    const dataDir =
        parseArgvFlag(userArgv, "--data-dir") ||
        (process.env.MESHCHAT_DATA_DIR && String(process.env.MESHCHAT_DATA_DIR).trim()) ||
        null;
    if (dataDir) {
        add(path.join(dataDir, "storage"));
        add(path.join(dataDir, ".reticulum"));
    }

    for (const root of roots) {
        if (root && isResolvedPathUnderRoot(resolved, root)) {
            return true;
        }
    }
    return false;
}

module.exports = {
    isAllowedShellPath,
};
