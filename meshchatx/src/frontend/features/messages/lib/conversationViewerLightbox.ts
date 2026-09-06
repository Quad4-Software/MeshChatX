// SPDX-License-Identifier: 0BSD

import type { MessageChatItem } from "./viewerActions.js";

export type ImageLightboxState = {
    url: string;
    gallery: string[] | null;
    items: MessageChatItem[] | null;
    index: number;
};

export type LightboxContextMenuState = {
    show: boolean;
    x: number;
    y: number;
};

const LIGHTBOX_CONTEXT_MENU_WIDTH = 240;
const LIGHTBOX_CONTEXT_MENU_HEIGHT = 88;

export function initialImageLightboxState(): ImageLightboxState {
    return {
        url: "",
        gallery: null,
        items: null,
        index: 0,
    };
}

export function initialLightboxContextMenuState(): LightboxContextMenuState {
    return {
        show: false,
        x: 0,
        y: 0,
    };
}

export function lightboxActiveChatItem(state: ImageLightboxState): MessageChatItem | null {
    if (state.items && state.items.length > 0) {
        return state.items[state.index] || null;
    }
    return null;
}

export function openLightboxContextMenu(
    event: { clientX: number; clientY: number },
    viewport: { innerWidth: number; innerHeight: number } = typeof window !== "undefined"
        ? window
        : { innerWidth: 0, innerHeight: 0 }
): LightboxContextMenuState {
    let x = event.clientX;
    let y = event.clientY;
    if (x + LIGHTBOX_CONTEXT_MENU_WIDTH > viewport.innerWidth) {
        x = Math.max(0, viewport.innerWidth - LIGHTBOX_CONTEXT_MENU_WIDTH - 10);
    }
    if (y + LIGHTBOX_CONTEXT_MENU_HEIGHT > viewport.innerHeight) {
        y = Math.max(0, viewport.innerHeight - LIGHTBOX_CONTEXT_MENU_HEIGHT - 10);
    }
    return { show: true, x, y };
}

export function openImageLightbox(
    src: string,
    gallery: string[] = [],
    items: MessageChatItem[] = []
): ImageLightboxState {
    const nextGallery = gallery.length > 1 ? gallery.slice() : null;
    const nextItems = items.length ? items.slice() : null;
    let nextIndex = 0;
    if (nextGallery) {
        const found = nextGallery.indexOf(src);
        nextIndex = found >= 0 ? found : 0;
    }
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
