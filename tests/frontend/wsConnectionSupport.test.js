import { describe, expect, it, vi } from "vitest";
import {
    formatDisconnectedDuration,
    getNextReconnectDelayMs,
    reconnectDelayWithJitterMs,
} from "../../meshchatx/src/frontend/js/wsConnectionSupport";

describe("getNextReconnectDelayMs", () => {
    it("doubles exponentially and caps at max", () => {
        expect(getNextReconnectDelayMs(0, 1000, 60000)).toBe(1000);
        expect(getNextReconnectDelayMs(1, 1000, 60000)).toBe(2000);
        expect(getNextReconnectDelayMs(2, 1000, 60000)).toBe(4000);
        expect(getNextReconnectDelayMs(16, 1000, 60000)).toBe(60000);
    });
});

describe("reconnectDelayWithJitterMs", () => {
    it("adds jitter in range", () => {
        vi.spyOn(Math, "random").mockReturnValue(0.5);
        expect(reconnectDelayWithJitterMs(0, 1000, 60000, 400)).toBe(1200);
        vi.mocked(Math.random).mockRestore();
    });
});

describe("formatDisconnectedDuration", () => {
    it("formats seconds", () => {
        expect(formatDisconnectedDuration(0)).toBe("0s");
        expect(formatDisconnectedDuration(1500)).toBe("1s");
        expect(formatDisconnectedDuration(59000)).toBe("59s");
    });
    it("formats minutes", () => {
        expect(formatDisconnectedDuration(60000)).toBe("1m");
        expect(formatDisconnectedDuration(125000)).toBe("2m 5s");
    });
    it("formats hours and days", () => {
        expect(formatDisconnectedDuration(3600000)).toBe("1h");
        expect(formatDisconnectedDuration(3720000)).toBe("1h 2m");
        expect(formatDisconnectedDuration(86400000)).toBe("1d");
        expect(formatDisconnectedDuration(90000000)).toBe("1d 1h");
    });
});
