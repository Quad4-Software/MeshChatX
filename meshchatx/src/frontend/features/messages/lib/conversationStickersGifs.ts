// SPDX-License-Identifier: 0BSD

import { GIF_MAX_BYTES, STICKER_MAX_BYTES } from "./constants.js";

export { GIF_MAX_BYTES, STICKER_MAX_BYTES };

export function isAllowedStickerMime(mime: string): boolean {
    return /^image\/(png|webp|jpeg|jpg|gif)$/i.test(mime || "");
}

export function isAllowedGifMime(mime: string): boolean {
    return /^image\/gif$/i.test(mime || "");
}
