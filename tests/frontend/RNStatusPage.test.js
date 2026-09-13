// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import RNStatusPage from "@/features/rnstatus/RNStatusPage.svelte";
import ToastUtils from "@/js/ToastUtils.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    buildInterfaceStatRows,
    copyText,
    extractQueueRows,
    filterI2pInterfaces,
    formatInt,
    hasStatusSummary,
    shortHash,
} from "@/features/rnstatus/lib/statusFormat.ts";
import {
    createManagementIdentity,
    fetchManagementIdentities,
    fetchRNStatus,
} from "@/features/rnstatus/lib/statusPoller.ts";
import { registerRNStatusFeature } from "@/features/rnstatus/index.ts";
import { clearRoutes, listRoutes } from "@/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "@/js/registries/featureRegistry.js";
import { dispatchWsEvent } from "@/js/registries/wsEventRegistry.ts";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

describe("rnstatus lib helpers", () => {
    it("formats integers and shortens hashes", () => {
        expect(formatInt(1234567)).toBe((1234567).toLocaleString());
        expect(formatInt(null)).toBe("");
        expect(shortHash("0123456789abcdef0123456789abcdef")).toBe("01234567...");
        expect(shortHash("")).toBe("");
    });

    it("checks status summary presence and filters I2P interfaces", () => {
        expect(hasStatusSummary({ link_count: 5 })).toBe(true);
        expect(hasStatusSummary({})).toBe(false);

        const ifaces = [{ name: "if1", i2p_b32: "xyz.b32.i2p" }, { name: "if2" }];
        const filtered = filterI2pInterfaces(ifaces);
        expect(filtered).toHaveLength(1);
        expect(filtered[0].name).toBe("if1");
    });

    it("extracts queue rows and builds stat rows", () => {
        const queueRows = extractQueueRows({
            queues: [{ name: "total", pressure: 0.1, packets: 5, dropped: 0 }],
        });
        expect(queueRows).toHaveLength(1);
        expect(queueRows[0].key).toBe("total");

        const statRows = buildInterfaceStatRows({
            name: "TestIF",
            bitrate: "1000 bps",
            rx_bytes_str: "50 B",
        });
        expect(statRows.some((r) => r.key === "bitrate")).toBe(true);
    });

    it("fetches status and management identities via API", async () => {
        const getMock = vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/rnstatus") {
                return Promise.resolve({ data: { link_count: 3 } });
            }
            if (url === "/api/v1/reticulum/management-identities") {
                return Promise.resolve({ data: { identities: [{ name: "mgmt1" }] } });
            }
            return Promise.resolve({ data: {} });
        });
        const postMock = vi.fn().mockResolvedValue({
            data: { identity: { name: "new-mgmt" } },
        });
        window.api = { get: getMock, post: postMock };

        const status = await fetchRNStatus({ include_link_stats: true, show_all: false });
        expect(status.link_count).toBe(3);

        const list = await fetchManagementIdentities();
        expect(list).toHaveLength(1);

        const created = await createManagementIdentity("new-mgmt");
        expect(created?.name).toBe("new-mgmt");

        delete window.api;
    });

    it("copies text and shows toast", async () => {
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.assign(navigator, { clipboard: { writeText } });

        const ok = await copyText("copy-content");
        expect(ok).toBe(true);
        expect(writeText).toHaveBeenCalledWith("copy-content");
        expect(ToastUtils.success).toHaveBeenCalled();
    });
});

describe("registerRNStatusFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers rnstatus route correctly", () => {
        registerRNStatusFeature();
        expect(listFeatureIds()).toContain("rnstatus");
        const route = listRoutes().find((r) => r.name === "rnstatus");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/rnstatus");
        expect(route?.mount).toBe("svelte");
    });
});

describe("RNStatusPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        registerTranslator(null);
        registerFallbackMessages({
            app: { tools: "Tools" },
            rnprobe: { network_diagnostics: "Network Diagnostics" },
            tools: {
                back_to_tools: "Back",
                rnstatus: {
                    title: "RNStatus",
                    description: "Inspect Reticulum interfaces and telemetry",
                },
            },
            common: {
                copied: "Copied",
                failed_to_copy: "Failed to copy",
                copy: "Copy",
            },
            rnstatus: {
                refresh: "Refresh",
                reloading: "Reloading...",
                failed_refresh: "Failed to refresh RNStatus",
                show_all_interfaces: "Show all interfaces",
                all_interfaces: "All interfaces",
                include_link_stats: "Include link stats",
                sort_by: "Sort by",
                none: "None",
                bitrate: "Bitrate",
                rx_bytes: "RX Bytes",
                tx_bytes: "TX Bytes",
                total_traffic: "Total Traffic",
                announces: "Announces",
                path_requests: "Path Requests",
                held_announces: "Held Announces",
                gravity: "Gravity",
                active: "Active",
                inactive: "Inactive",
                active_links_label: "Active Links",
                blackhole_heading: "Blackhole",
                blackhole_publishing: "Publishing",
                blackhole_inactive: "Inactive",
                blackhole_identities: "{count} Identities",
                blackhole_sources: "Blackhole Sources",
                queue_total: "Total",
                queue_data: "Data",
                queue_announce: "Announce",
                queue_path_request: "Path Request",
                queue_ingress_limiter: "Ingress Limiter",
                peers_reachable: "reachable",
                mode: "Mode",
                rx_speed: "RX Speed",
                tx_speed: "TX Speed",
                clients: "Clients",
                peers: "Peers",
                i2p_address: "I2P Address",
            },
        });

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
        cleanup();
        delete window.api;
    });

    it("renders and loads status data on mount", async () => {
        render(RNStatusPage);
        expect(screen.getByText("RNStatus")).toBeTruthy();
        expect(screen.getByText("Network Diagnostics")).toBeTruthy();

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rnstatus", expect.any(Object));
        });

        const ifaceElements = await screen.findAllByText("Interface 1");
        expect(ifaceElements.length).toBeGreaterThan(0);
        expect(screen.getAllByText("abc123.b32.i2p").length).toBeGreaterThan(0);
    });

    it("displays inactive blackhole state when disabled", async () => {
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

        render(RNStatusPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalled();
        });

        expect(await screen.findByText("Inactive")).toBeTruthy();
    });

    it("refreshes status when refresh button is clicked", async () => {
        render(RNStatusPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/rnstatus", expect.any(Object));
        });

        const statusCallsBefore = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/rnstatus").length;
        const refreshBtn = screen.getByText("Refresh");
        await fireEvent.click(refreshBtn);

        await waitFor(() => {
            const statusCallsAfter = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/rnstatus").length;
            expect(statusCallsAfter).toBe(statusCallsBefore + 1);
        });
    });

    it("toggles link stats checkbox", async () => {
        render(RNStatusPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalled();
        });

        const linkStatsCheckbox = screen.getByText("Include link stats").closest("label")?.querySelector("input");
        if (linkStatsCheckbox) {
            await fireEvent.click(linkStatsCheckbox);
        }

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(
                "/api/v1/rnstatus",
                expect.objectContaining({
                    params: expect.objectContaining({ include_link_stats: true }),
                })
            );
        });
    });

    it("toggles all-interfaces checkbox", async () => {
        render(RNStatusPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalled();
        });

        const allIfacesCheckbox = screen.getByText("Show all interfaces").closest("label")?.querySelector("input");
        if (allIfacesCheckbox) {
            await fireEvent.click(allIfacesCheckbox);
        }

        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalledWith(
                "/api/v1/rnstatus",
                expect.objectContaining({
                    params: expect.objectContaining({ show_all: true }),
                })
            );
        });
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

        render(RNStatusPage);

        await waitFor(() => {
            expect(ToastUtils.error).toHaveBeenCalled();
        });

        const msg = ToastUtils.error.mock.calls[0][0];
        expect(msg).toContain("Failed to refresh RNStatus");
        expect(msg).toContain("RNS stack is reloading");
    });

    it("handles websocket reload status to disable refresh", async () => {
        render(RNStatusPage);
        await waitFor(() => {
            expect(axiosMock.get).toHaveBeenCalled();
        });

        const callsBefore = axiosMock.get.mock.calls.length;

        await dispatchWsEvent("reticulum_reload_status", {
            type: "reticulum_reload_status",
            in_progress: true,
            message: "Reloading",
        });

        await waitFor(() => {
            expect(screen.getByText("Reloading...")).toBeTruthy();
        });

        const btn = screen.getByRole("button", { name: /Reloading.../i });
        expect(btn.hasAttribute("disabled")).toBe(true);

        await fireEvent.click(btn);
        expect(axiosMock.get.mock.calls.length).toBe(callsBefore);
    });
});
