// SPDX-License-Identifier: 0BSD

import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import ComposerEmojiStickerGifPicker from "@/features/messages/components/ComposerEmojiStickerGifPicker.svelte";
import { STICKER_MAX_BYTES, isAllowedStickerMime } from "@/features/messages/lib/conversationStickersGifs.ts";

describe("sticker picker", () => {
    afterEach(cleanup);

    it("accepts supported images and keeps a bounded upload size", () => {
        expect(isAllowedStickerMime("image/png")).toBe(true);
        expect(isAllowedStickerMime("image/webp")).toBe(true);
        expect(isAllowedStickerMime("text/plain")).toBe(false);
        expect(STICKER_MAX_BYTES).toBe(512 * 1024);
    });

    it("filters by sticker pack and selects a sticker", async () => {
        const sticker = { id: 7, name: "S", image_type: "png", pack_id: 2 };
        const onstickerselect = vi.fn();
        render(ComposerEmojiStickerGifPicker, {
            props: {
                open: true,
                activeTab: "stickers",
                stickers: [sticker, { id: 8, name: "Other", image_type: "png", pack_id: 3 }],
                activeStickerPackId: 2,
                onstickerselect,
            },
        });

        expect(screen.queryByTitle("Other")).toBeNull();
        await fireEvent.click(screen.getByTitle("S"));
        expect(onstickerselect).toHaveBeenCalledWith(sticker);
    });

    it("requests the stickers tab", async () => {
        const ontabchange = vi.fn();
        render(ComposerEmojiStickerGifPicker, {
            props: { open: true, activeTab: "emoji", ontabchange },
        });

        await fireEvent.click(screen.getAllByRole("tab")[1]);
        expect(ontabchange).toHaveBeenCalledWith("stickers");
    });
});
