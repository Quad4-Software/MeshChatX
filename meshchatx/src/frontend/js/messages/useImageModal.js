// @ts-check

import { nextTick, reactive, ref } from "vue";

/**
 * Image lightbox state for ConversationViewer: single-image and gallery
 * modes, context menu position, and wrap-around navigation.
 *
 * options.onOpened runs inside nextTick after openImage sets state so the
 * host can focus the overlay ref. options.onDownload and
 * options.onCopyToClipboard receive the active chat item for the
 * context-menu actions.
 */
export function useImageModal(options = {}) {
    const { onOpened, onDownload, onCopyToClipboard } = options;

    const imageModalUrl = ref(null);
    const imageModalGallery = ref(null);
    const imageModalGalleryChatItems = ref(null);
    const imageModalChatItem = ref(null);
    const imageModalIndex = ref(0);
    const imageModalContextMenu = reactive({
        show: false,
        x: 0,
        y: 0,
    });

    async function openImage(url, galleryUrls, galleryChatItems = null) {
        imageModalContextMenu.show = false;
        if (galleryUrls && galleryUrls.length > 1) {
            imageModalGallery.value = galleryUrls.slice();
            imageModalGalleryChatItems.value = Array.isArray(galleryChatItems) ? galleryChatItems.slice() : null;
            imageModalChatItem.value = null;
            let idx = galleryUrls.indexOf(url);
            if (idx < 0) idx = 0;
            imageModalIndex.value = idx;
            imageModalUrl.value = galleryUrls[idx];
        } else {
            imageModalGallery.value = null;
            imageModalGalleryChatItems.value = null;
            imageModalIndex.value = 0;
            imageModalUrl.value = url;
            imageModalChatItem.value =
                Array.isArray(galleryChatItems) && galleryChatItems.length > 0 ? galleryChatItems[0] : null;
        }
        await nextTick();
        onOpened?.();
    }

    function closeImageModal() {
        imageModalUrl.value = null;
        imageModalGallery.value = null;
        imageModalGalleryChatItems.value = null;
        imageModalChatItem.value = null;
        imageModalIndex.value = 0;
        imageModalContextMenu.show = false;
    }

    function imageModalActiveChatItem() {
        if (imageModalGalleryChatItems.value && imageModalGalleryChatItems.value.length > 0) {
            return imageModalGalleryChatItems.value[imageModalIndex.value] || null;
        }
        return imageModalChatItem.value;
    }

    function onImageModalContextMenu(event) {
        if (!imageModalActiveChatItem()) {
            return;
        }
        imageModalContextMenu.show = true;
        const menuWidth = 240;
        const menuHeight = 88;
        let x = event.clientX;
        let y = event.clientY;
        if (x + menuWidth > window.innerWidth) {
            x = window.innerWidth - menuWidth - 10;
        }
        if (y + menuHeight > window.innerHeight) {
            y = window.innerHeight - menuHeight - 10;
        }
        imageModalContextMenu.x = x;
        imageModalContextMenu.y = y;
    }

    function downloadImageModalCurrent() {
        const chatItem = imageModalActiveChatItem();
        imageModalContextMenu.show = false;
        if (chatItem) {
            onDownload?.(chatItem);
        }
    }

    function copyImageModalCurrentToClipboard() {
        const chatItem = imageModalActiveChatItem();
        imageModalContextMenu.show = false;
        if (chatItem) {
            void onCopyToClipboard?.(chatItem);
        }
    }

    function imageModalNavigate(delta) {
        const gallery = imageModalGallery.value;
        if (!gallery || gallery.length < 2) return;
        const n = gallery.length;
        imageModalIndex.value = (imageModalIndex.value + delta + n) % n;
        imageModalUrl.value = gallery[imageModalIndex.value];
        imageModalContextMenu.show = false;
    }

    return {
        imageModalUrl,
        imageModalGallery,
        imageModalGalleryChatItems,
        imageModalChatItem,
        imageModalIndex,
        imageModalContextMenu,
        openImage,
        closeImageModal,
        imageModalActiveChatItem,
        onImageModalContextMenu,
        downloadImageModalCurrent,
        copyImageModalCurrentToClipboard,
        imageModalNavigate,
    };
}
