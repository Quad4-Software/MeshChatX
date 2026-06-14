import { describe, it, expect } from "vitest";
import {
    ANNOUNCE_HASH_CHUNK_SIZE,
    VIZ_ANNOUNCE_ASPECTS,
    dedupeIconQueueEntries,
    pathHashesWithinHopFilter,
    pickAdaptiveFetchConcurrency,
} from "@/js/networkVisualiserPerf.js";

describe("networkVisualiserPerf", () => {
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
        expect(pathHashesWithinHopFilter(pathTable, 4).sort()).toEqual(["aa", "bb"]);
        expect(pathHashesWithinHopFilter(pathTable, null).sort()).toEqual(["aa", "bb", "cc"]);
    });

    it("dedupeIconQueueEntries collapses duplicate cache keys", () => {
        const queue = [
            { nodeId: "n1", cacheKey: "k1", iconName: "a", fg: "#000", bg: "#fff", size: 64, generation: 1 },
            { nodeId: "n2", cacheKey: "k1", iconName: "a", fg: "#000", bg: "#fff", size: 64, generation: 1 },
            { nodeId: "n3", cacheKey: "k2", iconName: "b", fg: "#111", bg: "#eee", size: 64, generation: 1 },
        ];
        const out = dedupeIconQueueEntries(queue);
        expect(out).toHaveLength(2);
        expect(out.find((x) => x.cacheKey === "k1")?.nodeIds).toEqual(["n1", "n2"]);
    });

    it("pickAdaptiveFetchConcurrency returns a positive integer", () => {
        expect(pickAdaptiveFetchConcurrency()).toBeGreaterThanOrEqual(2);
    });
});
