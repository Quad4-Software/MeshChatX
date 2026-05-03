import { describe, expect, it } from "vitest";
import { lxmfConversationListPreview } from "../../meshchatx/src/frontend/js/lxmfConversationPreview";

describe("lxmfConversationListPreview", () => {
    const me = "m".repeat(32);
    const peer = "p".repeat(32);

    it("uses reaction_emoji for outbound reaction from self", () => {
        const s = lxmfConversationListPreview(
            {
                content: "  ",
                is_incoming: false,
                is_reaction: true,
                reaction_emoji: "\u{1F44D}",
                source_hash: me,
            },
            { myLxmfAddressHash: me, peerDisplayName: "Pat" }
        );
        expect(s).toBe("You reacted \u{1F44D}");
    });

    it("uses peer name for incoming reaction", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: true,
                is_reaction: true,
                reaction_emoji: "\u2764\uFE0F",
                source_hash: peer,
            },
            { myLxmfAddressHash: me, peerDisplayName: "Alex" }
        );
        expect(s).toBe("Alex reacted \u2764\uFE0F");
    });

    it("reads emoji from fields.app_extensions when body fields are used", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: true,
                fields: { app_extensions: { reaction_to: "deadbeef", emoji: "\u{1F602}" } },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Sam" }
        );
        expect(s).toBe("Sam reacted \u{1F602}");
    });

    it("shows location share preview for telemetry with coordinates", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: true,
                source_hash: peer,
                fields: { telemetry: { location: { latitude: 1, longitude: 2 } } },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Alex" }
        );
        expect(s).toBe("Alex shared their location");
    });

    it("shows outbound location share preview as You", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: false,
                source_hash: me,
                fields: { telemetry: { location: { latitude: 1, longitude: 2 } } },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Pat" }
        );
        expect(s).toBe("You shared your location");
    });

    it("shows outbound location request preview as You", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: false,
                source_hash: me,
                fields: { commands: [{ "0x01": 1700000000 }] },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Pat" }
        );
        expect(s).toBe("You sent a location request");
    });

    it("shows incoming location request preview with peer name", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: true,
                source_hash: peer,
                fields: { commands: [{ "0x01": 1700000000 }] },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Riley" }
        );
        expect(s).toBe("Riley requested your location");
    });
});
