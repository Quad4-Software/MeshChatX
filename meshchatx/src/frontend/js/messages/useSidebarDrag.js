// @ts-check

import { ref } from "vue";

import { importMessagesFromFile } from "../messageImport.js";
import ToastUtils from "../ToastUtils.js";

/**
 * Drag-and-drop state for MessagesSidebar: conversation row dragging into
 * folders plus the file-drop zone for JSON message import.
 *
 * options.emit forwards component emits (conversation-drag-start,
 * conversation-drag-end, move-to-folder, messages-imported).
 * options.t is the host i18n function for import toasts.
 */
export function useSidebarDrag(options = {}) {
    const emit = options.emit || (() => {});
    const t = options.t || ((key) => key);

    const draggedHash = ref(null);
    const dragOverFolderId = ref(null);
    const messageImportDragOver = ref(false);
    const messageImportDragDepth = ref(0);

    function onDragStart(event, hash) {
        draggedHash.value = hash;
        event.dataTransfer.setData("text/plain", hash);
        event.dataTransfer.effectAllowed = "move";
        emit("conversation-drag-start");
    }

    function onDragEnd() {
        draggedHash.value = null;
        emit("conversation-drag-end");
    }

    function onDragOver(event, folderId) {
        event.preventDefault();
        dragOverFolderId.value = folderId;
        event.dataTransfer.dropEffect = "move";
    }

    function onDragLeave() {
        dragOverFolderId.value = null;
    }

    function onDropOnFolder(event, folderId) {
        event.preventDefault();
        dragOverFolderId.value = null;
        const hash = event.dataTransfer.getData("text/plain");
        if (hash) {
            emit("move-to-folder", {
                peer_hashes: [hash],
                folder_id: folderId,
            });
        }
        draggedHash.value = null;
    }

    function isMessagesImportFileDrag(event) {
        if (draggedHash.value) {
            return false;
        }
        const dataTransfer = event.dataTransfer;
        if (!dataTransfer) {
            return false;
        }
        return Array.from(dataTransfer.types || []).includes("Files");
    }

    function onMessagesImportDragEnter(event) {
        if (!isMessagesImportFileDrag(event)) {
            return;
        }
        messageImportDragDepth.value += 1;
        messageImportDragOver.value = true;
    }

    function onMessagesImportDragOver(event) {
        if (!isMessagesImportFileDrag(event)) {
            return;
        }
        event.dataTransfer.dropEffect = "copy";
    }

    function onMessagesImportDragLeave() {
        if (messageImportDragDepth.value > 0) {
            messageImportDragDepth.value -= 1;
        }
        if (messageImportDragDepth.value === 0) {
            messageImportDragOver.value = false;
        }
    }

    async function onMessagesImportDrop(event) {
        messageImportDragDepth.value = 0;
        messageImportDragOver.value = false;
        if (!isMessagesImportFileDrag(event)) {
            return;
        }
        const file = event.dataTransfer?.files?.[0];
        if (!file) {
            return;
        }
        const name = file.name.toLowerCase();
        if (!name.endsWith(".json") && file.type !== "application/json") {
            ToastUtils.error(t("maintenance.import_failed"));
            return;
        }
        try {
            const { imported } = await importMessagesFromFile(file);
            ToastUtils.success(t("maintenance.import_success", { count: imported }));
            emit("messages-imported");
        } catch {
            ToastUtils.error(t("maintenance.import_failed"));
        }
    }

    return {
        draggedHash,
        dragOverFolderId,
        messageImportDragOver,
        messageImportDragDepth,
        onDragStart,
        onDragEnd,
        onDragOver,
        onDragLeave,
        onDropOnFolder,
        isMessagesImportFileDrag,
        onMessagesImportDragEnter,
        onMessagesImportDragOver,
        onMessagesImportDragLeave,
        onMessagesImportDrop,
    };
}
