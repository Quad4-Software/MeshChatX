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
        window.axios = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            if (url === "/api/v1/lxmf/conversations") return Promise.resolve({ data: { conversations: [] } });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.axios;
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
});
