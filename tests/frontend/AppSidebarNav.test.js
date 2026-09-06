// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("AppSidebarNav.svelte wiring", () => {
    it("grouped and classic nav use SidebarLink and edit-hold constants", () => {
        const grouped = src("meshchatx/src/frontend/features/app-shell/components/AppSidebarNav.svelte");
        const classic = src("meshchatx/src/frontend/features/app-shell/components/AppSidebarClassicNav.svelte");
        const hold = src("meshchatx/src/frontend/js/appSidebarNavEditHold.ts");
        const layout = src("meshchatx/src/frontend/js/appSidebarNavLayout.ts");
        expect(grouped).toContain("AppSidebarNavGroup");
        expect(classic).toContain("SidebarLink");
        expect(hold).toContain("NAV_EDIT_CLICK_GUARD_MS");
        expect(layout).toContain("NAV_EDIT_HOLD_MS");
    });
});
