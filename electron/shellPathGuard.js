"use strict";

const fs = require("fs");
const path = require("node:path");

const { parseArgvFlag } = require("./mainHelpers");

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

function realpathOrNearest(targetPath) {
    // Resolve symlinks on the candidate itself; for paths that do not exist
    // yet, realpath the nearest existing ancestor and rejoin the tail so a
    // symlinked parent cannot smuggle the jail root.
    let current = path.resolve(targetPath);
    const tail = [];
    for (let depth = 0; depth < 64; depth += 1) {
        try {
            const real = fs.realpathSync.native ? fs.realpathSync.native(current) : fs.realpathSync(current);
            return tail.length ? path.join(real, ...tail.reverse()) : real;
        } catch {
            const parent = path.dirname(current);
            if (parent === current) {
                return path.resolve(targetPath);
            }
            tail.push(path.basename(current));
            current = parent;
        }
    }
    return path.resolve(targetPath);
}

function isResolvedPathUnderRoot(resolvedCandidate, rootPath) {
    const root = resolveDirForPrefixCheck(rootPath);
    const file = realpathOrNearest(resolvedCandidate);
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
 * @param {object} [options]
 * @param {boolean} [options.broadRoots] Also allow temp and the parent
 *   Downloads/Documents folders. Needed for reveal-in-folder and for reading
 *   user-picked files, but not for open-path execution.
 * @returns {boolean}
 */
function isAllowedShellPath(targetPath, ctx, options = {}) {
    const broadRoots = options.broadRoots !== false;
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
    // App-owned exchange folders are always allowed. The parent
    // Downloads/Documents folders and temp stay reveal-only: shell.openPath
    // executes targets, so it must not reach arbitrary downloaded files.
    const downloads = ctx.app.getPath("downloads");
    const documents = ctx.app.getPath("documents");
    add(path.join(downloads, "MeshChatX"));
    add(path.join(documents, "MeshChatX"));
    try {
        add(path.join(ctx.app.getPath("pictures"), "MeshChatX"));
    } catch {
        // pictures may be unavailable in some Electron test fakes
    }
    if (broadRoots) {
        add(ctx.app.getPath("temp"));
        add(downloads);
        add(documents);
    }

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
