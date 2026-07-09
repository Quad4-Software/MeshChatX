"use strict";

const { execFileSync } = require("node:child_process");

const { killOrphanBackendProcesses: killOrphanBackendProcessesWin } = require("./backendProcessWin");

const BACKEND_IMAGE_UNIX = "ReticulumMeshChatX";

/**
 * @param {string} args
 * @returns {boolean}
 */
function isHeadlessBackendArgs(args) {
    if (typeof args !== "string" || !args) {
        return false;
    }
    if (!args.includes(BACKEND_IMAGE_UNIX)) {
        return false;
    }
    return /\s--headless(?:\s|$)/.test(args) || args.endsWith(" --headless");
}

/**
 * @param {number|null|undefined} ownPid
 * @returns {number[]}
 */
function listUnixBackendPids(ownPid = null) {
    if (process.platform === "win32") {
        return [];
    }
    try {
        const out = execFileSync("ps", ["-eo", "pid=,args="], {
            encoding: "utf8",
            maxBuffer: 8 * 1024 * 1024,
        });
        const pids = [];
        for (const line of out.split(/\n/)) {
            const trimmed = line.trim();
            if (!trimmed) {
                continue;
            }
            const match = trimmed.match(/^(\d+)\s+(.*)$/);
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
            if (pid === process.pid) {
                continue;
            }
            if (!isHeadlessBackendArgs(match[2])) {
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
function killUnixPids(pids) {
    if (!Array.isArray(pids)) {
        return;
    }
    for (const pid of pids) {
        try {
            process.kill(pid, "SIGTERM");
        } catch {
            /* process may already be gone */
        }
    }
    const deadline = Date.now() + 1500;
    while (Date.now() < deadline) {
        let remaining = 0;
        for (const pid of pids) {
            try {
                process.kill(pid, 0);
                remaining += 1;
            } catch {
                /* gone */
            }
        }
        if (remaining === 0) {
            return;
        }
        const spinUntil = Date.now() + 50;
        while (Date.now() < spinUntil) {
            /* brief wait for SIGTERM to take effect */
        }
    }
    for (const pid of pids) {
        try {
            process.kill(pid, "SIGKILL");
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
    if (process.platform === "win32") {
        return killOrphanBackendProcessesWin(ownPid);
    }
    const pids = listUnixBackendPids(ownPid);
    killUnixPids(pids);
    return pids.length;
}

module.exports = {
    BACKEND_IMAGE_UNIX,
    isHeadlessBackendArgs,
    killOrphanBackendProcesses,
    killUnixPids,
    listUnixBackendPids,
};
