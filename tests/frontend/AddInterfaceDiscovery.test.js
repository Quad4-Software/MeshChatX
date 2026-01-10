import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AddInterfacePage from "../../meshchatx/src/frontend/components/interfaces/AddInterfacePage.vue";

// mocks
const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
};
window.axios = mockAxios;

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

        // discovery fields
        wrapper.vm.discovery.discoverable = true;
        wrapper.vm.discovery.discovery_name = "Region A";
        wrapper.vm.discovery.announce_interval = 720;
        wrapper.vm.discovery.reachable_on = "/usr/local/bin/ip.sh";
        wrapper.vm.discovery.discovery_stamp_value = 22;
        wrapper.vm.discovery.discovery_encrypt = true;
        wrapper.vm.discovery.publish_ifac = true;
        wrapper.vm.discovery.latitude = 1.23;
        wrapper.vm.discovery.longitude = 4.56;
        wrapper.vm.discovery.height = 7;
        wrapper.vm.discovery.discovery_frequency = 915000000;
        wrapper.vm.discovery.discovery_bandwidth = 125000;
        wrapper.vm.discovery.discovery_modulation = "LoRa";

        await wrapper.vm.addInterface();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                discoverable: "yes",
                discovery_name: "Region A",
                announce_interval: 720,
                reachable_on: "/usr/local/bin/ip.sh",
                discovery_stamp_value: 22,
                discovery_encrypt: true,
                publish_ifac: true,
                latitude: 1.23,
                longitude: 4.56,
                height: 7,
                discovery_frequency: 915000000,
                discovery_bandwidth: 125000,
                discovery_modulation: "LoRa",
            })
        );
    });
});
