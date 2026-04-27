import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    copyTextToClipboard,
    readTextFromClipboard,
    isWindowSecureContext,
} from "../../meshchatx/src/frontend/js/clipboardUtils.js";

describe("clipboardUtils", () => {
    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it("copyTextToClipboard uses execCommand when writeText rejects", async () => {
        const writeText = vi.fn(() => Promise.reject(new Error("blocked")));
        vi.stubGlobal("navigator", {
            ...navigator,
            clipboard: { writeText },
        });
        const prevExec = document.execCommand;
        const execCommand = vi.fn(() => true);
        document.execCommand = execCommand;
        try {
            const ok = await copyTextToClipboard("hello");
            expect(ok).toBe(true);
            expect(writeText).toHaveBeenCalledWith("hello");
            expect(execCommand).toHaveBeenCalledWith("copy");
        } finally {
            document.execCommand = prevExec;
        }
    });

    it("readTextFromClipboard returns insecure_context when window.isSecureContext is false (e.g. http://0.0.0.0)", async () => {
        const readText = vi.fn(() => Promise.resolve("should-not-run"));
        vi.stubGlobal("navigator", {
            ...navigator,
            clipboard: { readText },
        });
        const prev = window.isSecureContext;
        Object.defineProperty(window, "isSecureContext", {
            configurable: true,
            value: false,
        });
        const result = await readTextFromClipboard();
        expect(result.ok).toBe(false);
        expect(result.code).toBe("insecure_context");
        expect(readText).not.toHaveBeenCalled();
        Object.defineProperty(window, "isSecureContext", {
            configurable: true,
            value: prev,
        });
    });

    it("readTextFromClipboard reads when secure and API present", async () => {
        const readText = vi.fn(() => Promise.resolve("body"));
        vi.stubGlobal("navigator", {
            ...navigator,
            clipboard: { readText },
        });
        const prev = window.isSecureContext;
        Object.defineProperty(window, "isSecureContext", { configurable: true, value: true });
        try {
            const result = await readTextFromClipboard();
            expect(result.ok).toBe(true);
            expect(result.text).toBe("body");
            expect(readText).toHaveBeenCalled();
        } finally {
            Object.defineProperty(window, "isSecureContext", {
                configurable: true,
                value: prev,
            });
        }
    });

    it("isWindowSecureContext is false when explicitly false", () => {
        const prev = window.isSecureContext;
        Object.defineProperty(window, "isSecureContext", { configurable: true, value: false });
        expect(isWindowSecureContext()).toBe(false);
        Object.defineProperty(window, "isSecureContext", { configurable: true, value: prev });
    });
});
