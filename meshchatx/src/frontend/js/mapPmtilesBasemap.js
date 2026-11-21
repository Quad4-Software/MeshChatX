// SPDX-License-Identifier: 0BSD
/**
 * Online basemap backed by a single PMTiles archive.
 *
 * planet.pmtiles is a Protomaps/OpenMapTiles-schema vector archive served
 * from object storage. The pmtiles client fetches the header, tile
 * directory and only the tile ranges it needs via HTTP range requests, so
 * the browser never downloads the whole archive.
 */
import { PMTiles, SharedPromiseCache } from "pmtiles";
import MVT from "ol/format/MVT.js";
import VectorTileSource from "ol/source/VectorTile.js";
import VectorTileLayer from "ol/layer/VectorTile.js";
import LayerGroup from "ol/layer/Group.js";
import TileLayer from "ol/layer/Tile.js";
import TileImageSource from "ol/source/TileImage.js";
import TileState from "ol/TileState.js";
import { createXYZ } from "ol/tilegrid.js";
import { transformExtent } from "ol/proj.js";
import { applyStyle } from "ol-mapbox-style";
import { layers as basemapLayers, namedFlavor } from "@protomaps/basemaps";

import { PLANET_PM_TILES_URL } from "./mapTileProviders.js";
import { getCachedPmtilesSource } from "./pmtilesCacheSource.js";
import { trimBasemapLayers } from "./mapStyleTrim.js";

export { PLANET_PM_TILES_URL };

const PLANET_GLYPHS = "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf";
const PLANET_SPRITE = "https://protomaps.github.io/basemaps-assets/sprites/v4/light";
const PLANET_ATTRIBUTION =
    '© <a href="https://protomaps.com" target="_blank" rel="noopener noreferrer">Protomaps</a> ' +
    '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>';

let archivePromise = null;
// Module-level cache: header and directory range requests are shared and
// deduped across basemap rebuilds for the lifetime of the page.
const sharedPromiseCache = new SharedPromiseCache(500, true);

export function getArchive() {
    if (!archivePromise) {
        archivePromise = Promise.resolve().then(async () => {
            const archive = new PMTiles(getCachedPmtilesSource(PLANET_PM_TILES_URL), sharedPromiseCache);
            const header = await archive.getHeader();
            if (!header || header.tileType !== 1) {
                throw new Error("planet.pmtiles is not a vector (MVT) archive");
            }
            return archive;
        });
        archivePromise.catch(() => {
            archivePromise = null;
        });
    }
    return archivePromise;
}

function createPmtilesVectorSource(archive, urlBase, { minZoom = 0, maxZoom = 15 } = {}) {
    const format = new MVT();
    return new VectorTileSource({
        format,
        projection: "EPSG:3857",
        wrapX: true,
        attributions: PLANET_ATTRIBUTION,
        // No fade-in: the default 250ms transition keeps repainting the map
        // during tile loads and measurably extends zoom jank.
        transition: 0,
        tileGrid: createXYZ({ minZoom, maxZoom }),
        // OpenLayers only loads source tiles whose URL function returns a
        // truthy value; the URL is a cache key, bytes come from getZxy.
        tileUrlFunction: (tileCoord) => `${urlBase}/${tileCoord[0]}/${tileCoord[1]}/${tileCoord[2]}`,
        tileLoadFunction: (tile) => {
            const [z, x, y] = tile.tileCoord;
            tile.setLoader((extent, resolution, projection) => {
                archive
                    .getZxy(z, x, y)
                    .then((result) => {
                        const data = result && result.data ? result.data : result;
                        if (!data || !data.byteLength) {
                            tile.setFeatures([]);
                            return;
                        }
                        const features = format.readFeatures(data, {
                            extent,
                            featureProjection: projection,
                        });
                        tile.setFeatures(features);
                    })
                    .catch(() => {
                        tile.setFeatures([]);
                    });
            });
        },
    });
}

function createBasemapVectorLayer(source) {
    return new VectorTileLayer({
        source,
        // Keep the frame budget for pointer feedback during drags and zoom
        // animations instead of rebuilding tile batches mid-interaction.
        updateWhileAnimating: false,
        updateWhileInteracting: false,
        preload: 0,
        // Interim tiles from other zoom levels replay every style layer
        // for their zoom during animations and were the biggest single
        // frame cost in profiling. Skip them.
        useInterimTilesOnError: false,
    });
}

export function basemapStyleJson(layersSubset, { sprite = true, sourceUrl = PLANET_PM_TILES_URL } = {}) {
    const json = {
        version: 8,
        name: "protomaps-planet",
        glyphs: PLANET_GLYPHS,
        sources: {
            protomaps: {
                type: "vector",
                url: `pmtiles://${sourceUrl}`,
                attribution: PLANET_ATTRIBUTION,
            },
        },
        layers: layersSubset,
    };
    if (sprite) json.sprite = PLANET_SPRITE;
    return json;
}

async function buildStyledVectorGroup(archive, styleUrl, tileUrlBase, { minZoom, maxZoom, extent, offline }) {
    const stock = basemapLayers("protomaps", namedFlavor("light"), { lang: "en" });
    const trimmed = trimBasemapLayers(stock);
    const source = createPmtilesVectorSource(archive, tileUrlBase, { minZoom, maxZoom });
    const layer = createBasemapVectorLayer(source);
    layer.set("mapbox-source", "protomaps");
    if (extent) layer.setExtent(extent);
    await applyStyle(layer, basemapStyleJson(trimmed, { sprite: !offline }), {
        source: "protomaps",
        styleUrl,
        updateSource: false,
    });
    return new LayerGroup({ layers: [layer] });
}

/**
 * Build the basemap layer group for the planet PMTiles archive.
 * Resolves once the archive header has been validated and the style
 * applied; throws if the archive is unreachable or not vector data.
 * @returns {Promise<LayerGroup>}
 */
export async function buildPlanetPmtilesBaseMapLayer() {
    const archive = await getArchive();
    return buildStyledVectorGroup(archive, PLANET_PM_TILES_URL, PLANET_PM_TILES_URL, {
        minZoom: 0,
        maxZoom: 15,
    });
}

const RASTER_MIME = { 2: "image/png", 3: "image/jpeg", 4: "image/webp", 5: "image/avif" };
const LOCAL_ATTRIBUTION =
    'Local <a href="https://protomaps.com" target="_blank" rel="noopener noreferrer">PMTiles</a> archive';

/**
 * Build the offline basemap for a local .pmtiles archive served by the
 * backend range endpoint. Vector archives get the Protomaps style, raster
 * archives render as plain image tiles. Zoom range and bounds come from
 * the archive header so no requests fire outside them.
 * @param {string} sourceUrl same-origin endpoint URL
 * @returns {Promise<{layer: LayerGroup, header: object}>}
 */
export async function buildLocalPmtilesBaseMapLayer(sourceUrl) {
    const archive = new PMTiles(getCachedPmtilesSource(sourceUrl), sharedPromiseCache);
    const header = await archive.getHeader();
    const extent =
        header.minLon < header.maxLon
            ? transformExtent([header.minLon, header.minLat, header.maxLon, header.maxLat], "EPSG:4326", "EPSG:3857")
            : undefined;

    if (header.tileType === 1) {
        // offline: no sprite fetch, see buildStyledVectorGroup.
        const layer = await buildStyledVectorGroup(archive, sourceUrl, sourceUrl, {
            minZoom: header.minZoom,
            maxZoom: header.maxZoom,
            extent,
            offline: true,
        });
        return { layer, header };
    }

    const mime = RASTER_MIME[header.tileType] || "image/png";
    const source = new TileImageSource({
        projection: "EPSG:3857",
        wrapX: true,
        attributions: LOCAL_ATTRIBUTION,
        transition: 0,
        tileGrid: createXYZ({ minZoom: header.minZoom, maxZoom: header.maxZoom }),
        tileUrlFunction: (tileCoord) => `${sourceUrl}/${tileCoord[0]}/${tileCoord[1]}/${tileCoord[2]}`,
        tileLoadFunction: (tile) => {
            const [z, x, y] = tile.tileCoord;
            archive
                .getZxy(z, x, y)
                .then((result) => {
                    if (!result || !result.data || !result.data.byteLength) {
                        tile.setState(TileState.EMPTY);
                        return;
                    }
                    const blob = new Blob([result.data], { type: mime });
                    const img = tile.getImage();
                    const url = URL.createObjectURL(blob);
                    img.onload = () => URL.revokeObjectURL(url);
                    img.src = url;
                })
                .catch(() => tile.setState(TileState.ERROR));
        },
    });
    const layer = new TileLayer({
        source,
        updateWhileAnimating: false,
        updateWhileInteracting: false,
        preload: 0,
        useInterimTilesOnError: true,
    });
    if (extent) layer.setExtent(extent);
    return { layer: new LayerGroup({ layers: [layer] }), header };
}
