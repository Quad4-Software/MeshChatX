import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import ConversationMessageEntry from "@/components/messages/ConversationMessageEntry.vue";

function makeCv(overrides = {}) {
    return {
        hasMessageBubble: () => true,
        hasFileAttachments: () => false,
        getParsedItems: () => null,
        bubbleViewModel: (item) => ({
            kind: "html",
            textForRender: item?.lxmf_message?.content || "",
            singleEmoji: false,
            showFooter: false,
        }),
        renderMarkdown: (text) => text,
        bubbleMessageBodyFontSizePx: () => 14,
        shouldHideAutoImageCaption: () => false,
        isMessageBodyTooLargeForDisplay: () => false,
        messageBodyCharCount: () => 0,
        formatTimeAgo: () => "now",
        getMessageInfoLines: () => [],
        outboundBubbleSurfaceClass: () => "bubble",
        outboundBubbleFooterTimeClass: () => "",
        outboundEmbeddedCardClass: () => "",
        outboundEmbeddedSecondaryTextClass: () => "",
        outboundReplySnippetTitleClass: () => "",
        outboundExpandedActionsShellClass: () => "",
        outboundMessageMenuButtonClass: () => "",
        outboundMessageMenuButtonHoverClass: () => "",
        outboundBubbleDeliveredIconClass: () => "",
        outboundBubbleSentCheckIconClass: () => "",
        outboundSendingStatusIconClass: () => "",
        outboundBubblePendingCheckIconClass: () => "",
        outboundSentStatusTitle: () => "",
        outboundBubbleFailedTitle: () => "",
        outboundBubbleStatusHoverTitle: () => "",
        isOutboundPendingForUi: (item) => item?.lxmf_message?.state === "sending",
        isOutboundWaitingBubble: () => false,
        isOpportunisticDeferredDelivery: () => false,
        isThemeOutboundBubble: () => false,
        showRichOutboundPendingUi: () => false,
        showOutboundTransferProgress: () => false,
        canCancelOutboundSend: (item) =>
            item?.is_outbound && ["sending", "outbound", "generating"].includes(item?.lxmf_message?.state),
        onChatItemClick: vi.fn((item) => {
            item.is_actions_expanded = !item.is_actions_expanded;
        }),
        onMessageContextMenu: vi.fn(),
        replyToMessage: vi.fn(),
        deleteChatItem: vi.fn(),
        showRawMessage: vi.fn(),
        cancelSendingMessage: vi.fn(),
        downloadLxmfFileAttachment: vi.fn(),
        scrollToMessage: vi.fn(),
        copyOversizedMessageBody: vi.fn(),
        formatAttachmentSize: () => "1 B",
        bubbleStyles: () => ({}),
        isImageOnlyMessage: () => false,
        pendingOutboundImageSrc: () => "",
        onOutboundImageClick: vi.fn(),
        openImage: vi.fn(),
        imageGroupSortedChron: (items) => items,
        imageGroupGalleryUrls: () => [],
        lxmfImageUrl: () => "",
        expandedMessageInfo: null,
        ...overrides,
    };
}

describe("ConversationMessageEntry wiring", () => {
    it("shows Cancel send in expanded actions while outbound message is sending", async () => {
        const chatItem = {
            type: "lxmf_message",
            is_outbound: true,
            is_actions_expanded: true,
            lxmf_message: {
                hash: "aa".repeat(16),
                state: "sending",
                progress: 10,
                content: "hello",
                destination_hash: "bb".repeat(16),
                source_hash: "cc".repeat(16),
                fields: {},
            },
        };
        const cv = makeCv();

        const wrapper = mount(ConversationMessageEntry, {
            props: {
                entry: { type: "message", key: "m1", chatItem, showTimestamp: true },
                cv,
            },
            global: {
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: { template: "<span />" },
                    MessageReactionsOverlay: true,
                    OutboundTransferProgressFooter: true,
                },
            },
        });

        expect(wrapper.text()).toContain("messages.cancel_send");
    });

    it("clicking Cancel send calls cv.cancelSendingMessage", async () => {
        const chatItem = {
            type: "lxmf_message",
            is_outbound: true,
            is_actions_expanded: true,
            lxmf_message: {
                hash: "aa".repeat(16),
                state: "sending",
                content: "cancel me",
                destination_hash: "bb".repeat(16),
                source_hash: "cc".repeat(16),
                fields: {},
            },
        };
        const cv = makeCv();

        const wrapper = mount(ConversationMessageEntry, {
            props: {
                entry: { type: "message", key: "m2", chatItem, showTimestamp: true },
                cv,
            },
            global: {
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: { template: "<span />" },
                    MessageReactionsOverlay: true,
                    OutboundTransferProgressFooter: true,
                },
            },
        });

        const cancelBtn = wrapper.findAll("button").find((b) => b.text().includes("messages.cancel_send"));
        expect(cancelBtn).toBeDefined();
        await cancelBtn.trigger("click");
        expect(cv.cancelSendingMessage).toHaveBeenCalledWith(chatItem);
    });

    it("file attachment row calls downloadLxmfFileAttachment instead of navigating", async () => {
        const chatItem = {
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message: {
                hash: "dd".repeat(16),
                state: "delivered",
                content: "",
                destination_hash: "bb".repeat(16),
                source_hash: "cc".repeat(16),
                fields: {
                    file_attachments: [{ file_name: "photo.jpg", file_size: 100 }],
                },
            },
        };
        const cv = makeCv({
            hasFileAttachments: () => true,
        });

        const wrapper = mount(ConversationMessageEntry, {
            props: {
                entry: { type: "message", key: "m3", chatItem, showTimestamp: true },
                cv,
            },
            global: {
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: { template: "<span />" },
                    MessageReactionsOverlay: true,
                    OutboundTransferProgressFooter: true,
                },
            },
        });

        const fileBtn = wrapper.findAll("button").find((b) => b.text().includes("photo.jpg"));
        expect(fileBtn).toBeDefined();
        expect(fileBtn.attributes("href")).toBeUndefined();
        await fileBtn.trigger("click");
        expect(cv.downloadLxmfFileAttachment).toHaveBeenCalledWith(chatItem, 0);
    });
});
