import { describe, it, expect, beforeEach } from "vitest";
import {
    loadVisualiserDisplayPrefs,
    persistVisualiserLiveLayout,
    persistVisualiserAutoReload,
    persistVisualiserShowDisabled,
    persistVisualiserShowDiscovered,
    persistVisualiserRenderer,
    persistVisualiserViewMode,
    normalizeVisualiserRenderer,
    normalizeVisualiserViewMode,
} from "@/js/settings/settingsVisualiserPrefs.js";

describe("settingsVisualiserPrefs", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("defaults live layout on, auto-reload off, renderer auto, view flat", () => {
        expect(loadVisualiserDisplayPrefs()).toEqual({
            showDisabledInterfaces: false,
            showDiscoveredInterfaces: false,
            enablePhysics: true,
            autoReload: false,
            renderer: "auto",
            viewMode: "flat",
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
            viewMode: "flat",
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

    it("normalizes and persists planet view mode", () => {
        expect(normalizeVisualiserViewMode("nope")).toBe("flat");
        persistVisualiserViewMode("planet");
        expect(loadVisualiserDisplayPrefs().viewMode).toBe("planet");
        persistVisualiserViewMode("flat", { emit: false });
        expect(loadVisualiserDisplayPrefs().viewMode).toBe("flat");
    });
});
