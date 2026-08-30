import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RNStatusPage from "@/components/rnstatus/RNStatusPage.vue";
import ToastUtils from "@/js/ToastUtils";
import WebSocketConnection from "@/js/WebSocketConnection";
import { mountToolsPageGlobals } from "./testI18n.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
    },
}));

describe("RNStatusPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rnstatus") {
                return Promise.resolve({
                    data: {
                        interfaces: [
                            {
                                name: "Interface 1",
                                status: "Up",
                                discovered: true,
                                bitrate: "100 bps",
                                rx_bytes_str: "10 B",
                                tx_bytes_str: "5 B",
                                i2p_b32: "abc123.b32.i2p",
                                i2p_connectable: true,
                                i2p_tunnel_state: "Tunnel Active",
                            },
                        ],
                        link_count: 5,
                        blackhole_enabled: true,
                        blackhole_count: 10,
                        blackhole_sources: ["src1"],
                        transport_id: "aa".repeat(16),
                        transport_uptime_str: "1m 30s",
                        totals: {
                            rx_bytes_str: "10 B",
                            tx_bytes_str: "5 B",
                            rx_speed_str: "1.00 bps",
                            tx_speed_str: "2.00 bps",
                        },
                    },
                });
            }
            if (url === "/api/v1/reticulum/management-identities") {
                return Promise.resolve({ data: { identities: [] } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountRNStatusPage = () => {
        return mount(RNStatusPage, {
            global: mountToolsPageGlobals(),
        });
    };

    it("renders and loads status data", async () => {
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        expect(wrapper.text()).toContain("RNStatus");
        expect(wrapper.text()).toContain("Network Diagnostics");
        expect(wrapper.text()).toContain("Interface 1");
        expect(wrapper.text()).toContain("Discovered");
        expect(wrapper.text()).toContain("5");
        expect(wrapper.text()).toContain("Publishing");
        expect(wrapper.text()).toContain("abc123.b32.i2p");
        expect(wrapper.vm.blackholeEnabled).toBe(true);
        expect(wrapper.text()).toContain("src1");
        expect(typeof wrapper.vm.onWebsocketMessage).toBe("function");
    });

    it("labels disabled blackhole as Inactive", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rnstatus") {
                return Promise.resolve({
                    data: {
                        interfaces: [],
                        link_count: 0,
                        blackhole_enabled: false,
                        blackhole_count: 0,
                        blackhole_sources: [],
                    },
                });
            }
            if (url === "/api/v1/reticulum/management-identities") {
                return Promise.resolve({ data: { identities: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));
        expect(wrapper.text()).toContain("Inactive");
    });

    it("refreshes status when button is clicked", async () => {
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        const refreshButton = wrapper.find("button");
        await refreshButton.trigger("click");

        expect(axiosMock.get).toHaveBeenCalled();
    });

    it("toggles link stats", async () => {
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        const checkbox = wrapper.find("input[type='checkbox']");
        await checkbox.setValue(true);

        expect(axiosMock.get).toHaveBeenCalledWith(
            "/api/v1/rnstatus",
            expect.objectContaining({
                params: expect.objectContaining({ include_link_stats: true }),
            })
        );
    });

    it("toasts on refresh failure", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/rnstatus") {
                return Promise.reject({
                    response: { data: { message: "RNS stack is reloading" }, status: 503 },
                });
            }
            if (url === "/api/v1/reticulum/management-identities") {
                return Promise.resolve({ data: { identities: [] } });
            }
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(ToastUtils.error).toHaveBeenCalled());
        const msg = ToastUtils.error.mock.calls[0][0];
        expect(msg).toContain("Failed to refresh RNStatus");
        expect(msg).toContain("RNS stack is reloading");
    });

    it("copies the I2P address", async () => {
        const writeText = vi.fn().mockResolvedValue();
        Object.assign(navigator, { clipboard: { writeText } });
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));
        await wrapper.vm.copyText("abc123.b32.i2p");
        expect(writeText).toHaveBeenCalledWith("abc123.b32.i2p");
        expect(ToastUtils.success).toHaveBeenCalled();
    });

    it("sends show_all when the all-interfaces toggle is on", async () => {
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));
        wrapper.vm.showAll = true;
        await wrapper.vm.$nextTick();
        await vi.waitFor(() =>
            expect(axiosMock.get).toHaveBeenCalledWith(
                "/api/v1/rnstatus",
                expect.objectContaining({
                    params: expect.objectContaining({ show_all: true }),
                })
            )
        );
    });

    it("disables refresh while RNS reload is in progress", async () => {
        const wrapper = mountRNStatusPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));
        const callsBefore = axiosMock.get.mock.calls.length;

        wrapper.vm.onWebsocketMessage({
            type: "reticulum_reload_status",
            in_progress: true,
            message: "Reloading",
        });
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.reloadingRns).toBe(true);
        expect(wrapper.find("button").attributes("disabled")).toBeDefined();

        await wrapper.vm.refreshStatus();
        expect(axiosMock.get.mock.calls.length).toBe(callsBefore);
    });
});
