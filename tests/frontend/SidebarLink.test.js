// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("SidebarLink.svelte wiring", () => {
    it("uses hash hrefs and active route styling", () => {
        const link = src("meshchatx/src/frontend/features/app-shell/components/SidebarLink.svelte");
        expect(link).toContain("navRouteIsActive");
        expect(link).toContain("sidebar-nav-link");
        expect(link).toContain("rounded-r-full");
        expect(link).toContain("editMode");
    });
});
