import { describe, expect, it } from "vitest";
import {
    ANNOUNCE_SLIDER_POS_MAX,
    announceMinutesToSliderPos,
    announceSliderPosToMinutes,
    formatAnnounceIntervalMinutes,
    parseAnnounceIntervalMinutes,
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

describe("formatAnnounceIntervalMinutes", () => {
    it("shows minutes below an hour", () => {
        expect(formatAnnounceIntervalMinutes(1)).toBe("1 min");
        expect(formatAnnounceIntervalMinutes(45)).toBe("45 min");
    });

    it("shows hours for whole-hour values", () => {
        expect(formatAnnounceIntervalMinutes(60)).toBe("1 h");
        expect(formatAnnounceIntervalMinutes(360)).toBe("6 h");
    });

    it("combines hours and minutes", () => {
        expect(formatAnnounceIntervalMinutes(90)).toBe("1 h 30 min");
        expect(formatAnnounceIntervalMinutes(75)).toBe("1 h 15 min");
    });

    it("shows days at the day boundary", () => {
        expect(formatAnnounceIntervalMinutes(1440)).toBe("1 d");
    });

    it("handles zero and invalid input", () => {
        expect(formatAnnounceIntervalMinutes(0)).toBe("0 min");
        expect(formatAnnounceIntervalMinutes(-5)).toBe("0 min");
        expect(formatAnnounceIntervalMinutes(NaN)).toBe("0 min");
    });
});

describe("parseAnnounceIntervalMinutes", () => {
    it("parses bare numbers as minutes", () => {
        expect(parseAnnounceIntervalMinutes("45")).toBe(45);
        expect(parseAnnounceIntervalMinutes("0")).toBe(0);
        expect(parseAnnounceIntervalMinutes(" 90 ")).toBe(90);
    });

    it("parses unit suffixes", () => {
        expect(parseAnnounceIntervalMinutes("6h")).toBe(360);
        expect(parseAnnounceIntervalMinutes("45m")).toBe(45);
        expect(parseAnnounceIntervalMinutes("45min")).toBe(45);
        expect(parseAnnounceIntervalMinutes("1d")).toBe(1440);
    });

    it("parses composite values", () => {
        expect(parseAnnounceIntervalMinutes("1h 30m")).toBe(90);
        expect(parseAnnounceIntervalMinutes("1h30min")).toBe(90);
    });

    it("rejects unparseable input", () => {
        expect(parseAnnounceIntervalMinutes("")).toBeNull();
        expect(parseAnnounceIntervalMinutes("abc")).toBeNull();
        expect(parseAnnounceIntervalMinutes("6x")).toBeNull();
        expect(parseAnnounceIntervalMinutes("h")).toBeNull();
    });
});
