// SPDX-License-Identifier: 0BSD

import MarkdownRenderer from "../../../js/MarkdownRenderer.js";
import Utils from "../../../js/Utils.js";
import { t } from "../../../js/i18n.js";
import {
    isOpportunisticDeferredDelivery,
    outboundBubbleStatusIconName,
    outboundBubbleStatusTitleKey,
} from "../../../js/outboundMessageStatus.js";
import { formatDate, fromNow } from "../../../libs/datetime.js";
import { AUTO_IMAGE_CAPTION_MAX_CHARS, MESSAGE_BODY_MAX_DISPLAY_CHARS } from "./constants.js";
import {
    hasFileAttachments,
    hasMessageBubble,
    isImageOnlyMessage,
    type ChatItemLike,
} from "./conversationMessageHelpers.js";
import { outboundStateTitle, transferProgressPercent } from "./conversationOutboundUi.js";
import type {
    ConversationViewerActions,
    LxmfMessageLike,
    MessageBubbleViewModel,
    MessageChatItem,
    ParsedMessageItems,
} from "./viewerActions.js";

export type ConversationViewerActionDeps = {
    chatItems: MessageChatItem[];
    selectedPeer?: {
        destination_hash?: string;
        display_name?: string;
        custom_display_name?: string;
        is_tracking?: boolean;
    } | null;
    conversations?: Array<{ destination_hash?: string; display_name?: string; custom_display_name?: string }>;
    myLxmfAddressHash?: string;
    messageFontSize?: number;
    expandedMessageInfo?: string | null;
    audioAttachmentUrls?: Readonly<Record<string, string>>;
    openImage: (src: string, gallery?: string[], items?: MessageChatItem[]) => void;
    onMessageContextMenu: (event: MouseEvent, chatItem: MessageChatItem, suppressToggle?: boolean) => void;
    onChatItemClick: (chatItem: MessageChatItem) => void;
    openReactionPicker: (chatItem: MessageChatItem) => void;
    replyToMessage: (chatItem: MessageChatItem) => void;
    retrySendingMessage: (chatItem: MessageChatItem) => void;
    cancelSendingMessage: (chatItem: MessageChatItem) => void;
    deleteChatItem: (chatItem: MessageChatItem) => void;
    showRawMessage: (chatItem: MessageChatItem) => void;
    scrollToMessage: (hash: string) => void;
    copyText: (text: string) => unknown;
    downloadMessageImage: (chatItem: MessageChatItem) => void | Promise<void>;
    downloadLxmfFileAttachment: (chatItem: MessageChatItem, index: number, name: string) => void | Promise<void>;
    addContact: (name?: string, hash?: string, lxmfAddress?: string, lxstAddress?: string) => void | Promise<void>;
};

function imageDataUrl(message: LxmfMessageLike): string {
    const image = message.fields?.image;
    if (typeof image?.image_bytes !== "string") {
        return "";
    }
    const rawType = String(image.image_type || "png")
        .toLowerCase()
        .replace(/^image\//, "");
    const mime = rawType === "jpg" ? "image/jpeg" : rawType === "webm" ? "video/webm" : `image/${rawType}`;
    return `data:${mime};base64,${image.image_bytes}`;
}

function shouldHideAutoImageCaption(chatItem: MessageChatItem): boolean {
    const message = chatItem.lxmf_message;
    const text = String(message.content || "").trim();
    if (!message.fields?.image || !text || text.includes("\n") || text.length > AUTO_IMAGE_CAPTION_MAX_CHARS) {
        return false;
    }
    if (/[\\/<>[\]{}]/.test(text)) {
        return false;
    }
    return /^[\w.\- ()#@%&!+,;=']+\.(png|jpe?g|gif|webp|bmp|heif|heic|avif|svg|ico)$/i.test(text);
}

function canUseImageStrip(chatItem: MessageChatItem): boolean {
    const message = chatItem.lxmf_message;
    return Boolean(
        message.fields?.image &&
        !message.is_spam &&
        !["cancelled", "failed", "rejected"].includes(String(message.state || "")) &&
        !message.reply_to_hash &&
        !message.fields.audio &&
        !message.fields.file_attachments?.length &&
        !message.fields.telemetry &&
        !message.fields.telemetry_stream &&
        !message.fields.commands?.length &&
        (!String(message.content || "").trim() || shouldHideAutoImageCaption(chatItem))
    );
}

function attachmentSize(attachment: unknown, kind: string): string {
    if (!attachment || typeof attachment !== "object") {
        return "0 Bytes";
    }
    const value = attachment as Record<string, unknown>;
    const explicit = Number(value[`${kind}_size`] ?? value.size ?? 0);
    if (explicit > 0) {
        return Utils.formatBytes(explicit);
    }
    const encoded = value[`${kind}_bytes`];
    if (typeof encoded === "string") {
        return Utils.formatBytes(Math.max(0, Math.floor((encoded.length * 3) / 4)));
    }
    return "0 Bytes";
}

function parseBasicItems(chatItem: MessageChatItem): ParsedMessageItems {
    const content = String(chatItem.lxmf_message.content || "");
    if (!content) {
        return {};
    }
    const parsed: ParsedMessageItems = {};
    const contact = content.match(
        /^Contact:\s+(.+?)\s+<([a-fA-F0-9]{32})>(?:\s+\[LXMF:\s+([a-fA-F0-9]{32})\])?(?:\s+\[LXST:\s+([a-fA-F0-9]{32})\])?/i
    );
    if (contact) {
        parsed.contact = {
            name: contact[1],
            hash: contact[2],
            lxmf_address: contact[3],
            lxst_address: contact[4],
        };
    }
    const paper = content.match(/(lxm|lxmf):\/\/[a-zA-Z0-9+/=._-]+/i)?.[0];
    if (paper) {
        parsed.paperMessage = paper;
        parsed.isOnlyPaperMessage = content.trim() === paper;
    }
    return parsed;
}

function pending(chatItem: MessageChatItem): boolean {
    const message = chatItem.lxmf_message;
    return Boolean(
        chatItem.is_outbound &&
        (message._pendingPathfinding || ["outbound", "sending", "generating"].includes(String(message.state || "")))
    );
}

function themedOutbound(chatItem: MessageChatItem): boolean {
    return Boolean(
        chatItem.is_outbound &&
        !chatItem.lxmf_message.is_spam &&
        !chatItem.lxmf_message._pendingPathfinding &&
        !["cancelled", "failed", "rejected"].includes(String(chatItem.lxmf_message.state || ""))
    );
}

function bubbleClass(chatItem: MessageChatItem): string {
    if (!chatItem.is_outbound) {
        return "";
    }
    if (["cancelled", "failed", "rejected"].includes(String(chatItem.lxmf_message.state || ""))) {
        return "bg-red-600 text-white border border-red-500 shadow-xs";
    }
    if (chatItem.lxmf_message._pendingPathfinding) {
        return "bg-sem-surface-muted text-sem-fg border border-sem-border shadow-xs";
    }
    return "bg-sem-action-primary text-white border border-sem-action-primary shadow-xs";
}

function classForOutbound(chatItem: MessageChatItem, themed: string, defaultClass: string, inbound = ""): string {
    if (!chatItem.is_outbound) {
        return inbound;
    }
    return themedOutbound(chatItem) ? themed : defaultClass;
}

export function createConversationViewerActions(
    deps: ConversationViewerActionDeps
): ConversationViewerActions & { canMergeImageIntoImageStrip: (item: MessageChatItem) => boolean } {
    const lxmfImageUrl = (hash?: string) => (hash ? `/api/v1/lxmf-messages/attachment/${hash}/image` : "");
    const progress = (message: LxmfMessageLike) => {
        if (message._pendingPathfinding) {
            return 0;
        }
        const value = Number(message.progress ?? 0);
        return ["sending", "outbound", "generating"].includes(String(message.state || "")) && value > 0
            ? transferProgressPercent(value, 100)
            : 0;
    };
    const bubbleViewModel = (chatItem: MessageChatItem): MessageBubbleViewModel => {
        const content = String(chatItem.lxmf_message.content || "");
        return {
            kind: "html",
            textForRender: content,
            singleEmoji: content.length < 64 && MarkdownRenderer.isSingleEmojiMessage(content),
            showFooter: false,
            messageHash: chatItem.lxmf_message.hash,
        };
    };

    return {
        expandedMessageInfo: deps.expandedMessageInfo,
        audioAttachmentUrls: deps.audioAttachmentUrls || {},
        selectedPeer: deps.selectedPeer,
        canMergeImageIntoImageStrip: canUseImageStrip,
        imageGroupSortedChron: (items) =>
            items.slice().sort((a, b) => {
                const aTime = Number(
                    a.lxmf_message.timestamp || new Date(a.lxmf_message.created_at as string).getTime()
                );
                const bTime = Number(
                    b.lxmf_message.timestamp || new Date(b.lxmf_message.created_at as string).getTime()
                );
                return aTime - bTime;
            }),
        imageGroupGalleryUrls: (items) =>
            items
                .slice()
                .sort((a, b) => Number(a.lxmf_message.timestamp || 0) - Number(b.lxmf_message.timestamp || 0))
                .map((item) => imageDataUrl(item.lxmf_message) || lxmfImageUrl(item.lxmf_message.hash)),
        lxmfImageUrl,
        pendingOutboundImageSrc: (item) => imageDataUrl(item.lxmf_message) || lxmfImageUrl(item.lxmf_message.hash),
        openImage: deps.openImage,
        onOutboundImageClick: (item) =>
            deps.openImage(imageDataUrl(item.lxmf_message) || lxmfImageUrl(item.lxmf_message.hash), undefined, [item]),
        onChatItemClick: deps.onChatItemClick,
        onMessageContextMenu: deps.onMessageContextMenu,
        downloadMessageImage: (item) => void deps.downloadMessageImage(item),
        openReactionPicker: deps.openReactionPicker,
        reactionReactorLabel: (sender) => {
            const hash = String(sender || "");
            if (!hash) return "";
            if (hash.toLowerCase() === String(deps.myLxmfAddressHash || "").toLowerCase()) {
                return t("messages.reaction_you");
            }
            const peer = deps.selectedPeer;
            if (hash.toLowerCase() === String(peer?.destination_hash || "").toLowerCase()) {
                return peer?.custom_display_name || peer?.display_name || Utils.formatDestinationHash(hash);
            }
            const conversation = deps.conversations?.find(
                (item) => String(item.destination_hash || "").toLowerCase() === hash.toLowerCase()
            );
            return conversation?.custom_display_name || conversation?.display_name || Utils.formatDestinationHash(hash);
        },
        replyToMessage: deps.replyToMessage,
        retrySendingMessage: deps.retrySendingMessage,
        cancelSendingMessage: deps.cancelSendingMessage,
        deleteChatItem: deps.deleteChatItem,
        showRawMessage: deps.showRawMessage,
        scrollToMessage: deps.scrollToMessage,
        getRepliedMessage: (hash) =>
            deps.chatItems.find((item) => item.lxmf_message.hash === hash)?.lxmf_message || null,
        handleMessageClick: (event) => {
            const target = event.target as HTMLElement | null;
            const anchor = target?.closest("a");
            if (anchor) {
                event.stopPropagation();
            }
        },
        setBubbleMessageShowOriginal: () => {},
        copyOversizedMessageBody: (item) => void deps.copyText(String(item.lxmf_message.content || "")),
        downloadLxmfFileAttachment: (item, index) => {
            const name = String(item.lxmf_message.fields?.file_attachments?.[index]?.file_name || "download");
            void deps.downloadLxmfFileAttachment(item, index, name);
        },
        addContact: (name, hash, lxmfAddress, lxstAddress) =>
            void deps.addContact(name, hash, lxmfAddress, lxstAddress),
        ingestPaperMessage: () => {},
        openMapShareFromParsed: () => {},
        copyMapShareUri: (uri) => {
            if (uri) void deps.copyText(uri);
        },
        openRelayShareFromParsed: () => {},
        copyRelayShareUri: (uri) => {
            if (uri) void deps.copyText(uri);
        },
        viewLocationOnMap: () => {},
        toggleTracking: () => {},
        bubbleViewModel,
        renderMarkdown: (text) => MarkdownRenderer.render(text || ""),
        getParsedItems: parseBasicItems,
        formatTimeAgo: (value) => fromNow(value),
        formatDateDividerLabel: (value) => formatDate(value, "MMM D, YYYY"),
        formatAttachmentSize: attachmentSize,
        getMessageInfoLines: (message, isOutbound) => {
            const lines = [fromNow(message.created_at)];
            if (isOutbound && message.state) lines.push(outboundStateTitle(message.state));
            if (message.hash) lines.push(message.hash);
            return lines.filter(Boolean);
        },
        messageBodyCharCount: (item) => String(item.lxmf_message.content || "").length,
        bubbleMessageBodyFontSizePx: (model) =>
            Math.round((Number(deps.messageFontSize) || 14) * (model.singleEmoji ? 2.75 : 1)),
        bubbleStyles: () => "",
        isImageOnlyMessage: (item) =>
            isImageOnlyMessage(item as ChatItemLike, shouldHideAutoImageCaption as (item: ChatItemLike) => boolean),
        hasMessageBubble: (item) =>
            hasMessageBubble(item as ChatItemLike, shouldHideAutoImageCaption as (item: ChatItemLike) => boolean),
        hasFileAttachments,
        shouldHideAutoImageCaption,
        isMessageBodyTooLargeForDisplay: (item) =>
            String(item.lxmf_message.content || "").length > MESSAGE_BODY_MAX_DISPLAY_CHARS,
        isPaperMessageIngested: () => false,
        isThemeOutboundBubble: themedOutbound,
        isOutboundWaitingBubble: (item) => Boolean(item.is_outbound && item.lxmf_message._pendingPathfinding),
        isOutboundPendingForUi: pending,
        isOpportunisticDeferredDelivery,
        showRichOutboundPendingUi: pending,
        canCancelOutboundSend: (item) => Boolean(item.lxmf_message.hash && pending(item)),
        showOutboundTransferProgress: (message) => progress(message) > 0,
        outboundTransferProgressPercent: progress,
        outboundSendingProgressLabel: (message) => `${progress(message)}%`,
        outboundTransferStatsLabel: () => "",
        outboundBubbleStatusIconName,
        outboundBubbleStatusTitle: (message) => {
            const key = outboundBubbleStatusTitleKey(message);
            return key ? t(key) : outboundStateTitle(message.state);
        },
        outboundBubbleStatusHoverTitle: (message) => outboundStateTitle(message.state),
        outboundBubbleFailedTitle: (message) => outboundStateTitle(message.state),
        outboundBubbleSurfaceClass: bubbleClass,
        outboundBubbleFooterTimeClass: (item) =>
            classForOutbound(item, "text-white/85", "text-sem-fg-muted", "text-sem-fg-muted"),
        outboundBubbleDeliveredIconClass: (item) => classForOutbound(item, "text-blue-200", "text-sem-fg-muted"),
        outboundBubbleSentCheckIconClass: (item) => classForOutbound(item, "text-white", "text-sem-fg-muted"),
        outboundBubblePendingCheckIconClass: (item) =>
            classForOutbound(item, "text-white opacity-50", "text-sem-fg-muted opacity-50"),
        outboundSendingStatusIconClass: (item) => classForOutbound(item, "text-white", "text-sem-fg-muted"),
        outboundExpandedActionsShellClass: (item) =>
            classForOutbound(
                item,
                "border-white/20 bg-white/10",
                "border-sem-border bg-sem-surface-muted",
                "border-sem-border bg-sem-surface-muted"
            ),
        outboundMessageMenuButtonClass: (item) =>
            classForOutbound(item, "text-white/90 hover:text-white", "text-sem-fg-muted", "text-sem-fg-muted"),
        outboundMessageMenuButtonHoverClass: (item) =>
            classForOutbound(item, "hover:bg-white/20", "hover:bg-sem-surface-muted", "hover:bg-sem-surface-muted"),
        outboundReplySnippetTitleClass: (item) =>
            classForOutbound(item, "text-white/80", "text-sem-fg-muted", "text-indigo-500/80"),
        outboundAttachmentCaptionClass: (item) =>
            classForOutbound(item, "text-white/85", "text-sem-fg-muted", "text-sem-fg-muted"),
        outboundEmbeddedCardClass: (item) =>
            classForOutbound(
                item,
                "bg-white/20 text-white border-white/20 hover:bg-white/30",
                "bg-sem-surface-muted text-sem-fg border-sem-border",
                ""
            ),
        outboundEmbeddedSecondaryTextClass: (item) => classForOutbound(item, "text-white/60", "text-sem-fg-muted", ""),
    };
}
