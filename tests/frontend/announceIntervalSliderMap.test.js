import { describe, expect, it } from "vitest";
import {
    ANNOUNCE_SLIDER_POS_MAX,
    announceMinutesToSliderPos,
    announceSliderPosToMinutes,
} from "@/js/announceIntervalSliderMap.js";

describe("announceIntervalSliderMap", () => {
    it("maps endpoints", () => {
        expect(announceSliderPosToMinutes(0)).toBe(1);
        expect(announceSliderPosToMinutes(ANNOUNCE_SLIDER_POS_MAX)).toBe(1440);
        expect(announceMinutesToSliderPos(1)).toBeGreaterThanOrEqual(0);
        expect(announceMinutesToSliderPos(1440)).toBeLessThanOrEqual(ANNOUNCE_SLIDER_POS_MAX);
    });

    it("round-trips common minute values", () => {
        for (const minutes of [1, 5, 15, 30, 60, 120, 360, 720, 1440]) {
            const pos = announceMinutesToSliderPos(minutes);
            expect(announceSliderPosToMinutes(pos)).toBe(minutes);
        }
    });

    it("increases monotonically across the track", () => {
        let prev = announceSliderPosToMinutes(0);
        for (let pos = 1; pos <= ANNOUNCE_SLIDER_POS_MAX; pos += 17) {
            const next = announceSliderPosToMinutes(pos);
            expect(next).toBeGreaterThanOrEqual(prev);
            prev = next;
        }
    });
});
