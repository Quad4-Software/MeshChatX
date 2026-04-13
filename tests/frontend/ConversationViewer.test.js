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
        GlobalState.config.message_outbound_bubble_color = "#4f46e5";
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
});
