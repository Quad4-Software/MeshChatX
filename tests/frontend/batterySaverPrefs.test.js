import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
    BATTERY_SAVER_DEFAULTS,
    loadBatterySaverPrefs,
    saveBatterySaverPrefs,
    normalizeBatterySaverPrefs,
    applyBackgroundPollInterval,
    effectiveVisualiserReloadMs,
    activeBatterySaverMeasures,
    BATTERY_SAVER_STORAGE_KEY,
} from "@/js/settings/batterySaverPrefs.js";

describe("batterySaverPrefs", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("loads defaults when empty", () => {
        const loaded = loadBatterySaverPrefs();
        expect(loaded.enabled).toBe(false);
        expect(loaded.applyInterfaceBitrateLimits).toBe(false);
        expect(loaded.interfaceBitrateLimits).toEqual({});
    });

    it("round-trips prefs through localStorage", () => {
        const saved = saveBatterySaverPrefs({
            enabled: true,
            maxVisualiserInterfaces: 4,
            visualiserReloadSeconds: 90,
            backgroundPollMultiplier: 4,
            applyInterfaceBitrateLimits: true,
            interfaceBitrateLimits: { LoRa: 1200 },
        });
        expect(saved.enabled).toBe(true);
        expect(saved.maxVisualiserInterfaces).toBe(4);
        expect(saved.interfaceBitrateLimits.LoRa).toBe(1200);
        expect(JSON.parse(localStorage.getItem(BATTERY_SAVER_STORAGE_KEY)).enabled).toBe(true);
        expect(loadBatterySaverPrefs().visualiserReloadSeconds).toBe(90);
    });

    it("clamps numeric fields", () => {
        const n = normalizeBatterySaverPrefs({
            enabled: true,
            maxVisualiserInterfaces: 999,
            backgroundPollMultiplier: 1,
            visualiserReloadSeconds: -5,
            interfacesStatsPollSeconds: 0,
            interfacesDiscoveryPollSeconds: 1,
        });
        expect(n.maxVisualiserInterfaces).toBe(128);
        expect(n.backgroundPollMultiplier).toBe(2);
        expect(n.visualiserReloadSeconds).toBe(0);
        expect(n.interfacesStatsPollSeconds).toBe(1);
        expect(n.interfacesDiscoveryPollSeconds).toBe(5);
    });

    it("applyBackgroundPollInterval only scales when enabled", () => {
        expect(applyBackgroundPollInterval(1000, { ...BATTERY_SAVER_DEFAULTS, enabled: false })).toBe(1000);
        expect(
            applyBackgroundPollInterval(1000, {
                ...BATTERY_SAVER_DEFAULTS,
                enabled: true,
                reduceBackgroundPolling: true,
                backgroundPollMultiplier: 3,
            })
        ).toBe(3000);
    });

    it("effectiveVisualiserReloadMs disables or slows auto-reload", () => {
        expect(effectiveVisualiserReloadMs(15000, { ...BATTERY_SAVER_DEFAULTS, enabled: false })).toBe(15000);
        expect(
            effectiveVisualiserReloadMs(15000, {
                ...BATTERY_SAVER_DEFAULTS,
                enabled: true,
                visualiserReloadSeconds: 0,
            })
        ).toBeNull();
        expect(
            effectiveVisualiserReloadMs(15000, {
                ...BATTERY_SAVER_DEFAULTS,
                enabled: true,
                visualiserReloadSeconds: 60,
            })
        ).toBe(60000);
    });

    it("activeBatterySaverMeasures lists enabled knobs", () => {
        expect(activeBatterySaverMeasures({ ...BATTERY_SAVER_DEFAULTS, enabled: false })).toEqual([]);
        const measures = activeBatterySaverMeasures({
            ...BATTERY_SAVER_DEFAULTS,
            enabled: true,
            interfaceBitrateLimits: {},
            interfaceBitratePrevious: {},
        });
        expect(measures).toContain("disableVisualiserDiscovery");
        expect(measures).toContain("reduceBackgroundPolling");
        expect(measures).not.toContain("applyInterfaceBitrateLimits");
        expect(
            activeBatterySaverMeasures({
                ...BATTERY_SAVER_DEFAULTS,
                enabled: true,
                applyInterfaceBitrateLimits: true,
                interfaceBitrateLimits: { A: 1000 },
                interfaceBitratePrevious: {},
            })
        ).toContain("applyInterfaceBitrateLimits");
    });
});
