import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TrafficPage from "@/components/tools/TrafficPage.vue";
import { mountToolsPageGlobals } from "./testI18n.js";

function makePayload(overrides = {}) {
    return {
        updated_at: Math.floor(Date.now() / 1000),
        uptime_s: 120,
        interfaces: [
            {
                name: "TCP Client",
                short_name: "TCP Client",
                type: "TCPClientInterface",
                txb: 4096,
                rxb: 8192,
                tx_bps: 512,
                rx_bps: 1024,
                announce_tx_bps: 64,
                announce_rx_bps: 64,
                propagated_tx_bps: 0,
                propagated_rx_bps: 0,
            },
        ],
        components: [
            {
                id: "lxmf",
                label: "LXMF messaging",
                tx_bytes: 2048,
                rx_bytes: 4096,
                tx_bps: 256,
                rx_bps: 512,
            },
        ],
        peers: [
            {
                hash: "ab".repeat(16),
                tx_bytes: 2048,
                rx_bytes: 4096,
                tx_bps: 256,
                rx_bps: 512,
                components: { lxmf: { tx: 2048, rx: 4096 } },
            },
        ],
        peers_total: 1,
        transfers: [],
        totals: { tx_bytes: 4096, rx_bytes: 8192, tx_bps: 512, rx_bps: 1024 },
        residual: { tx_bytes: 2048, rx_bytes: 4096, tx_bps: 256, rx_bps: 512 },
        history: [
            { t: 1000, tx_bps: 100, rx_bps: 0, top: "lxmf", top_bps: 100 },
            { t: 1003, tx_bps: 0, rx_bps: 1000, top: "nomadnet", top_bps: 1000 },
        ],
        warnings: [],
        hints: [],
        ...overrides,
    };
}

describe("TrafficPage.vue", () => {
    beforeEach(() => {
        window.api = {
            get: vi.fn(async () => ({ data: makePayload() })),
            post: vi.fn(async () => ({ data: {} })),
        };
    });

    const mountPage = () => mount(TrafficPage, { global: mountToolsPageGlobals() });

    const waitForData = async (wrapper) => {
        await vi.waitFor(() => expect(wrapper.vm.data).toBeTruthy());
    };

    it("renders totals, components, and interfaces from the payload", async () => {
        const wrapper = mountPage();
        await waitForData(wrapper);
        expect(wrapper.text()).toContain("LXMF messaging");
        expect(wrapper.text()).toContain("TCP Client");
        expect(wrapper.vm.componentRows[0].tx_bytes).toBe(2048);
        wrapper.unmount();
    });

    it("scales both chart series on one shared maximum", async () => {
        const wrapper = mountPage();
        await waitForData(wrapper);
        // TX peaks at 100, RX at 1000: with per-series scaling both would
        // reach the top of the chart, which misrepresents the comparison.
        expect(wrapper.vm.sparkGeometry.max).toBe(1000);
        const txPoints = wrapper.vm.sparklineTx.split(" ");
        const rxPoints = wrapper.vm.sparklineRx.split(" ");
        const txPeakY = parseFloat(txPoints[0].split(",")[1]);
        const rxPeakY = parseFloat(rxPoints[1].split(",")[1]);
        expect(rxPeakY).toBeLessThan(txPeakY);
        wrapper.unmount();
    });

    it("shows a hover tooltip with the point in time values", async () => {
        const wrapper = mountPage();
        await waitForData(wrapper);
        const svg = wrapper.find("svg");
        svg.element.getBoundingClientRect = () => ({
            left: 0,
            top: 0,
            width: 320,
            height: 80,
            right: 320,
            bottom: 80,
        });
        await svg.trigger("mousemove", { clientX: 320 });
        expect(wrapper.vm.sparkHover).toBeTruthy();
        expect(wrapper.vm.sparkHover.rx_bps).toBe(1000);
        expect(wrapper.vm.sparkHover.topLabel).toBe("NomadNet");
        expect(wrapper.text()).toContain("Mostly NomadNet");
        await svg.trigger("mouseleave");
        expect(wrapper.vm.sparkHover).toBeNull();
        wrapper.unmount();
    });

    it("renders active transfers with progress", async () => {
        window.api.get = vi.fn(async () => ({
            data: makePayload({
                transfers: [
                    {
                        id: "t1",
                        kind: "rncp",
                        label: "backup.tar",
                        direction: "tx",
                        peer: "cd".repeat(16),
                        done: 512,
                        total: 1024,
                        progress: 0.5,
                        started_at: 1,
                    },
                ],
            }),
        }));
        const wrapper = mountPage();
        await waitForData(wrapper);
        expect(wrapper.text()).toContain("Active transfers");
        expect(wrapper.text()).toContain("backup.tar");
        expect(wrapper.text()).toContain("50%");
        expect(wrapper.vm.transferRows).toHaveLength(1);
        wrapper.unmount();
    });

    it("notes when the peer table is truncated", async () => {
        window.api.get = vi.fn(async () => ({
            data: makePayload({ peers_total: 120 }),
        }));
        const wrapper = mountPage();
        await waitForData(wrapper);
        expect(wrapper.vm.peersNote).toContain("1");
        expect(wrapper.vm.peersNote).toContain("120");
        wrapper.unmount();
    });

    it("renders flood warnings as a warning hint", async () => {
        window.api.get = vi.fn(async () => ({
            data: makePayload({
                warnings: [
                    {
                        ts: 1,
                        component: "rrc",
                        label: "RRC hubs",
                        direction: "tx",
                        bps: 204800,
                        kbps: 200,
                    },
                ],
                hints: [
                    {
                        id: "flood_warning",
                        severity: "warning",
                        params: { component: "RRC hubs", kbps: 200, direction: "tx" },
                    },
                ],
            }),
        }));
        const wrapper = mountPage();
        await waitForData(wrapper);
        expect(wrapper.vm.hints[0].severity).toBe("warning");
        expect(wrapper.text()).toContain("RRC hubs");
        wrapper.unmount();
    });
});
