// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import { useImageModal } from "../../meshchatx/src/frontend/js/messages/useImageModal.js";

describe("useImageModal", () => {
    it("opens a single image with its chat item", async () => {
        const modal = useImageModal();
        await modal.openImage("img://one", null, [{ id: "a" }]);
        expect(modal.imageModalUrl.value).toBe("img://one");
        expect(modal.imageModalGallery.value).toBeNull();
        expect(modal.imageModalActiveChatItem()).toEqual({ id: "a" });
    });

    it("opens a gallery at the clicked index and wraps navigation", async () => {
        const modal = useImageModal();
        const items = [{ id: "a" }, { id: "b" }, { id: "c" }];
        await modal.openImage("img://b", ["img://a", "img://b", "img://c"], items);
        expect(modal.imageModalIndex.value).toBe(1);
        expect(modal.imageModalUrl.value).toBe("img://b");
        modal.imageModalNavigate(1);
        expect(modal.imageModalUrl.value).toBe("img://c");
        expect(modal.imageModalActiveChatItem()).toEqual({ id: "c" });
        modal.imageModalNavigate(1);
        expect(modal.imageModalUrl.value).toBe("img://a");
        modal.imageModalNavigate(-1);
        expect(modal.imageModalUrl.value).toBe("img://c");
    });

    it("falls back to index 0 when the url is not in the gallery", async () => {
        const modal = useImageModal();
        await modal.openImage("img://missing", ["img://a", "img://b"]);
        expect(modal.imageModalIndex.value).toBe(0);
        expect(modal.imageModalUrl.value).toBe("img://a");
    });

    it("navigate is a no-op without a multi-image gallery", async () => {
        const modal = useImageModal();
        await modal.openImage("img://one", ["img://one"]);
        modal.imageModalNavigate(1);
        expect(modal.imageModalUrl.value).toBe("img://one");
        expect(modal.imageModalIndex.value).toBe(0);
    });

    it("close resets all state", async () => {
        const modal = useImageModal();
        await modal.openImage("img://a", ["img://a", "img://b"], [{ id: "a" }, { id: "b" }]);
        modal.onImageModalContextMenu({ clientX: 10, clientY: 10 });
        modal.closeImageModal();
        expect(modal.imageModalUrl.value).toBeNull();
        expect(modal.imageModalGallery.value).toBeNull();
        expect(modal.imageModalGalleryChatItems.value).toBeNull();
        expect(modal.imageModalChatItem.value).toBeNull();
        expect(modal.imageModalIndex.value).toBe(0);
        expect(modal.imageModalContextMenu.show).toBe(false);
    });

    it("context menu stays hidden without an active chat item", async () => {
        const modal = useImageModal();
        await modal.openImage("img://one", null);
        modal.onImageModalContextMenu({ clientX: 10, clientY: 10 });
        expect(modal.imageModalContextMenu.show).toBe(false);
    });

    it("context menu clamps inside the viewport", async () => {
        const modal = useImageModal();
        await modal.openImage("img://one", null, [{ id: "a" }]);
        modal.onImageModalContextMenu({ clientX: window.innerWidth - 5, clientY: window.innerHeight - 5 });
        expect(modal.imageModalContextMenu.show).toBe(true);
        expect(modal.imageModalContextMenu.x).toBeLessThanOrEqual(window.innerWidth - 250);
        expect(modal.imageModalContextMenu.y).toBeLessThanOrEqual(window.innerHeight - 98);
    });

    it("download and copy actions dispatch the active chat item", async () => {
        const onDownload = vi.fn();
        const onCopyToClipboard = vi.fn();
        const modal = useImageModal({ onDownload, onCopyToClipboard });
        await modal.openImage("img://one", null, [{ id: "a" }]);
        modal.downloadImageModalCurrent();
        expect(onDownload).toHaveBeenCalledWith({ id: "a" });
        modal.copyImageModalCurrentToClipboard();
        expect(onCopyToClipboard).toHaveBeenCalledWith({ id: "a" });
        expect(modal.imageModalContextMenu.show).toBe(false);
    });

    it("runs onOpened after open", async () => {
        const onOpened = vi.fn();
        const modal = useImageModal({ onOpened });
        await modal.openImage("img://one", null);
        expect(onOpened).toHaveBeenCalledTimes(1);
    });
});
