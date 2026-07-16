// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    appBatteryUsageToneClass,
    batteryStatusIconName,
    formatAppBatteryShareLabel,
    formatAppBatteryUsageLabel,
    formatProcessUptime,
    getDeviceBatteryStatus,
    isNativeBatteryStatus,
    normalizeBatteryPercent,
    normalizeBatteryStatus,
    parseAndroidBatteryPayload,
} from "@/js/deviceBattery.js";

describe("deviceBattery", () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        delete window.electron;
        delete window.MeshChatXAndroid;
        if (Object.prototype.hasOwnProperty.call(navigator, "getBattery")) {
            try {
                delete navigator.getBattery;
            } catch {
                navigator.getBattery = undefined;
            }
        }
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("normalizeBatteryPercent edge cases", () => {
        it("accepts 0 and 100 as native percents", () => {
            expect(normalizeBatteryPercent(0)).toBe(0);
            expect(normalizeBatteryPercent(100)).toBe(100);
        });

        it("keeps native 1% as 1, not 100", () => {
            expect(normalizeBatteryPercent(1)).toBe(1);
            expect(normalizeBatteryPercent(1, { unitFraction: false })).toBe(1);
        });

        it("scales web unit fractions including 0 and 1", () => {
            expect(normalizeBatteryPercent(0, { unitFraction: true })).toBe(0);
            expect(normalizeBatteryPercent(1, { unitFraction: true })).toBe(100);
            expect(normalizeBatteryPercent(0.42, { unitFraction: true })).toBe(42);
        });

        it("rejects NaN Infinity strings and out of range", () => {
            expect(normalizeBatteryPercent(Number.NaN)).toBe(null);
            expect(normalizeBatteryPercent(Number.POSITIVE_INFINITY)).toBe(null);
            expect(normalizeBatteryPercent("nope")).toBe(null);
            expect(normalizeBatteryPercent(-1)).toBe(null);
            expect(normalizeBatteryPercent(101)).toBe(null);
            expect(normalizeBatteryPercent(undefined)).toBe(null);
        });

        it("treats ambiguous mid floats as fractions", () => {
            expect(normalizeBatteryPercent(0.5)).toBe(50);
        });
    });

    describe("normalizeBatteryStatus edge cases", () => {
        it("rejects arrays and non-objects", () => {
            expect(normalizeBatteryStatus([])).toBe(null);
            expect(normalizeBatteryStatus("x")).toBe(null);
            expect(normalizeBatteryStatus(null)).toBe(null);
        });

        it("accepts charging-only electron payloads without level", () => {
            expect(normalizeBatteryStatus({ on_battery: true }, "electron")).toEqual({
                supported: true,
                level: null,
                charging: false,
                source: "electron",
            });
        });

        it("parses string and numeric charging flags", () => {
            expect(normalizeBatteryStatus({ level: 10, charging: "true" }).charging).toBe(true);
            expect(normalizeBatteryStatus({ level: 10, charging: "0" }).charging).toBe(false);
            expect(normalizeBatteryStatus({ level: 10, charging: 1 }).charging).toBe(true);
            expect(normalizeBatteryStatus({ level: 10, is_charging: false }).charging).toBe(false);
        });

        it("uses unitFraction only for web source when level is 1", () => {
            expect(normalizeBatteryStatus({ level: 1, charging: true }, "web").level).toBe(100);
            expect(normalizeBatteryStatus({ level: 1, charging: false }, "android").level).toBe(1);
        });

        it("rejects empty objects without level or charging", () => {
            expect(normalizeBatteryStatus({ source: "web" })).toBe(null);
            expect(normalizeBatteryStatus({ level: "bad" })).toBe(null);
        });
    });

    describe("parseAndroidBatteryPayload", () => {
        it("parses JSON strings and objects", () => {
            expect(parseAndroidBatteryPayload('{"level":9,"charging":true}')).toEqual({
                supported: true,
                level: 9,
                charging: true,
                source: "android",
            });
            expect(parseAndroidBatteryPayload("")).toBe(null);
            expect(parseAndroidBatteryPayload(null)).toBe(null);
            expect(parseAndroidBatteryPayload("not-json")).toBe(null);
            expect(parseAndroidBatteryPayload("[]")).toBe(null);
            expect(parseAndroidBatteryPayload('{"level":999}')).toBe(null);
        });
    });

    it("picks icon names across thresholds", () => {
        expect(batteryStatusIconName(null)).toBe("battery-unknown");
        expect(batteryStatusIconName({ supported: false })).toBe("battery-unknown");
        expect(batteryStatusIconName({ supported: true, charging: true, level: 40 })).toBe("battery-charging");
        expect(batteryStatusIconName({ supported: true, charging: false, level: null })).toBe("battery");
        expect(batteryStatusIconName({ supported: true, charging: false, level: 0 })).toBe("battery-alert");
        expect(batteryStatusIconName({ supported: true, charging: false, level: 15 })).toBe("battery-alert");
        expect(batteryStatusIconName({ supported: true, charging: false, level: 30 })).toBe("battery-low");
        expect(batteryStatusIconName({ supported: true, charging: false, level: 90 })).toBe("battery");
        expect(batteryStatusIconName({ supported: true, charging: false, level: 55 })).toBe("battery-medium");
    });

    it("marks only android and electron as native battery sources", () => {
        expect(isNativeBatteryStatus(null)).toBe(false);
        expect(isNativeBatteryStatus({ supported: true, source: "web", level: 100 })).toBe(false);
        expect(isNativeBatteryStatus({ supported: true, source: "android", level: 50 })).toBe(true);
        expect(isNativeBatteryStatus({ supported: true, source: "electron", level: 12 })).toBe(true);
    });

    it("formats process uptime from create_time", () => {
        const now = 1_700_000_000_000;
        expect(formatProcessUptime(now / 1000 - 45, now)).toBe("45s");
        expect(formatProcessUptime(now / 1000 - 125, now)).toBe("2m 5s");
        expect(formatProcessUptime(now / 1000 - 3700, now)).toBe("1h 1m");
        expect(formatProcessUptime(now / 1000 - 90000, now)).toBe("1d 1h");
        expect(formatProcessUptime(null)).toBe(null);
    });

    it("formats estimated app battery usage labels", () => {
        const t = (key, values = {}) => {
            if (key === "about.app_battery_use_warming") return "warming";
            if (key === "about.app_battery_use_with_intensity") {
                return `~${values.rate} (${values.intensity})`;
            }
            if (key === "about.app_battery_use_rate") return `~${values.rate}`;
            if (key.startsWith("about.app_battery_intensity_")) return key.split("_").pop();
            if (key === "about.app_battery_share_value") return `${values.percent}% of device`;
            return key;
        };
        expect(formatAppBatteryUsageLabel({ confidence: "warming_up" }, t)).toBe("warming");
        expect(
            formatAppBatteryUsageLabel(
                {
                    confidence: "estimate",
                    estimated_percent_per_hour: 1.4,
                    intensity: "moderate",
                },
                t
            )
        ).toBe("~1.4%/hr (moderate)");
        expect(formatAppBatteryShareLabel({ machine_share_percent: 2.5 }, t)).toBe("2.5% of device");
        expect(appBatteryUsageToneClass({ intensity: "high" })).toContain("amber");
    });

    describe("getDeviceBatteryStatus probe order and failures", () => {
        it("prefers android bridge and skips web by default", async () => {
            window.MeshChatXAndroid = {
                getBatteryStatus: () => '{"level":77,"charging":true}',
            };
            navigator.getBattery = vi.fn(async () => ({ level: 0.1, charging: false }));
            const status = await getDeviceBatteryStatus();
            expect(status).toEqual({
                supported: true,
                level: 77,
                charging: true,
                source: "android",
            });
            expect(navigator.getBattery).not.toHaveBeenCalled();
        });

        it("ignores docker-style web battery unless allowWeb is set", async () => {
            navigator.getBattery = vi.fn(async () => ({ level: 1, charging: true }));
            await expect(getDeviceBatteryStatus()).resolves.toBe(null);
            expect(navigator.getBattery).not.toHaveBeenCalled();

            await expect(getDeviceBatteryStatus({ allowWeb: true })).resolves.toEqual({
                supported: true,
                level: 100,
                charging: true,
                source: "web",
            });
        });

        it("falls back to web only when allowWeb and android fails", async () => {
            window.MeshChatXAndroid = {
                getBatteryStatus: () => {
                    throw new Error("bridge boom");
                },
            };
            navigator.getBattery = vi.fn(async () => ({ level: 0.33, charging: false }));
            await expect(getDeviceBatteryStatus()).resolves.toBe(null);
            await expect(getDeviceBatteryStatus({ allowWeb: true })).resolves.toEqual({
                supported: true,
                level: 33,
                charging: false,
                source: "web",
            });
        });

        it("uses electron before web and survives electron rejection", async () => {
            window.electron = {
                getBatteryStatus: vi.fn().mockResolvedValue({
                    level: 12,
                    charging: false,
                    on_battery: true,
                }),
            };
            navigator.getBattery = vi.fn(async () => ({ level: 0.9, charging: true }));
            await expect(getDeviceBatteryStatus()).resolves.toEqual({
                supported: true,
                level: 12,
                charging: false,
                source: "electron",
            });
            expect(navigator.getBattery).not.toHaveBeenCalled();

            window.electron.getBatteryStatus = vi.fn().mockRejectedValue(new Error("ipc fail"));
            await expect(getDeviceBatteryStatus()).resolves.toBe(null);
            await expect(getDeviceBatteryStatus({ allowWeb: true })).resolves.toEqual({
                supported: true,
                level: 90,
                charging: true,
                source: "web",
            });
        });

        it("returns null when web getBattery rejects or returns empty", async () => {
            navigator.getBattery = vi.fn(async () => {
                throw new Error("denied");
            });
            await expect(getDeviceBatteryStatus({ allowWeb: true })).resolves.toBe(null);

            navigator.getBattery = vi.fn(async () => null);
            await expect(getDeviceBatteryStatus({ allowWeb: true })).resolves.toBe(null);
        });

        it("returns null when no probe is available", async () => {
            const status = await getDeviceBatteryStatus();
            expect(status).toBe(null);
        });
    });
});
