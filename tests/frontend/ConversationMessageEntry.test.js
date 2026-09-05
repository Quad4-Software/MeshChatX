// SPDX-License-Identifier: 0BSD

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import ConversationMessageEntry from "@/features/messages/components/ConversationMessageEntry.svelte";

function makeActions(overrides = {}) {
    return {
        expandedMessageInfo: null,
        audioAttachmentUrls: {},
        selectedPeer: null,
        imageGroupSortedChron: (items) => items,
        imageGroupGalleryUrls: () => [],
        lxmfImageUrl: () => "",
        pendingOutboundImageSrc: () => "",
        openImage: vi.fn(),
        onOutboundImageClick: vi.fn(),
        onChatItemClick: vi.fn(),
        onMessageContextMenu: vi.fn(),
        downloadMessageImage: vi.fn(),
        openReactionPicker: vi.fn(),
        reactionReactorLabel: () => "",
        replyToMessage: vi.fn(),
        retrySendingMessage: vi.fn(),
        cancelSendingMessage: vi.fn(),
        deleteChatItem: vi.fn(),
        showRawMessage: vi.fn(),
        scrollToMessage: vi.fn(),
        getRepliedMessage: () => null,
        handleMessageClick: vi.fn(),
        setBubbleMessageShowOriginal: vi.fn(),
        copyOversizedMessageBody: vi.fn(),
        downloadLxmfFileAttachment: vi.fn(),
        addContact: vi.fn(),
        ingestPaperMessage: vi.fn(),
        openMapShareFromParsed: vi.fn(),
        copyMapShareUri: vi.fn(),
        openRelayShareFromParsed: vi.fn(),
        copyRelayShareUri: vi.fn(),
        viewLocationOnMap: vi.fn(),
        toggleTracking: vi.fn(),
        bubbleViewModel: (item) => ({
            kind: "html",
            textForRender: item?.lxmf_message?.content || "",
            singleEmoji: false,
            showFooter: false,
        }),
        renderMarkdown: (text) => text || "",
        getParsedItems: () => ({}),
        formatTimeAgo: () => "now",
        formatDateDividerLabel: () => "",
        formatAttachmentSize: () => "1 B",
        getMessageInfoLines: () => [],
        messageBodyCharCount: () => 0,
        bubbleMessageBodyFontSizePx: () => 14,
        bubbleStyles: () => ({}),
        isImageOnlyMessage: () => false,
        hasMessageBubble: () => true,
        hasFileAttachments: () => false,
        shouldHideAutoImageCaption: () => false,
        isMessageBodyTooLargeForDisplay: () => false,
        isPaperMessageIngested: () => false,
        isThemeOutboundBubble: () => false,
        isOutboundWaitingBubble: () => false,
        isOutboundPendingForUi: (item) => item?.lxmf_message?.state === "sending",
        isOpportunisticDeferredDelivery: () => false,
        showRichOutboundPendingUi: () => false,
        canCancelOutboundSend: (item) =>
            Boolean(item?.is_outbound && ["sending", "outbound", "generating"].includes(item?.lxmf_message?.state)),
        showOutboundTransferProgress: () => false,
        outboundTransferProgressPercent: () => 0,
        outboundSendingProgressLabel: () => "",
        outboundTransferStatsLabel: () => "",
        outboundBubbleStatusIconName: () => "check",
        outboundBubbleStatusTitle: () => "",
        outboundBubbleStatusHoverTitle: () => "",
        outboundBubbleFailedTitle: () => "",
        outboundBubbleSurfaceClass: () => "bubble",
        outboundBubbleFooterTimeClass: () => "",
        outboundBubbleDeliveredIconClass: () => "",
        outboundBubbleSentCheckIconClass: () => "",
        outboundBubblePendingCheckIconClass: () => "",
        outboundSendingStatusIconClass: () => "",
        outboundExpandedActionsShellClass: () => "",
        outboundMessageMenuButtonClass: () => "",
        outboundMessageMenuButtonHoverClass: () => "",
        outboundReplySnippetTitleClass: () => "",
        outboundAttachmentCaptionClass: () => "",
        outboundEmbeddedCardClass: () => "",
        outboundEmbeddedSecondaryTextClass: () => "",
        ...overrides,
    };
}

function makeChatItem(overrides = {}) {
    return {
        type: "lxmf_message",
        is_outbound: false,
        is_actions_expanded: false,
        lxmf_message: {
            hash: "aa".repeat(16),
            state: "delivered",
            content: "hello",
            destination_hash: "bb".repeat(16),
            source_hash: "cc".repeat(16),
            fields: {},
        },
        ...overrides,
    };
}

function renderEntry(chatItem, actions) {
    return render(ConversationMessageEntry, {
        entry: { type: "single", key: "message", chatItem, showTimestamp: true },
        actions,
    });
}

afterEach(cleanup);

describe("ConversationMessageEntry.svelte", () => {
    it("cancels an expanded outbound send", async () => {
        const chatItem = makeChatItem({
            is_outbound: true,
            is_actions_expanded: true,
            lxmf_message: {
                hash: "aa".repeat(16),
                state: "sending",
                content: "cancel me",
                fields: {},
            },
        });
        const actions = makeActions();
        renderEntry(chatItem, actions);

        await fireEvent.click(screen.getByRole("button", { name: "messages.cancel_send" }));
        expect(actions.cancelSendingMessage).toHaveBeenCalledWith(chatItem);
    });

    it("downloads a file attachment through the viewer action", async () => {
        const chatItem = makeChatItem({
            lxmf_message: {
                hash: "dd".repeat(16),
                state: "delivered",
                content: "",
                fields: {
                    file_attachments: [{ file_name: "photo.jpg", file_size: 100 }],
                },
            },
        });
        const actions = makeActions({ hasFileAttachments: () => true });
        renderEntry(chatItem, actions);

        const button = screen.getByText("photo.jpg").closest("button");
        expect(button).toBeTruthy();
        expect(button.getAttribute("href")).toBeNull();
        await fireEvent.click(button);
        expect(actions.downloadLxmfFileAttachment).toHaveBeenCalledWith(chatItem, 0);
    });

    it("ingests a detected paper message with its message hash", async () => {
        const uri = "lxmf://deadbeefpaperpayload";
        const chatItem = makeChatItem({
            lxmf_message: {
                hash: "ee".repeat(16),
                state: "delivered",
                content: uri,
                fields: {},
            },
        });
        const actions = makeActions({
            getParsedItems: () => ({ paperMessage: uri, isOnlyPaperMessage: true }),
        });
        renderEntry(chatItem, actions);

        await fireEvent.click(screen.getByRole("button", { name: "messages.paper_message_ingest" }));
        expect(actions.ingestPaperMessage).toHaveBeenCalledWith(uri, chatItem.lxmf_message.hash);
    });

    it("shows the ingested paper state without an ingest action", () => {
        const uri = "lxmf://alreadyingested";
        const chatItem = makeChatItem({
            lxmf_message: {
                hash: "ff".repeat(16),
                state: "delivered",
                content: uri,
                fields: {},
            },
        });
        const actions = makeActions({
            getParsedItems: () => ({ paperMessage: uri, isOnlyPaperMessage: true }),
            isPaperMessageIngested: () => true,
        });
        renderEntry(chatItem, actions);

        expect(screen.getByText("messages.paper_message_ingested")).toBeTruthy();
        expect(screen.queryByRole("button", { name: "messages.paper_message_ingest" })).toBeNull();
    });
});
