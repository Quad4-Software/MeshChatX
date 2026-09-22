import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const {
    isHeadlessBackendArgs,
    killOrphanBackendProcesses,
    killUnixPids,
} = require("../../electron/backendProcessOrphans.js");

describe("electron/backendProcessOrphans", () => {
    it("detects headless backend command lines", () => {
        expect(isHeadlessBackendArgs("/tmp/.mount_x/resources/backend/ReticulumMeshChatX --headless --port 9337")).toBe(
            true
        );
        expect(isHeadlessBackendArgs("/home/user/ReticulumMeshChatX --headless")).toBe(true);
    });

    it("ignores non-backend and non-headless processes", () => {
        expect(isHeadlessBackendArgs("reticulum-meshchatx --type=renderer")).toBe(false);
        expect(isHeadlessBackendArgs("/tmp/ReticulumMeshChatX")).toBe(false);
        expect(isHeadlessBackendArgs("")).toBe(false);
        expect(isHeadlessBackendArgs(null)).toBe(false);
    });

    it("killOrphanBackendProcesses is async and resolves with a count", async () => {
        const result = killOrphanBackendProcesses(process.pid);
        expect(typeof result.then).toBe("function");
        expect(typeof (await result)).toBe("number");
    });

    it("killUnixPids reaps a real process without blocking the event loop", async () => {
        if (process.platform === "win32") {
            return;
        }
        const { spawn } = require("node:child_process");
        const sleeper = spawn("sleep", ["30"]);
        const intervalTicks = [];
        const interval = setInterval(() => intervalTicks.push(Date.now()), 10);
        try {
            await killUnixPids([sleeper.pid]);
        } finally {
            clearInterval(interval);
            try {
                process.kill(sleeper.pid, "SIGKILL");
            } catch {
                /* already gone */
            }
        }
        // A synchronous busy-wait would starve the interval timer entirely.
        expect(intervalTicks.length).toBeGreaterThan(0);
        expect(() => process.kill(sleeper.pid, 0)).toThrow();
    });
});
