// SPDX-License-Identifier: 0BSD

import { describe, it, expect } from "vitest";
import { bundledReticulumManualDeepLink } from "../../meshchatx/src/frontend/js/reticulumDocsNavigation.js";

describe("bundledReticulumManualDeepLink", () => {
    it("builds meshchatx://docs with reticulum query", () => {
        const u = bundledReticulumManualDeepLink("manual/interfaces.html#common-interface-options");
        expect(u.startsWith("meshchatx://docs?")).toBe(true);
        const parsed = new URL(u.replace(/^meshchatx:/, "https:"));
        expect(parsed.searchParams.get("reticulum")).toBe("manual/interfaces.html#common-interface-options");
    });

    it("supports meshchat scheme alias", () => {
        expect(bundledReticulumManualDeepLink("manual/index.html", "meshchat")).toMatch(
            /^meshchat:\/\/docs\?reticulum=/
        );
    });
});
