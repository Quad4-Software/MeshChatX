import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AddInterfacePage from "../../meshchatx/src/frontend/components/interfaces/AddInterfacePage.vue";

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

    const mountPage = () =>
        mount(AddInterfacePage, {
            global: {
                mocks: {
                    $route: { query: {} },
                    $router: { push: vi.fn() },
                    $t: (msg) => msg,
                },
                stubs: ["RouterLink", "MaterialDesignIcon", "Toggle", "ExpandingSection", "FormLabel", "FormSubLabel"],
            },
        });

    it("adds discovery fields when interface is discoverable", async () => {
        const wrapper = mountPage();

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

    it("does not require latitude or longitude (optional coordinates)", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "NoCoords";
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        wrapper.vm.newInterfaceTargetHost = "example.com";
        wrapper.vm.newInterfaceTargetPort = "4242";

        wrapper.vm.discovery.discoverable = true;
        wrapper.vm.discovery.discovery_name = "X";
        wrapper.vm.discovery.announce_interval = 360;
        wrapper.vm.discovery.reachable_on = "192.0.2.1";
        wrapper.vm.discovery.latitude = null;
        wrapper.vm.discovery.longitude = null;
        wrapper.vm.discovery.height = null;

        await wrapper.vm.saveInterface();

        const payload = mockAxios.post.mock.calls[0][1];
        expect(payload.latitude).toBe(null);
        expect(payload.longitude).toBe(null);
        expect(payload.height).toBe(null);
        expect(payload.discoverable).toBe("yes");
    });

    it("sends coordinates when set (text input compatible)", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "WithCoords";
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        wrapper.vm.newInterfaceTargetHost = "example.com";
        wrapper.vm.newInterfaceTargetPort = "4242";

        wrapper.vm.discovery.discoverable = true;
        wrapper.vm.discovery.discovery_name = "Y";
        wrapper.vm.discovery.announce_interval = 360;
        wrapper.vm.discovery.reachable_on = "192.0.2.2";
        wrapper.vm.discovery.latitude = "51.5";
        wrapper.vm.discovery.longitude = "-0.12";
        wrapper.vm.discovery.height = "42";

        await wrapper.vm.saveInterface();

        const payload = mockAxios.post.mock.calls[0][1];
        expect(payload.latitude).toBe(51.5);
        expect(payload.longitude).toBe(-0.12);
        expect(payload.height).toBe(42);
    });

    it("toggles discovery_encrypt and publish_ifac in payload", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "Enc";
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        wrapper.vm.newInterfaceTargetHost = "example.com";
        wrapper.vm.newInterfaceTargetPort = "4242";

        wrapper.vm.discovery.discoverable = true;
        wrapper.vm.discovery.discovery_name = "Z";
        wrapper.vm.discovery.announce_interval = 120;
        wrapper.vm.discovery.reachable_on = "10.0.0.1";
        wrapper.vm.discovery.discovery_encrypt = true;
        wrapper.vm.discovery.publish_ifac = false;

        await wrapper.vm.saveInterface();

        const payload = mockAxios.post.mock.calls[0][1];
        expect(payload.discovery_encrypt).toBe(true);
        expect(payload.publish_ifac).toBe(false);
    });

    it("clears discovery fields when discoverable is off", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "Off";
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        wrapper.vm.newInterfaceTargetHost = "example.com";
        wrapper.vm.newInterfaceTargetPort = "4242";

        wrapper.vm.discovery.discoverable = false;

        await wrapper.vm.saveInterface();

        const payload = mockAxios.post.mock.calls[0][1];
        expect(payload.discoverable).toBe(null);
        expect(payload.discovery_name).toBe(null);
        expect(payload.latitude).toBe(null);
    });

    it("fuzz: random safe discovery_name and announce_interval still save", async () => {
        const wrapper = mountPage();

        wrapper.vm.newInterfaceName = "Fuzz";
        wrapper.vm.newInterfaceType = "TCPClientInterface";
        wrapper.vm.newInterfaceTargetHost = "example.com";
        wrapper.vm.newInterfaceTargetPort = "4242";

        for (let i = 0; i < 30; i++) {
            vi.clearAllMocks();
            mockAxios.post.mockResolvedValue({ data: { message: "ok" } });

            const name = `node-${Math.random().toString(36).slice(2, 10)}`;
            const interval = Math.max(5, Math.floor(Math.random() * 10000));

            wrapper.vm.discovery.discoverable = true;
            wrapper.vm.discovery.discovery_name = name;
            wrapper.vm.discovery.announce_interval = interval;
            wrapper.vm.discovery.reachable_on = "192.0.2.1";

            await wrapper.vm.saveInterface();

            const payload = mockAxios.post.mock.calls[0][1];
            expect(payload.discovery_name).toBe(name);
            expect(payload.announce_interval).toBe(interval);
        }
    });

    it("loadInterfaceToEdit restores discoverable and coordinates from API", async () => {
        mockAxios.get.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/interfaces") {
                return Promise.resolve({
                    data: {
                        interfaces: {
                            MyIface: {
                                type: "TCPClientInterface",
                                target_host: "h.example",
                                target_port: "5555",
                                discoverable: "yes",
                                discovery_name: "Loaded",
                                announce_interval: 180,
                                reachable_on: "192.0.2.3",
                                latitude: 12.34,
                                longitude: 56.78,
                                height: 100,
                                discovery_stamp_value: 18,
                                discovery_encrypt: true,
                                publish_ifac: false,
                            },
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountPage();
        await wrapper.vm.loadInterfaceToEdit("MyIface");

        expect(wrapper.vm.discovery.discoverable).toBe(true);
        expect(wrapper.vm.discovery.discovery_name).toBe("Loaded");
        expect(wrapper.vm.discovery.announce_interval).toBe(180);
        expect(wrapper.vm.discovery.latitude).toBe(12.34);
        expect(wrapper.vm.discovery.longitude).toBe(56.78);
        expect(wrapper.vm.discovery.height).toBe(100);
        expect(wrapper.vm.discovery.discovery_stamp_value).toBe(18);
        expect(wrapper.vm.discovery.discovery_encrypt).toBe(true);
        expect(wrapper.vm.discovery.publish_ifac).toBe(false);
    });

    it("quickAddInterfaceFromConfig posts add endpoint and routes back", async () => {
        const routerPush = vi.fn();
        const wrapper = mount(AddInterfacePage, {
            global: {
                mocks: {
                    $route: { query: {} },
                    $router: { push: routerPush },
                    $t: (msg) => msg,
                },
                stubs: ["RouterLink", "MaterialDesignIcon", "Toggle", "ExpandingSection", "FormLabel", "FormSubLabel"],
            },
        });

        await wrapper.vm.quickAddInterfaceFromConfig({
            name: "Quick Node",
            type: "TCPClientInterface",
            target_host: "node.example",
            target_port: "4242",
            discoverable: "yes",
        });

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                name: "Quick Node",
                type: "TCPClientInterface",
                target_host: "node.example",
                target_port: 4242,
                discoverable: "yes",
            })
        );
        expect(routerPush).toHaveBeenCalledWith({ name: "interfaces" });
    });

    it("handleRawConfigInput auto-imports a single detected config", async () => {
        const wrapper = mountPage();
        const quickAddSpy = vi.spyOn(wrapper.vm, "quickAddInterfaceFromConfig").mockResolvedValue();

        wrapper.vm.rawConfigInput = `[[Auto Node]]
type = TCPClientInterface
target_host = auto.example
target_port = 4242`;
        wrapper.vm.handleRawConfigInput();

        expect(quickAddSpy).toHaveBeenCalledWith(
            expect.objectContaining({
                name: "Auto Node",
                type: "TCPClientInterface",
                target_host: "auto.example",
                target_port: "4242",
            })
        );
    });
});
