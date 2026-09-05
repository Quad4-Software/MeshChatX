// SPDX-License-Identifier: 0BSD

export type MessageReaction = {
    reactionHash?: string;
    emoji?: string;
    sender?: string;
    [key: string]: unknown;
};

export type MessageAttachment = {
    file_name?: string;
    size?: number;
    [key: string]: unknown;
};

export type LxmfMessageLike = {
    hash?: string;
    content?: string;
    created_at?: unknown;
    state?: string;
    is_spam?: boolean;
    is_reaction?: boolean;
    reply_to_hash?: string;
    reactions?: MessageReaction[];
    fields?: {
        image?: Record<string, unknown> & { image_type?: string };
        audio?: Record<string, unknown>;
        file_attachments?: MessageAttachment[];
        commands?: Array<Record<string, unknown>>;
        telemetry?: Record<string, any>;
        telemetry_stream?: unknown[];
        reply_quoted_content?: string;
        [key: string]: unknown;
    };
    [key: string]: unknown;
};

export type MessageChatItem = {
    lxmf_message: LxmfMessageLike;
    is_outbound?: boolean;
    is_actions_expanded?: boolean;
    [key: string]: unknown;
};

export type MessageBubbleViewModel = {
    kind?: string;
    singleEmoji?: boolean;
    textForRender?: string;
    showFooter?: boolean;
    showOriginalLink?: boolean;
    showTranslationLink?: boolean;
    fromCode?: string;
    toCode?: string;
    messageHash?: string;
};

export type ParsedMessageItems = {
    isOnlyPaperMessage?: boolean;
    isOnlyMapLink?: boolean;
    isOnlyRelayLink?: boolean;
    contact?: Record<string, any>;
    paperMessage?: unknown;
    mapLink?: Record<string, any>;
    relayLink?: Record<string, any>;
};

export type ConversationViewerActions = {
    expandedMessageInfo?: string | null;
    audioAttachmentUrls?: Readonly<Record<string, string>>;
    selectedPeer?: { is_tracking?: boolean } | null;
    imageGroupSortedChron: (items: MessageChatItem[]) => MessageChatItem[];
    imageGroupGalleryUrls: (items: MessageChatItem[]) => string[];
    lxmfImageUrl: (hash?: string) => string;
    pendingOutboundImageSrc: (chatItem: MessageChatItem) => string;
    openImage: (src: string, gallery?: string[], items?: MessageChatItem[]) => void;
    onOutboundImageClick: (chatItem: MessageChatItem) => void;
    onChatItemClick: (chatItem: MessageChatItem) => void;
    onMessageContextMenu: (event: MouseEvent, chatItem: MessageChatItem, suppressToggle?: boolean) => void;
    downloadMessageImage: (chatItem: MessageChatItem) => void;
    openReactionPicker: (chatItem: MessageChatItem) => void;
    reactionReactorLabel: (sender?: string) => string;
    replyToMessage: (chatItem: MessageChatItem) => void;
    retrySendingMessage: (chatItem: MessageChatItem) => void;
    cancelSendingMessage: (chatItem: MessageChatItem) => void;
    deleteChatItem: (chatItem: MessageChatItem) => void;
    showRawMessage: (chatItem: MessageChatItem) => void;
    scrollToMessage: (hash: string) => void;
    getRepliedMessage: (hash: string) => { content?: string } | null | undefined;
    handleMessageClick: (event: MouseEvent) => void;
    setBubbleMessageShowOriginal: (hash?: string, showOriginal?: boolean) => void;
    copyOversizedMessageBody: (chatItem: MessageChatItem) => void;
    downloadLxmfFileAttachment: (chatItem: MessageChatItem, index: number) => void;
    addContact: (name?: string, hash?: string, lxmfAddress?: string, lxstAddress?: string) => void;
    ingestPaperMessage: (paperMessage: unknown, hash?: string) => void;
    openMapShareFromParsed: (parsed: unknown) => void;
    copyMapShareUri: (uri?: string) => void;
    openRelayShareFromParsed: (parsed: unknown) => void;
    copyRelayShareUri: (uri?: string) => void;
    viewLocationOnMap: (location: unknown) => void;
    toggleTracking: () => void;
    bubbleViewModel: (chatItem: MessageChatItem) => MessageBubbleViewModel;
    renderMarkdown: (text?: string) => string;
    getParsedItems: (chatItem: MessageChatItem) => ParsedMessageItems | null | undefined;
    formatTimeAgo: (ts: unknown) => string;
    formatDateDividerLabel: (dayKey: unknown) => string;
    formatAttachmentSize: (attachment: unknown, kind: string) => string;
    getMessageInfoLines: (message: LxmfMessageLike, isOutbound?: boolean) => string[];
    messageBodyCharCount: (chatItem: MessageChatItem) => number;
    bubbleMessageBodyFontSizePx: (model: MessageBubbleViewModel) => number;
    bubbleStyles: (chatItem: MessageChatItem) => string | Record<string, string>;
    isImageOnlyMessage: (chatItem: MessageChatItem) => boolean;
    hasMessageBubble: (chatItem: MessageChatItem) => boolean;
    hasFileAttachments: (message: LxmfMessageLike) => boolean;
    shouldHideAutoImageCaption: (chatItem: MessageChatItem) => boolean;
    isMessageBodyTooLargeForDisplay: (chatItem: MessageChatItem) => boolean;
    isPaperMessageIngested: (chatItem: MessageChatItem) => boolean;
    isThemeOutboundBubble: (chatItem: MessageChatItem) => boolean;
    isOutboundWaitingBubble: (chatItem: MessageChatItem) => boolean;
    isOutboundPendingForUi: (chatItem: MessageChatItem) => boolean;
    isOpportunisticDeferredDelivery: (message: LxmfMessageLike) => boolean;
    showRichOutboundPendingUi: (chatItem: MessageChatItem) => boolean;
    canCancelOutboundSend: (chatItem: MessageChatItem) => boolean;
    showOutboundTransferProgress: (message: LxmfMessageLike) => boolean;
    outboundTransferProgressPercent: (message: LxmfMessageLike) => number;
    outboundSendingProgressLabel: (message: LxmfMessageLike) => string;
    outboundTransferStatsLabel: (message: LxmfMessageLike, chatItem: MessageChatItem) => string;
    outboundBubbleStatusIconName: (message: LxmfMessageLike) => string;
    outboundBubbleStatusTitle: (message: LxmfMessageLike) => string;
    outboundBubbleStatusHoverTitle: (message: LxmfMessageLike) => string;
    outboundBubbleFailedTitle: (message: LxmfMessageLike) => string;
    outboundBubbleSurfaceClass: (chatItem: MessageChatItem) => string;
    outboundBubbleFooterTimeClass: (chatItem: MessageChatItem) => string;
    outboundBubbleDeliveredIconClass: (chatItem: MessageChatItem) => string;
    outboundBubbleSentCheckIconClass: (chatItem: MessageChatItem) => string;
    outboundBubblePendingCheckIconClass: (chatItem: MessageChatItem) => string;
    outboundSendingStatusIconClass: (chatItem: MessageChatItem) => string;
    outboundExpandedActionsShellClass: (chatItem: MessageChatItem) => string;
    outboundMessageMenuButtonClass: (chatItem: MessageChatItem) => string;
    outboundMessageMenuButtonHoverClass: (chatItem: MessageChatItem) => string;
    outboundReplySnippetTitleClass: (chatItem: MessageChatItem) => string;
    outboundAttachmentCaptionClass: (chatItem: MessageChatItem) => string;
    outboundEmbeddedCardClass: (chatItem: MessageChatItem) => string;
    outboundEmbeddedSecondaryTextClass: (chatItem: MessageChatItem) => string;
};
