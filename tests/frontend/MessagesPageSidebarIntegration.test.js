import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MessagesPage from "@/components/messages/MessagesPage.vue";

vi.mock("@/js/GlobalState", async (importOriginal) => {
    const mod = await importOriginal();
    return {
        ...mod,
        default: {
            ...mod.default,
            blockedDestinations: [],
            config: {
                ...mod.default.config,
                banished_effect_enabled: false,
                telemetry_enabled: false,
            },
        },
    };
});

vi.mock("@/js/Utils", () => ({
    default: {
        formatTimeAgo: vi.fn(() => "1h ago"),
        formatDestinationHash: (h) => (h && h.length >= 8 ? h.slice(0, 8) + "…" : h),
    },
}));

const ConversationViewerStub = {
    name: "ConversationViewer",
    template: "<div class=\"cv-stub\"></div>",
    methods: {
        markConversationAsRead: vi.fn(),
    },
};

describe("MessagesPage with MessagesSidebar integration", () => {
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
            if (url === "/api/v1/lxmf/conversations")
                return Promise.resolve({ data: { conversations: [] } });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            if (url === "/api/v1/lxmf/conversation-pins")
                return Promise.resolve({ data: { peer_hashes: [] } });
            if (url === "/api/v1/lxmf/folders") return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
    });

    it("renders live MessagesSidebar and switches to Announces tab", async () => {
        const wrapper = mount(MessagesPage, {
            props: { destinationHash: "" },
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { replace: vi.fn() },
                },
                stubs: {
                    ConversationViewer: ConversationViewerStub,
                    MaterialDesignIcon: { template: '<div class="mdi-stub"><slot /></div>' },
                },
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.text()).toContain("messages.conversations");

        const tabs = wrapper.findAll("div.flex.w-full.cursor-pointer.border-b-2");
        expect(tabs.length).toBeGreaterThanOrEqual(2);
        await tabs[1].trigger("click");
        await wrapper.vm.$nextTick();

        const sidebar = wrapper.findComponent({ name: "MessagesSidebar" });
        expect(sidebar.vm.tab).toBe("announces");
    });

    it("selects peer from sidebar conversation row and updates MessagesPage selectedPeer", async () => {
        const destHash = "0123456789abcdef0123456789abcdef";
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            if (url === "/api/v1/lxmf/conversations")
                return Promise.resolve({
                    data: {
                        conversations: [
                            {
                                destination_hash: destHash,
                                display_name: "Integration Peer",
                                updated_at: new Date().toISOString(),
                                is_unread: false,
                                failed_messages_count: 0,
                            },
                        ],
                    },
                });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            if (url === "/api/v1/lxmf/conversation-pins")
                return Promise.resolve({ data: { peer_hashes: [] } });
            if (url === "/api/v1/lxmf/folders") return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mount(MessagesPage, {
            props: { destinationHash: "" },
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { replace: vi.fn() },
                },
                stubs: {
                    ConversationViewer: ConversationViewerStub,
                    MaterialDesignIcon: { template: '<div class="mdi-stub"><slot /></div>' },
                },
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const row = wrapper.find(".conversation-item");
        expect(row.exists()).toBe(true);
        await row.trigger("click");
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.selectedPeer).toMatchObject({
            destination_hash: destHash,
            display_name: "Integration Peer",
        });
    });
});
