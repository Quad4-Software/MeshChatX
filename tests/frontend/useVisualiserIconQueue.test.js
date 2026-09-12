// SPDX-License-Identifier: 0BSD

import { describe, expect, it, vi } from "vitest";
import { useVisualiserIconQueue } from "../../meshchatx/src/frontend/js/network/useVisualiserIconQueue.js";

function entry(nodeId, cacheKey = "k1", generation = 0) {
    return { nodeId, cacheKey, iconName: "account", fg: "#fff", bg: "#000", size: 64, generation };
}

describe("useVisualiserIconQueue", () => {
    it("drains the queue and updates the nodes DataSet", async () => {
        const update = vi.fn();
        const get = vi.fn(() => ({}));
        const q = useVisualiserIconQueue({
            getNodes: () => ({ get, update }),
            createIconImage: vi.fn(async () => "blob:icon"),
            yieldToMain: vi.fn(async () => {}),
        });
        q.iconQueue.value = [entry("n1"), entry("n2")];
        await q.runIconQueue();
        expect(update).toHaveBeenCalledWith([
            { id: "n1", image: "blob:icon" },
            { id: "n2", image: "blob:icon" },
        ]);
        expect(q.iconQueue.value).toEqual([]);
        expect(q.iconQueueRunning.value).toBe(false);
    });

    it("uses the webgl engine when present", async () => {
        const updateNodeImages = vi.fn();
        const q = useVisualiserIconQueue({
            getWebglEngine: () => ({ updateNodeImages }),
            getNodes: () => ({ get: vi.fn(), update: vi.fn() }),
            createIconImage: vi.fn(async () => "blob:icon"),
            yieldToMain: vi.fn(async () => {}),
        });
        q.iconQueue.value = [entry("n1")];
        await q.runIconQueue();
        expect(updateNodeImages).toHaveBeenCalledWith([{ id: "n1", image: "blob:icon" }]);
    });

    it("skips stale-generation entries", async () => {
        const update = vi.fn();
        const q = useVisualiserIconQueue({
            getNodes: () => ({ get: vi.fn(() => ({})), update }),
            createIconImage: vi.fn(async () => "blob:icon"),
            yieldToMain: vi.fn(async () => {}),
        });
        q.iconQueueGeneration.value = 5;
        q.iconQueue.value = [entry("n1", "k1", 4)];
        await q.runIconQueue();
        expect(update).not.toHaveBeenCalled();
    });

    it("stops when the run is aborted mid-queue", async () => {
        const update = vi.fn();
        const signal = { aborted: false };
        const q = useVisualiserIconQueue({
            getAbortSignal: () => signal,
            getNodes: () => ({ get: vi.fn(() => ({})), update }),
            createIconImage: vi.fn(async () => {
                signal.aborted = true;
                return "blob:icon";
            }),
            yieldToMain: vi.fn(async () => {}),
        });
        q.iconQueue.value = [entry("n1"), entry("n2", "k2")];
        await q.runIconQueue();
        expect(update).not.toHaveBeenCalled();
    });

    it("serves repeated cache keys from iconCache without re-rendering", async () => {
        const update = vi.fn();
        const createIconImage = vi.fn(async () => "blob:new");
        const q = useVisualiserIconQueue({
            getNodes: () => ({ get: vi.fn(() => ({})), update }),
            createIconImage,
            yieldToMain: vi.fn(async () => {}),
        });
        q.iconCache.value["k1"] = "blob:cached";
        q.iconQueue.value = [entry("n1", "k1"), entry("n2", "k1")];
        await q.runIconQueue();
        expect(createIconImage).not.toHaveBeenCalled();
        expect(update).toHaveBeenCalledWith([
            { id: "n1", image: "blob:cached" },
            { id: "n2", image: "blob:cached" },
        ]);
    });
});
