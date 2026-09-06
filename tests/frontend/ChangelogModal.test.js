// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("ChangelogModal.svelte wiring", () => {
    it("fetches changelog HTML and supports page mode", () => {
        const modal = src("meshchatx/src/frontend/features/app-shell/components/ChangelogModal.svelte");
        expect(modal).toContain("/api/v1/app/changelog");
        expect(modal).toContain("export async function show");
        expect(modal).toContain("isPage");
        expect(modal).toContain("changelogHtml");
        expect(modal).toContain("{@html changelogHtml}");
    });
});
