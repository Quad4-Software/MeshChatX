// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import { useSidebarDrag } from "../../meshchatx/src/frontend/js/messages/useSidebarDrag.js";

function dragEvent({ types = ["Files"], files = [] } = {}) {
    return {
        preventDefault: vi.fn(),
        dataTransfer: {
            types,
            files,
            setData: vi.fn(),
            getData: vi.fn(() => "peer-hash"),
            effectAllowed: "",
            dropEffect: "",
        },
    };
}

describe("useSidebarDrag", () => {
    it("tracks conversation drag and emits start/end", () => {
        const emit = vi.fn();
        const d = useSidebarDrag({ emit });
        const ev = dragEvent();
        d.onDragStart(ev, "peer-hash");
        expect(d.draggedHash.value).toBe("peer-hash");
        expect(ev.dataTransfer.setData).toHaveBeenCalledWith("text/plain", "peer-hash");
        expect(emit).toHaveBeenCalledWith("conversation-drag-start");
        d.onDragEnd();
        expect(d.draggedHash.value).toBeNull();
        expect(emit).toHaveBeenCalledWith("conversation-drag-end");
    });

    it("emits move-to-folder on drop", () => {
        const emit = vi.fn();
        const d = useSidebarDrag({ emit });
        const ev = dragEvent();
        d.onDropOnFolder(ev, 7);
        expect(emit).toHaveBeenCalledWith("move-to-folder", {
            peer_hashes: ["peer-hash"],
            folder_id: 7,
        });
        expect(d.dragOverFolderId.value).toBeNull();
    });

    it("file drags drive the import overlay with enter/leave depth", () => {
        const d = useSidebarDrag();
        const ev = dragEvent();
        expect(d.isMessagesImportFileDrag(ev)).toBe(true);
        d.onMessagesImportDragEnter(ev);
        d.onMessagesImportDragEnter(ev);
        expect(d.messageImportDragOver.value).toBe(true);
        d.onMessagesImportDragLeave();
        expect(d.messageImportDragOver.value).toBe(true);
        d.onMessagesImportDragLeave();
        expect(d.messageImportDragOver.value).toBe(false);
    });

    it("conversation drags do not trigger import overlay", () => {
        const d = useSidebarDrag();
        d.onDragStart(dragEvent(), "peer-hash");
        expect(d.isMessagesImportFileDrag(dragEvent())).toBe(false);
    });

    it("rejects non-json drops without emitting", async () => {
        const emit = vi.fn();
        const d = useSidebarDrag({ emit });
        const file = new File(["x"], "notes.txt", { type: "text/plain" });
        await d.onMessagesImportDrop(dragEvent({ files: [file] }));
        expect(emit).not.toHaveBeenCalledWith("messages-imported");
        expect(d.messageImportDragOver.value).toBe(false);
    });
});
