// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");

function readRepo(relPath) {
    return readFileSync(resolve(ROOT, relPath), "utf8");
}

describe("sidebar virtualization wiring oracle", () => {
    it("MessagesSidebar renders keyed conversations and keeps incremental loading wired", () => {
        const src = readRepo("meshchatx/src/frontend/features/messages/components/MessagesSidebar.svelte");
        expect(src).toContain("{#each sortedConversations as c (c.destination_hash)}");
        expect(src).toContain("onscroll={onConversationsScroll}");
        expect(src).toContain("onloadMore?.()");
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
