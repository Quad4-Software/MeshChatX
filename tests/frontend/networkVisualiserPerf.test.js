import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    ANNOUNCE_HASH_CHUNK_SIZE,
    VIZ_ANNOUNCE_ASPECTS,
    buildPathGraph,
    buildPathGraphJs,
    computeLodUpdatesJs,
    computeRadialPositions,
    declutterLabelBoxes,
    dedupeIconQueueEntries,
    dedupeIconQueueEntriesJs,
    hashposXY,
    lodLevelFromScale,
    pathHashesWithinHopFilter,
    pathHashesWithinHopFilterJs,
    layoutSpringLength,
    pickAdaptiveFetchConcurrency,
} from "@/js/networkVisualiserPerf.js";

describe("networkVisualiserPerf", () => {
    beforeEach(() => {
        delete globalThis.meshchatxVisualiserPathHashes;
        delete globalThis.meshchatxVisualiserDedupeIcons;
        delete globalThis.meshchatxVisualiserBuildPathGraph;
        delete globalThis.meshchatxVisualiserLODLevel;
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("exports visualiser constants", () => {
        expect(VIZ_ANNOUNCE_ASPECTS).toEqual(["lxmf.delivery", "nomadnetwork.node"]);
        expect(ANNOUNCE_HASH_CHUNK_SIZE).toBe(500);
        expect(layoutSpringLength(3)).toBe(250);
        expect(layoutSpringLength(1)).toBe(300);
    });

    it("pathHashesWithinHopFilter respects hop max", () => {
        const pathTable = [
            { hash: "aa", hops: 1 },
            { hash: "bb", hops: 4 },
            { hash: "cc", hops: 5 },
            { hash: "dd", hops: null },
        ];
        expect(pathHashesWithinHopFilterJs(pathTable, 4).sort()).toEqual(["aa", "bb"]);
        expect(pathHashesWithinHopFilter(pathTable, null).sort()).toEqual(["aa", "bb", "cc"]);
    });

    it("dedupeIconQueueEntries collapses duplicate cache keys", () => {
        const queue = [
            { nodeId: "n1", cacheKey: "k1", iconName: "a", fg: "#000", bg: "#fff", size: 64, generation: 1 },
            { nodeId: "n2", cacheKey: "k1", iconName: "a", fg: "#000", bg: "#fff", size: 64, generation: 1 },
            { nodeId: "n3", cacheKey: "k2", iconName: "b", fg: "#111", bg: "#eee", size: 64, generation: 1 },
        ];
        const out = dedupeIconQueueEntriesJs(queue);
        expect(out).toHaveLength(2);
        expect(out.find((x) => x.cacheKey === "k1")?.nodeIds).toEqual(["n1", "n2"]);
        expect(dedupeIconQueueEntries(queue)).toHaveLength(2);
    });

    it("pickAdaptiveFetchConcurrency returns a positive integer", () => {
        expect(pickAdaptiveFetchConcurrency()).toBeGreaterThanOrEqual(2);
    });

    it("buildPathGraphJs filters hops and builds nodes/edges", () => {
        const res = buildPathGraphJs({
            path_table: [
                { hash: "aa", interface: "eth0", hops: 1 },
                { hash: "bb", interface: "eth0", hops: 9 },
            ],
            announces: {
                aa: {
                    destination_hash: "aa",
                    aspect: "lxmf.delivery",
                    display_name: "Alice",
                    last_seen: "now",
                },
                bb: {
                    destination_hash: "bb",
                    aspect: "lxmf.delivery",
                    display_name: "Far",
                    last_seen: "now",
                },
            },
            positions: { eth0: { x: 10, y: 20 } },
            hop_max: 4,
            dark_mode: false,
            lod: "high",
        });
        expect(res.nodes).toHaveLength(1);
        expect(res.edges).toHaveLength(1);
        expect(res.nodes[0].id).toBe("aa");
        expect(res.edges[0].width).toBe(2.5);
        const dx = res.nodes[0].x - 10;
        const dy = res.nodes[0].y - 20;
        expect(Math.hypot(dx, dy)).toBeGreaterThanOrEqual(140);
        expect(buildPathGraph({ path_table: [], announces: {} }).nodes).toEqual([]);
    });

    it("buildPathGraphJs falls back to display_name on empty custom_display_name", () => {
        const res = buildPathGraphJs({
            path_table: [{ hash: "aa", interface: "eth0", hops: 1 }],
            announces: {
                aa: {
                    destination_hash: "aa",
                    aspect: "lxmf.delivery",
                    display_name: "Alice",
                    custom_display_name: "",
                },
            },
            lod: "high",
        });
        expect(res.nodes[0].label).toBe("Alice");
        expect(res.nodes[0].title).toContain("Alice");
    });

    it("computeLodUpdatesJs restores the stashed semantic color after low LOD", () => {
        const semantic = { border: "#10b981", background: "#ecfdf5" };
        const stamped = { border: "#3b82f6", background: "#eff6ff" };
        const nodes = [
            {
                id: "n1",
                shape: "dot",
                size: 10,
                _originalShape: "circularImage",
                _originalSize: 25,
                _originalColor: semantic,
                color: stamped,
                font: { size: 0 },
            },
        ];
        const updates = computeLodUpdatesJs(nodes, "high", false, null);
        expect(updates).toHaveLength(1);
        expect(updates[0].color).toEqual(semantic);
        const med = computeLodUpdatesJs(nodes, "medium", false, null);
        expect(med[0].color).toEqual(semantic);
    });

    it("hashposXY hashes UTF-8 bytes like the Go helper", () => {
        // Independent reference: encode UTF-16 code points to UTF-8 bytes.
        const refFnv = (s) => {
            const bytes = [];
            for (const ch of s) {
                const cp = ch.codePointAt(0);
                if (cp < 0x80) bytes.push(cp);
                else if (cp < 0x800) bytes.push(0xc0 | (cp >> 6), 0x80 | (cp & 0x3f));
                else if (cp < 0x10000) bytes.push(0xe0 | (cp >> 12), 0x80 | ((cp >> 6) & 0x3f), 0x80 | (cp & 0x3f));
                else
                    bytes.push(
                        0xf0 | (cp >> 18),
                        0x80 | ((cp >> 12) & 0x3f),
                        0x80 | ((cp >> 6) & 0x3f),
                        0x80 | (cp & 0x3f)
                    );
            }
            let h = 2166136261;
            for (const b of bytes) {
                h ^= b;
                h = Math.imul(h, 16777619);
            }
            return h >>> 0;
        };
        const id = "café-/δ";
        const a = ((refFnv(id) % 10000) / 10000) * Math.PI * 2;
        const d = 560 + ((refFnv(`${id}\0r`) % 10000) / 10000) * 240;
        const p = hashposXY(id, 560, 240);
        expect(p.x).toBeCloseTo(Math.cos(a) * d, 10);
        expect(p.y).toBeCloseTo(Math.sin(a) * d, 10);
    });

    it("computeLodUpdatesJs and lodLevelFromScale work without WASM", () => {
        expect(lodLevelFromScale(0.1)).toBe("low");
        expect(lodLevelFromScale(0.3)).toBe("medium");
        expect(lodLevelFromScale(0.8)).toBe("high");
        const updates = computeLodUpdatesJs(
            [{ id: "n1", shape: "circularImage", size: 25, _originalShape: "circularImage", _originalSize: 25 }],
            "low",
            false
        );
        expect(updates[0].shape).toBe("dot");
    });

    it("falls back to JS when WASM export throws", () => {
        globalThis.meshchatxVisualiserPathHashes = () => {
            throw new Error("boom");
        };
        globalThis.meshchatxVisualiserBuildPathGraph = () => {
            throw new Error("boom");
        };
        globalThis.meshchatxVisualiserDedupeIcons = () => {
            throw new Error("boom");
        };
        expect(pathHashesWithinHopFilter([{ hash: "aa", hops: 1 }], 4)).toEqual(["aa"]);
        expect(dedupeIconQueueEntries([])).toEqual([]);
        expect(buildPathGraph({ path_table: [], announces: {} }).nodes).toEqual([]);
    });

    it("declutterLabelBoxes drops overlapping labels, first wins", () => {
        const keep = declutterLabelBoxes(
            [
                { id: "a", sx: 100, sy: 100, w: 60, h: 14 },
                { id: "b", sx: 110, sy: 105, w: 60, h: 14 },
                { id: "c", sx: 500, sy: 100, w: 60, h: 14 },
            ],
            4
        );
        expect(keep.has("a")).toBe(true);
        expect(keep.has("b")).toBe(false);
        expect(keep.has("c")).toBe(true);
        expect(declutterLabelBoxes([])).toEqual(new Set());
        expect(declutterLabelBoxes(null)).toEqual(new Set());
    });

    it("computeLodUpdatesJs hides labels outside the allowlist", () => {
        const nodes = [
            { id: "me", label: "Local", font: { size: 0 }, size: 10, _originalSize: 50 },
            { id: "n1", label: "Alice", font: { size: 0 }, size: 10, _originalSize: 25 },
            { id: "n2", label: "Bob", font: { size: 11 }, size: 25, _originalSize: 25 },
        ];
        const updates = computeLodUpdatesJs(nodes, "high", false, new Set(["me", "n1"]));
        const byId = Object.fromEntries(updates.map((u) => [u.id, u]));
        expect(byId.me.font.size).toBe(16);
        expect(byId.n1.font.size).toBe(11);
        expect(byId.n2.font.size).toBe(0);
        // Null allowlist keeps every label (WASM parity path).
        const all = computeLodUpdatesJs(nodes, "high", false, null);
        expect(all.find((u) => u.id === "n2").font.size).toBe(11);
    });

    it("computeRadialPositions lays out hop rings around me", () => {
        const pos = computeRadialPositions({
            interfaces: ["eth0"],
            discovered: ["discovered~x"],
            pathTable: [
                { hash: "h1", interface: "eth0", hops: 1 },
                { hash: "h2", interface: "eth0", hops: 1 },
                { hash: "h3", interface: "eth0", hops: 3 },
                { hash: "h4", interface: "eth0", hops: null },
                { hash: "h5", interface: "eth0", hops: 9 },
            ],
            hopMax: 4,
        });
        expect(pos.me).toEqual({ x: 0, y: 0 });
        expect(Math.hypot(pos.eth0.x, pos.eth0.y)).toBeCloseTo(300, 1);
        expect(Math.hypot(pos["discovered~x"].x, pos["discovered~x"].y)).toBeCloseTo(300, 1);
        // Hop-1 ring at 560, hop-3 ring at 560 + 2 * 230 = 1020.
        expect(Math.hypot(pos.h1.x, pos.h1.y)).toBeCloseTo(560, 1);
        expect(Math.hypot(pos.h2.x, pos.h2.y)).toBeCloseTo(560, 1);
        expect(Math.hypot(pos.h3.x, pos.h3.y)).toBeCloseTo(1020, 1);
        // Hop-less and over-max entries get no position.
        expect(pos.h4).toBeUndefined();
        expect(pos.h5).toBeUndefined();
        // Deterministic across calls.
        const again = computeRadialPositions({
            interfaces: ["eth0"],
            discovered: ["discovered~x"],
            pathTable: [
                { hash: "h1", interface: "eth0", hops: 1 },
                { hash: "h3", interface: "eth0", hops: 3 },
            ],
            hopMax: 4,
        });
        expect(again.h1).toEqual(pos.h1);
        expect(again.h3).toEqual(pos.h3);
    });
});
