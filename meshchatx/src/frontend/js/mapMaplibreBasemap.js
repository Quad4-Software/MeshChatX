// SPDX-License-Identifier: 0BSD
/**
 * GPU basemap path: MapLibre GL JS rendering under OpenLayers.
 *
 * MapLibre decodes PMTiles vector tiles in web workers and rasterizes on
 * the GPU, which removes the main-thread MVT decode and ~70-layer canvas
 * replay that made the OpenLayers vector path slow. OpenLayers stays in
 * charge of the view and of every overlay, marker and drawing layer; this
 * custom Layer only paints a MapLibre canvas at the bottom of the stack.
 *
 * The layer follows the ol-maplibre-layer approach: on each OpenLayers
 * render frame we jumpTo the current view state and drive MapLibre's
 * synchronous render so both canvases stay pixel-aligned during pans.
 */
import Layer from "ol/layer/Layer.js";
import { toLonLat } from "ol/proj.js";
import { transformExtent } from "ol/proj.js";
import * as maplibregl from "maplibre-gl";
// Vite serves pre-bundled deps from a different URL than the worker file
// expects via import.meta.url, so tile decode workers 404 without this.
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "maplibre-gl/dist/maplibre-gl.css";
import { PMTiles, Protocol } from "pmtiles";
import { layers as basemapLayers, namedFlavor } from "@protomaps/basemaps";

import { getArchive, basemapStyleJson } from "./mapPmtilesBasemap.js";
import { getCachedPmtilesSource } from "./pmtilesCacheSource.js";
import { trimBasemapLayers } from "./mapStyleTrim.js";

// One global protocol registration; add() keys archives by source.getKey()
// so pmtiles://<url> style sources resolve to the cached-range archive.
const pmtilesProtocol = new Protocol();
let protocolRegistered = false;

function ensureProtocol() {
    if (protocolRegistered || typeof maplibregl.addProtocol !== "function") {
        protocolRegistered = true;
        return;
    }
    maplibregl.addProtocol("pmtiles", pmtilesProtocol.tile);
    maplibregl.setWorkerUrl(maplibreWorkerUrl);
    protocolRegistered = true;
}

class MaplibreBasemapLayer extends Layer {
    constructor(styleJson) {
        super({ zIndex: -10 });
        this.styleJson = styleJson;
        this.container = document.createElement("div");
        this.container.className = "mcx-maplibre-basemap";
        this.container.style.position = "absolute";
        this.container.style.inset = "0";
        this.container.style.pointerEvents = "none";
        this.mlMap = null;
        this.width = 0;
        this.height = 0;
        this.initError = null;
    }

    initMaplibre(frameState) {
        this.width = Math.round(frameState.size[0]);
        this.height = Math.round(frameState.size[1]);
        this.container.style.width = `${this.width}px`;
        this.container.style.height = `${this.height}px`;
        this.mlMap = new maplibregl.Map({
            container: this.container,
            style: this.styleJson,
            attributionControl: false,
            interactive: false,
            fadeDuration: 0,
            renderWorldCopies: true,
            canvasContextAttributes: { antialias: true },
        });
        // Debug and e2e hook: the sync spec compares maplibre.project()
        // output against OpenLayers pixels for overlay alignment.
        this.container.__mlMap = this.mlMap;
        const canvas = this.mlMap.getCanvas();
        if (canvas && typeof canvas.addEventListener === "function") {
            canvas.addEventListener("webglcontextlost", (event) => {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                if (!this.initError) {
                    this.initError = new Error("webgl context lost");
                    this.dispatchEvent("maplibre-init-error");
                }
            });
        }
    }

    render(frameState) {
        if (this.initError) {
            return null;
        }
        if (!this.mlMap) {
            try {
                this.initMaplibre(frameState);
            } catch (e) {
                // WebGL context creation failed at runtime. Paint nothing and
                // let the caller rebuild with the CPU path.
                this.initError = e;
                this.dispatchEvent("maplibre-init-error");
                return null;
            }
        }
        const viewState = frameState.viewState;
        const w = Math.round(frameState.size[0]);
        const h = Math.round(frameState.size[1]);
        if (w !== this.width || h !== this.height) {
            this.width = w;
            this.height = h;
            this.container.style.width = `${w}px`;
            this.container.style.height = `${h}px`;
            this.mlMap.resize();
        }
        this.container.style.opacity = String(this.getOpacity());
        this.container.style.display = this.getVisible() ? "block" : "none";
        this.mlMap.jumpTo({
            center: toLonLat(viewState.center, viewState.projection),
            // MapLibre zoom 0 spans the world at 512px, OpenLayers at 256px.
            zoom: viewState.zoom - 1,
            bearing: (-viewState.rotation * 180) / Math.PI,
            pitch: 0,
        });
        if (typeof this.mlMap._render === "function") {
            this.mlMap._render();
        } else {
            this.mlMap.triggerRepaint();
        }
        return this.container;
    }

    disposeInternal() {
        if (this.mlMap) {
            try {
                this.mlMap.remove();
            } catch {
                // Tearing down a half-initialized map can throw. Ignore it.
            }
            this.mlMap = null;
        }
        super.disposeInternal();
    }
}

/**
 * Planet basemap via MapLibre. The archive is registered with the pmtiles
 * protocol under its URL so tile requests go through the shared cache
 * source (ETag, If-Range, Cache API) instead of plain fetches.
 * @returns {Promise<MaplibreBasemapLayer>}
 */
export async function buildMaplibrePlanetBaseMapLayer() {
    ensureProtocol();
    const archive = await getArchive();
    pmtilesProtocol.add(archive);
    const trimmed = trimBasemapLayers(basemapLayers("protomaps", namedFlavor("light"), { lang: "en" }));
    return new MaplibreBasemapLayer(basemapStyleJson(trimmed));
}

/**
 * Offline local .pmtiles archive via MapLibre. Same shape as the OL
 * fallback: resolves {layer, header}. Raster archives are not handled
 * here and keep the existing TileLayer path.
 * @param {string} sourceUrl same-origin backend range endpoint
 * @returns {Promise<{layer: MaplibreBasemapLayer, header: object}>}
 */
export async function buildMaplibreLocalPmtilesBaseMapLayer(sourceUrl) {
    ensureProtocol();
    const archive = new PMTiles(getCachedPmtilesSource(sourceUrl));
    const header = await archive.getHeader();
    if (header.tileType !== 1) {
        throw new Error("not a vector archive");
    }
    const extent =
        header.minLon < header.maxLon
            ? transformExtent([header.minLon, header.minLat, header.maxLon, header.maxLat], "EPSG:4326", "EPSG:3857")
            : undefined;
    pmtilesProtocol.add(archive);
    const trimmed = trimBasemapLayers(basemapLayers("protomaps", namedFlavor("light"), { lang: "en" }));
    const layer = new MaplibreBasemapLayer(basemapStyleJson(trimmed, { sprite: false, sourceUrl }));
    if (extent) layer.setExtent(extent);
    return { layer, header };
}
