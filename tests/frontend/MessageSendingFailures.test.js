import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalState from "@/js/GlobalState";
import DialogUtils from "@/js/DialogUtils";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(() => Promise.resolve()),
    },
}));

describe("MessageSendingFailures.test.js", () => {
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
                if (url.includes("/lxmf-messages/conversation/"))
                    return Promise.resolve({ data: { lxmf_messages: [] } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockImplementation(() => Promise.resolve({ data: { lxmf_message: { hash: "mock" } } })),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;

        // Mock URL.createObjectURL
        window.URL.createObjectURL = vi.fn(() => "mock-url");
        vi.spyOn(window, "open").mockImplementation(() => null);
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

    it("handles API 503 failure when sending message", async () => {
        const wrapper = mountConversationViewer();
        wrapper.vm.newMessageText = "Hello failure";

        axiosMock.post.mockRejectedValueOnce({
            response: {
                status: 503,
                data: { message: "Sending failed" },
            },
        });

        await wrapper.vm.sendMessage();

        // Optimistic placeholder should be gone
        const pendingItems = wrapper.vm.chatItems.filter((item) => item.lxmf_message.hash.startsWith("pending-"));
        expect(pendingItems).toHaveLength(0);

        // Alert should be shown
        expect(DialogUtils.alert).toHaveBeenCalledWith("Sending failed");
    });

    it("updates UI when message state becomes failed via WebSocket", async () => {
        const wrapper = mountConversationViewer();
        const messageHash = "msg-123";

        // Add a message that is currently "sending"
        wrapper.vm.chatItems.push({
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: messageHash,
                content: "Going to fail",
                state: "sending",
                progress: 50,
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
            },
        });

        // Simulate WebSocket update
        wrapper.vm.onLxmfMessageUpdated({
            hash: messageHash,
            state: "failed",
            progress: 50,
        });

        const updatedItem = wrapper.vm.chatItems.find((i) => i.lxmf_message.hash === messageHash);
        expect(updatedItem.lxmf_message.state).toBe("failed");

        await wrapper.vm.$nextTick();
        // The retry button should be visible in the context menu if we were to open it
        // (Testing the logic of onLxmfMessageUpdated is enough here as retry logic is tested elsewhere)
    });

    it("handles second image failure in multi-image send", async () => {
        const wrapper = mountConversationViewer();
        wrapper.vm.newMessageText = "Two images";

        const image1 = new File([""], "image1.png", { type: "image/png" });
        const image2 = new File([""], "image2.png", { type: "image/png" });
        image1.arrayBuffer = vi.fn(() => Promise.resolve(new ArrayBuffer(8)));
        image2.arrayBuffer = vi.fn(() => Promise.resolve(new ArrayBuffer(8)));

        await wrapper.vm.onImageSelected(image1);
        await wrapper.vm.onImageSelected(image2);

        // First image succeeds, second fails
        axiosMock.post
            .mockResolvedValueOnce({
                data: { lxmf_message: { hash: "hash-1", content: "Two images", state: "outbound" } },
            })
            .mockRejectedValueOnce({ response: { data: { message: "Second image failed" } } });

        const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

        await wrapper.vm.sendMessage();

        // Both images should be processed, but second one logs an error
        const sendCalls = axiosMock.post.mock.calls.filter((c) => c[0] === "/api/v1/lxmf-messages/send");
        expect(sendCalls.length).toBe(2);
        expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining("Failed to send image 2"), expect.anything());

        consoleSpy.mockRestore();
    });

    it("removes placeholder even if buildOutboundJobSnapshot fails", async () => {
        const wrapper = mountConversationViewer();
        wrapper.vm.newMessageText = "Fail early";

        vi.spyOn(wrapper.vm, "buildOutboundJobSnapshot").mockRejectedValueOnce(new Error("Snapshot failed"));

        await wrapper.vm.sendMessage();

        expect(DialogUtils.alert).toHaveBeenCalledWith("Snapshot failed");
        expect(wrapper.vm.chatItems).toHaveLength(0);
    });

    it("retrying a failed message sends it again", async () => {
        const wrapper = mountConversationViewer();
        const failedItem = {
            type: "lxmf_message",
            is_outbound: true,
            lxmf_message: {
                hash: "failed-hash",
                state: "failed",
                content: "retry me",
                destination_hash: "test-hash",
                source_hash: "my-hash",
                fields: {},
            },
        };
        wrapper.vm.chatItems = [failedItem];

        axiosMock.post.mockResolvedValue({ data: { lxmf_message: { hash: "new-hash", state: "outbound" } } });

        await wrapper.vm.retrySendingMessage(failedItem);

        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/lxmf-messages/send",
            expect.objectContaining({
                lxmf_message: expect.objectContaining({
                    content: "retry me",
                    destination_hash: "test-hash",
                }),
            })
        );

        // Old item should be removed
        expect(wrapper.vm.chatItems.find((i) => i.lxmf_message.hash === "failed-hash")).toBeUndefined();
        // New item should be added
        expect(wrapper.vm.chatItems.find((i) => i.lxmf_message.hash === "new-hash")).toBeDefined();
    });
});
