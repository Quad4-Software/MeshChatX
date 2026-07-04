"use strict";

const fs = require("node:fs");
const path = require("node:path");

const { diagnoseBackendCrash } = require("./backendCrashReport");

/**
 * @param {string} dir
 * @param {"auto"|"snapshot"} kind
 * @returns {Array<{name: string, path: string, size: number, createdAt: string, kind: string, suspicious: boolean}>}
 */
function listZipBackupsInDir(dir, kind) {
    if (!dir || !fs.existsSync(dir)) {
        return [];
    }
    const entries = [];
    for (const name of fs.readdirSync(dir)) {
        if (!name.endsWith(".zip")) {
            continue;
        }
        const fullPath = path.join(dir, name);
        try {
            const stats = fs.statSync(fullPath);
            if (!stats.isFile()) {
                continue;
            }
            entries.push({
                name,
                path: fullPath,
                size: stats.size,
                createdAt: new Date(stats.mtimeMs).toISOString(),
                kind,
                suspicious: /SUSPICIOUS/i.test(name),
            });
        } catch {
            // skip unreadable entries
        }
    }
    return entries;
}

/**
 * @param {string} storageDir
 * @returns {Array<{name: string, path: string, size: number, createdAt: string, kind: string, suspicious: boolean}>}
 */
function listRecoveryBackups(storageDir) {
    if (!storageDir) {
        return [];
    }
    const auto = listZipBackupsInDir(path.join(storageDir, "database-backups"), "auto");
    const snapshots = listZipBackupsInDir(path.join(storageDir, "snapshots"), "snapshot");
    return [...auto, ...snapshots].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt));
}

/**
 * @param {Array<{suspicious: boolean, createdAt: string}>} backups
 * @returns {object|null}
 */
function pickPreferredRestoreBackup(backups) {
    if (!Array.isArray(backups) || backups.length === 0) {
        return null;
    }
    const healthy = backups.filter((entry) => !entry.suspicious);
    if (healthy.length > 0) {
        return healthy[0];
    }
    return backups[0];
}

/**
 * @param {object} ctx
 * @param {string} ctx.storageDir
 * @param {string} ctx.reticulumConfigDir
 * @param {string} ctx.platform
 * @param {string|null} ctx.portableExecutableDir
 * @returns {string}
 */
function buildDataCleanupGuide(ctx) {
    const storageDir = ctx.storageDir || "~/.reticulum-meshchatx";
    const reticulumDir = ctx.reticulumConfigDir || "~/.reticulum";
    const legacyDir = storageDir.replace(/meshchatx$/i, "meshchat").replace(/MeshChatX$/i, "meshchat");
    const lines = [
        "Complete MeshChatX / Reticulum data reset",
        "",
        "Quit MeshChatX completely before deleting anything. On Windows, also end ReticulumMeshChatX.exe in Task Manager if it is still running.",
        "",
        "MeshChatX storage (database, identities, automatic backups, logs):",
        `  ${storageDir}`,
        "",
        "Reticulum network stack (config, ratchets, path table, interface state):",
        `  ${reticulumDir}`,
        "",
    ];

    if (legacyDir && legacyDir !== storageDir) {
        lines.push("Legacy Reticulum MeshChat storage (only if you migrated from the old app):");
        lines.push(`  ${legacyDir}`);
        lines.push("");
    }

    if (ctx.platform === "win32" && ctx.portableExecutableDir) {
        lines.push("Portable Windows install: the folders above are next to MeshChatX.exe, not in your user profile.");
        lines.push(`  Portable app folder: ${ctx.portableExecutableDir}`);
        lines.push("");
    }

    lines.push("Linux / macOS default locations:");
    lines.push("  ~/.reticulum-meshchatx/");
    lines.push("  ~/.reticulum/");
    lines.push("  ~/.reticulum-meshchat/ (legacy, if present)");
    lines.push("");
    lines.push("Windows default locations:");
    lines.push("  %USERPROFILE%\\.reticulum-meshchatx\\");
    lines.push("  %USERPROFILE%\\.reticulum\\");
    lines.push("  %USERPROFILE%\\.reticulum-meshchat\\ (legacy, if present)");
    lines.push("");
    lines.push(
        "Removing these folders deletes your local identity, messages, contacts, and network path cache. You will get a new identity on the next launch unless you restore from a backup zip first."
    );
    lines.push("");
    lines.push(
        "Automatic database backups are kept under database-backups/ inside the MeshChatX storage folder when the app has run successfully before."
    );

    return lines.join("\n");
}

/**
 * @param {object} params
 * @param {string} params.storageDir
 * @param {string} params.reticulumConfigDir
 * @param {string} params.platform
 * @param {string|null} params.portableExecutableDir
 * @param {string} params.stderr
 * @param {string} params.stdout
 * @param {number|null} params.exitCode
 * @returns {object}
 */
function getCrashRecoveryInfo(params) {
    const backups = listRecoveryBackups(params.storageDir);
    const preferredBackup = pickPreferredRestoreBackup(backups);
    const diagnosis = diagnoseBackendCrash(params.stderr || "", params.stdout || "", params.exitCode ?? null);
    const paths = {
        storageDir: params.storageDir || null,
        reticulumConfigDir: params.reticulumConfigDir || null,
        backupsDir: params.storageDir ? path.join(params.storageDir, "database-backups") : null,
        snapshotsDir: params.storageDir ? path.join(params.storageDir, "snapshots") : null,
        logsDir: params.storageDir ? path.join(params.storageDir, "logs") : null,
    };
    const cleanupGuide = buildDataCleanupGuide({
        storageDir: params.storageDir,
        reticulumConfigDir: params.reticulumConfigDir,
        platform: params.platform,
        portableExecutableDir: params.portableExecutableDir,
    });

    return {
        diagnosis,
        paths,
        backups,
        preferredBackup,
        cleanupGuide,
        supportsOfflineRestore: Boolean(params.storageDir),
    };
}

module.exports = {
    buildDataCleanupGuide,
    getCrashRecoveryInfo,
    listRecoveryBackups,
    pickPreferredRestoreBackup,
};
