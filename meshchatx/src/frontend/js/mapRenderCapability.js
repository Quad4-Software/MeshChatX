// SPDX-License-Identifier: 0BSD
/**
 * Basemap renderer capability detection and mode selection.
 *
 * The GPU path renders the PMTiles basemap through MapLibre (WebGL, worker
 * tile decode). The CPU path is the trimmed OpenLayers canvas vector layer.
 * Auto picks GPU only when a real hardware renderer is present, because
 * software WebGL (SwiftShader, llvmpipe) is slower than the CPU path.
 */

export const MAP_BASEMAP_RENDERER_KEY = "mcx.map-basemap-renderer";
export const MAP_BASEMAP_MODES = ["auto", "gpu", "cpu", "raster"];

const SOFTWARE_RENDERER_RE = /swiftshader|llvmpipe|softpipe|software|basic render|mali-4|angle \(google/i;

/**
 * Probe for a usable WebGL context and classify the renderer.
 * A context that exists but runs on a software rasterizer is reported
 * separately so callers can prefer the CPU path instead of trusting
 * "WebGL available" alone.
 * @returns {{available: boolean, software: boolean, renderer: string|null}}
 */
export function detectWebglSupport() {
    try {
        const canvas = document.createElement("canvas");
        const gl =
            canvas.getContext("webgl2", { failIfMajorPerformanceCaveat: false }) ||
            canvas.getContext("webgl", { failIfMajorPerformanceCaveat: false });
        if (!gl) {
            return { available: false, software: false, renderer: null };
        }
        let renderer = null;
        const dbg = gl.getExtension("WEBGL_debug_renderer_info");
        if (dbg) {
            renderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
        } else {
            renderer = gl.getParameter(gl.RENDERER);
        }
        const software = SOFTWARE_RENDERER_RE.test(renderer || "");
        if (typeof gl.getExtension === "function") {
            const lose = gl.getExtension("WEBGL_lose_context");
            if (lose) lose.loseContext();
        }
        return { available: true, software, renderer: renderer || null };
    } catch {
        return { available: false, software: false, renderer: null };
    }
}

export function getBasemapRendererSetting() {
    try {
        const raw = window.localStorage.getItem(MAP_BASEMAP_RENDERER_KEY);
        return MAP_BASEMAP_MODES.includes(raw) ? raw : "auto";
    } catch {
        return "auto";
    }
}

export function setBasemapRendererSetting(mode) {
    if (!MAP_BASEMAP_MODES.includes(mode)) return getBasemapRendererSetting();
    try {
        window.localStorage.setItem(MAP_BASEMAP_RENDERER_KEY, mode);
    } catch {
        // Storage can be denied. The in-memory choice still applies.
    }
    return mode;
}

/**
 * Resolve the effective renderer for a user setting plus probed caps.
 * @param {string} setting auto|gpu|cpu|raster
 * @param {{available: boolean, software: boolean}} caps
 * @returns {"gpu"|"cpu"|"raster"}
 */
export function resolveBasemapRenderer(setting, caps) {
    const mode = MAP_BASEMAP_MODES.includes(setting) ? setting : "auto";
    const webglOk = Boolean(caps && caps.available);
    const gpuFastEnough = webglOk && !caps.software;
    if (mode === "raster") {
        return "raster";
    }
    if (mode === "gpu") {
        return webglOk ? "gpu" : "cpu";
    }
    if (mode === "cpu") {
        return "cpu";
    }
    return gpuFastEnough ? "gpu" : "cpu";
}
