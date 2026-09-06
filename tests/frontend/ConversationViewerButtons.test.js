// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function source(relativePath) {
    return readFileSync(resolve(process.cwd(), "meshchatx/src/frontend/features/messages", relativePath), "utf8");
}

describe("ConversationViewer button wiring", () => {
    it("wires retry, cancel, reply, delete, and raw-message actions", () => {
        const entry = source("components/ConversationMessageEntry.svelte");
        expect(entry).toContain("actions.retrySendingMessage(chatItem)");
        expect(entry).toContain("actions.cancelSendingMessage(chatItem)");
        expect(entry).toContain("actions.replyToMessage(chatItem)");
        expect(entry).toContain("actions.deleteChatItem(chatItem)");
        expect(entry).toContain("actions.showRawMessage(chatItem)");
    });

    it("wires image and attachment download actions", () => {
        const entry = source("components/ConversationMessageEntry.svelte");
        expect(entry).toContain("actions.downloadMessageImage(chatItem)");
        expect(entry).toContain("actions.downloadLxmfFileAttachment(chatItem, index)");
    });

    it("wires send callbacks through the composer", () => {
        const composer = source("components/ConversationComposer.svelte");
        expect(composer).toContain("onsend={() => onsend?.()}");
        expect(composer).toContain("ondeliverymethodchanged");
        expect(composer).toContain("onsendcommandorrequest");
        expect(composer).toContain("onsendpapercompose");
    });

    it("wires stamp signal path dialogs and image context menu actions", () => {
        const viewer = source("components/ConversationViewer.svelte");
        const header = source("components/ConversationViewerHeaderHost.svelte");
        expect(header).toContain("{onstampinfoclick}");
        expect(header).toContain("{onsignalmetricsclick}");
        expect(viewer).toContain("formatStampInfoAlert");
        expect(viewer).toContain("retryAllFailedOrCancelledMessages");
        expect(viewer).toContain("oncopyimage=");
        expect(viewer).toContain("onsavesticker=");
        expect(viewer).toContain("onsavegif=");
    });
});
