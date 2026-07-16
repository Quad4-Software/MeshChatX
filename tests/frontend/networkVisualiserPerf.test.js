import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    ANNOUNCE_HASH_CHUNK_SIZE,
    VIZ_ANNOUNCE_ASPECTS,
    buildPathGraph,
    buildPathGraphJs,
    computeLodUpdatesJs,
    dedupeIconQueueEntries,
    dedupeIconQueueEntriesJs,
    lodLevelFromScale,
    pathHashesWithinHopFilter,
    pathHashesWithinHopFilterJs,
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
        expect(buildPathGraph({ path_table: [], announces: {} }).nodes).toEqual([]);
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
});
