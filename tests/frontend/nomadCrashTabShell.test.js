// SPDX-License-Identifier: 0BSD
import { describe, expect, it } from "vitest";
import {
    NOMAD_CRASH_TAB_CHANNEL,
    nomadCrashTabRendererUrl,
} from "../../meshchatx/src/frontend/js/nomadCrashTabShell.js";

describe("nomadCrashTabShell", () => {
    it("exports a stable postMessage channel", () => {
        expect(NOMAD_CRASH_TAB_CHANNEL).toBe("nomad-crash-tab");
    });

    it("builds a same-origin crash-tab URL", () => {
        const url = nomadCrashTabRendererUrl();
        expect(url).toContain("nomad-crash-tab.html");
    });
});
