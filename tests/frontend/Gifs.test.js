// SPDX-License-Identifier: 0BSD

import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import ComposerEmojiStickerGifPicker from "@/features/messages/components/ComposerEmojiStickerGifPicker.svelte";
import { GIF_MAX_BYTES, isAllowedGifMime } from "@/features/messages/lib/conversationStickersGifs.ts";

describe("GIF picker", () => {
    afterEach(cleanup);

    it("accepts GIF content and keeps a bounded upload size", () => {
        expect(isAllowedGifMime("image/gif")).toBe(true);
        expect(isAllowedGifMime("image/webp")).toBe(false);
        expect(GIF_MAX_BYTES).toBe(2 * 1024 * 1024);
    });

    it("renders library items and selects a GIF", async () => {
        const gif = { id: 11, name: "G1", usage_count: 3 };
        const ongifselect = vi.fn();
        render(ComposerEmojiStickerGifPicker, {
            props: {
                open: true,
                activeTab: "gifs",
                gifs: [gif],
                gifImageUrl: (id) => `/api/v1/gifs/${id}/image`,
                ongifselect,
            },
        });

        await fireEvent.click(screen.getByTitle("G1"));
        expect(ongifselect).toHaveBeenCalledWith(gif);
        expect(screen.getByText("3")).toBeTruthy();
    });

    it("requests the GIF tab", async () => {
        const ontabchange = vi.fn();
        render(ComposerEmojiStickerGifPicker, {
            props: { open: true, activeTab: "emoji", ontabchange },
        });

        await fireEvent.click(screen.getAllByRole("tab")[2]);
        expect(ontabchange).toHaveBeenCalledWith("gifs");
    });
});
