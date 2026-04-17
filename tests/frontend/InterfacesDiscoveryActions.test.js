import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InterfacesPage from "../../meshchatx/src/frontend/components/interfaces/InterfacesPage.vue";

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        config: { theme: "light" },
        hasPendingInterfaceChanges: false,
        modifiedInterfaceNames: new Set(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: {
        formatBytes: (b) => `${b} B`,
        isInterfaceEnabled: () => true,
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ElectronUtils", () => ({
    default: {
        relaunch: vi.fn(),
        isElectron: () => false,
    },
}));

const mockAxios = {
    get: vi.fn((url) => {
        if (url.includes("/api/v1/reticulum/interfaces")) {
            return Promise.resolve({ data: { interfaces: {} } });
        }
        if (url.includes("/api/v1/app/info")) {
            return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
        }
        if (url.includes("/api/v1/interface-stats")) {
            return Promise.resolve({ data: { interface_stats: { interfaces: [] } } });
        }
        if (url.includes("/api/v1/reticulum/discovery")) {
            return Promise.resolve({
                data: {
                    discovery: {
                        discover_interfaces: true,
                        interface_discovery_whitelist: "",
                        interface_discovery_blacklist: "",
                    },
                },
            });
        }
        if (url.includes("/api/v1/reticulum/discovered-interfaces")) {
            return Promise.resolve({ data: { interfaces: [], active: [] } });
        }
        return Promise.resolve({ data: {} });
    }),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
};
window.api = mockAxios;

describe("InterfacesPage discovery actions", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows discovery action menu and allows announce", async () => {
        const wrapper = mount(InterfacesPage, {
            global: {
                stubs: {
                    RouterLink: true,
                    MaterialDesignIcon: true,
                    Toggle: true,
                    ImportInterfacesModal: true,
                    Interface: true,
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.setData({
            discoveredInterfaces: [
                {
                    name: "Peer Node",
                    type: "TCPClientInterface",
                    reachable_on: "10.0.0.8",
                    port: 4242,
                    discovery_hash: "hash-1",
                },
            ],
            discoveryConfig: {
                discover_interfaces: true,
                interface_discovery_sources: "",
                interface_discovery_whitelist: "",
                interface_discovery_blacklist: "old-entry",
                required_discovery_value: null,
                autoconnect_discovered_interfaces: 0,
                network_identity: "",
            },
        });

        const actionButton = wrapper.find('button[title="Discovery actions"]');
        expect(actionButton.exists()).toBe(true);
        await actionButton.trigger("click");
        expect(wrapper.text()).toContain("Allow this announce");

        const allowButton = wrapper.findAll("button").find((btn) => btn.text().includes("Allow this announce"));
        expect(allowButton).toBeTruthy();
        await allowButton.trigger("click");

        expect(mockAxios.patch).toHaveBeenCalledWith("/api/v1/reticulum/discovery", {
            interface_discovery_whitelist: "10.0.0.8:4242",
            interface_discovery_blacklist: null,
        });
    });

    it("blacklists announce and removes same token from whitelist", async () => {
        const wrapper = mount(InterfacesPage, {
            global: {
                stubs: {
                    RouterLink: true,
                    MaterialDesignIcon: true,
                    Toggle: true,
                    ImportInterfacesModal: true,
                    Interface: true,
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.setData({
            discoveredInterfaces: [
                {
                    name: "Peer Node",
                    type: "TCPClientInterface",
                    reachable_on: "10.0.0.8",
                    port: 4242,
                    discovery_hash: "hash-2",
                },
            ],
            discoveryConfig: {
                discover_interfaces: true,
                interface_discovery_sources: "",
                interface_discovery_whitelist: "10.0.0.8:4242,other",
                interface_discovery_blacklist: "",
                required_discovery_value: null,
                autoconnect_discovered_interfaces: 0,
                network_identity: "",
            },
        });

        await wrapper.find('button[title="Discovery actions"]').trigger("click");
        const blockButton = wrapper.findAll("button").find((btn) => btn.text().includes("Blacklist this announce"));
        expect(blockButton).toBeTruthy();
        await blockButton.trigger("click");

        expect(mockAxios.patch).toHaveBeenCalledWith("/api/v1/reticulum/discovery", {
            interface_discovery_whitelist: null,
            interface_discovery_blacklist: "10.0.0.8:4242",
        });
    });

    it("reloadRns posts reticulum restart endpoint", async () => {
        const wrapper = mount(InterfacesPage, {
            global: {
                stubs: {
                    RouterLink: true,
                    MaterialDesignIcon: true,
                    Toggle: true,
                    ImportInterfacesModal: true,
                    Interface: true,
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.vm.reloadRns();

        expect(mockAxios.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
    });
});
