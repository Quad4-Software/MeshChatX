// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("app-shell sidebar identity label and announce control", () => {
    it("wires identity sidebar label and announce controls in Svelte shell", () => {
        const derived = src("meshchatx/src/frontend/features/app-shell/lib/appShellDerived.ts");
        const identity = src("meshchatx/src/frontend/features/app-shell/lib/appShellIdentity.ts");
        const panel = src("meshchatx/src/frontend/features/app-shell/components/AppShellSidebarPanel.svelte");
        const footer = src("meshchatx/src/frontend/features/app-shell/components/AppSidebarAccountFooter.svelte");
        expect(derived).toContain("identitySidebarLabel");
        expect(derived).toContain("lastAnnouncedSidebarLabel");
        expect(identity).toContain("export async function sendAnnounce");
        expect(identity).toContain("export async function onAnnounceIntervalChange");
        expect(panel).toContain("sendAnnounce(shell)");
        expect(panel).toContain("onAnnounceIntervalChange(shell, seconds)");
        expect(footer).toContain("onsendannounce");
        expect(footer).toContain("sidebar-auto-announce-interval");
    });
});
