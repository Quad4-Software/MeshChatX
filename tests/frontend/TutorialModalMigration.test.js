// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("TutorialModal Svelte migration wiring", () => {
    it("TutorialModalHost and page steps remain connected", () => {
        const host = src("meshchatx/src/frontend/features/tutorial/components/TutorialModalHost.svelte");
        const steps = src("meshchatx/src/frontend/features/tutorial/components/TutorialSteps.svelte");
        expect(host).toContain("TutorialSteps");
        expect(steps).toContain("TutorialStepWelcome");
        expect(steps).toContain("TutorialStepIdentity");
        expect(steps).toContain("TutorialPrivacyStep");
        expect(steps).toContain("TutorialStepConnect");
    });
});
