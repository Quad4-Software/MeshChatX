import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalState from "@/js/GlobalState";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
    },
}));

describe("ConversationViewer.vue", () => {
    let axiosMock;

    beforeEach(() => {
        GlobalState.config.theme = "light";
        GlobalState.config.message_outbound_bubble_color = "#4f46e5";
        GlobalState.config.message_waiting_bubble_color = "#e5e7eb";
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
        window.api = axiosMock;

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
        delete window.api;
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

    it("onMessagePaste adds images from clipboard and prevents default", async () => {
        const wrapper = mountConversationViewer();
        const file = new File([""], "clip.png", { type: "image/png" });
        const items = [
            {
                kind: "file",
                type: "image/png",
                getAsFile: () => file,
            },
        ];
        const event = {
            preventDefault: vi.fn(),
            clipboardData: { items },
        };
        wrapper.vm.onMessagePaste(event);
        expect(event.preventDefault).toHaveBeenCalled();
        expect(wrapper.vm.newMessageImages).toHaveLength(1);
    });

    it("onMessagePaste ignores non-image clipboard files (e.g. PDF) and does not prevent default", () => {
        const wrapper = mountConversationViewer();
        const file = new File([""], "doc.pdf", { type: "application/pdf" });
        const event = {
            preventDefault: vi.fn(),
            clipboardData: {
                items: [
                    {
                        kind: "file",
                        type: "application/pdf",
                        getAsFile: () => file,
                    },
                ],
            },
        };
        wrapper.vm.onMessagePaste(event);
        expect(event.preventDefault).not.toHaveBeenCalled();
        expect(wrapper.vm.newMessageImages).toHaveLength(0);
    });

    it("onMessagePaste does nothing when clipboard has no image file items", () => {
        const wrapper = mountConversationViewer();
        const event = {
            preventDefault: vi.fn(),
            clipboardData: {
                items: [{ kind: "string", type: "text/plain", getAsString: () => "hi" }],
            },
        };
        wrapper.vm.onMessagePaste(event);
        expect(event.preventDefault).not.toHaveBeenCalled();
        expect(wrapper.vm.newMessageImages).toHaveLength(0);
    });

    it("onMessagePaste adds multiple images from a single paste event", () => {
        const wrapper = mountConversationViewer();
        const f1 = new File([""], "a.png", { type: "image/png" });
        const f2 = new File([""], "b.png", { type: "image/png" });
        const event = {
            preventDefault: vi.fn(),
            clipboardData: {
                items: [
                    { kind: "file", type: "image/png", getAsFile: () => f1 },
                    { kind: "file", type: "image/png", getAsFile: () => f2 },
                ],
            },
        };
        wrapper.vm.onMessagePaste(event);
        expect(event.preventDefault).toHaveBeenCalled();
        expect(wrapper.vm.newMessageImages).toHaveLength(2);
    });

    it("pasteFromClipboard inserts text at the message input selection", async () => {
        const readText = vi.fn(() => Promise.resolve("pasted-text"));
        vi.stubGlobal("navigator", {
            ...navigator,
            clipboard: { readText },
        });
        const wrapper = mountConversationViewer();
        const ta = wrapper.find("#message-input").element;
        ta.selectionStart = 0;
        ta.selectionEnd = 0;
        wrapper.vm.newMessageText = "";
        await wrapper.vm.pasteFromClipboard();
        expect(wrapper.vm.newMessageText).toBe("pasted-text");
    });

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

        const sendCalls = axiosMock.post.mock.calls.filter((c) => c[0] === "/api/v1/lxmf-messages/send");
        expect(sendCalls.length).toBe(2);

        expect(sendCalls[0][1]).toEqual(
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    content: "Hello",
                }),
            })
        );

        expect(sendCalls[1][1]).toEqual(
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    content: "",
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

    it("uses theme outbound bubble: no inline background for default indigo config", () => {
        GlobalState.config.message_outbound_bubble_color = "#4f46e5";
        const wrapper = mountConversationViewer();
        const chatItem = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "h1",
                state: "delivered",
                content: "hi",
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
            },
        };
        const styles = wrapper.vm.bubbleStyles(chatItem);
        expect(styles["background-color"]).toBeUndefined();
        expect(wrapper.vm.outboundBubbleSurfaceClass(chatItem)).toContain("bg-sky-100");
        expect(wrapper.vm.isThemeOutboundBubble(chatItem)).toBe(true);
    });

    it("uses solid outbound bubble when custom color is set", () => {
        GlobalState.config.message_outbound_bubble_color = "#ff0000";
        const wrapper = mountConversationViewer();
        const chatItem = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "h2",
                state: "delivered",
                content: "hi",
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
            },
        };
        expect(wrapper.vm.bubbleStyles(chatItem)).toMatchObject({
            "background-color": "#ff0000",
            color: "#ffffff",
        });
        expect(wrapper.vm.outboundBubbleSurfaceClass(chatItem)).toBe("shadow-sm");
        expect(wrapper.vm.isThemeOutboundBubble(chatItem)).toBe(false);
    });

    it("applies waiting bubble color when pathfinding", () => {
        GlobalState.config.message_waiting_bubble_color = "#ccddff";
        const wrapper = mountConversationViewer();
        const chatItem = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "h-wait",
                state: "sending",
                content: "hi",
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
                _pendingPathfinding: true,
            },
        };
        expect(wrapper.vm.bubbleStyles(chatItem)).toMatchObject({
            "background-color": "#ccddff",
            color: "#111827",
        });
        expect(wrapper.vm.outboundBubbleSurfaceClass(chatItem)).toBe("");
    });

    it("uses dark neutral waiting bubble when pathfinding in dark theme with default gray", () => {
        GlobalState.config.theme = "dark";
        GlobalState.config.message_waiting_bubble_color = "#e5e7eb";
        const wrapper = mountConversationViewer();
        const chatItem = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "h-wait-dark",
                state: "sending",
                content: "hi",
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
                _pendingPathfinding: true,
            },
        };
        expect(wrapper.vm.bubbleStyles(chatItem)).toMatchObject({
            "background-color": "#3f3f46",
            color: "#ffffff",
        });
    });

    it("marks inbound messages with markdown-content--inbound for link styling", async () => {
        GlobalState.config.message_outbound_bubble_color = "#4f46e5";
        const wrapper = mountConversationViewer();
        const chatItem = {
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message: {
                hash: "in1",
                state: "delivered",
                content: "https://example.com",
                destination_hash: "my-hash",
                source_hash: "test-hash",
                fields: {},
            },
        };
        wrapper.vm.chatItems = [chatItem];
        await wrapper.vm.$nextTick();
        await vi.waitFor(() => {
            expect(wrapper.find(".markdown-content--inbound").exists()).toBe(true);
        });
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

    describe("conversation history loading", () => {
        const deferredConversationGet = () => {
            const deferredResolvers = [];
            axiosMock.get.mockImplementation((url) => {
                if (url.includes("/lxmf-messages/conversation/")) {
                    return new Promise((resolve) => {
                        deferredResolvers.push(resolve);
                    });
                }
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                if (url.includes("/contacts/check/")) return Promise.resolve({ data: {} });
                return Promise.resolve({ data: {} });
            });
            return deferredResolvers;
        };

        let inboundMsgId = 1000;
        const inboundFrom = (hash, content) => ({
            id: inboundMsgId++,
            hash: `msg-${hash.slice(0, 4)}-${content}`,
            source_hash: hash,
            destination_hash: "my-hash",
            content,
            state: "delivered",
            timestamp: 1700000000,
            fields: {},
        });

        it("loads the current peer after switching while a prior fetch was still in flight", async () => {
            const deferredResolvers = deferredConversationGet();

            const peerA = { destination_hash: "a".repeat(32), display_name: "A" };
            const peerB = { destination_hash: "b".repeat(32), display_name: "B" };

            const wrapper = mountConversationViewer({
                selectedPeer: peerA,
            });

            await vi.waitFor(() => expect(deferredResolvers.length).toBeGreaterThanOrEqual(1));

            await wrapper.setProps({ selectedPeer: peerB });
            await wrapper.vm.$nextTick();

            await vi.waitFor(() => expect(deferredResolvers.length).toBeGreaterThanOrEqual(2));

            deferredResolvers[0]({ data: { lxmf_messages: [] } });
            await wrapper.vm.$nextTick();
            await Promise.resolve();
            expect(wrapper.vm.chatItems).toHaveLength(0);

            deferredResolvers[1]({
                data: {
                    lxmf_messages: [inboundFrom("b".repeat(32), "hello")],
                },
            });
            await vi.waitFor(() => expect(wrapper.vm.chatItems.length).toBe(1));
            expect(wrapper.vm.chatItems[0].lxmf_message.content).toBe("hello");
        });

        it("applies only the latest peer response when multiple requests resolve out of order", async () => {
            const deferredResolvers = deferredConversationGet();

            const peerA = { destination_hash: "a".repeat(32), display_name: "A" };
            const peerB = { destination_hash: "b".repeat(32), display_name: "B" };
            const peerC = { destination_hash: "c".repeat(32), display_name: "C" };

            const wrapper = mountConversationViewer({ selectedPeer: peerA });
            await vi.waitFor(() => expect(deferredResolvers.length).toBeGreaterThanOrEqual(1));

            await wrapper.setProps({ selectedPeer: peerB });
            await wrapper.vm.$nextTick();
            await vi.waitFor(() => expect(deferredResolvers.length).toBeGreaterThanOrEqual(2));

            await wrapper.setProps({ selectedPeer: peerC });
            await wrapper.vm.$nextTick();
            await vi.waitFor(() => expect(deferredResolvers.length).toBeGreaterThanOrEqual(3));

            deferredResolvers[0]({
                data: { lxmf_messages: [inboundFrom("a".repeat(32), "stale-a")] },
            });
            deferredResolvers[1]({
                data: { lxmf_messages: [inboundFrom("b".repeat(32), "stale-b")] },
            });
            await wrapper.vm.$nextTick();
            await Promise.resolve();
            expect(wrapper.vm.chatItems).toHaveLength(0);

            deferredResolvers[2]({
                data: { lxmf_messages: [inboundFrom("c".repeat(32), "current")] },
            });
            await vi.waitFor(() => expect(wrapper.vm.chatItems.length).toBe(1));
            expect(wrapper.vm.chatItems[0].lxmf_message.content).toBe("current");
        });

        it("does not start another page fetch while pagination is already in flight", async () => {
            const baseMsg = {
                id: 42,
                hash: "page1-msg",
                source_hash: "test-hash",
                destination_hash: "my-hash",
                content: "first page",
                state: "delivered",
                timestamp: 1700000000,
                fields: {},
            };
            axiosMock.get.mockImplementation((url) => {
                if (url.includes("/lxmf-messages/conversation/")) {
                    return Promise.resolve({ data: { lxmf_messages: [baseMsg] } });
                }
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                if (url.includes("/contacts/check/")) return Promise.resolve({ data: {} });
                return Promise.resolve({ data: {} });
            });

            const wrapper = mountConversationViewer();
            await vi.waitFor(() => expect(wrapper.vm.chatItems.length).toBe(1));

            const conversationGets = () =>
                axiosMock.get.mock.calls.filter((c) => String(c[0]).includes("/lxmf-messages/conversation/"));
            const countBefore = conversationGets().length;

            wrapper.vm.isLoadingPrevious = true;
            await wrapper.vm.loadPrevious();

            expect(conversationGets().length).toBe(countBefore);
        });
    });

    describe("compose draft persistence", () => {
        let draftStore;

        beforeEach(() => {
            draftStore = {};
            vi.stubGlobal("localStorage", {
                getItem: (key) => (Object.prototype.hasOwnProperty.call(draftStore, key) ? draftStore[key] : null),
                setItem: (key, value) => {
                    draftStore[key] = String(value);
                },
                removeItem: (key) => {
                    delete draftStore[key];
                },
            });
        });

        it("persists the previous peer draft in localStorage when switching peers", async () => {
            const peerA = { destination_hash: "a".repeat(32), display_name: "A" };
            const peerB = { destination_hash: "b".repeat(32), display_name: "B" };

            const wrapper = mountConversationViewer({ selectedPeer: peerA });
            await wrapper.vm.$nextTick();

            wrapper.vm.newMessageText = "draft for A";
            await wrapper.setProps({ selectedPeer: peerB });
            await wrapper.vm.$nextTick();

            const drafts = JSON.parse(draftStore["meshchat.drafts"] || "{}");
            expect(drafts["a".repeat(32)]).toBe("draft for A");
        });

        it("loads the stored draft when opening a peer", async () => {
            draftStore["meshchat.drafts"] = JSON.stringify({
                ["b".repeat(32)]: "remembered",
            });

            const wrapper = mountConversationViewer({
                selectedPeer: { destination_hash: "b".repeat(32), display_name: "B" },
            });
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.newMessageText).toBe("remembered");
        });

        it("round-trips drafts for A then B then back to A", async () => {
            const peerA = { destination_hash: "a".repeat(32), display_name: "A" };
            const peerB = { destination_hash: "b".repeat(32), display_name: "B" };

            const wrapper = mountConversationViewer({ selectedPeer: peerA });
            await wrapper.vm.$nextTick();
            wrapper.vm.newMessageText = "text-a";
            await wrapper.setProps({ selectedPeer: peerB });
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.newMessageText).toBe("");

            wrapper.vm.newMessageText = "text-b";
            await wrapper.setProps({ selectedPeer: peerA });
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.newMessageText).toBe("text-a");

            await wrapper.setProps({ selectedPeer: peerB });
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.newMessageText).toBe("text-b");
        });

        it("removes the draft key when saving an empty compose box for that peer", async () => {
            draftStore["meshchat.drafts"] = JSON.stringify({
                ["a".repeat(32)]: "will clear",
            });

            const wrapper = mountConversationViewer({
                selectedPeer: { destination_hash: "a".repeat(32), display_name: "A" },
            });
            await wrapper.vm.$nextTick();

            wrapper.vm.newMessageText = "";
            wrapper.vm.saveDraft("a".repeat(32));

            const drafts = JSON.parse(draftStore["meshchat.drafts"] || "{}");
            expect(drafts["a".repeat(32)]).toBeUndefined();
        });

        it("persists the current compose text when the component unmounts", async () => {
            const peer = { destination_hash: "a".repeat(32), display_name: "A" };
            const wrapper = mountConversationViewer({ selectedPeer: peer });
            await wrapper.vm.$nextTick();

            wrapper.vm.newMessageText = "save on leave";
            wrapper.unmount();

            const drafts = JSON.parse(draftStore["meshchat.drafts"] || "{}");
            expect(drafts["a".repeat(32)]).toBe("save on leave");
        });
    });

    describe("message visibility and empty bubble prevention", () => {
        const makeChatItem = (overrides = {}) => ({
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message: {
                hash: `hash-${Math.random().toString(36).slice(2, 10)}`,
                state: "delivered",
                content: "",
                destination_hash: "my-hash",
                source_hash: "test-hash",
                fields: {},
                timestamp: 1700000000,
                created_at: "2023-11-14T22:13:20.000Z",
                ...overrides,
            },
        });

        describe("hasRenderableContent", () => {
            it("returns true for message with text content", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "hello", fields: {} })).toBe(true);
            });

            it("returns true for whitespace-padded text", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "  hi  ", fields: {} })).toBe(true);
            });

            it("returns false for empty string content and no fields", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "", fields: {} })).toBe(false);
            });

            it("returns false for whitespace-only content and no fields", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "   ", fields: {} })).toBe(false);
            });

            it("returns false for null content and no fields", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: null, fields: {} })).toBe(false);
            });

            it("returns false for undefined content and no fields", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ fields: {} })).toBe(false);
            });

            it("returns false for undefined fields", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "" })).toBe(false);
            });

            it("returns false for null fields", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "", fields: null })).toBe(false);
            });

            it("returns true for image field", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "", fields: { image: { image_type: "png" } } })).toBe(
                    true
                );
            });

            it("returns true for audio field", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "", fields: { audio: { audio_mode: 0x10 } } })).toBe(
                    true
                );
            });

            it("returns true for file attachments", () => {
                const wrapper = mountConversationViewer();
                expect(
                    wrapper.vm.hasRenderableContent({
                        content: "",
                        fields: { file_attachments: [{ file_name: "doc.pdf" }] },
                    })
                ).toBe(true);
            });

            it("returns true for telemetry", () => {
                const wrapper = mountConversationViewer();
                expect(
                    wrapper.vm.hasRenderableContent({
                        content: "",
                        fields: { telemetry: { location: { latitude: 0, longitude: 0 } } },
                    })
                ).toBe(true);
            });

            it("returns true for telemetry stream", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "", fields: { telemetry_stream: [{}] } })).toBe(true);
            });

            it("returns true for location request command", () => {
                const wrapper = mountConversationViewer();
                expect(
                    wrapper.vm.hasRenderableContent({
                        content: "",
                        fields: { commands: [{ "0x01": true }] },
                    })
                ).toBe(true);
            });

            it("returns true for location request via string key '1'", () => {
                const wrapper = mountConversationViewer();
                expect(
                    wrapper.vm.hasRenderableContent({
                        content: "",
                        fields: { commands: [{ 1: true }] },
                    })
                ).toBe(true);
            });

            it("returns false for commands with no location request", () => {
                const wrapper = mountConversationViewer();
                expect(
                    wrapper.vm.hasRenderableContent({
                        content: "",
                        fields: { commands: [{ "0x99": true }] },
                    })
                ).toBe(false);
            });

            it("returns false for empty commands array", () => {
                const wrapper = mountConversationViewer();
                expect(wrapper.vm.hasRenderableContent({ content: "", fields: { commands: [] } })).toBe(false);
            });

            it("returns false for unknown/unsupported fields only", () => {
                const wrapper = mountConversationViewer();
                expect(
                    wrapper.vm.hasRenderableContent({
                        content: "",
                        fields: { some_future_field: { data: 42 }, another_unknown: "value" },
                    })
                ).toBe(false);
            });
        });

        describe("isImageOnlyMessage", () => {
            it("returns true for image with no text", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({ fields: { image: { image_type: "png" } } });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(true);
            });

            it("returns true for image with null content", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({ content: null, fields: { image: { image_type: "jpg" } } });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(true);
            });

            it("returns true for image with whitespace-only content", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({ content: "   ", fields: { image: { image_type: "png" } } });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(true);
            });

            it("returns true for image with auto-generated filename caption", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "photo_2024.jpg",
                    fields: { image: { image_type: "jpg" } },
                });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(true);
            });

            it("returns false for image with real text caption", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "Look at this sunset!",
                    fields: { image: { image_type: "jpg" } },
                });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("returns false for image with reply", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    reply_to_hash: "abc123",
                    fields: { image: { image_type: "png" } },
                });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("returns false for image + audio", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    fields: { image: { image_type: "png" }, audio: { audio_mode: 0x10 } },
                });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("returns false for image + file attachments", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    fields: {
                        image: { image_type: "png" },
                        file_attachments: [{ file_name: "data.csv" }],
                    },
                });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("returns false for image + telemetry", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    fields: {
                        image: { image_type: "png" },
                        telemetry: { location: { latitude: 1, longitude: 2 } },
                    },
                });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("returns false for image + telemetry stream", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    fields: { image: { image_type: "png" }, telemetry_stream: [{}] },
                });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("returns false for image + location request command", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    fields: { image: { image_type: "png" }, commands: [{ "0x01": true }] },
                });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("returns false when there is no image", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({ content: "just text", fields: {} });
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("returns true for outbound image-only", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    source_hash: "my-hash",
                    destination_hash: "test-hash",
                    fields: { image: { image_type: "png" } },
                });
                item.is_outbound = true;
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(true);
            });
        });

        describe("selectedPeerChatItems filtering", () => {
            it("filters out messages with no renderable content", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({ content: "visible" }),
                    makeChatItem({ content: "", fields: {} }),
                    makeChatItem({ content: "", fields: { some_unknown: true } }),
                ];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(1);
                expect(wrapper.vm.selectedPeerChatItems[0].lxmf_message.content).toBe("visible");
            });

            it("keeps image-only messages visible", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [makeChatItem({ fields: { image: { image_type: "png" } } })];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(1);
            });

            it("keeps audio-only messages visible", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [makeChatItem({ fields: { audio: { audio_mode: 0x10 } } })];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(1);
            });

            it("keeps telemetry messages visible when showTelemetryInChat is true", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.showTelemetryInChat = true;
                wrapper.vm.chatItems = [
                    makeChatItem({
                        fields: { telemetry: { location: { latitude: 0, longitude: 0 } } },
                    }),
                ];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(1);
            });

            it("filters out reactions", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [makeChatItem({ content: "reaction", is_reaction: true })];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(0);
            });

            it("filters out empty messages even if state is delivered", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({ content: "", fields: {}, state: "delivered" }),
                    makeChatItem({ content: null, fields: {}, state: "delivered" }),
                    makeChatItem({ content: "   ", fields: {}, state: "delivered" }),
                ];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(0);
            });

            it("filters out empty outbound messages", async () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "",
                    fields: {},
                    source_hash: "my-hash",
                    destination_hash: "test-hash",
                });
                item.is_outbound = true;
                wrapper.vm.chatItems = [item];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(0);
            });

            it("keeps file-only messages", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({
                        fields: { file_attachments: [{ file_name: "readme.txt" }] },
                    }),
                ];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(1);
            });

            it("handles mixed visible and invisible messages correctly", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({ content: "text message" }),
                    makeChatItem({ content: "", fields: {} }),
                    makeChatItem({ fields: { image: { image_type: "png" } } }),
                    makeChatItem({ content: "", fields: { weird_field: true } }),
                    makeChatItem({ fields: { audio: { audio_mode: 0x10 } } }),
                    makeChatItem({ content: "", fields: {} }),
                ];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(3);
            });
        });

        describe("image strip grouping", () => {
            it("groups 2+ consecutive image-only messages from same sender into imageGroup", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({ hash: "img1", fields: { image: { image_type: "png" } } }),
                    makeChatItem({ hash: "img2", fields: { image: { image_type: "jpg" } } }),
                ];
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                expect(groups).toHaveLength(1);
                expect(groups[0].type).toBe("imageGroup");
                expect(groups[0].items).toHaveLength(2);
            });

            it("does not group a single image-only message", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [makeChatItem({ hash: "solo-img", fields: { image: { image_type: "png" } } })];
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                expect(groups).toHaveLength(1);
                expect(groups[0].type).toBe("single");
            });

            it("does not merge images with real captions into strip", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({
                        hash: "captioned1",
                        content: "Beautiful landscape",
                        fields: { image: { image_type: "png" } },
                    }),
                    makeChatItem({
                        hash: "captioned2",
                        content: "Another beautiful shot",
                        fields: { image: { image_type: "png" } },
                    }),
                ];
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                expect(groups).toHaveLength(2);
                expect(groups.every((g) => g.type === "single")).toBe(true);
            });

            it("groups images with filename captions into strip", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({
                        hash: "fn1",
                        content: "photo_001.jpg",
                        fields: { image: { image_type: "jpg" } },
                    }),
                    makeChatItem({
                        hash: "fn2",
                        content: "photo_002.png",
                        fields: { image: { image_type: "png" } },
                    }),
                ];
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                expect(groups).toHaveLength(1);
                expect(groups[0].type).toBe("imageGroup");
            });

            it("does not merge images from different senders", async () => {
                const wrapper = mountConversationViewer();
                const inbound = makeChatItem({
                    hash: "in-img",
                    fields: { image: { image_type: "png" } },
                });
                inbound.is_outbound = false;
                const outbound = makeChatItem({
                    hash: "out-img",
                    source_hash: "my-hash",
                    destination_hash: "test-hash",
                    fields: { image: { image_type: "png" } },
                });
                outbound.is_outbound = true;
                wrapper.vm.chatItems = [inbound, outbound];
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                expect(groups).toHaveLength(2);
                expect(groups.every((g) => g.type === "single")).toBe(true);
            });

            it("does not merge failed images into strip", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({
                        hash: "fail-img",
                        state: "failed",
                        fields: { image: { image_type: "png" } },
                    }),
                    makeChatItem({
                        hash: "ok-img",
                        fields: { image: { image_type: "png" } },
                    }),
                ];
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                expect(groups).toHaveLength(2);
                expect(groups.every((g) => g.type === "single")).toBe(true);
            });

            it("does not merge spam images into strip", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({
                        hash: "spam-img",
                        is_spam: true,
                        fields: { image: { image_type: "png" } },
                    }),
                    makeChatItem({ hash: "ok-img2", fields: { image: { image_type: "png" } } }),
                ];
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                expect(groups).toHaveLength(2);
            });

            it("does not merge image with reply into strip", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({
                        hash: "reply-img",
                        reply_to_hash: "some-hash",
                        fields: { image: { image_type: "png" } },
                    }),
                    makeChatItem({ hash: "plain-img", fields: { image: { image_type: "png" } } }),
                ];
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                expect(groups).toHaveLength(2);
            });

            it("caps image strip at 12 images", async () => {
                const wrapper = mountConversationViewer();
                const items = [];
                for (let i = 0; i < 15; i++) {
                    items.push(makeChatItem({ hash: `strip-${i}`, fields: { image: { image_type: "png" } } }));
                }
                wrapper.vm.chatItems = items;
                await wrapper.vm.$nextTick();

                const groups = wrapper.vm.selectedPeerChatDisplayGroups;
                const imgGroup = groups.find((g) => g.type === "imageGroup");
                expect(imgGroup).toBeDefined();
                expect(imgGroup.items.length).toBeLessThanOrEqual(12);
            });
        });

        describe("isLikelyMultiImagePlaceholderCaption", () => {
            let wrapper;
            beforeEach(() => {
                wrapper = mountConversationViewer();
            });

            it("recognizes standard image filenames", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("photo.jpg")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("IMG_20240101.png")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("screenshot.webp")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("image.heic")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("cat.gif")).toBe(true);
            });

            it("rejects non-image filenames", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("document.pdf")).toBe(false);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("video.mp4")).toBe(false);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("archive.zip")).toBe(false);
            });

            it("rejects normal text messages", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("hello world")).toBe(false);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("check out this image")).toBe(false);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("I sent you a .png file")).toBe(false);
            });

            it("rejects multiline text", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("photo.jpg\nmore text")).toBe(false);
            });

            it("rejects text with path separators", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("/home/user/photo.jpg")).toBe(false);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("C:\\Users\\photo.jpg")).toBe(false);
            });

            it("rejects text with special characters", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("<script>photo.jpg")).toBe(false);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("[photo].jpg")).toBe(false);
            });

            it("rejects null or empty", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption(null)).toBe(false);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("")).toBe(false);
            });

            it("rejects very long strings", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("a".repeat(250) + ".png")).toBe(false);
            });

            it("handles edge case extensions", () => {
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("photo.jpeg")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("photo.JPEG")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("photo.PNG")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("photo.avif")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("photo.svg")).toBe(true);
                expect(wrapper.vm.isLikelyMultiImagePlaceholderCaption("photo.bmp")).toBe(true);
            });
        });

        describe("shouldHideAutoImageCaption", () => {
            it("hides filename caption on image message", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "photo_2024.jpg",
                    fields: { image: { image_type: "jpg" } },
                });
                expect(wrapper.vm.shouldHideAutoImageCaption(item)).toBe(true);
            });

            it("does not hide real text on image message", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "Here is the picture from yesterday",
                    fields: { image: { image_type: "jpg" } },
                });
                expect(wrapper.vm.shouldHideAutoImageCaption(item)).toBe(false);
            });

            it("does not hide anything on non-image message", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({ content: "photo.jpg", fields: {} });
                expect(wrapper.vm.shouldHideAutoImageCaption(item)).toBe(false);
            });

            it("does not hide empty content", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "",
                    fields: { image: { image_type: "png" } },
                });
                expect(wrapper.vm.shouldHideAutoImageCaption(item)).toBe(false);
            });
        });

        describe("edge cases with multiple field combinations", () => {
            it("image + text shows bubble (not image-only)", async () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "Check this out",
                    fields: { image: { image_type: "png" } },
                });
                wrapper.vm.chatItems = [item];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(1);
                expect(wrapper.vm.isImageOnlyMessage(wrapper.vm.selectedPeerChatItems[0])).toBe(false);
            });

            it("audio + text renders and is not image-only", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "Listen to this",
                    fields: { audio: { audio_mode: 0x10 } },
                });
                expect(wrapper.vm.hasRenderableContent(item.lxmf_message)).toBe(true);
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("file attachment with no text still shows", () => {
                const wrapper = mountConversationViewer();
                const msg = { content: "", fields: { file_attachments: [{ file_name: "a.zip" }] } };
                expect(wrapper.vm.hasRenderableContent(msg)).toBe(true);
            });

            it("telemetry with text still shows", () => {
                const wrapper = mountConversationViewer();
                const msg = {
                    content: "My location",
                    fields: { telemetry: { location: { latitude: 0, longitude: 0 } } },
                };
                expect(wrapper.vm.hasRenderableContent(msg)).toBe(true);
            });

            it("image + audio + text is renderable but not image-only", () => {
                const wrapper = mountConversationViewer();
                const item = makeChatItem({
                    content: "multimedia",
                    fields: {
                        image: { image_type: "png" },
                        audio: { audio_mode: 0x10 },
                    },
                });
                expect(wrapper.vm.hasRenderableContent(item.lxmf_message)).toBe(true);
                expect(wrapper.vm.isImageOnlyMessage(item)).toBe(false);
            });

            it("message with only unknown future fields is hidden", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({
                        content: "",
                        fields: { future_feature: { data: "something" } },
                    }),
                ];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(0);
            });

            it("message with multiple unknown fields is hidden", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [
                    makeChatItem({
                        content: "",
                        fields: {
                            sticker: { pack: "animals", id: 3 },
                            icon_appearance: { theme: "dark" },
                        },
                    }),
                ];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(0);
            });

            it("message with empty fields object is hidden", async () => {
                const wrapper = mountConversationViewer();
                wrapper.vm.chatItems = [makeChatItem({ content: "", fields: {} })];
                await wrapper.vm.$nextTick();

                expect(wrapper.vm.selectedPeerChatItems).toHaveLength(0);
            });
        });
    });
});
