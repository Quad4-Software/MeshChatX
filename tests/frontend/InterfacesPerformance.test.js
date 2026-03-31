import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import InterfacesPage from "../../meshchatx/src/frontend/components/interfaces/InterfacesPage.vue";

// Mock dependencies
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
    },
}));

// Mock axios
global.api = {
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
            return Promise.resolve({ data: { discovery: { discover_interfaces: true } } });
        }
        if (url.includes("/api/v1/reticulum/discovered-interfaces")) {
            return Promise.resolve({ data: { interfaces: [], active: [] } });
        }
        return Promise.resolve({ data: {} });
    }),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    isCancel: vi.fn().mockReturnValue(false),
};
window.api = global.api;

// Mock MaterialDesignIcon
const MaterialDesignIcon = {
    template: '<div class="mdi"></div>',
    props: ["iconName"],
};

describe("InterfacesPage Performance", () => {
    it("renders InterfacesPage with 1000 disconnected discovered interfaces", async () => {
        const numDiscovered = 1000;
        const discoveredInterfaces = Array.from({ length: numDiscovered }, (_, i) => ({
            name: `Discovered ${i}`,
            type: "UDPInterface",
            reachable_on: `192.168.1.${i}`,
            port: 4242,
            discovery_hash: `hash_${i}`,
        }));

        const start = performance.now();
        const wrapper = mount(InterfacesPage, {
            global: {
                components: {
                    MaterialDesignIcon,
                    Toggle: { template: "<div></div>" },
                    ImportInterfacesModal: {
                        template: "<div></div>",
                        methods: { show: vi.fn() },
                    },
                    Interface: { template: "<div></div>" },
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.setData({
            discoveredInterfaces,
            activeTab: "overview",
        });

        const end = performance.now();
        console.log(`Rendered ${numDiscovered} discovered interfaces in ${(end - start).toFixed(2)}ms`);

        const disconnectedBadges = wrapper.findAll(".bg-red-500\\/90");
        expect(disconnectedBadges.length).toBe(numDiscovered);
        expect(end - start).toBeLessThan(6000);
    });

    it("disconnected discovered interfaces render without pulse animation", async () => {
        const iface = {
            name: "Discovered 1",
            type: "UDPInterface",
            reachable_on: "192.168.1.1",
            port: 4242,
            discovery_hash: "hash_1",
        };

        const wrapper = mount(InterfacesPage, {
            global: {
                components: {
                    MaterialDesignIcon,
                    Toggle: { template: "<div></div>" },
                    ImportInterfacesModal: {
                        template: "<div></div>",
                        methods: { show: vi.fn() },
                    },
                    Interface: { template: "<div></div>" },
                },
                mocks: {
                    $t: (key) => key,
                    $router: { push: vi.fn() },
                },
            },
        });

        await wrapper.setData({
            discoveredInterfaces: [iface],
            activeTab: "overview",
        });

        const pulsingElements = wrapper.findAll(".animate-pulse");
        expect(pulsingElements.length).toBe(0);
    });
});
