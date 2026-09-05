// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const source = readFileSync(
    resolve(process.cwd(), "meshchatx/src/frontend/features/messages/MessagesPage.svelte"),
    "utf8"
);

describe("MessagesPage sidebar integration", () => {
    it("passes conversation, peer, folder, filter, and loading state", () => {
        for (const binding of [
            "{conversations}",
            "{peers}",
            "{folders}",
            "{selectedFolderId}",
            "{conversationSearchTerm}",
            "{filterUnreadOnly}",
            "{filterFailedOnly}",
            "{filterHasAttachmentsOnly}",
            "{pinnedPeerHashes}",
        ]) {
            expect(source).toContain(binding);
        }
    });

    it("wires public sidebar callbacks to page behavior", () => {
        expect(source).toContain("onconversationClick={onConversationClick}");
        expect(source).toContain("onpeerClick={onPeerClick}");
        expect(source).toContain("onconversationSearchChanged");
        expect(source).toContain("onannouncesTabActivated");
        expect(source).toContain("onbulkMarkAsRead");
        expect(source).toContain("ontoggleConversationPin");
    });
});
