import { describe, it, expect } from "vitest";
import {
    normalizeRetentionValue,
    MAX_RETENTION_DAYS,
    MAX_RETENTION_MONTHS,
} from "../../meshchatx/src/frontend/js/localMessageRetention.js";

describe("localMessageRetention", () => {
    it("clamps day values", () => {
        expect(normalizeRetentionValue(5, "days")).toEqual({ value: 5, unit: "days" });
        expect(normalizeRetentionValue(99999, "days").value).toBe(MAX_RETENTION_DAYS);
        expect(normalizeRetentionValue(0, "days").value).toBe(1);
    });
    it("clamps month values", () => {
        expect(normalizeRetentionValue(2, "months")).toEqual({ value: 2, unit: "months" });
        expect(normalizeRetentionValue(500, "months").value).toBe(MAX_RETENTION_MONTHS);
    });
    it("defaults bad numbers to 1", () => {
        expect(normalizeRetentionValue("x", "days")).toEqual({ value: 1, unit: "days" });
    });
});
