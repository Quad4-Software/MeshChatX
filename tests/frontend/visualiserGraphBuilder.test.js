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
            expect(n.fixed).toBeUndefined();
        }
    });
});
