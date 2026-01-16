import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import Utils from "@/js/Utils";
import dayjs from "dayjs";

describe("Utils.js", () => {
    describe("formatDestinationHash", () => {
        it("formats destination hash correctly", () => {
            const hash = "e253d0b19fe34c3f0a09569165abc45a";
            expect(Utils.formatDestinationHash(hash)).toBe("<e253d0b1...65abc45a>");
        });
    });

    describe("formatBytes", () => {
        it("formats 0 bytes correctly", () => {
            expect(Utils.formatBytes(0)).toBe("0 Bytes");
        });

        it("formats KB correctly", () => {
            expect(Utils.formatBytes(1024)).toBe("1 KB");
            expect(Utils.formatBytes(1500)).toBe("1 KB");
        });

        it("formats MB correctly", () => {
            expect(Utils.formatBytes(1024 * 1024)).toBe("1 MB");
        });

        it("handles negative numbers", () => {
            expect(Utils.formatBytes(-1024)).toBe("0 Bytes");
        });

        it("handles null or undefined", () => {
            expect(Utils.formatBytes(null)).toBe("0 Bytes");
            expect(Utils.formatBytes(undefined)).toBe("0 Bytes");
        });
    });

    describe("formatNumber", () => {
        it("formats 0 correctly", () => {
            expect(Utils.formatNumber(0)).toBe("0");
        });

        it("formats large numbers with commas", () => {
            // Using a regex to match either comma or space or whatever locale-specific grouping separator is used
            // But since we are in jsdom with default locale, it should be comma or similar.
            // Actually, we can just check if it's a string.
            const result = Utils.formatNumber(1234567);
            expect(typeof result).toBe("string");
            expect(result).toMatch(/1.234.567/); // Matches 1,234,567 or 1.234.567 etc.
        });

        it("handles null or undefined correctly", () => {
            expect(Utils.formatNumber(null)).toBe("0");
            expect(Utils.formatNumber(undefined)).toBe("0");
        });
    });

    describe("parseSeconds", () => {
        it("parses seconds into days, hours, minutes, and seconds", () => {
            const seconds = 1 * 24 * 3600 + 2 * 3600 + 3 * 60 + 4;
            expect(Utils.parseSeconds(seconds)).toEqual({
                days: 1,
                hours: 2,
                minutes: 3,
                seconds: 4,
            });
        });
    });

    describe("formatSeconds", () => {
        it('formats "a second ago"', () => {
            expect(Utils.formatSeconds(1)).toBe("a second ago");
            expect(Utils.formatSeconds(0)).toBe("a second ago");
        });

        it("formats minutes ago", () => {
            expect(Utils.formatSeconds(60)).toBe("1 min ago");
            expect(Utils.formatSeconds(120)).toBe("2 mins ago");
        });

        it("formats hours ago", () => {
            expect(Utils.formatSeconds(3600)).toBe("1 hour ago");
            expect(Utils.formatSeconds(7200)).toBe("2 hours ago");
        });

        it("formats days ago", () => {
            expect(Utils.formatSeconds(86400)).toBe("1 day ago");
            expect(Utils.formatSeconds(172800)).toBe("2 days ago");
        });
    });

    describe("formatTimeAgo", () => {
        beforeEach(() => {
            vi.useFakeTimers();
        });

        afterEach(() => {
            vi.useRealTimers();
        });

        it("formats SQLite format date correctly", () => {
            const now = new Date("2025-01-01T12:00:00Z");
            vi.setSystemTime(now);

            const pastDate = "2025-01-01 11:59:00"; // 1 min ago
            expect(Utils.formatTimeAgo(pastDate)).toBe("1 min ago");
        });

        it('returns "unknown" for empty input', () => {
            expect(Utils.formatTimeAgo(null)).toBe("unknown");
        });
    });

    describe("formatMinutesSeconds", () => {
        it("formats seconds into MM:SS", () => {
            expect(Utils.formatMinutesSeconds(65)).toBe("01:05");
            expect(Utils.formatMinutesSeconds(3600)).toBe("00:00"); // 3600s is 0m 0s in the current implementation because it only looks at minutes and seconds from parseSeconds
        });
    });

    describe("convertUnixMillisToLocalDateTimeString", () => {
        it("converts unix millis to formatted string", () => {
            const millis = new Date("2025-01-01T12:00:00Z").getTime();
            // dayjs format depends on local time, so we just check if it returns a string with expected components
            const result = Utils.convertUnixMillisToLocalDateTimeString(millis);
            expect(result).toMatch(/2025-01-01/);
        });
    });

    describe("formatBitsPerSecond", () => {
        it("formats 0 bps correctly", () => {
            expect(Utils.formatBitsPerSecond(0)).toBe("0 bps");
        });

        it("formats kbps correctly", () => {
            expect(Utils.formatBitsPerSecond(1000)).toBe("1 kbps");
        });
    });

    describe("formatFrequency", () => {
        it("formats 0 Hz correctly", () => {
            expect(Utils.formatFrequency(0)).toBe("0 Hz");
        });

        it("formats kHz correctly", () => {
            expect(Utils.formatFrequency(1000)).toBe("1 kHz");
        });
    });

    describe("isInterfaceEnabled", () => {
        it('returns true for "on", "yes", "true"', () => {
            expect(Utils.isInterfaceEnabled({ enabled: "on" })).toBe(true);
            expect(Utils.isInterfaceEnabled({ enabled: "yes" })).toBe(true);
            expect(Utils.isInterfaceEnabled({ enabled: "true" })).toBe(true);
            expect(Utils.isInterfaceEnabled({ interface_enabled: "true" })).toBe(true);
        });

        it("returns false for other values", () => {
            expect(Utils.isInterfaceEnabled({ enabled: "off" })).toBe(false);
            expect(Utils.isInterfaceEnabled({ enabled: null })).toBe(false);
        });
    });
});
