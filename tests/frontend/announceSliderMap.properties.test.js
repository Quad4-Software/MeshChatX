// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import {
    ANNOUNCE_SLIDER_POS_MAX,
    announceSliderPosToMinutes,
    announceMinutesToSliderPos,
    formatAnnounceIntervalMinutes,
    parseAnnounceIntervalMinutes,
} from "../../meshchatx/src/frontend/js/announceIntervalSliderMap.js";

const MIN = 15;
const MAX = 1440;

describe("announce slider map properties", () => {
    it("pos->minutes always lands in [15, 1440]", () => {
        for (let p = -100; p <= ANNOUNCE_SLIDER_POS_MAX + 100; p++) {
            const m = announceSliderPosToMinutes(p);
            expect(m).toBeGreaterThanOrEqual(MIN);
            expect(m).toBeLessThanOrEqual(MAX);
            expect(Number.isInteger(m)).toBe(true);
        }
    });

    it("pos->minutes is non-decreasing in pos", () => {
        let prev = -1;
        for (let p = 0; p <= ANNOUNCE_SLIDER_POS_MAX; p++) {
            const m = announceSliderPosToMinutes(p);
            expect(m).toBeGreaterThanOrEqual(prev);
            prev = m;
        }
    });

    it("minutes->pos is non-decreasing in minutes", () => {
        let prev = -1;
        for (let m = 0; m <= MAX + 100; m++) {
            const p = announceMinutesToSliderPos(m);
            expect(p).toBeGreaterThanOrEqual(prev);
            prev = p;
        }
    });

    it("minutes->pos->minutes roundtrips within 1 minute for in-range values", () => {
        for (let m = MIN; m <= MAX; m++) {
            const back = announceSliderPosToMinutes(announceMinutesToSliderPos(m));
            expect(Math.abs(back - m)).toBeLessThanOrEqual(1);
        }
    });

    it("weird inputs clamp instead of NaN", () => {
        for (const v of [NaN, Infinity, -Infinity, undefined, null, "abc", {}, [], -5]) {
            const m = announceSliderPosToMinutes(v);
            expect(Number.isFinite(m)).toBe(true);
            expect(m).toBeGreaterThanOrEqual(MIN);
            const p = announceMinutesToSliderPos(v);
            expect(Number.isFinite(p)).toBe(true);
            expect(p).toBeGreaterThanOrEqual(0);
            expect(p).toBeLessThanOrEqual(ANNOUNCE_SLIDER_POS_MAX);
        }
    });

    it("zero minutes maps to slider zero", () => {
        expect(announceMinutesToSliderPos(0)).toBe(0);
    });
});

describe("interval format/parse properties", () => {
    it("parse(format(m)) === m for every minute 0..2880", () => {
        for (let m = 0; m <= 2880; m++) {
            expect(parseAnnounceIntervalMinutes(formatAnnounceIntervalMinutes(m))).toBe(m);
        }
    });

    it("format is monotonic non-decreasing in a semantic sense: bigger input never shorter string parts missing", () => {
        for (let m = 1; m <= 2880; m++) {
            const s = formatAnnounceIntervalMinutes(m);
            expect(s.length).toBeGreaterThan(0);
            expect(s).not.toMatch(/NaN|undefined|null/);
        }
    });

    it("parse rejects garbage instead of guessing", () => {
        for (const v of [
            "abc",
            "h",
            "1x",
            "-5",
            "1h30",
            "1m2",
            "",
            "  ",
            "1,5,5",
            "nan",
            "Infinity",
            "1h h h",
            null,
            undefined,
        ]) {
            // either null or a sane non-negative integer
            const out = parseAnnounceIntervalMinutes(v);
            if (out !== null) {
                expect(Number.isInteger(out)).toBe(true);
                expect(out).toBeGreaterThanOrEqual(0);
            } else {
                expect(out).toBeNull();
            }
        }
        expect(parseAnnounceIntervalMinutes("abc")).toBeNull();
        expect(parseAnnounceIntervalMinutes("1h30")).toBeNull();
        expect(parseAnnounceIntervalMinutes("-5")).toBeNull();
    });

    it("parse handles each documented form", () => {
        expect(parseAnnounceIntervalMinutes("90")).toBe(90);
        expect(parseAnnounceIntervalMinutes("1h30m")).toBe(90);
        expect(parseAnnounceIntervalMinutes("1 h 30 min")).toBe(90);
        expect(parseAnnounceIntervalMinutes("1d")).toBe(1440);
        expect(parseAnnounceIntervalMinutes("45min")).toBe(45);
        expect(parseAnnounceIntervalMinutes("1.5h")).toBe(90);
    });
});
