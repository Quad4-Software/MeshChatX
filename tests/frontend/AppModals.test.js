// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("app-shell overlays and modals", () => {
    it("AppShellOverlays hosts changelog, command palette, confirm, and prompt", () => {
        const overlays = src("meshchatx/src/frontend/features/app-shell/components/AppShellOverlays.svelte");
        expect(overlays).toContain("ChangelogModal");
        expect(overlays).toContain("CommandPalette");
        expect(overlays).toContain("ConfirmDialog");
        expect(overlays).toContain("PromptDialog");
        expect(overlays).toContain("AndroidStorageChoicePrompt");
        expect(overlays).toContain("AppIdentitySwitchOverlay");
    });

    it("command and changelog shell hooks stay connected", () => {
        const commands = src("meshchatx/src/frontend/features/app-shell/lib/appShellCommands.ts");
        const nav = src("meshchatx/src/frontend/features/app-shell/lib/appShellNav.ts");
        expect(commands).toContain("onShowChangelogShell");
        expect(commands).toContain("onShowTutorialShell");
        expect(nav).toContain("export function openCommandPalette");
    });
});
