// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    splitBitrate,
    joinBitrate,
    splitDurationSeconds,
    joinDurationSeconds,
} from "../../meshchatx/src/frontend/js/interfaces/unitConversion.js";

describe("splitBitrate", () => {
    it("keeps small values in bps", () => {
        expect(splitBitrate(500)).toEqual({ value: 500, unit: "bps" });
    });

    it("uses kbps for values of a thousand and up", () => {
        expect(splitBitrate(20000)).toEqual({ value: 20, unit: "kbps" });
        expect(splitBitrate(57600)).toEqual({ value: 57.6, unit: "kbps" });
    });

    it("uses Mbps for millions", () => {
        expect(splitBitrate(5000000)).toEqual({ value: 5, unit: "Mbps" });
        expect(splitBitrate(2500000)).toEqual({ value: 2.5, unit: "Mbps" });
    });

    it("accepts numeric strings", () => {
        expect(splitBitrate("1000000")).toEqual({ value: 1, unit: "Mbps" });
    });

    it("returns null value with a default unit for empty input", () => {
        expect(splitBitrate(null)).toEqual({ value: null, unit: "kbps" });
        expect(splitBitrate("")).toEqual({ value: null, unit: "kbps" });
        expect(splitBitrate(0)).toEqual({ value: null, unit: "kbps" });
    });
});

describe("joinBitrate", () => {
    it("converts display values back to raw bps", () => {
        expect(joinBitrate(20, "kbps")).toBe(20000);
        expect(joinBitrate(2.5, "Mbps")).toBe(2500000);
        expect(joinBitrate(500, "bps")).toBe(500);
    });

    it("rounds to whole bits", () => {
        expect(joinBitrate(1.2345678, "Mbps")).toBe(1234568);
    });

    it("returns null for empty input", () => {
        expect(joinBitrate("", "kbps")).toBeNull();
        expect(joinBitrate(null, "kbps")).toBeNull();
    });

    it("round-trips with splitBitrate", () => {
        for (const bps of [1, 999, 1000, 57600, 250000, 5000000, 10000000]) {
            const split = splitBitrate(bps);
            expect(joinBitrate(split.value, split.unit)).toBe(bps);
        }
    });
});

describe("splitDurationSeconds", () => {
    it("keeps non-divisible values in seconds", () => {
        expect(splitDurationSeconds(90)).toEqual({ value: 90, unit: "seconds" });
        expect(splitDurationSeconds(5)).toEqual({ value: 5, unit: "seconds" });
        expect(splitDurationSeconds(0.1)).toEqual({ value: 0.1, unit: "seconds" });
    });

    it("uses minutes for whole-minute values", () => {
        expect(splitDurationSeconds(360)).toEqual({ value: 6, unit: "minutes" });
        expect(splitDurationSeconds(600)).toEqual({ value: 10, unit: "minutes" });
        expect(splitDurationSeconds(720)).toEqual({ value: 12, unit: "minutes" });
    });

    it("uses hours for whole-hour values", () => {
        expect(splitDurationSeconds(3600)).toEqual({ value: 1, unit: "hours" });
        expect(splitDurationSeconds(7200)).toEqual({ value: 2, unit: "hours" });
    });

    it("returns null value for empty input", () => {
        expect(splitDurationSeconds(null)).toEqual({ value: null, unit: "seconds" });
        expect(splitDurationSeconds("")).toEqual({ value: null, unit: "seconds" });
    });
});

describe("joinDurationSeconds", () => {
    it("converts display values back to raw seconds", () => {
        expect(joinDurationSeconds(10, "minutes")).toBe(600);
        expect(joinDurationSeconds(2, "hours")).toBe(7200);
        expect(joinDurationSeconds(45, "seconds")).toBe(45);
    });

    it("supports fractional display values", () => {
        expect(joinDurationSeconds(1.5, "minutes")).toBe(90);
    });

    it("returns null for empty input", () => {
        expect(joinDurationSeconds("", "seconds")).toBeNull();
        expect(joinDurationSeconds(null, "minutes")).toBeNull();
    });

    it("round-trips with splitDurationSeconds", () => {
        for (const seconds of [5, 90, 360, 600, 720, 3600, 7200]) {
            const split = splitDurationSeconds(seconds);
            expect(joinDurationSeconds(split.value, split.unit)).toBe(seconds);
        }
    });
});
