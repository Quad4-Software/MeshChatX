import { describe, it, expect } from "vitest";
import { mergeResourceBreakdown, topResourceByCpu, topResourceByRss } from "@/js/resourceBreakdown.js";

describe("resourceBreakdown", () => {
    it("merges electron private memory as bytes", () => {
        const rows = mergeResourceBreakdown([{ name: "backend", rss: 10_000_000, cpu_percent: 3 }], { private: 2048 });
        expect(rows).toHaveLength(2);
        expect(rows[1]).toEqual({ name: "electron", rss: 2048 * 1024, cpu_percent: null });
        expect(topResourceByRss(rows)?.name).toBe("backend");
        expect(topResourceByCpu(rows)?.name).toBe("backend");
    });

    it("picks top cpu when present", () => {
        const rows = mergeResourceBreakdown(
            [
                { name: "backend", rss: 10, cpu_percent: 1 },
                { name: "child:bot", rss: 5, cpu_percent: 40 },
            ],
            null
        );
        expect(topResourceByCpu(rows)?.name).toBe("child:bot");
        expect(topResourceByRss(rows)?.name).toBe("backend");
    });
});
