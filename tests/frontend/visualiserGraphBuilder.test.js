// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { buildVisualiserGraph } from "@/features/network-visualiser/lib/visualiserGraphBuilder.ts";
import { buildFullGraph } from "@/js/networkVisualiserPerf.js";

vi.mock("@/js/networkVisualiserPerf.js", async (importOriginal) => {
    const mod = await importOriginal();
    return {
        ...mod,
        buildFullGraph: vi.fn((req) => ({
            nodes: Object.keys(req.positions || {}).map((id) => ({
                id,
                x: req.positions[id].x,
                y: req.positions[id].y,
            })),
            edges: [],
            layout_nodes: Object.keys(req.positions || {}).map((id) => ({ id, fixed: false })),
            layout_edges: [],
        })),
    };
});

const baseOptions = () => ({
    config: { display_name: "Me", identity_hash: "abc" },
    interfaces: [{ name: "eth0", status: true, bitrate: 1000, txb: 0, rxb: 0 }],
    discoveredInterfaces: [],
    pathTable: [
        { hash: "node1", interface: "eth0", hops: 1 },
        { hash: "node2", interface: "eth0", hops: 2 },
    ],
    announces: {},
    conversations: {},
    showDisabledInterfaces: false,
    showDiscoveredInterfaces: false,
    searchQuery: "",
    hopMaxFilter: null,
    positions: {},
    isDarkMode: false,
    currentLOD: "high",
});

describe("visualiserGraphBuilder", () => {
    beforeEach(() => {
        vi.mocked(buildFullGraph).mockClear();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("radial mode pins every node on deterministic hop rings around me", () => {
        const graph = buildVisualiserGraph({ ...baseOptions(), radial: true });

        const req = vi.mocked(buildFullGraph).mock.calls[0][0];
        expect(req.positions.me).toEqual({ x: 0, y: 0 });
        expect(Math.hypot(req.positions.eth0.x, req.positions.eth0.y)).toBeCloseTo(300, 1);
        expect(Math.hypot(req.positions.node1.x, req.positions.node1.y)).toBeCloseTo(560, 1);
        expect(Math.hypot(req.positions.node2.x, req.positions.node2.y)).toBeCloseTo(790, 1);
        for (const n of graph.nodes) {
            expect(n.fixed).toBe(true);
        }
        for (const body of graph.layout_nodes) {
            expect(body.fixed).toBe(true);
        }
    });

    it("flat mode keeps existing positions and does not pin", () => {
        const graph = buildVisualiserGraph({
            ...baseOptions(),
            positions: { node1: { x: 12, y: 34 } },
            radial: false,
        });

        const req = vi.mocked(buildFullGraph).mock.calls[0][0];
        expect(req.positions.node1).toEqual({ x: 12, y: 34 });
        expect(req.positions.me).toBeUndefined();
        for (const n of graph.nodes) {
            // flat emits fixed explicitly so a stale radial pin cannot
            // survive vis-network's deep-merged node updates
            expect(n.fixed).toBe(n.id === "me" ? true : false);
        }
    });
});

describe("visualiserGraphBuilder JS fallback synthesis", () => {
    // Tests run without WASM globals, so isVisualiserWasmReady() is false and
    // the builder synthesizes me/ifaces/discovered in JS like the WASM path.
    const emptyGraph = () => ({ nodes: [], edges: [], layout_nodes: [], layout_edges: [], icon_queue: [] });

    beforeEach(() => {
        vi.mocked(buildFullGraph).mockClear();
        // Fresh object per call: the builder replaces graph.nodes/edges on
        // the returned object when it merges synthesized local nodes.
        vi.mocked(buildFullGraph).mockImplementation(() => emptyGraph());
    });

    afterEach(() => {
        vi.mocked(buildFullGraph).mockImplementation((req) => ({
            nodes: Object.keys(req.positions || {}).map((id) => ({
                id,
                x: req.positions[id].x,
                y: req.positions[id].y,
            })),
            edges: [],
            layout_nodes: Object.keys(req.positions || {}).map((id) => ({ id, fixed: false })),
            layout_edges: [],
        }));
    });

    it("sends the WASM full-graph request in the snake_case contract", () => {
        buildVisualiserGraph({ ...baseOptions(), showDiscoveredInterfaces: true });
        const req = vi.mocked(buildFullGraph).mock.calls[0][0];
        expect(req.me_label).toBe("Me");
        expect(req.identity_hash).toBe("abc");
        expect(Array.isArray(req.interfaces)).toBe(true);
        expect(Array.isArray(req.path_only_interfaces)).toBe(true);
        expect(Array.isArray(req.discovered)).toBe(true);
        expect(req.path_table).toEqual(baseOptions().pathTable);
        expect(req.dark_mode).toBe(false);
        expect(req.lod).toBe("high");
        expect(req.show_discovered).toBe(true);
    });

    it("renders discovered interface nodes in JS fallback mode", () => {
        const graph = buildVisualiserGraph({
            ...baseOptions(),
            showDiscoveredInterfaces: true,
            discoveredInterfaces: [
                {
                    name: "Peer Relay",
                    discovery_hash: "d1",
                    reachable_on: "10.9.0.1",
                    port: 4242,
                    hops: 1,
                    type: "TCPInterface",
                },
            ],
            discoveredActive: [{ target_host: "10.9.0.1", target_port: 4242 }],
        });
        const node = graph.nodes.find((n) => n.id === "discovered~d1");
        expect(node).toBeTruthy();
        expect(node.group).toBe("discovered");
        expect(node.image).toContain("interface_connected");
        // WASM parity: discovered nodes scatter on the 560-800 band.
        const r = Math.hypot(node.x, node.y);
        expect(r).toBeGreaterThanOrEqual(560);
        expect(r).toBeLessThanOrEqual(800);
        expect(graph.edges.some((e) => e.id === "me~discovered~d1")).toBe(true);
    });

    it("skips discovered nodes when showDiscoveredInterfaces is false", () => {
        const graph = buildVisualiserGraph({
            ...baseOptions(),
            showDiscoveredInterfaces: false,
            discoveredInterfaces: [{ name: "Peer", discovery_hash: "d1", hops: 1 }],
        });
        expect(graph.nodes.some((n) => n.id === "discovered~d1")).toBe(false);
    });

    it("applies hop_max to discovered nodes in JS fallback mode", () => {
        const graph = buildVisualiserGraph({
            ...baseOptions(),
            hopMaxFilter: 2,
            showDiscoveredInterfaces: true,
            discoveredInterfaces: [
                { name: "Near", discovery_hash: "dn", hops: 1 },
                { name: "Far", discovery_hash: "df", hops: 7 },
                { name: "NoHops", discovery_hash: "du" },
            ],
        });
        expect(graph.nodes.some((n) => n.id === "discovered~dn")).toBe(true);
        // null hops bypass hop_max, matching the WASM builder.
        expect(graph.nodes.some((n) => n.id === "discovered~du")).toBe(true);
        expect(graph.nodes.some((n) => n.id === "discovered~df")).toBe(false);
        expect(graph.edges.some((e) => e.id === "me~discovered~df")).toBe(false);
    });

    it("matches discovered nodes by reachable_on or transport_id in JS fallback mode", () => {
        const graph = buildVisualiserGraph({
            ...baseOptions(),
            searchQuery: "10.20.0",
            showDiscoveredInterfaces: true,
            discoveredInterfaces: [
                { name: "Alpha", discovery_hash: "da", reachable_on: "10.20.0.9", hops: 1 },
                { name: "Beta", discovery_hash: "db", transport_id: "ff10.20.0cc", hops: 1 },
                { name: "Gamma", discovery_hash: "dc", hops: 1 },
            ],
        });
        expect(graph.nodes.some((n) => n.id === "discovered~da")).toBe(true);
        expect(graph.nodes.some((n) => n.id === "discovered~db")).toBe(true);
        expect(graph.nodes.some((n) => n.id === "discovered~dc")).toBe(false);
    });

    it("does not emit me~iface edges when me is filtered out by search", () => {
        const graph = buildVisualiserGraph({
            ...baseOptions(),
            config: { display_name: "Home Node", identity_hash: "zzz" },
            searchQuery: "eth0",
            interfaces: [{ name: "eth0", status: true, bitrate: 0, txb: 0, rxb: 0 }],
            pathTable: [],
            showDiscoveredInterfaces: true,
            discoveredInterfaces: [{ name: "eth0-peer", discovery_hash: "d9", hops: 1 }],
        });
        expect(graph.nodes.some((n) => n.id === "me")).toBe(false);
        expect(graph.nodes.some((n) => n.id === "eth0")).toBe(true);
        expect(graph.nodes.some((n) => n.id === "discovered~d9")).toBe(true);
        expect(graph.edges.some((e) => e.id === "me~eth0")).toBe(false);
        expect(graph.edges.some((e) => e.id === "me~discovered~d9")).toBe(false);
    });

    it("spreads interface nodes on a circle instead of stacking them", () => {
        const graph = buildVisualiserGraph({
            ...baseOptions(),
            interfaces: [
                { name: "eth0", status: true, bitrate: 0, txb: 0, rxb: 0 },
                { name: "wlan0", status: true, bitrate: 0, txb: 0, rxb: 0 },
                { name: "tun0", status: true, bitrate: 0, txb: 0, rxb: 0 },
            ],
            pathTable: [],
        });
        const spots = ["eth0", "wlan0", "tun0"].map((id) => graph.nodes.find((n) => n.id === id));
        for (const n of spots) {
            expect(n).toBeTruthy();
            expect(Math.hypot(n.x, n.y)).toBeCloseTo(210, 1);
        }
        const unique = new Set(spots.map((n) => `${Math.round(n.x)},${Math.round(n.y)}`));
        expect(unique.size).toBe(3);
    });

    it("drops path edges whose endpoints were filtered out", () => {
        vi.mocked(buildFullGraph).mockReturnValue({
            nodes: [{ id: "node1", group: "announce" }],
            edges: [
                { id: "e1", from: "eth0", to: "node1" },
                { id: "e2", from: "ghost", to: "node1" },
            ],
            layout_nodes: [],
            layout_edges: [],
        });
        const graph = buildVisualiserGraph({
            ...baseOptions(),
            pathTable: [{ hash: "node1", interface: "eth0", hops: 1 }],
        });
        const ids = graph.edges.map((e) => e.id);
        expect(ids).toContain("e1");
        expect(ids).not.toContain("e2");
    });
});
