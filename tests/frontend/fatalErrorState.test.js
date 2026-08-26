import { describe, it, expect, beforeEach, vi } from "vitest";
import {
    buildFatalErrorRecord,
    formatFatalErrorReport,
    reportFatalError,
    reportBootFailure,
    clearFatalError,
} from "../../meshchatx/src/frontend/js/fatalErrorState.js";

describe("fatalErrorState", () => {
    beforeEach(() => {
        clearFatalError();
    });

    it("builds normalized fatal error records", () => {
        const record = buildFatalErrorRecord({
            kind: "backend",
            message: "Backend unreachable",
            details: "status timeout",
        });
        expect(record.kind).toBe("backend");
        expect(record.message).toBe("Backend unreachable");
        expect(record.details).toBe("status timeout");
        expect(record.timestamp).toBeTypeOf("number");
    });

    it("reports active frontend errors", () => {
        reportFatalError({
            kind: "frontend",
            message: "Render failed",
            stack: "Error: Render failed",
            context: "render",
        });
        const report = formatFatalErrorReport(
            buildFatalErrorRecord({
                kind: "frontend",
                message: "Render failed",
                stack: "Error: Render failed",
                context: "render",
                timestamp: 1,
            })
        );
        expect(report).toContain("Kind: frontend");
        expect(report).toContain("Render failed");
        expect(report).toContain("Context: render");
    });

    it("stores boot failures as active errors", () => {
        const record = reportBootFailure({
            kind: "backend",
            title: "Backend unreachable",
            message: "Network startup timed out. Try reloading.",
        });
        expect(record.kind).toBe("backend");
        expect(record.title).toBe("Backend unreachable");
    });
});

describe("bootSplashError", () => {
    it("reveals boot splash actions on fatal startup", async () => {
        document.body.innerHTML = `
            <div id="meshchatx-boot-splash">
                <div data-boot-title hidden></div>
                <div data-boot-line></div>
                <pre data-boot-details hidden></pre>
                <div data-boot-actions hidden>
                    <button data-boot-reload></button>
                    <button data-boot-copy><span data-boot-copy-label data-copied-label="Copied">Copy</span></button>
                </div>
            </div>
        `;

        const { showBootSplashFatalError } = await import("../../meshchatx/src/frontend/js/bootSplashError.js");
        showBootSplashFatalError({
            kind: "backend",
            title: "Backend unreachable",
            message: "Network startup timed out. Try reloading.",
            details: "status timeout",
        });

        const splash = document.getElementById("meshchatx-boot-splash");
        expect(splash?.getAttribute("data-state")).toBe("error");
        expect(document.querySelector("[data-boot-actions]")?.hidden).toBe(false);
        expect(document.querySelector("[data-boot-line]")?.textContent).toContain("timed out");
    });
});
