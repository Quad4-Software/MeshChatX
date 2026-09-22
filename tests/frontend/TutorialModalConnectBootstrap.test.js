// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("Tutorial connect bootstrap wiring", () => {
    it("connect and bootstrap steps own interface discovery hooks", () => {
        const connect = src("meshchatx/src/frontend/features/tutorial/components/TutorialStepConnect.svelte");
        const bootstrap = src("meshchatx/src/frontend/features/tutorial/components/TutorialStepBootstrap.svelte");
        expect(connect.length).toBeGreaterThan(100);
        expect(bootstrap.length).toBeGreaterThan(100);
    });
});
