import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InterfacesPage from "../../meshchatx/src/frontend/components/interfaces/InterfacesPage.vue";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";

// Mock global objects
const mockAxios = {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
};
window.axios = mockAxios;

const mockToast = {
    success: vi.fn(),
    error: vi.fn(),
};
// We need to handle how ToastUtils is imported in the component
// If it's a global or imported, we might need a different approach.
// Let's assume it's available via window or we can mock the import if using vitest aliases.

vi.mock("../../js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

// Mock router/route
const mockRoute = {
    query: {},
};
const mockRouter = {
    push: vi.fn(),
};

describe("InterfacesPage.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAxios.get.mockResolvedValue({ data: { interfaces: [], app_info: { is_reticulum_running: true } } });
        GlobalState.hasPendingInterfaceChanges = false;
        GlobalState.modifiedInterfaceNames.clear();
    });

    it("loads interfaces on mount", async () => {
        mockAxios.get.mockImplementation((url) => {
            if (url.includes("interfaces")) {
                return Promise.resolve({ data: { interfaces: [{ name: "Test Iface", type: "TCP" }] } });
            }
            if (url.includes("app/info")) {
                return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
            }
            return Promise.reject();
        });

        const wrapper = mount(InterfacesPage, {
            global: {
                mocks: {
                    $route: mockRoute,
                    $router: mockRouter,
                    $t: (msg) => msg,
                },
                stubs: ["RouterLink", "MaterialDesignIcon", "IconButton", "Interface", "ImportInterfacesModal"],
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // wait for multiple awaits

        expect(mockAxios.get).toHaveBeenCalledWith("/api/v1/reticulum/interfaces");
        expect(wrapper.vm.interfaces.length).toBe(1);
    });

    it("tracks changes when an interface is enabled", async () => {
        const wrapper = mount(InterfacesPage, {
            global: {
                mocks: {
                    $route: mockRoute,
                    $router: mockRouter,
                    $t: (msg) => msg,
                },
                stubs: ["RouterLink", "MaterialDesignIcon", "IconButton", "Interface", "ImportInterfacesModal"],
            },
        });

        await wrapper.vm.enableInterface("test-iface");
        expect(wrapper.vm.hasPendingInterfaceChanges).toBe(true);
        expect(wrapper.vm.modifiedInterfaceNames.has("test-iface")).toBe(true);
    });

    it("clears pending changes after RNS reload", async () => {
        mockAxios.post.mockResolvedValue({ data: { message: "Reloaded" } });

        const wrapper = mount(InterfacesPage, {
            global: {
                mocks: {
                    $route: mockRoute,
                    $router: mockRouter,
                    $t: (msg) => msg,
                },
                stubs: ["RouterLink", "MaterialDesignIcon", "IconButton", "Interface", "ImportInterfacesModal"],
            },
        });

        GlobalState.hasPendingInterfaceChanges = true;
        GlobalState.modifiedInterfaceNames.add("test-iface");

        await wrapper.vm.reloadRns();

        expect(wrapper.vm.hasPendingInterfaceChanges).toBe(false);
        expect(wrapper.vm.modifiedInterfaceNames.size).toBe(0);
        expect(mockAxios.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
    });

    it("loads and saves discovery config", async () => {
        mockAxios.get.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/interfaces") {
                return Promise.resolve({ data: { interfaces: [] } });
            }
            if (url === "/api/v1/app/info") {
                return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
            }
            if (url === "/api/v1/reticulum/discovery") {
                return Promise.resolve({
                    data: {
                        discovery: {
                            discover_interfaces: "true",
                            interface_discovery_sources: "abc",
                            required_discovery_value: "16",
                            autoconnect_discovered_interfaces: "3",
                            network_identity: "/tmp/netid",
                        },
                    },
                });
            }
            return Promise.reject();
        });

        mockAxios.patch.mockResolvedValue({
            data: {
                discovery: {
                    discover_interfaces: false,
                    interface_discovery_sources: null,
                    required_discovery_value: 18,
                    autoconnect_discovered_interfaces: 5,
                    network_identity: "/tmp/new",
                },
            },
        });

        const wrapper = mount(InterfacesPage, {
            global: {
                mocks: {
                    $route: mockRoute,
                    $router: mockRouter,
                    $t: (msg) => msg,
                },
                stubs: [
                    "RouterLink",
                    "MaterialDesignIcon",
                    "IconButton",
                    "Interface",
                    "ImportInterfacesModal",
                    "Toggle",
                ],
            },
        });

        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.discoveryConfig.discover_interfaces).toBe(true);
        expect(wrapper.vm.discoveryConfig.interface_discovery_sources).toBe("abc");
        expect(wrapper.vm.discoveryConfig.required_discovery_value).toBe(16);
        expect(wrapper.vm.discoveryConfig.autoconnect_discovered_interfaces).toBe(3);
        expect(wrapper.vm.discoveryConfig.network_identity).toBe("/tmp/netid");

        wrapper.vm.discoveryConfig.discover_interfaces = false;
        wrapper.vm.discoveryConfig.interface_discovery_sources = "";
        wrapper.vm.discoveryConfig.required_discovery_value = 18;
        wrapper.vm.discoveryConfig.autoconnect_discovered_interfaces = 5;
        wrapper.vm.discoveryConfig.network_identity = "/tmp/new";

        await wrapper.vm.saveDiscoveryConfig();

        expect(mockAxios.patch).toHaveBeenCalledWith("/api/v1/reticulum/discovery", {
            discover_interfaces: false,
            interface_discovery_sources: null,
            required_discovery_value: 18,
            autoconnect_discovered_interfaces: 5,
            network_identity: "/tmp/new",
        });
        expect(wrapper.vm.savingDiscovery).toBe(false);
    });
});
