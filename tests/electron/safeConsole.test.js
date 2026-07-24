// SPDX-License-Identifier: 0BSD

import { createRequire } from "module";
import { beforeEach, describe, expect, it, vi } from "vitest";

const require = createRequire(import.meta.url);
const {
    isBrokenPipeError,
    installBrokenPipeGuards,
    safeConsoleLog,
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
});
