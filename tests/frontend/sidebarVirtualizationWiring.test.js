// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");

function readRepo(relPath) {
    return readFileSync(resolve(ROOT, relPath), "utf8");
}

describe("sidebar virtualization wiring oracle", () => {
    it("MessagesSidebar virtualizes conversations at MIN_VIRTUAL_SIDEBAR_ITEMS", () => {
        const src = readRepo("meshchatx/src/frontend/components/messages/MessagesSidebar.vue");
        expect(src).toContain("SidebarVirtualList");
        expect(src).toContain("displayedConversations.length >= MIN_VIRTUAL_SIDEBAR_ITEMS");
        expect(src).toContain('@scroll="onConversationsScroll"');
        expect(src).toContain("MIN_VIRTUAL_SIDEBAR_ITEMS");
    });

    it("NomadNetworkSidebar virtualizes searched nodes at the threshold", () => {
        const src = readRepo("meshchatx/src/frontend/components/nomadnetwork/NomadNetworkSidebar.vue");
        expect(src).toContain("SidebarVirtualList");
        expect(src).toContain("searchedNodes.length >= MIN_VIRTUAL_SIDEBAR_ITEMS");
        expect(src).toContain('@scroll="onNodesScroll"');
    });

    it("ContactsPage uses paginated list (virtual list deferred for Svelte port)", () => {
        const src = readRepo("meshchatx/src/frontend/features/contacts/ContactsPage.svelte");
        expect(src).toContain("getContacts(true)");
        expect(src).toContain("mergedContacts");
        expect(src).not.toContain("SidebarVirtualList");
    });
});
