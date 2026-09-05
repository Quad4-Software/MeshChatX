// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    applyWsMessage,
    deleteWsMessage,
    updateWsMessage,
    visibleConversationItems,
} from "@/features/messages/lib/conversationViewerMessages.ts";
import {
    collectImageFilesFromDataTransfer,
    hasMessageBubble,
    isTelemetryOnly,
} from "@/features/messages/lib/conversationMessageHelpers.ts";
import { loadDraft, saveDraft } from "@/features/messages/lib/conversationDrafts.ts";

const peerHash = "aa".repeat(16);
const myHash = "bb".repeat(16);

function item(message) {
    return {
        type: "lxmf_message",
        is_outbound: message.source_hash === myHash,
        lxmf_message: {
            hash: "message",
            source_hash: peerHash,
            destination_hash: myHash,
            content: "hello",
            fields: {},
            ...message,
        },
    };
}

describe("ConversationViewer message contracts", () => {
    it("shows selected-peer messages and excludes unrelated rows", () => {
        const selected = item({ hash: "selected" });
        const unrelated = item({
            hash: "unrelated",
            source_hash: "cc".repeat(16),
            destination_hash: "dd".repeat(16),
        });

        expect(visibleConversationItems([selected, unrelated], peerHash, true)).toEqual([selected]);
    });

    it("hides telemetry-only rows when telemetry display is disabled", () => {
        const telemetry = item({
            content: "",
            fields: { telemetry: { location: { latitude: 1, longitude: 2 } } },
        });

        expect(isTelemetryOnly(telemetry.lxmf_message)).toBe(true);
        expect(visibleConversationItems([telemetry], peerHash, false)).toEqual([]);
    });

    it("replaces a matching websocket row and deletes by hash", () => {
        const current = [item({ hash: "target", state: "sending" })];
        const updated = updateWsMessage(current, { hash: "TARGET", state: "delivered" });

        expect(updated).not.toBe(current);
        expect(updated[0].lxmf_message.state).toBe("delivered");
        expect(deleteWsMessage(updated, "target")).toEqual([]);
    });

    it("replaces a pending outbound placeholder with its server message", () => {
        const current = [
            item({
                hash: "pending-1",
                source_hash: myHash,
                destination_hash: peerHash,
                state: "sending",
            }),
        ];

        const result = applyWsMessage(
            current,
            {
                hash: "server-hash",
                source_hash: myHash,
                destination_hash: peerHash,
                content: "sent",
                fields: {},
            },
            peerHash,
            myHash
        );

        expect(result.changed).toBe(true);
        expect(result.items).toHaveLength(1);
        expect(result.items[0].lxmf_message.hash).toBe("server-hash");
    });

    it("collects only image files from a drop", () => {
        const image = new File(["image"], "photo.png", { type: "image/png" });
        const text = new File(["text"], "note.txt", { type: "text/plain" });
        const transfer = { files: [image, text], items: [] };

        expect(collectImageFilesFromDataTransfer(transfer)).toEqual([image]);
    });

    it("keeps drafts isolated by identity and destination", () => {
        localStorage.clear();
        saveDraft(peerHash, "identity-a", "draft a");
        saveDraft(peerHash, "identity-b", "draft b");

        expect(loadDraft(peerHash, "identity-a")).toBe("draft a");
        expect(loadDraft(peerHash, "identity-b")).toBe("draft b");
    });

    it("renders a bubble for ordinary content", () => {
        expect(hasMessageBubble(item({ content: "hello" }))).toBe(true);
    });
});
