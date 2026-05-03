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
    add(ctx.app.getPath("downloads"));
    add(ctx.app.getPath("documents"));

    const portable = process.env.PORTABLE_EXECUTABLE_DIR;
    if (portable) {
        add(portable);
    }

    const userArgv = ctx.getUserProvidedArguments(process.argv);
    add(parseArgvFlag(userArgv, "--storage-dir"));
    add(parseArgvFlag(userArgv, "--reticulum-config-dir"));

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
