import { describe, it, expect } from "vitest";
import {
    isTelemetryOnly,
    hasRenderableContent,
    isImageOnlyMessage,
    collectImageFilesFromDataTransfer,
    extractClipboardImageFiles,
} from "../../meshchatx/src/frontend/components/messages/conversationMessageHelpers.js";

describe("conversationMessageHelpers", () => {
    it("hasRenderableContent detects text and attachments", () => {
        expect(hasRenderableContent({ content: " hi " })).toBe(true);
        expect(hasRenderableContent({ content: "", fields: { image: {} } })).toBe(true);
        expect(hasRenderableContent({ content: "  ", fields: {} })).toBe(false);
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
