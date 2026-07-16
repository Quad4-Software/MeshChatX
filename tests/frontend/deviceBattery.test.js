// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    batteryStatusIconName,
    getDeviceBatteryStatus,
    normalizeBatteryPercent,
    normalizeBatteryStatus,
    parseAndroidBatteryPayload,
    shouldShowBatteryChip,
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

        it("uses web scale when source is web so level 1 means 100%", () => {
            expect(normalizeBatteryStatus({ level: 1, charging: true }, "web").level).toBe(100);
            expect(normalizeBatteryStatus({ level: 1, charging: false }, "android").level).toBe(1);
        });

        it("returns null when both level and charging are missing", () => {
            expect(normalizeBatteryStatus({ source: "web" })).toBe(null);
            expect(normalizeBatteryStatus({ level: "bad" })).toBe(null);
        });
    });

    describe("parseAndroidBatteryPayload edge cases", () => {
        it("handles object payloads and empty failures", () => {
            expect(parseAndroidBatteryPayload({ level: 9, charging: true })).toEqual({
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

    it("shows chip only when level is known", () => {
        expect(shouldShowBatteryChip(null)).toBe(false);
        expect(shouldShowBatteryChip({ supported: true, level: null })).toBe(false);
        expect(shouldShowBatteryChip({ supported: false, level: 50 })).toBe(false);
        expect(shouldShowBatteryChip({ supported: true, level: 0 })).toBe(true);
        expect(shouldShowBatteryChip({ supported: true, level: 55 })).toBe(true);
    });

    describe("getDeviceBatteryStatus probe order and failures", () => {
        it("prefers android bridge over web battery", async () => {
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

        it("falls back when android returns empty or throws", async () => {
            window.MeshChatXAndroid = {
                getBatteryStatus: () => {
                    throw new Error("bridge boom");
                },
            };
            navigator.getBattery = vi.fn(async () => ({ level: 0.33, charging: false }));
            await expect(getDeviceBatteryStatus()).resolves.toEqual({
                supported: true,
                level: 33,
                charging: false,
                source: "web",
            });

            window.MeshChatXAndroid = { getBatteryStatus: () => "" };
            await expect(getDeviceBatteryStatus()).resolves.toEqual({
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
            await expect(getDeviceBatteryStatus()).resolves.toEqual({
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
            await expect(getDeviceBatteryStatus()).resolves.toBe(null);

            navigator.getBattery = vi.fn(async () => null);
            await expect(getDeviceBatteryStatus()).resolves.toBe(null);
        });

        it("returns null when no probe is available", async () => {
            const status = await getDeviceBatteryStatus();
            expect(status).toBe(null);
        });
    });
});
