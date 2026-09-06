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
import {
    formatPeerPathClickAlert,
    formatSignalMetricsAlert,
    formatStampInfoAlert,
} from "@/features/messages/lib/conversationPathActions.ts";
import { listFailedOrCancelledOutbound } from "@/features/messages/lib/conversationViewerMutations.ts";
import {
    initialImageLightboxState,
    lightboxActiveChatItem,
    navigateImageLightbox,
    openImageLightbox,
    openLightboxContextMenu,
} from "@/features/messages/lib/conversationViewerLightbox.ts";

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

    it("migrates legacy Vue meshchat.drafts into the modern compose draft key", () => {
        localStorage.clear();
        localStorage.setItem(
            "meshchat.drafts",
            JSON.stringify({
                "identity-a": { [peerHash]: "legacy nested" },
            })
        );
        expect(loadDraft(peerHash, "identity-a")).toBe("legacy nested");
        expect(localStorage.getItem(`meshchatx.compose_draft.identity-a:${peerHash}`)).toBe("legacy nested");
    });

    it("formats path stamp and signal header dialogs", () => {
        const t = (key, values) => {
            if (key === "messages.path_stale_hint") return "stale";
            if (key === "messages.path_unresponsive_hint") return "unresponsive";
            if (key === "messages.path_hops_unknown_iface") return "unknown interface";
            if (key === "messages.signal_quality") return `Signal Quality: ${values.quality}%`;
            if (key === "messages.rssi_val") return `RSSI: ${values.rssi}dBm`;
            if (key === "messages.snr_val") return `SNR: ${values.snr}dB`;
            return key;
        };
        expect(formatPeerPathClickAlert({ hops: 2, next_hop_interface: "TCP" }, { path_stale: true }, t)).toContain(
            "2 hops away via TCP"
        );
        expect(formatPeerPathClickAlert({ hops: 2, next_hop_interface: "TCP" }, { path_stale: true }, t)).toContain(
            "stale"
        );
        expect(formatStampInfoAlert({ stamp_cost: 8 })).toContain("Time per message:");
        expect(formatSignalMetricsAlert({ quality: 90, rssi: -40, snr: 12 }, t)).toBe(
            "Signal Quality: 90%\nRSSI: -40dBm\nSNR: 12dB"
        );
    });

    it("lists failed and cancelled outbound messages for retry-all", () => {
        const rows = [
            item({ hash: "ok", source_hash: myHash, destination_hash: peerHash, state: "delivered" }),
            item({ hash: "fail", source_hash: myHash, destination_hash: peerHash, state: "failed" }),
            item({ hash: "cancel", source_hash: myHash, destination_hash: peerHash, state: "cancelled" }),
            item({ hash: "inbound-fail", state: "failed" }),
        ];
        expect(listFailedOrCancelledOutbound(rows).map((row) => row.lxmf_message.hash)).toEqual(["fail", "cancel"]);
    });

    it("resolves lightbox active chat item and clamps context menu position", () => {
        const a = item({ hash: "img-a" });
        const b = item({ hash: "img-b" });
        const opened = openImageLightbox("url-b", ["url-a", "url-b"], [a, b]);
        expect(lightboxActiveChatItem(opened)?.lxmf_message.hash).toBe("img-b");
        expect(lightboxActiveChatItem(navigateImageLightbox(opened, 1))?.lxmf_message.hash).toBe("img-a");

        const single = openImageLightbox("solo", [], [a]);
        expect(lightboxActiveChatItem(single)?.lxmf_message.hash).toBe("img-a");
        expect(lightboxActiveChatItem(initialImageLightboxState())).toBeNull();

        const menu = openLightboxContextMenu({ clientX: 900, clientY: 700 }, { innerWidth: 800, innerHeight: 600 });
        expect(menu.show).toBe(true);
        expect(menu.x).toBeLessThanOrEqual(800 - 240 - 10);
        expect(menu.y).toBeLessThanOrEqual(600 - 88 - 10);
    });

    it("renders a bubble for ordinary content", () => {
        expect(hasMessageBubble(item({ content: "hello" }))).toBe(true);
    });
});
