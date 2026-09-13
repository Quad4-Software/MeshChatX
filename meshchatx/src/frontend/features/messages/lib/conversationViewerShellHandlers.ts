// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import { t } from "../../../js/i18n.js";
import type { LxmfMessage, ViewerChatItem } from "./conversationViewerCtx.js";
import { sameHash } from "./conversationViewerCtx.js";
import type { MessageChatItem } from "./viewerActions.js";

export type ShellHandlerBag = {
    chatItems: ViewerChatItem[];
    setChatItems: (items: ViewerChatItem[]) => void;
    contextMenu: {
        show: boolean;
        x: number;
        y: number;
        chatItem: ViewerChatItem | null;
        justOpened: boolean;
    };
    setContextMenu: (value: ShellHandlerBag["contextMenu"]) => void;
    reactionPicker: { open: boolean; style: string; chatItem: ViewerChatItem | null };
    setReactionPicker: (value: ShellHandlerBag["reactionPicker"]) => void;
    setReplyingTo: (item: ViewerChatItem | null) => void;
    setRawMessageData: (data: LxmfMessage) => void;
    setIsRawMessageModalOpen: (open: boolean) => void;
    useVirtualMessageList: boolean;
    listPane: { scrollToMessageHash?: (hash: string) => void } | null | undefined;
};

export function openContextMenu(
    bag: ShellHandlerBag,
    event: MouseEvent,
    item: ViewerChatItem,
    suppressToggle = false,
    toggleChatItemActions: (item: MessageChatItem) => void
) {
    event.preventDefault();
    event.stopPropagation();
    if (!suppressToggle) {
        toggleChatItemActions(item as unknown as MessageChatItem);
    }
    bag.setContextMenu({
        show: true,
        x: event.clientX,
        y: event.clientY,
        chatItem: item,
        justOpened: true,
    });
    queueMicrotask(() => {
        bag.setContextMenu({ ...bag.contextMenu, justOpened: false });
    });
}

export function toggleChatItemActions(bag: ShellHandlerBag, item: MessageChatItem) {
    const hash = item.lxmf_message.hash;
    bag.setChatItems(
        bag.chatItems.map((candidate) =>
            candidate.lxmf_message.hash === hash
                ? ({ ...candidate, is_actions_expanded: !item.is_actions_expanded } as ViewerChatItem)
                : candidate
        )
    );
}

export function replyToMessage(bag: ShellHandlerBag, item: MessageChatItem) {
    bag.setReplyingTo(item as ViewerChatItem);
    bag.setContextMenu({ ...bag.contextMenu, show: false });
    requestAnimationFrame(() => document.getElementById("message-input")?.focus());
}

export function showRawMessage(bag: ShellHandlerBag, item: MessageChatItem) {
    bag.setRawMessageData(item.lxmf_message as LxmfMessage);
    bag.setIsRawMessageModalOpen(true);
    bag.setContextMenu({ ...bag.contextMenu, show: false });
}

export function openReactionPicker(bag: ShellHandlerBag, item: MessageChatItem) {
    if (!item?.lxmf_message?.hash) {
        return;
    }
    bag.setReactionPicker({
        open: true,
        style: "bottom:0.5rem;left:50%;transform:translateX(-50%);",
        chatItem: item as ViewerChatItem,
    });
    bag.setContextMenu({ ...bag.contextMenu, show: false });
}

export function scrollToMessage(bag: ShellHandlerBag, hash: string) {
    const item = bag.chatItems.find((candidate) => sameHash(candidate.lxmf_message.hash, hash));
    if (!item) {
        void DialogUtils.alert(t("messages.message_not_found_in_cache"));
        return;
    }
    const element = document.getElementById(`message-${hash}`);
    if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
    }
    if (bag.useVirtualMessageList) {
        bag.listPane?.scrollToMessageHash?.(hash);
    }
}
