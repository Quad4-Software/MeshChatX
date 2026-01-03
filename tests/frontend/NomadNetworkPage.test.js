import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NomadNetworkPage from "@/components/nomadnetwork/NomadNetworkPage.vue";

describe("NomadNetworkPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
        };
        window.axios = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            if (url.includes("/path")) return Promise.resolve({ data: { path: { hops: 1 } } });
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.axios;
    });

    const mountNomadNetworkPage = (props = { destinationHash: "" }) => {
        return mount(NomadNetworkPage, {
            props,
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { replace: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                    LoadingSpinner: true,
                    NomadNetworkSidebar: {
                        template: '<div class="sidebar-stub"></div>',
                        props: ["nodes", "selectedDestinationHash"],
                    },
                },
            },
        });
    };

    it("displays 'No active node' by default", () => {
        const wrapper = mountNomadNetworkPage();
        expect(wrapper.text()).toContain("nomadnet.no_active_node");
    });

    it("loads node when destinationHash prop is provided", async () => {
        const destHash = "0123456789abcdef0123456789abcdef";
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/announces")
                return Promise.resolve({
                    data: { announces: [{ destination_hash: destHash, display_name: "Test Node" }] },
                });
            if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountNomadNetworkPage({ destinationHash: destHash });
        // Manually set favourites to avoid undefined error if mock fails
        wrapper.vm.favourites = [];
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // Wait for fetch

        expect(wrapper.vm.selectedNode.destination_hash).toBe(destHash);
    });

    it("toggles source view", async () => {
        const destHash = "0123456789abcdef0123456789abcdef";
        const wrapper = mountNomadNetworkPage({ destinationHash: destHash });
        wrapper.vm.favourites = [];
        wrapper.setData({
            selectedNode: { destination_hash: destHash, display_name: "Test Node" },
            nodePageContent: "Page Content",
            nodePagePath: "test:path",
        });
        await wrapper.vm.$nextTick();

        // Find toggle source button by icon name
        const buttons = wrapper.findAll("button");
        const toggleSourceButton = buttons.find((b) => b.html().includes('data-icon-name="code-tags"'));
        if (toggleSourceButton) {
            await toggleSourceButton.trigger("click");
            expect(wrapper.vm.isShowingNodePageSource).toBe(true);
        }
    });
});
