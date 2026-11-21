// SPDX-License-Identifier: 0BSD
import { describe, it, expect, beforeEach } from "vitest";
import {
    detectWebglSupport,
    resolveBasemapRenderer,
    getBasemapRendererSetting,
    setBasemapRendererSetting,
    MAP_BASEMAP_RENDERER_KEY,
} from "../../meshchatx/src/frontend/js/mapRenderCapability.js";

describe("mapRenderCapability", () => {
    beforeEach(() => {
        window.localStorage.clear();
    });

    it("reports no WebGL when context creation fails", () => {
        // jsdom canvases return null from getContext, which is the same
        // shape as a shell with WebGL blocked.
        const caps = detectWebglSupport();
        expect(caps.available).toBe(false);
        expect(caps.software).toBe(false);
        expect(caps.renderer).toBe(null);
    });

    it("auto picks gpu only for hardware WebGL", () => {
        expect(resolveBasemapRenderer("auto", { available: true, software: false })).toBe("gpu");
        expect(resolveBasemapRenderer("auto", { available: true, software: true })).toBe("cpu");
        expect(resolveBasemapRenderer("auto", { available: false, software: false })).toBe("cpu");
    });

    it("gpu falls back to cpu when the context is unavailable", () => {
        expect(resolveBasemapRenderer("gpu", { available: true, software: true })).toBe("gpu");
        expect(resolveBasemapRenderer("gpu", { available: false, software: false })).toBe("cpu");
    });

    it("cpu and raster ignore the probe", () => {
        expect(resolveBasemapRenderer("cpu", { available: true, software: false })).toBe("cpu");
        expect(resolveBasemapRenderer("raster", { available: true, software: false })).toBe("raster");
    });

    it("unknown settings resolve as auto", () => {
        expect(resolveBasemapRenderer("bogus", { available: true, software: false })).toBe("gpu");
        expect(resolveBasemapRenderer("", { available: false })).toBe("cpu");
    });

    it("setting persists and rejects unknown values", () => {
        expect(getBasemapRendererSetting()).toBe("auto");
        setBasemapRendererSetting("raster");
        expect(window.localStorage.getItem(MAP_BASEMAP_RENDERER_KEY)).toBe("raster");
        expect(getBasemapRendererSetting()).toBe("raster");
        setBasemapRendererSetting("bogus");
        expect(getBasemapRendererSetting()).toBe("raster");
    });
});
