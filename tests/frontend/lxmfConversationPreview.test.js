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

    it("reads emoji from fields.reaction when body fields are used", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: true,
                fields: { reaction: { reaction_to: "deadbeef", reaction_content: "\u{1F602}" } },
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

    it("shows image preview when body is empty", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: true,
                source_hash: peer,
                fields: { image: { image_type: "png", image_size: 10 } },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Jo" }
        );
        expect(s).toBe("Jo sent an image");
    });

    it("shows outbound image preview as You", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: false,
                source_hash: me,
                fields: { image: { image_type: "webp", image_size: 20 } },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Jo" }
        );
        expect(s).toBe("You sent an image");
    });

    it("shows voice note preview for audio field", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: true,
                source_hash: peer,
                fields: { audio: { audio_mode: "opus", audio_size: 100 } },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Max" }
        );
        expect(s).toBe("Max sent a voice note");
    });

    it("shows multiple file attachment preview", () => {
        const s = lxmfConversationListPreview(
            {
                content: "",
                is_incoming: false,
                source_hash: me,
                fields: {
                    file_attachments: [
                        { file_name: "a.bin", file_size: 1 },
                        { file_name: "b.bin", file_size: 2 },
                    ],
                },
            },
            { myLxmfAddressHash: me, peerDisplayName: "Jo" }
        );
        expect(s).toBe("You sent 2 files");
    });
});
