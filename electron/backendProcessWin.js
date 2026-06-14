"use strict";

const { execFileSync } = require("node:child_process");

const BACKEND_IMAGE = "ReticulumMeshChatX.exe";

/**
 * @param {number|null|undefined} ownPid
 * @returns {number[]}
 */
function listBackendPids(ownPid = null) {
    if (process.platform !== "win32") {
        return [];
    }
    try {
        const out = execFileSync("tasklist", ["/FI", `IMAGENAME eq ${BACKEND_IMAGE}`, "/FO", "CSV", "/NH"], {
            encoding: "utf8",
            windowsHide: true,
        });
        const pids = [];
        for (const line of out.split(/\r?\n/)) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith("INFO:")) {
                continue;
            }
            const match = trimmed.match(/"[^"]+","(\d+)"/);
            if (!match) {
                continue;
            }
            const pid = Number(match[1]);
            if (!Number.isFinite(pid) || pid <= 0) {
                continue;
            }
            if (ownPid != null && pid === ownPid) {
                continue;
            }
            pids.push(pid);
        }
        return pids;
    } catch {
        return [];
    }
}

/**
 * @param {number[]} pids
 */
function killPids(pids) {
    if (process.platform !== "win32" || !Array.isArray(pids)) {
        return;
    }
    for (const pid of pids) {
        try {
            execFileSync("taskkill", ["/F", "/T", "/PID", String(pid)], {
                stdio: "ignore",
                windowsHide: true,
            });
        } catch {
            /* process may already be gone */
        }
    }
}

/**
 * @param {number|null|undefined} ownPid
 * @returns {number}
 */
function killOrphanBackendProcesses(ownPid = null) {
    const pids = listBackendPids(ownPid);
    killPids(pids);
    return pids.length;
}

module.exports = {
    BACKEND_IMAGE,
    killOrphanBackendProcesses,
    killPids,
    listBackendPids,
};
