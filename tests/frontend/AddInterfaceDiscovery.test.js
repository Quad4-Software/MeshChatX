import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AddInterfacePage from "../../meshchatx/src/frontend/components/interfaces/AddInterfacePage.vue";

// mocks
const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
};
window.api = mockAxios;

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

describe("AddInterfacePage.vue discovery", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAxios.get.mockResolvedValue({ data: {} });
        mockAxios.post.mockResolvedValue({ data: { message: "ok" } });
    });

    it("adds discovery fields when interface is discoverable", async () => {
        const wrapper = mount(AddInterfacePage, {
            global: {
                mocks: {
                    $route: { query: {} },
                    $router: { push: vi.fn() },
                    $t: (msg) => msg,
                },
                stubs: ["RouterLink", "MaterialDesignIcon", "Toggle", "ExpandingSection", "FormLabel", "FormSubLabel"],
            },
        });

        // required interface fields
        wrapper.vm.newInterfaceName = "TestIface";
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        wrapper.vm.newInterfaceTargetHost = "example.com";
        wrapper.vm.newInterfaceTargetPort = "4242";

        wrapper.vm.discovery.discoverable = true;
        wrapper.vm.discovery.discovery_name = "Region A";
        wrapper.vm.discovery.announce_interval = 720;
        wrapper.vm.discovery.reachable_on = "/usr/local/bin/ip.sh";

        await wrapper.vm.saveInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                discoverable: "yes",
                discovery_name: "Region A",
                announce_interval: 720,
                reachable_on: "/usr/local/bin/ip.sh",
            })
        );
    });
});
