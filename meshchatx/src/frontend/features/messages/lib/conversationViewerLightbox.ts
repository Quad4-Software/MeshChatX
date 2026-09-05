// SPDX-License-Identifier: 0BSD

import type { MessageChatItem } from "./viewerActions.js";

export type ImageLightboxState = {
    url: string;
    gallery: string[] | null;
    items: MessageChatItem[] | null;
    index: number;
};

export function initialImageLightboxState(): ImageLightboxState {
    return {
        url: "",
        gallery: null,
        items: null,
        index: 0,
    };
}

export function openImageLightbox(
    src: string,
    gallery: string[] = [],
    items: MessageChatItem[] = []
): ImageLightboxState {
    const nextGallery = gallery.length > 1 ? gallery.slice() : null;
    const nextItems = items.length ? items.slice() : null;
    const nextIndex = nextGallery ? Math.max(0, nextGallery.indexOf(src)) : 0;
    return {
        url: nextGallery?.[nextIndex] || src,
        gallery: nextGallery,
        items: nextItems,
        index: nextIndex,
    };
}

export function navigateImageLightbox(state: ImageLightboxState, delta: number): ImageLightboxState {
    if (!state.gallery?.length) {
        return state;
    }
    const nextIndex = (state.index + delta + state.gallery.length) % state.gallery.length;
    return {
        ...state,
        index: nextIndex,
        url: state.gallery[nextIndex],
    };
}
