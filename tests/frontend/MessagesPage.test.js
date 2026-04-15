import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MessagesPage from "@/components/messages/MessagesPage.vue";

describe("MessagesPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            if (url === "/api/v1/lxmf/conversations") return Promise.resolve({ data: { conversations: [] } });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
    });

    const mountMessagesPage = (props = { destinationHash: "" }) => {
        return mount(MessagesPage, {
            props,
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { replace: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    LoadingSpinner: true,
                    MessagesSidebar: {
                        template: '<div class="sidebar-stub"></div>',
                        props: ["conversations", "selectedDestinationHash"],
                    },
                    ConversationViewer: {
                        template: '<div class="viewer-stub"></div>',
                        props: ["selectedPeer", "myLxmfAddressHash"],
                    },
                    Modal: true,
                },
            },
        });
    };

    it("fetches config and conversations on mount", async () => {
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/config");
        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/lxmf/conversations", expect.any(Object));
    });

    it("debounces conversation search and sends search param to conversations API", async () => {
        vi.useFakeTimers();
        axiosMock.isCancel = vi.fn(() => false);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();
        axiosMock.get.mockClear();

        wrapper.vm.onConversationSearchChanged("findme");
        await vi.advanceTimersByTimeAsync(100);
        expect(axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/lxmf/conversations")).toHaveLength(0);

        await vi.advanceTimersByTimeAsync(200);
        const convCalls = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/lxmf/conversations");
        expect(convCalls.length).toBeGreaterThanOrEqual(1);
        expect(convCalls[convCalls.length - 1][1].params.search).toBe("findme");
        vi.useRealTimers();
    });

    it("debounces peers search and sends search param to announces API", async () => {
        vi.useFakeTimers();
        axiosMock.isCancel = vi.fn(() => false);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();
        axiosMock.get.mockClear();

        wrapper.vm.onPeersSearchChanged("peerq");
        await vi.advanceTimersByTimeAsync(400);
        expect(
            axiosMock.get.mock.calls.filter(
                (c) => c[0] === "/api/v1/announces" && c[1]?.params?.aspect === "lxmf.delivery"
            )
        ).toHaveLength(0);

        await vi.advanceTimersByTimeAsync(200);
        const ann = axiosMock.get.mock.calls.filter(
            (c) => c[0] === "/api/v1/announces" && c[1]?.params?.aspect === "lxmf.delivery"
        );
        expect(ann.length).toBeGreaterThanOrEqual(1);
        expect(ann[ann.length - 1][1].params.search).toBe("peerq");
        vi.useRealTimers();
    });

    it("opens ingest paper message modal", async () => {
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        // Find button to ingest paper message
        const buttons = wrapper.findAll("button");
        const ingestButton = buttons.find((b) => b.html().includes('icon-name="note-plus"'));
        if (ingestButton) {
            await ingestButton.trigger("click");
            expect(wrapper.vm.isShowingIngestPaperMessageModal).toBe(true);
        }
    });

    it("composes new message when destinationHash prop is provided", async () => {
        const destHash = "0123456789abcdef0123456789abcdef";
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/announces")
                return Promise.resolve({
                    data: { announces: [{ destination_hash: destHash, display_name: "Test Peer" }] },
                });
            if (url === "/api/v1/lxmf/conversations") return Promise.resolve({ data: { conversations: [] } });
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountMessagesPage({ destinationHash: destHash });
        // Ensure conversations is initialized as array to avoid filter error in watcher
        wrapper.vm.conversations = [];
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // Wait for fetch

        expect(wrapper.vm.selectedPeer.destination_hash).toBe(destHash);
    });

    it("routes to compose when ingest result is lxma contact", async () => {
        const wrapper = mountMessagesPage();
        const composeSpy = vi.spyOn(wrapper.vm, "onComposeNewMessage").mockResolvedValue(undefined);

        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "lxm.ingest_uri.result",
                status: "success",
                ingest_type: "lxma_contact",
                destination_hash: "f".repeat(32),
            }),
        });

        expect(composeSpy).toHaveBeenCalledWith("f".repeat(32));
    });

    it("updates existing conversation in-place without API call on lxmf_message_created", async () => {
        const destHash = "a".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.conversations = [
            {
                destination_hash: destHash,
                display_name: "Test Peer",
                latest_message_preview: "old msg",
                updated_at: "2025-01-01T00:00:00Z",
            },
        ];

        axiosMock.get.mockClear();

        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "lxmf_message_created",
                lxmf_message: {
                    hash: "abc",
                    source_hash: "my-hash",
                    destination_hash: destHash,
                    is_incoming: false,
                    content: "new msg",
                    title: "",
                    timestamp: 1700000000,
                },
            }),
        });

        expect(wrapper.vm.conversations[0].latest_message_preview).toBe("new msg");
        const convCalls = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/lxmf/conversations");
        expect(convCalls).toHaveLength(0);
    });

    it("resolves display name for new conversation only", async () => {
        const destHash = "d".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.conversations = [];
        wrapper.vm.selectedPeer = { destination_hash: destHash, display_name: "Anonymous Peer" };

        axiosMock.get.mockClear();
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/lxmf/conversations")
                return Promise.resolve({
                    data: {
                        conversations: [
                            {
                                destination_hash: destHash,
                                display_name: "Resolved Name",
                                custom_display_name: null,
                            },
                        ],
                    },
                });
            return Promise.resolve({ data: {} });
        });

        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "lxmf_message_created",
                lxmf_message: {
                    hash: "new1",
                    source_hash: "my-hash",
                    destination_hash: destHash,
                    is_incoming: false,
                    content: "hello",
                    title: "",
                    timestamp: 1700000000,
                },
            }),
        });

        await wrapper.vm.$nextTick();
        expect(wrapper.vm.conversations[0].display_name).toBe("Resolved Name");
        expect(wrapper.vm.selectedPeer.display_name).toBe("Resolved Name");

        const convCalls = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/lxmf/conversations");
        expect(convCalls).toHaveLength(1);
        expect(convCalls[0][1].params.search).toBe(destHash);
        expect(convCalls[0][1].params.limit).toBe(1);
    });

    it("updates failed_messages_count on state transition to failed", async () => {
        const destHash = "e".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.conversations = [{ destination_hash: destHash, failed_messages_count: 0 }];

        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "lxmf_message_state_updated",
                lxmf_message: {
                    hash: "f1",
                    source_hash: "my-hash",
                    destination_hash: destHash,
                    is_incoming: false,
                    state: "failed",
                },
            }),
        });

        expect(wrapper.vm.conversations[0].failed_messages_count).toBe(1);
    });

    it("does not trigger API call on state updates", async () => {
        const destHash = "f".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.conversations = [{ destination_hash: destHash, failed_messages_count: 0 }];

        axiosMock.get.mockClear();

        for (const state of ["outbound", "sending", "sent", "delivered"]) {
            await wrapper.vm.onWebsocketMessage({
                data: JSON.stringify({
                    type: "lxmf_message_state_updated",
                    lxmf_message: {
                        hash: "s1",
                        source_hash: "my-hash",
                        destination_hash: destHash,
                        is_incoming: false,
                        state,
                    },
                }),
            });
        }

        const convCalls = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/lxmf/conversations");
        expect(convCalls).toHaveLength(0);
    });

    it("mutates existing conversation object without replacing array entry", async () => {
        const destHash = "a".repeat(32);
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        wrapper.vm.conversations = [
            {
                destination_hash: destHash,
                display_name: "Peer",
                latest_message_preview: "old",
                updated_at: "2025-01-01T00:00:00Z",
            },
        ];

        const lengthBefore = wrapper.vm.conversations.length;

        await wrapper.vm.onWebsocketMessage({
            data: JSON.stringify({
                type: "lxmf_message_created",
                lxmf_message: {
                    hash: "abc",
                    source_hash: "my-hash",
                    destination_hash: destHash,
                    is_incoming: false,
                    content: "new",
                    title: "",
                    timestamp: 1700000000,
                },
            }),
        });

        expect(wrapper.vm.conversations.length).toBe(lengthBefore);
        expect(wrapper.vm.conversations[0].latest_message_preview).toBe("new");
        expect(wrapper.vm.conversations[0].display_name).toBe("Peer");
    });

    it("uses conversation display name instead of Unknown Peer when composing", async () => {
        const destHash = "c".repeat(32);
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            if (url === "/api/v1/lxmf/conversations")
                return Promise.resolve({
                    data: {
                        conversations: [
                            {
                                destination_hash: destHash,
                                display_name: "Existing Peer",
                                custom_display_name: null,
                            },
                        ],
                    },
                });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountMessagesPage();
        wrapper.vm.conversations = [
            { destination_hash: destHash, display_name: "Existing Peer", custom_display_name: null },
        ];
        await wrapper.vm.$nextTick();

        await wrapper.vm.onComposeNewMessage(destHash);
        expect(wrapper.vm.selectedPeer.display_name).toBe("Existing Peer");
    });
});
