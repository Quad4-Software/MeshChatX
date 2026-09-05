// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import { GIF_MAX_BYTES, STICKER_MAX_BYTES } from "./constants.js";

export { GIF_MAX_BYTES, STICKER_MAX_BYTES };

export type StickerItem = {
    id: string | number;
    name?: string | null;
    emoji?: string | null;
    image_type?: string | null;
    pack_id?: string | number | null;
    [key: string]: unknown;
};

export type StickerPackItem = {
    id: string | number;
    title?: string | null;
    [key: string]: unknown;
};

export type GifItem = {
    id: string | number;
    name?: string | null;
    usage_count?: number | null;
    [key: string]: unknown;
};

export function isAllowedStickerMime(mime: string): boolean {
    return /^image\/(png|webp|jpeg|jpg|gif)$/i.test(mime || "");
}

export function isAllowedGifMime(mime: string): boolean {
    return /^image\/gif$/i.test(mime || "");
}

export async function loadStickers(api: { get: (url: string) => Promise<{ data?: unknown }> }): Promise<StickerItem[]> {
    try {
        const response = await api.get("/api/v1/stickers");
        const data = response.data as { stickers?: unknown } | undefined;
        const list = data?.stickers;
        return Array.isArray(list) ? (list as StickerItem[]) : [];
    } catch {
        return [];
    }
}

export async function loadStickerPacks(api: { get: (url: string) => Promise<{ data?: unknown }> }): Promise<StickerPackItem[]> {
    try {
        const response = await api.get("/api/v1/stickers/packs");
        const data = response.data as { packs?: unknown } | undefined;
        const list = data?.packs;
        return Array.isArray(list) ? (list as StickerPackItem[]) : [];
    } catch {
        return [];
    }
}

export async function loadGifs(api: { get: (url: string) => Promise<{ data?: unknown }> }): Promise<GifItem[]> {
    try {
        const response = await api.get("/api/v1/gifs");
        const data = response.data as { gifs?: unknown } | undefined;
        const list = data?.gifs;
        return Array.isArray(list) ? (list as GifItem[]) : [];
    } catch {
        return [];
    }
}

export async function uploadStickerFile(
    api: { post: (url: string, body?: unknown) => Promise<{ data?: unknown }> },
    file: File,
    packId?: string | number | null
): Promise<StickerItem | null> {
    const buffer = await file.arrayBuffer();
    const base64 = Utils.arrayBufferToBase64(buffer);
    const extension = file.name.split(".").pop()?.toLowerCase() || "png";
    const name = file.name.replace(/\.[^/.]+$/, "");
    const payload: Record<string, unknown> = {
        name,
        image_bytes: base64,
        image_type: extension,
    };
    if (packId != null) {
        payload.pack_id = packId;
    }
    const response = await api.post("/api/v1/stickers", payload);
    const data = response.data as { sticker?: StickerItem } | undefined;
    return data?.sticker || null;
}

export async function uploadGifFile(
    api: { post: (url: string, body?: unknown) => Promise<{ data?: unknown }> },
    file: File
): Promise<GifItem | null> {
    const buffer = await file.arrayBuffer();
    const base64 = Utils.arrayBufferToBase64(buffer);
    const extension = file.name.split(".").pop()?.toLowerCase() || "gif";
    const name = file.name.replace(/\.[^/.]+$/, "");
    const payload = {
        name,
        image_bytes: base64,
        image_type: extension,
    };
    const response = await api.post("/api/v1/gifs", payload);
    const data = response.data as { gif?: GifItem } | undefined;
    return data?.gif || null;
}
