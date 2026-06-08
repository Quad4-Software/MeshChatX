import { describe, it, expect } from "vitest";
import {
    isTelemetryOnly,
    hasRenderableContent,
    hasFileAttachments,
    hasMessageBubble,
    isFileOnlyMessage,
    isImageOnlyMessage,
    collectImageFilesFromDataTransfer,
    extractClipboardImageFiles,
} from "../../meshchatx/src/frontend/components/messages/conversationMessageHelpers.js";

describe("conversationMessageHelpers", () => {
    it("hasRenderableContent detects text and attachments", () => {
        expect(hasRenderableContent({ content: " hi " })).toBe(true);
        expect(hasRenderableContent({ content: "", fields: { image: {} } })).toBe(true);
        expect(hasRenderableContent({ content: "  ", fields: {} })).toBe(false);
        expect(hasRenderableContent({ content: "", fields: { file_attachments: [] } })).toBe(false);
        expect(hasRenderableContent({ content: "", fields: { file_attachments: [{ file_name: "a.zip" }] } })).toBe(
            true
        );
    });

    it("hasFileAttachments requires a non-empty array", () => {
        expect(hasFileAttachments({ fields: { file_attachments: [{ file_name: "a.zip" }] } })).toBe(true);
        expect(hasFileAttachments({ fields: { file_attachments: [] } })).toBe(false);
        expect(hasFileAttachments({ fields: {} })).toBe(false);
    });

    it("isFileOnlyMessage matches attachment-only rows", () => {
        const chatItem = {
            lxmf_message: {
                fields: { file_attachments: [{ file_name: "readme.txt" }] },
            },
        };
        expect(isFileOnlyMessage(chatItem, () => false)).toBe(true);
        expect(hasMessageBubble(chatItem, () => false)).toBe(true);
    });

    it("isTelemetryOnly when only telemetry fields", () => {
        expect(
            isTelemetryOnly({
                content: "",
                fields: { telemetry: { x: 1 } },
            })
        ).toBe(true);
        expect(
            isTelemetryOnly({
                content: "a",
                fields: { telemetry: { x: 1 } },
            })
        ).toBe(false);
    });

    it("isImageOnlyMessage respects shouldHideAutoImageCaption", () => {
        const chatItem = {
            lxmf_message: {
                fields: { image: {} },
                content: "cap",
            },
        };
        expect(isImageOnlyMessage(chatItem, () => true)).toBe(true);
        expect(isImageOnlyMessage(chatItem, () => false)).toBe(false);
    });

    it("collectImageFilesFromDataTransfer collects image files", () => {
        const f = new File(["x"], "a.png", { type: "image/png" });
        const dt = { files: [f] };
        const out = collectImageFilesFromDataTransfer(dt);
        expect(out.length).toBe(1);
        expect(out[0].type.startsWith("image/")).toBe(true);
    });

    it("extractClipboardImageFiles reads image items", () => {
        const f = new File(["x"], "c.png", { type: "image/png" });
        const item = {
            kind: "file",
            type: "image/png",
            getAsFile: () => f,
        };
        const ev = { clipboardData: { items: [item] } };
        const files = extractClipboardImageFiles(ev);
        expect(files.length).toBe(1);
        expect(files[0].name).toBe("c.png");
    });
});
