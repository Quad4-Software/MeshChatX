import { describe, it, expect } from "vitest";
import {
    HOP_SLIDER_POS_ALL,
    hopSliderPosToMaxHops,
    hopMaxHopsToSliderPos,
} from "@/components/network-visualiser/internal/hopMaxFilterSliderMap.js";

describe("hopMaxFilterSliderMap", () => {
    it("maps rightmost slider position to unlimited hops", () => {
        expect(hopSliderPosToMaxHops(HOP_SLIDER_POS_ALL)).toBe(null);
        expect(hopSliderPosToMaxHops(HOP_SLIDER_POS_ALL + 10)).toBe(null);
    });

    it("round-trips every hop count 0..128", () => {
        for (let h = 0; h <= 128; h++) {
            const pos = hopMaxHopsToSliderPos(h);
            expect(hopSliderPosToMaxHops(pos)).toBe(h);
        }
    });

    it("round-trips null as the all position", () => {
        expect(hopMaxHopsToSliderPos(null)).toBe(HOP_SLIDER_POS_ALL);
        expect(hopSliderPosToMaxHops(HOP_SLIDER_POS_ALL)).toBe(null);
    });
});
