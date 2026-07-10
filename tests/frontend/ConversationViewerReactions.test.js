import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalState from "@/js/GlobalState";
import ToastUtils from "@/js/ToastUtils";

describe("ConversationViewer reactions", () => {
    let axiosMock;

    beforeEach(() => {
        GlobalState.config.theme = "light";
        GlobalState.config.message_outbound_bubble_color = "#4f46e5";
        GlobalState.config.message_waiting_bubble_color = "#e5e7eb";
        WebSocketConnection.connect();
        axiosMock = {
            get: vi.fn().mockResolvedValue({ data: {} }),
            post: vi.fn().mockResolvedValue({
                data: {
                    lxmf_message: {
                        hash: "reaction-hash",
                        is_reaction: true,
                        reaction_to: "msg-hash",
                        reaction_emoji: "\u{1F44D}",
                        reaction_sender: "my-hash",
                        source_hash: "my-hash",
                        destination_hash: "test-hash",
                    },
                },
            }),
        };
        window.api = axiosMock;
        vi.spyOn(ToastUtils, "error").mockImplementation(() => {});
        vi.spyOn(console, "error").mockImplementation(() => {});
    });

    afterEach(() => {
        delete window.api;
        WebSocketConnection.destroy();
        vi.restoreAllMocks();
    });

    const mountViewer = (props = {}) =>
        mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: "test-hash", display_name: "Test Peer" },
                myLxmfAddressHash: "my-hash",
                conversations: [],
                ...props,
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: true,
                    AddImageButton: true,
                    AddAudioButton: true,
                    SendMessageButton: true,
                    ConversationDropDownMenu: true,
                    PaperMessageModal: true,
                    AudioWaveformPlayer: true,
                    LxmfUserIcon: true,
                    "emoji-picker": true,
                },
            },
        });

    const parentChatItem = () => ({
        type: "lxmf_message",
        is_outbound: false,
        lxmf_message: {
            hash: "msg-hash",
            content: "hello",
            source_hash: "test-hash",
            destination_hash: "my-hash",
            reactions: [],
        },
    });

    it("sends a reaction and optimistically attaches it to the parent", async () => {
        const wrapper = mountViewer();
        const chatItem = parentChatItem();
        wrapper.vm.chatItems = [chatItem];

        await wrapper.vm.sendReactionEmojiFromMenu(chatItem, "\u{1F44D}");
        await flushPromises();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/lxmf-messages/reactions", {
            destination_hash: "test-hash",
            target_message_hash: "msg-hash",
            emoji: "\u{1F44D}",
        });
        expect(chatItem.lxmf_message.reactions).toHaveLength(1);
        expect(chatItem.lxmf_message.reactions[0]).toMatchObject({
            emoji: "\u{1F44D}",
            sender: "my-hash",
            reactionHash: "reaction-hash",
        });
        wrapper.unmount();
    });

    it("toasts and does not crash when reaction API fails", async () => {
        axiosMock.post.mockRejectedValueOnce({ response: { data: { message: "No path" } } });
        const wrapper = mountViewer();
        const chatItem = parentChatItem();
        wrapper.vm.chatItems = [chatItem];

        await wrapper.vm.sendReactionEmojiFromMenu(chatItem, "\u{1F44D}");
        await flushPromises();

        expect(ToastUtils.error).toHaveBeenCalledWith("messages.reaction_send_failed");
        expect(chatItem.lxmf_message.reactions).toHaveLength(0);
        wrapper.unmount();
    });

    it("ignores null/invalid chatItem and emoji without throwing", async () => {
        const wrapper = mountViewer();
        await flushPromises();
        axiosMock.post.mockClear();
        await expect(wrapper.vm.sendReactionEmojiFromMenu(null, "\u{1F44D}")).resolves.toBeUndefined();
        await expect(wrapper.vm.sendReactionEmojiFromMenu({ lxmf_message: {} }, "")).resolves.toBeUndefined();
        await expect(wrapper.vm.sendReactionEmojiFromMenu(parentChatItem(), null)).resolves.toBeUndefined();
        const reactionPosts = axiosMock.post.mock.calls.filter(
            (c) => typeof c[0] === "string" && c[0].includes("/lxmf-messages/reactions")
        );
        expect(reactionPosts).toHaveLength(0);
        wrapper.unmount();
    });

    it("dedupes concurrent double-taps of the same reaction (Android race)", async () => {
        let resolvePost;
        axiosMock.post.mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolvePost = resolve;
                })
        );
        const wrapper = mountViewer();
        const chatItem = parentChatItem();
        wrapper.vm.chatItems = [chatItem];

        const p1 = wrapper.vm.sendReactionEmojiFromMenu(chatItem, "\u{1F44D}");
        const p2 = wrapper.vm.sendReactionEmojiFromMenu(chatItem, "\u{1F44D}");
        expect(axiosMock.post).toHaveBeenCalledTimes(1);

        resolvePost({
            data: {
                lxmf_message: {
                    hash: "reaction-hash",
                    is_reaction: true,
                    reaction_to: "msg-hash",
                    reaction_emoji: "\u{1F44D}",
                    reaction_sender: "my-hash",
                    source_hash: "my-hash",
                },
            },
        });
        await Promise.all([p1, p2]);
        await flushPromises();

        expect(chatItem.lxmf_message.reactions).toHaveLength(1);
        wrapper.unmount();
    });

    it("applyIncomingReaction merges case-insensitively and upgrades null reactionHash", async () => {
        const wrapper = mountViewer();
        const chatItem = parentChatItem();
        chatItem.lxmf_message.hash = "AaBbCcDdEeFf00112233445566778899";
        chatItem.lxmf_message.reactions = [{ emoji: "\u{1F44D}", sender: "My-Hash", reactionHash: null }];
        wrapper.vm.chatItems = [chatItem];

        wrapper.vm.applyIncomingReaction({
            hash: "server-reaction",
            is_reaction: true,
            reaction_to: "aabbccddeeff00112233445566778899",
            reaction_emoji: "\u{1F44D}",
            reaction_sender: "my-hash",
            source_hash: "my-hash",
        });

        expect(chatItem.lxmf_message.reactions).toHaveLength(1);
        expect(chatItem.lxmf_message.reactions[0].reactionHash).toBe("server-reaction");
        wrapper.unmount();
    });

    it("applyIncomingReaction tolerates malformed payloads", async () => {
        const wrapper = mountViewer();
        wrapper.vm.chatItems = [parentChatItem()];
        expect(() => wrapper.vm.applyIncomingReaction(null)).not.toThrow();
        expect(() => wrapper.vm.applyIncomingReaction({})).not.toThrow();
        expect(() => wrapper.vm.applyIncomingReaction({ reaction_to: "missing", reaction_emoji: "x" })).not.toThrow();
        expect(() =>
            wrapper.vm.applyIncomingReaction({
                reaction_to: "msg-hash",
                reaction_emoji: 123,
                source_hash: "peer",
            })
        ).not.toThrow();
        expect(wrapper.vm.chatItems[0].lxmf_message.reactions).toHaveLength(0);
        wrapper.unmount();
    });

    it("onLxmfMessageCreated applies outbound reactions instead of inserting a bubble", async () => {
        const wrapper = mountViewer();
        const chatItem = parentChatItem();
        wrapper.vm.chatItems = [chatItem];

        wrapper.vm.onLxmfMessageCreated({
            hash: "out-reaction",
            destination_hash: "test-hash",
            source_hash: "my-hash",
            is_reaction: true,
            reaction_to: "msg-hash",
            reaction_emoji: "\u2764\uFE0F",
            reaction_sender: "my-hash",
        });

        expect(wrapper.vm.chatItems).toHaveLength(1);
        expect(chatItem.lxmf_message.reactions).toHaveLength(1);
        expect(chatItem.lxmf_message.reactions[0].emoji).toBe("\u2764\uFE0F");
        wrapper.unmount();
    });

    it("does not crash when Android touchcancel fires after picker close mid-drag", async () => {
        const wrapper = mountViewer();
        const chatItem = parentChatItem();
        wrapper.vm.chatItems = [chatItem];
        wrapper.vm.openReactionPicker(chatItem);
        await wrapper.vm.$nextTick();

        const panel = document.createElement("div");
        panel.getBoundingClientRect = () => ({
            left: 10,
            top: 20,
            width: 200,
            height: 300,
            right: 210,
            bottom: 320,
        });
        wrapper.vm.$refs.reactionPickerPanel = panel;

        wrapper.vm.onReactionPickerDragStart({
            touches: [{ clientX: 15, clientY: 25 }],
            preventDefault: vi.fn(),
        });
        expect(wrapper.vm.reactionDragState).not.toBeNull();

        // Closing the picker (or Android touchcancel) must remove listeners safely.
        wrapper.vm.closeReactionPicker();
        expect(wrapper.vm.reactionDragState).toBeNull();

        expect(() => {
            document.dispatchEvent(new Event("touchmove"));
            document.dispatchEvent(new Event("touchcancel"));
            document.dispatchEvent(new Event("touchend"));
            document.dispatchEvent(new Event("mousemove"));
        }).not.toThrow();

        wrapper.unmount();
    });

    it("cleans up reaction drag listeners on unmount", async () => {
        const wrapper = mountViewer();
        wrapper.vm.openReactionPicker(parentChatItem());
        await wrapper.vm.$nextTick();
        const panel = document.createElement("div");
        panel.getBoundingClientRect = () => ({
            left: 0,
            top: 0,
            width: 100,
            height: 100,
            right: 100,
            bottom: 100,
        });
        wrapper.vm.$refs.reactionPickerPanel = panel;
        wrapper.vm.onReactionPickerDragStart({ clientX: 1, clientY: 2 });
        expect(typeof wrapper.vm.reactionDragCleanup).toBe("function");
        wrapper.unmount();
        expect(() => {
            document.dispatchEvent(new Event("touchmove"));
            document.dispatchEvent(new Event("touchend"));
        }).not.toThrow();
    });

    it("reactionReactorLabel never throws on bad sender values", async () => {
        const wrapper = mountViewer();
        expect(wrapper.vm.reactionReactorLabel(null)).toBe("");
        expect(wrapper.vm.reactionReactorLabel(undefined)).toBe("");
        expect(wrapper.vm.reactionReactorLabel(12)).toContain("<");
        expect(wrapper.vm.reactionReactorLabel("my-hash")).toBe("messages.reaction_you");
        wrapper.unmount();
    });

    it("emoji click closes picker and sends without throwing when detail is missing", async () => {
        const wrapper = mountViewer();
        wrapper.vm.openReactionPicker(parentChatItem());
        expect(() => wrapper.vm.onReactionPickerEmojiClick({})).not.toThrow();
        expect(() => wrapper.vm.onReactionPickerEmojiClick({ detail: {} })).not.toThrow();
        // Malformed picker events leave the picker open so the user can try again.
        expect(wrapper.vm.reactionPickerChatItem).not.toBeNull();
        expect(() => wrapper.vm.onReactionPickerEmojiClick({ detail: { unicode: "\u{1F44D}" } })).not.toThrow();
        expect(wrapper.vm.reactionPickerChatItem).toBeNull();
        await flushPromises();
        wrapper.unmount();
    });
});
