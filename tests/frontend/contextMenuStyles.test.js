import { readFileSync } from "fs";
import { join } from "path";
import { describe, it, expect } from "vitest";

const root = process.cwd();

function readProjectFile(relativePath) {
    return readFileSync(join(root, relativePath), "utf8");
}

describe("context menu styling", () => {
    it("defines shared classes in style.css", () => {
        const css = readProjectFile("meshchatx/src/frontend/style.css");
        expect(css).toMatch(/\.context-menu-panel\s*\{/);
        expect(css).toMatch(/\.context-item\s*\{/);
        expect(css).toMatch(/\.context-menu-divider\s*\{/);
        expect(css).toMatch(/\.context-menu-section-label\s*\{/);
        expect(css).toContain("min-w-48");
        expect(css).toContain("rounded-xl");
        expect(css).toContain("shadow-xl");
    });

    it("uses context-menu-panel classes on all right-click context menus", () => {
        const files = [
            "meshchatx/src/frontend/features/contacts/components/ContactsContextMenu.svelte",
            "meshchatx/src/frontend/features/messages/components/ConversationMessageContextMenu.svelte",
            "meshchatx/src/frontend/features/nomadnetwork/components/NomadBrowserContextMenu.svelte",
            "meshchatx/src/frontend/features/map/components/MapContextMenu.svelte",
        ];
        for (const f of files) {
            const src = readProjectFile(f);
            expect(src, f).toContain("context-menu-panel");
            expect(src, f).toContain("context-item");
            expect(src, f).toContain("clampFloatingToViewport");
        }
    });
});
