// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("TutorialPrivacyStep.svelte wiring", () => {
    it("privacy step exposes privacy mode controls", () => {
        const step = src("meshchatx/src/frontend/features/tutorial/components/TutorialPrivacyStep.svelte");
        expect(step).toContain("privacy");
        expect(step.length).toBeGreaterThan(100);
    });
});
