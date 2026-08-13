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
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/ElectronUtils", () => ({
    default: {
        relaunch: vi.fn(),
        isElectron: () => false,
        isWindowsElectron: () => false,
    },
}));

function mountInterfacesPage() {
    return mount(InterfacesPage, {
        global: {
            stubs: {
                RouterLink: true,
                MaterialDesignIcon: true,
                Toggle: true,
                ImportInterfacesModal: true,
                Interface: true,
                BundledDocsHint: true,
            },
            mocks: {
                $t: (key) => key,
                $router: { push: vi.fn() },
            },
        },
    });
}

describe("InterfacesPage interface-stats merge", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.api = {
            get: vi.fn((url) => {
                if (url.includes("/api/v1/reticulum/interfaces")) {
                    return Promise.resolve({
                        data: {
                            interfaces: {
                                "RNode LoRa Interface": { type: "RNodeInterface", enabled: true },
                            },
                        },
                    });
                }
                if (url.includes("/api/v1/app/info")) {
                    return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
                }
                if (url.includes("/api/v1/interface-stats")) {
                    return Promise.resolve({
                        data: {
                            interface_stats: {
                                interfaces: [
                                    {
                                        interface_name: "RNode LoRa Interface",
                                        short_name: "LoRa",
                                        status: true,
                                        rxb: 100,
                                        txb: 50,
                                    },
                                ],
                            },
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
        };
    });

    it("indexes stats by interface_name so config keys match live status", async () => {
        const wrapper = mountInterfacesPage();
        await wrapper.vm.loadInterfaces();
        await wrapper.vm.updateInterfaceStats();

        const stats = wrapper.vm.interfaceStats["RNode LoRa Interface"];
        expect(stats).toBeDefined();
        expect(stats.status).toBe(true);
        expect(stats.short_name).toBe("LoRa");
        expect(wrapper.vm.interfacesWithStats[0]._stats).toEqual(stats);
    });

    it("keeps hostname section names such as artyom.ddns.net in the tile list", async () => {
        window.api.get = vi.fn((url) => {
            if (url.includes("/api/v1/reticulum/interfaces")) {
                return Promise.resolve({
                    data: {
                        interfaces: {
                            "Default Interface": { type: "AutoInterface", enabled: true },
                            "artyom.ddns.net": {
                                type: "TCPClientInterface",
                                interface_enabled: "True",
                                target_host: "10.100.11.12",
                                target_port: "4242",
                            },
                            "Catz-Node (TCP)": { type: "TCPClientInterface", enabled: true },
                        },
                    },
                });
            }
            if (url.includes("/api/v1/app/info")) {
                return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountInterfacesPage();
        await wrapper.vm.loadInterfaces();
        const names = wrapper.vm.filteredInterfaces.map((iface) => iface._name);
        expect(names).toContain("artyom.ddns.net");
        expect(names).toContain("Default Interface");
        expect(names).toContain("Catz-Node (TCP)");
        expect(names).toHaveLength(3);
    });

    it("falls back to short_name when interface_name is absent", async () => {
        window.api.get = vi.fn((url) => {
            if (url.includes("/api/v1/reticulum/interfaces")) {
                return Promise.resolve({ data: { interfaces: { LoRa: { type: "RNodeInterface" } } } });
            }
            if (url.includes("/api/v1/app/info")) {
                return Promise.resolve({ data: { app_info: { is_reticulum_running: true } } });
            }
            if (url.includes("/api/v1/interface-stats")) {
                return Promise.resolve({
                    data: {
                        interface_stats: {
                            interfaces: [{ short_name: "LoRa", status: true }],
                        },
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountInterfacesPage();
        await wrapper.vm.updateInterfaceStats();
        expect(wrapper.vm.interfaceStats.LoRa.status).toBe(true);
    });
});
