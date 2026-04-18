import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import InterfacesPage from "../../meshchatx/src/frontend/components/interfaces/InterfacesPage.vue";
import AddInterfacePage from "../../meshchatx/src/frontend/components/interfaces/AddInterfacePage.vue";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

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
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
        confirm: vi.fn(() => Promise.resolve(true)),
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

const ifaceWithIfac = {
    name: "kin.earth",
    type: "BackboneInterface",
    reachable_on: "rns.kin.earth",
    port: 4242,
    transport_id: "eea3d09f02143e157b3dae83060ee843",
    network_id: "abc123",
    discovery_hash: "kin-earth-1",
    network_name: "kin.earth",
    passphrase: "asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
    ifac_netname: "kin.earth",
    ifac_netkey: "asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
    publish_ifac: true,
    config_entry:
        "[[kin.earth]]\n  type = BackboneInterface\n  enabled = yes\n  remote = rns.kin.earth\n  target_port = 4242\n  network_name = kin.earth\n  passphrase = asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
};

const mountInterfacesPage = () =>
    mount(InterfacesPage, {
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

describe("InterfacesPage discovered IFAC display", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        if (typeof sessionStorage !== "undefined") {
            sessionStorage.clear();
        }
        Object.defineProperty(navigator, "clipboard", {
            value: { writeText: vi.fn(() => Promise.resolve()) },
            configurable: true,
        });
    });

    it("derives network_name and passphrase from either alias", () => {
        const wrapper = mountInterfacesPage();
        expect(wrapper.vm.discoveredNetworkName(ifaceWithIfac)).toBe("kin.earth");
        expect(wrapper.vm.discoveredPassphrase(ifaceWithIfac)).toBe("asty8vT8spXNQdCnPVMATbCKkwUxuzG9");

        // raw RNS keys only, no aliases
        const rawOnly = {
            name: "raw",
            ifac_netname: "raw.net",
            ifac_netkey: "rawkey",
        };
        expect(wrapper.vm.discoveredNetworkName(rawOnly)).toBe("raw.net");
        expect(wrapper.vm.discoveredPassphrase(rawOnly)).toBe("rawkey");

        // missing IFAC
        expect(wrapper.vm.discoveredNetworkName({ name: "open" })).toBe(null);
        expect(wrapper.vm.discoveredPassphrase({ name: "open" })).toBe(null);
    });

    it("masks passphrase for display safety", () => {
        const wrapper = mountInterfacesPage();
        expect(wrapper.vm.maskPassphrase("asty8vT8spXNQdCnPVMATbCKkwUxuzG9")).toMatch(/^as\*+G9$/);
        expect(wrapper.vm.maskPassphrase("ab")).toBe("**");
        expect(wrapper.vm.maskPassphrase("")).toBe("");
        expect(wrapper.vm.maskPassphrase(null)).toBe("");
    });

    it("renders network_name and passphrase chips when announce includes IFAC", async () => {
        const wrapper = mountInterfacesPage();
        await wrapper.setData({
            discoveredInterfaces: [ifaceWithIfac],
            discoveryConfig: {
                discover_interfaces: true,
                interface_discovery_sources: "",
                interface_discovery_whitelist: "",
                interface_discovery_blacklist: "",
                required_discovery_value: null,
                autoconnect_discovered_interfaces: 0,
                network_identity: "",
            },
        });

        const text = wrapper.text();
        expect(text).toContain("interfaces.discovered_network_name");
        expect(text).toContain("kin.earth");
        expect(text).toContain("interfaces.discovered_passphrase");
        expect(text).toMatch(/as\*+G9/);
        expect(text).not.toContain("asty8vT8spXNQdCnPVMATbCKkwUxuzG9");
    });

    it("does not render passphrase row when announce omits IFAC", async () => {
        const wrapper = mountInterfacesPage();
        await wrapper.setData({
            discoveredInterfaces: [
                {
                    name: "open",
                    type: "BackboneInterface",
                    reachable_on: "10.0.0.1",
                    port: 4242,
                    discovery_hash: "open-1",
                },
            ],
        });
        const text = wrapper.text();
        expect(text).not.toContain("interfaces.discovered_network_name");
        expect(text).not.toContain("interfaces.discovered_passphrase");
    });

    it("copyDiscoveredConfigEntry writes the config block to clipboard", async () => {
        const wrapper = mountInterfacesPage();
        wrapper.vm.copyDiscoveredConfigEntry(ifaceWithIfac);
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith(ifaceWithIfac.config_entry);
        expect(ToastUtils.success).toHaveBeenCalled();
    });

    it("copyDiscoveredConfigEntry shows error when no config_entry is present", async () => {
        const wrapper = mountInterfacesPage();
        wrapper.vm.copyDiscoveredConfigEntry({ name: "no-config" });
        expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
        expect(ToastUtils.error).toHaveBeenCalled();
    });

    it("useDiscoveredInterface stores prefill in sessionStorage and navigates", async () => {
        const routerPush = vi.fn();
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
                    $router: { push: routerPush },
                },
            },
        });

        wrapper.vm.useDiscoveredInterface(ifaceWithIfac);

        const stored = JSON.parse(sessionStorage.getItem("meshchatx.discoveredInterfacePrefill"));
        expect(stored.name).toBe("kin.earth");
        expect(stored.type).toBe("BackboneInterface");
        expect(stored.target_host).toBe("rns.kin.earth");
        expect(stored.target_port).toBe(4242);
        expect(stored.network_name).toBe("kin.earth");
        expect(stored.passphrase).toBe("asty8vT8spXNQdCnPVMATbCKkwUxuzG9");
        expect(stored.config_entry).toContain("[[kin.earth]]");

        expect(routerPush).toHaveBeenCalledWith({
            name: "interfaces.add",
            query: { from_discovered: "1" },
        });
    });

    it("Use this interface menu item appears for every discovered card", async () => {
        const wrapper = mountInterfacesPage();
        await wrapper.setData({
            discoveredInterfaces: [ifaceWithIfac],
            openDiscoveryActionKey: "kin-earth-1",
        });
        const useButton = wrapper.find('[data-testid="use-discovered-interface"]');
        expect(useButton.exists()).toBe(true);
        const copyCfg = wrapper.find('[data-testid="copy-discovered-config"]');
        expect(copyCfg.exists()).toBe(true);
    });
});

describe("AddInterfacePage discovered prefill", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        if (typeof sessionStorage !== "undefined") {
            sessionStorage.clear();
        }
        mockAxios.get.mockResolvedValue({ data: {} });
        mockAxios.post.mockResolvedValue({ data: { message: "ok" } });
    });

    const mountAdd = ($route = { query: { from_discovered: "1" } }) =>
        mount(AddInterfacePage, {
            global: {
                mocks: {
                    $route,
                    $router: { push: vi.fn() },
                    $t: (msg) => msg,
                },
                stubs: ["RouterLink", "MaterialDesignIcon", "Toggle", "ExpandingSection", "FormLabel", "FormSubLabel"],
            },
        });

    it("applies a discovered prefill payload to the form on mount", async () => {
        sessionStorage.setItem(
            "meshchatx.discoveredInterfacePrefill",
            JSON.stringify({
                name: "kin.earth",
                type: "BackboneInterface",
                target_host: "rns.kin.earth",
                target_port: 4242,
                transport_identity: "eea3d09f02143e157b3dae83060ee843",
                network_name: "kin.earth",
                passphrase: "asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
            })
        );

        const wrapper = mountAdd();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.newInterfaceName).toBe("kin.earth");
        expect(wrapper.vm.newInterfaceType).toBe("BackboneInterface");
        expect(wrapper.vm.newInterfaceTargetHost).toBe("rns.kin.earth");
        expect(wrapper.vm.newInterfaceTargetPort).toBe(4242);
        expect(wrapper.vm.sharedInterfaceSettings.network_name).toBe("kin.earth");
        expect(wrapper.vm.sharedInterfaceSettings.passphrase).toBe("asty8vT8spXNQdCnPVMATbCKkwUxuzG9");
        expect(sessionStorage.getItem("meshchatx.discoveredInterfacePrefill")).toBeNull();
    });

    it("uses config_entry directly when provided", async () => {
        sessionStorage.setItem(
            "meshchatx.discoveredInterfacePrefill",
            JSON.stringify({
                config_entry:
                    "[[Quick Backbone]]\ntype = BackboneInterface\nremote = node.example\ntarget_port = 4242\nnetwork_name = quick.net\npassphrase = quickpass",
            })
        );

        const wrapper = mountAdd();
        await wrapper.vm.$nextTick();

        expect(mockAxios.post).toHaveBeenCalledWith(
            "/api/v1/reticulum/interfaces/add",
            expect.objectContaining({
                name: "Quick Backbone",
                type: "BackboneInterface",
                target_host: "node.example",
                target_port: 4242,
                network_name: "quick.net",
                passphrase: "quickpass",
            })
        );
    });

    it("does not crash when from_discovered query is set but no payload is in storage", async () => {
        const wrapper = mountAdd();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.newInterfaceName).toBe(null);
    });

    it("end-to-end with config_entry: useDiscoveredInterface -> AddInterfacePage POST", async () => {
        const routerPush = vi.fn();
        const interfacesWrapper = mount(InterfacesPage, {
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
                    $router: { push: routerPush },
                },
            },
        });
        interfacesWrapper.vm.useDiscoveredInterface(ifaceWithIfac);
        interfacesWrapper.unmount();

        expect(routerPush).toHaveBeenCalledWith({
            name: "interfaces.add",
            query: { from_discovered: "1" },
        });

        const addWrapper = mountAdd({ query: { from_discovered: "1" } });
        await addWrapper.vm.$nextTick();
        await addWrapper.vm.$nextTick();

        // when a config_entry is present, the prefill triggers an immediate
        // POST through quickAddInterfaceFromConfig with the IFAC values intact
        const postCall = mockAxios.post.mock.calls.find(([url]) => url === "/api/v1/reticulum/interfaces/add");
        expect(postCall).toBeTruthy();
        expect(postCall[1]).toEqual(
            expect.objectContaining({
                name: "kin.earth",
                type: "BackboneInterface",
                target_host: "rns.kin.earth",
                target_port: 4242,
                network_name: "kin.earth",
                passphrase: "asty8vT8spXNQdCnPVMATbCKkwUxuzG9",
            })
        );
    });

    it("end-to-end without config_entry: prefill populates form fields", async () => {
        const routerPush = vi.fn();
        const ifaceNoCfg = { ...ifaceWithIfac, config_entry: null };
        const interfacesWrapper = mount(InterfacesPage, {
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
                    $router: { push: routerPush },
                },
            },
        });
        interfacesWrapper.vm.useDiscoveredInterface(ifaceNoCfg);
        interfacesWrapper.unmount();

        const addWrapper = mountAdd({ query: { from_discovered: "1" } });
        await addWrapper.vm.$nextTick();

        expect(addWrapper.vm.newInterfaceName).toBe("kin.earth");
        expect(addWrapper.vm.newInterfaceType).toBe("BackboneInterface");
        expect(addWrapper.vm.newInterfaceTargetHost).toBe("rns.kin.earth");
        expect(addWrapper.vm.newInterfaceTargetPort).toBe(4242);
        expect(addWrapper.vm.sharedInterfaceSettings.network_name).toBe("kin.earth");
        expect(addWrapper.vm.sharedInterfaceSettings.passphrase).toBe("asty8vT8spXNQdCnPVMATbCKkwUxuzG9");
    });
});
