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

    it("ContextMenuPanel and ContextMenuItem components define the shared CSS classes", () => {
        const panel = readProjectFile("meshchatx/src/frontend/components/contextmenu/ContextMenuPanel.vue");
        const item = readProjectFile("meshchatx/src/frontend/components/contextmenu/ContextMenuItem.vue");
        expect(panel).toContain("context-menu-panel");
        expect(item).toContain("context-item");
    });

    it("uses ContextMenuPanel and ContextMenuItem on all right-click context menus", () => {
        const files = [
            "meshchatx/src/frontend/components/contacts/ContactsPage.vue",
            "meshchatx/src/frontend/components/messages/MessagesSidebar.vue",
            "meshchatx/src/frontend/components/messages/ConversationViewer.vue",
            "meshchatx/src/frontend/components/nomadnetwork/NomadNetworkSidebar.vue",
            "meshchatx/src/frontend/components/map/MapPage.vue",
        ];
        for (const f of files) {
            const src = readProjectFile(f);
            expect(src, f).toContain("ContextMenuPanel");
            expect(src, f).toContain("ContextMenuItem");
        }
    });
});
