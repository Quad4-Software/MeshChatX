// SPDX-License-Identifier: 0BSD
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
    NOMAD_CRASH_TAB_CHANNEL,
    nomadCrashTabRendererUrl,
} from "../../meshchatx/src/frontend/js/nomadCrashTabShell.js";

const crashTabHtml = readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "../../meshchatx/src/frontend/nomad-crash-tab.html"),
    "utf8"
);

describe("nomadCrashTabShell", () => {
    it("exports a stable postMessage channel", () => {
        expect(NOMAD_CRASH_TAB_CHANNEL).toBe("nomad-crash-tab");
    });

    it("builds a same-origin crash-tab URL", () => {
        const url = nomadCrashTabRendererUrl();
        expect(url).toContain("nomad-crash-tab.html");
    });

    it("pins the crash-tab URL to the build so stale heuristic caches miss", () => {
        // In dev __APP_BUILD_TIME__ may be undefined; the URL must still work.
        const url = nomadCrashTabRendererUrl();
        expect(url.startsWith("/") || url.startsWith("http")).toBe(true);
        if (typeof __APP_BUILD_TIME__ !== "undefined" && __APP_BUILD_TIME__) {
            expect(url).toContain(`v=${encodeURIComponent(__APP_BUILD_TIME__)}`);
        }
    });

    it("clamps document width so pages do not spawn a body x-scrollbar", () => {
        expect(crashTabHtml).toContain("overflow-x: hidden");
        expect(crashTabHtml).toContain("max-width: 100%");
        expect(crashTabHtml).toMatch(/#root\s*\{[^}]*overflow-x:\s*hidden/s);
    });

    it("paints a dark document before the renderer module loads", () => {
        expect(crashTabHtml).toContain('content="dark"');
        expect(crashTabHtml).toContain("color-scheme: dark");
        expect(crashTabHtml).toContain("background: #000000");
    });

    it("has a neutral document title for screen readers before the page loads", () => {
        expect(crashTabHtml).toContain("<title>Nomad</title>");
    });
});
