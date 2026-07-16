import { describe, it, expect, beforeEach } from "vitest";
import {
    loadVisualiserDisplayPrefs,
    persistVisualiserLiveLayout,
    persistVisualiserAutoReload,
    persistVisualiserShowDisabled,
    persistVisualiserShowDiscovered,
    persistVisualiserRenderer,
    normalizeVisualiserRenderer,
} from "@/js/settings/settingsVisualiserPrefs.js";

describe("settingsVisualiserPrefs", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("defaults live layout on, auto-reload off, renderer auto", () => {
        expect(loadVisualiserDisplayPrefs()).toEqual({
            showDisabledInterfaces: false,
            showDiscoveredInterfaces: false,
            enablePhysics: true,
            autoReload: false,
            renderer: "auto",
        });
    });

    it("persists live layout and auto-reload across loads", () => {
        persistVisualiserLiveLayout(false);
        persistVisualiserAutoReload(true);
        persistVisualiserShowDisabled(true);
        persistVisualiserShowDiscovered(true);
        expect(loadVisualiserDisplayPrefs()).toEqual({
            showDisabledInterfaces: true,
            showDiscoveredInterfaces: true,
            enablePhysics: false,
            autoReload: true,
            renderer: "auto",
        });
        persistVisualiserLiveLayout(true);
        expect(loadVisualiserDisplayPrefs().enablePhysics).toBe(true);
    });

    it("can persist live layout without emitting rebuild events", () => {
        persistVisualiserLiveLayout(false, { emit: false });
        expect(loadVisualiserDisplayPrefs().enablePhysics).toBe(false);
        persistVisualiserAutoReload(true, { emit: false });
        expect(loadVisualiserDisplayPrefs().autoReload).toBe(true);
    });

    it("normalizes and persists renderer preference", () => {
        expect(normalizeVisualiserRenderer("nope")).toBe("auto");
        persistVisualiserRenderer("webgl");
        expect(loadVisualiserDisplayPrefs().renderer).toBe("webgl");
        persistVisualiserRenderer("vis", { emit: false });
        expect(loadVisualiserDisplayPrefs().renderer).toBe("vis");
    });
});
