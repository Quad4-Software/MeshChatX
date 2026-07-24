// SPDX-License-Identifier: 0BSD

import { createRequire } from "module";
import { beforeEach, describe, expect, it, vi } from "vitest";

const require = createRequire(import.meta.url);
const {
    isBrokenPipeError,
    installBrokenPipeGuards,
    safeConsoleLog,
    shouldMirrorStdout,
    createMainProcessLogger,
    ELECTRON_LOG_PREFIX,
} = require("../../electron/safeConsole");

describe("safeConsole", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it("detects EPIPE by code and message", () => {
        expect(isBrokenPipeError({ code: "EPIPE" })).toBe(true);
        expect(isBrokenPipeError({ errno: "EPIPE" })).toBe(true);
        expect(isBrokenPipeError(new Error("write EPIPE"))).toBe(true);
        expect(isBrokenPipeError(new Error("other"))).toBe(false);
        expect(isBrokenPipeError(null)).toBe(false);
    });

    it("installBrokenPipeGuards ignores EPIPE stream errors", () => {
        const handlers = [];
        const stream = {
            on(event, handler) {
                handlers.push([event, handler]);
            },
        };
        installBrokenPipeGuards({ stdout: stream, stderr: null });
        expect(handlers).toHaveLength(1);
        expect(handlers[0][0]).toBe("error");
        expect(() => handlers[0][1]({ code: "EPIPE" })).not.toThrow();
        installBrokenPipeGuards({ stdout: stream, stderr: null });
        expect(handlers).toHaveLength(1);
    });

    it("safeConsoleLog swallows EPIPE from console.log", () => {
        const spy = vi.spyOn(console, "log").mockImplementation(() => {
            const err = new Error("write EPIPE");
            err.code = "EPIPE";
            throw err;
        });
        expect(() => safeConsoleLog("backend line")).not.toThrow();
        expect(spy).toHaveBeenCalledWith("backend line");
    });

    it("safeConsoleLog rethrows non-EPIPE errors", () => {
        vi.spyOn(console, "log").mockImplementation(() => {
            throw new Error("boom");
        });
        expect(() => safeConsoleLog("x")).toThrow("boom");
    });

    it("shouldMirrorStdout is false without a TTY unless forced", () => {
        expect(shouldMirrorStdout({ stdout: { isTTY: false } }, {})).toBe(false);
        expect(shouldMirrorStdout({ stdout: { isTTY: true } }, {})).toBe(true);
        expect(shouldMirrorStdout({ stdout: { isTTY: false } }, { MESHCHAT_FORCE_STDOUT_LOG: "1" })).toBe(true);
        expect(shouldMirrorStdout({ stdout: { isTTY: true } }, { MESHCHAT_DISABLE_STDOUT_LOG: "1" })).toBe(false);
    });

    it("createMainProcessLogger appends durable lines and skips non-TTY stdout", () => {
        const writes = [];
        const mkdirCalls = [];
        const logger = createMainProcessLogger({
            getLogsDir: () => "/tmp/meshchat-logs",
            mkdirSync: (dir, opts) => {
                mkdirCalls.push([dir, opts]);
            },
            appendFileSync: (file, data) => {
                writes.push([file, data]);
            },
        });
        const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});

        logger.write("backend ready", {
            proc: { stdout: { isTTY: false } },
            env: {},
        });

        expect(consoleSpy).not.toHaveBeenCalled();
        expect(mkdirCalls.length).toBeGreaterThan(0);
        expect(writes).toHaveLength(1);
        expect(writes[0][0]).toBe("/tmp/meshchat-logs/meshchatx.log");
        expect(writes[0][1]).toContain(ELECTRON_LOG_PREFIX);
        expect(writes[0][1]).toContain("backend ready");
    });

    it("createMainProcessLogger mirrors to stdout when TTY is present", () => {
        const logger = createMainProcessLogger({
            getLogsDir: () => "/tmp/meshchat-logs",
            mkdirSync: () => {},
            appendFileSync: () => {},
        });
        const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
        logger.write("tty line", {
            proc: { stdout: { isTTY: true } },
            env: {},
        });
        expect(consoleSpy).toHaveBeenCalledWith("tty line");
    });

    it("createMainProcessLogger buffers until logs dir is available", () => {
        let logsDir = null;
        const writes = [];
        const logger = createMainProcessLogger({
            getLogsDir: () => logsDir,
            mkdirSync: () => {},
            appendFileSync: (file, data) => {
                writes.push([file, data]);
            },
        });
        logger.write("early", { mirrorStdout: false });
        expect(writes).toHaveLength(0);
        expect(logger._pendingForTests.length).toBe(1);

        logsDir = "/tmp/meshchat-logs";
        logger.write("later", { mirrorStdout: false });
        expect(writes.length).toBeGreaterThanOrEqual(1);
        const joined = writes.map((entry) => entry[1]).join("");
        expect(joined).toContain("early");
        expect(joined).toContain("later");
        expect(logger._pendingForTests.length).toBe(0);
    });
});
