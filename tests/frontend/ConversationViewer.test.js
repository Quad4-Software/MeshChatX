import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
    },
}));

describe("ConversationViewer.vue", () => {
    let axiosMock;

    beforeEach(() => {
        WebSocketConnection.connect();
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;

        // Mock localStorage
        const localStorageMock = {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        };
        vi.stubGlobal("localStorage", localStorageMock);

        // Mock URL.createObjectURL
        window.URL.createObjectURL = vi.fn(() => "mock-url");

        // Mock FileReader
        const mockFileReader = {
            readAsDataURL: vi.fn(function (blob) {
                this.result = "data:image/png;base64,mock";
                this.onload({ target: { result: this.result } });
            }),
        };
        vi.stubGlobal(
            "FileReader",
            vi.fn(function () {
                return mockFileReader;
            })
        );
    });

    afterEach(() => {
        delete window.axios;
        vi.unstubAllGlobals();
        WebSocketConnection.destroy();
    });

    const mountConversationViewer = (props = {}) => {
        return mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: "test-hash", display_name: "Test Peer" },
                myLxmfAddressHash: "my-hash",
                conversations: [],
                ...props,
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: true,
                    AddImageButton: true,
                    AddAudioButton: true,
                    SendMessageButton: true,
                    ConversationDropDownMenu: true,
                    PaperMessageModal: true,
                    AudioWaveformPlayer: true,
                    LxmfUserIcon: true,
                },
            },
        });
    };

    it("adds multiple images and renders previews", async () => {
        const wrapper = mountConversationViewer();

        const image1 = new File([""], "image1.png", { type: "image/png" });
        const image2 = new File([""], "image2.png", { type: "image/png" });

        await wrapper.vm.onImageSelected(image1);
        await wrapper.vm.onImageSelected(image2);

        expect(wrapper.vm.newMessageImages).toHaveLength(2);
        expect(wrapper.vm.newMessageImageUrls).toHaveLength(2);

        // Check if previews are rendered
        const previews = wrapper.findAll("img");
        expect(previews).toHaveLength(2);
    });

    it("removes an image attachment", async () => {
        const wrapper = mountConversationViewer();

        const image1 = new File([""], "image1.png", { type: "image/png" });
        await wrapper.vm.onImageSelected(image1);

        expect(wrapper.vm.newMessageImages).toHaveLength(1);

        await wrapper.vm.removeImageAttachment(0);
        expect(wrapper.vm.newMessageImages).toHaveLength(0);
    });

    it("sends multiple images as separate messages", async () => {
        const wrapper = mountConversationViewer();
        wrapper.vm.newMessageText = "Hello";

        const image1 = new File([""], "image1.png", { type: "image/png" });
        const image2 = new File([""], "image2.png", { type: "image/png" });

        // Mock arrayBuffer for files
        image1.arrayBuffer = vi.fn(() => Promise.resolve(new ArrayBuffer(8)));
        image2.arrayBuffer = vi.fn(() => Promise.resolve(new ArrayBuffer(8)));

        await wrapper.vm.onImageSelected(image1);
        await wrapper.vm.onImageSelected(image2);

        axiosMock.post.mockResolvedValue({ data: { lxmf_message: { hash: "mock-hash" } } });

        await wrapper.vm.sendMessage();

        // Should call post twice
        expect(axiosMock.post).toHaveBeenCalledTimes(2);

        // First call should have the message text
        expect(axiosMock.post).toHaveBeenNthCalledWith(
            1,
            "/api/v1/lxmf-messages/send",
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    content: "Hello",
                }),
            })
        );

        // Second call should have the image name as content
        expect(axiosMock.post).toHaveBeenNthCalledWith(
            2,
            "/api/v1/lxmf-messages/send",
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    content: "image2.png",
                }),
            })
        );
    });

    it("auto-loads audio attachments on mount", async () => {
        const chatItems = [
            {
                lxmf_message: {
                    hash: "audio-hash",
                    fields: {
                        audio: { audio_mode: 0x10, audio_bytes: "base64-data" },
                    },
                },
            },
        ];

        axiosMock.get.mockResolvedValue({
            data: { lxmf_messages: chatItems.map((i) => i.lxmf_message) },
        });

        const wrapper = mountConversationViewer({
            conversations: [],
        });

        // initialLoad is called on mount
        await vi.waitFor(() => expect(axiosMock.get).toHaveBeenCalled());

        // downloadAndDecodeAudio should be triggered by autoLoadAudioAttachments
        await vi.waitFor(() =>
            expect(axiosMock.get).toHaveBeenCalledWith(expect.stringContaining("/audio"), expect.any(Object))
        );
    });

    it("shows retry button in context menu for failed outbound messages", async () => {
        const wrapper = mountConversationViewer();
        const failedChatItem = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "failed-hash",
                state: "failed",
                content: "failed message",
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
            },
        };
        wrapper.vm.chatItems = [failedChatItem];
        await wrapper.vm.$nextTick();

        wrapper.vm.messageContextMenu.chatItem = failedChatItem;
        wrapper.vm.messageContextMenu.show = true;
        await wrapper.vm.$nextTick();

        const menuHtml = wrapper.html();
        expect(menuHtml).toContain("Retry");
    });

    it("does not show retry in context menu for delivered messages", async () => {
        const wrapper = mountConversationViewer();
        const deliveredItem = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "delivered-hash",
                state: "delivered",
                content: "delivered message",
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
            },
        };
        wrapper.vm.chatItems = [deliveredItem];
        await wrapper.vm.$nextTick();

        wrapper.vm.messageContextMenu.chatItem = deliveredItem;
        wrapper.vm.messageContextMenu.show = true;
        await wrapper.vm.$nextTick();

        const retryButtons = wrapper.findAll("button").filter((b) => b.text().includes("Retry"));
        expect(retryButtons).toHaveLength(0);
    });

    it("calls retrySendingMessage when retry context menu clicked", async () => {
        const wrapper = mountConversationViewer();
        const failedChatItem = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "retry-hash",
                state: "failed",
                content: "retry me",
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
                reply_to_hash: null,
            },
        };

        axiosMock.post.mockResolvedValue({
            data: { lxmf_message: { hash: "new-hash", state: "outbound" } },
        });

        wrapper.vm.messageContextMenu.chatItem = failedChatItem;
        wrapper.vm.messageContextMenu.show = true;
        wrapper.vm.messageContextMenu.x = 0;
        wrapper.vm.messageContextMenu.y = 0;
        await wrapper.vm.$nextTick();

        const retryButtonEl = Array.from(document.body.querySelectorAll("button")).find((b) =>
            b.textContent.includes("Retry")
        );
        expect(retryButtonEl).toBeDefined();

        await wrapper.vm.retrySendingMessage(failedChatItem);
        expect(axiosMock.post).toHaveBeenCalledWith(
            expect.stringContaining("/lxmf-messages/send"),
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    destination_hash: "test-hash",
                    content: "retry me",
                }),
            })
        );
    });

    it("marks received messages as not outbound", async () => {
        const wrapper = mountConversationViewer();

        const incomingMessage = {
            hash: "incoming-hash",
            source_hash: "test-hash",
            destination_hash: "my-hash",
            content: "hello",
            state: "delivered",
            fields: {},
        };

        wrapper.vm.onLxmfMessageReceived(incomingMessage);

        const addedItem = wrapper.vm.chatItems.find((i) => i.lxmf_message?.hash === "incoming-hash");
        expect(addedItem).toBeDefined();
        expect(addedItem.is_outbound).toBe(false);
    });

    it("generates created_at from timestamp when missing", async () => {
        const wrapper = mountConversationViewer();

        const liveMsg = {
            hash: "live-hash",
            source_hash: "test-hash",
            destination_hash: "my-hash",
            content: "hello",
            state: "delivered",
            timestamp: 1700000000,
            fields: {},
        };

        wrapper.vm.onLxmfMessageReceived(liveMsg);

        const addedItem = wrapper.vm.chatItems.find((i) => i.lxmf_message?.hash === "live-hash");
        expect(addedItem.lxmf_message.created_at).toBe(new Date(1700000000 * 1000).toISOString());
    });

    it("converts unknown state to outbound for outgoing messages", async () => {
        const wrapper = mountConversationViewer();

        const outMsg = {
            hash: "out-hash",
            source_hash: "my-hash",
            destination_hash: "test-hash",
            content: "hello",
            state: "unknown",
            timestamp: 1700000000,
            fields: {},
        };

        wrapper.vm.onLxmfMessageCreated(outMsg);

        const addedItem = wrapper.vm.chatItems.find((i) => i.lxmf_message?.hash === "out-hash");
        expect(addedItem).toBeDefined();
        expect(addedItem.lxmf_message.state).toBe("outbound");
        expect(addedItem.is_outbound).toBe(true);
    });

    it("preserves unknown state for incoming messages", async () => {
        const wrapper = mountConversationViewer();

        const inMsg = {
            hash: "in-unknown-hash",
            source_hash: "test-hash",
            destination_hash: "my-hash",
            content: "hello",
            state: "unknown",
            timestamp: 1700000000,
            fields: {},
        };

        wrapper.vm.onLxmfMessageReceived(inMsg);

        const addedItem = wrapper.vm.chatItems.find((i) => i.lxmf_message?.hash === "in-unknown-hash");
        expect(addedItem.lxmf_message.state).toBe("unknown");
    });

    it("does not overwrite existing created_at", async () => {
        const wrapper = mountConversationViewer();

        const dbMsg = {
            hash: "db-hash",
            source_hash: "test-hash",
            destination_hash: "my-hash",
            content: "hello",
            state: "delivered",
            timestamp: 1700000000,
            created_at: "2023-11-14T22:13:20.000Z",
            fields: {},
        };

        wrapper.vm.onLxmfMessageReceived(dbMsg);

        const addedItem = wrapper.vm.chatItems.find((i) => i.lxmf_message?.hash === "db-hash");
        expect(addedItem.lxmf_message.created_at).toBe("2023-11-14T22:13:20.000Z");
    });

    it("sets reply state and includes reply_to_hash in sendMessage", async () => {
        const wrapper = mountConversationViewer();
        const chatItem = {
            lxmf_message: { hash: "original-hash", content: "Original message" },
        };

        // Add to chatItems
        wrapper.vm.chatItems = [chatItem];

        await wrapper.vm.replyToMessage(chatItem);
        expect(wrapper.vm.replyingTo.lxmf_message.hash).toBe(chatItem.lxmf_message.hash);

        wrapper.vm.newMessageText = "My reply";
        axiosMock.post.mockResolvedValue({ data: { lxmf_message: { hash: "reply-hash" } } });

        await wrapper.vm.sendMessage();

        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/lxmf-messages/send",
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    content: "My reply",
                    reply_to_hash: "original-hash",
                }),
            })
        );
        expect(wrapper.vm.replyingTo).toBeNull();
    });
});
