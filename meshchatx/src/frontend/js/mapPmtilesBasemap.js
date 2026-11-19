// SPDX-License-Identifier: 0BSD
/**
 * Online basemap backed by a single PMTiles archive.
 *
 * planet.pmtiles is a Protomaps/OpenMapTiles-schema vector archive served
 * from object storage. The pmtiles client fetches the header, tile
 * directory and only the tile ranges it needs via HTTP range requests, so
 * the browser never downloads the whole archive.
 */
import { PMTiles } from "pmtiles";
import MVT from "ol/format/MVT.js";
import VectorTileSource from "ol/source/VectorTile.js";
import VectorTileLayer from "ol/layer/VectorTile.js";
import LayerGroup from "ol/layer/Group.js";
import { createXYZ } from "ol/tilegrid.js";
import { applyStyle } from "ol-mapbox-style";
import { layers as basemapLayers, namedFlavor } from "@protomaps/basemaps";

import { PLANET_PM_TILES_URL } from "./mapTileProviders.js";

export { PLANET_PM_TILES_URL };

const PLANET_GLYPHS = "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf";
const PLANET_SPRITE = "https://protomaps.github.io/basemaps-assets/sprites/v4/light";
const PLANET_ATTRIBUTION =
    '© <a href="https://protomaps.com" target="_blank" rel="noopener noreferrer">Protomaps</a> ' +
    '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>';

let archivePromise = null;

function getArchive() {
    if (!archivePromise) {
        archivePromise = Promise.resolve().then(async () => {
            const archive = new PMTiles(PLANET_PM_TILES_URL);
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

function createPlanetVectorTileLayer(archive) {
    const format = new MVT();
    const source = new VectorTileSource({
        format,
        projection: "EPSG:3857",
        wrapX: true,
        attributions: PLANET_ATTRIBUTION,
        tileGrid: createXYZ({ minZoom: 0, maxZoom: 15 }),
        // OpenLayers only loads source tiles whose URL function returns a
        // truthy value; the URL is a cache key, bytes come from getZxy.
        tileUrlFunction: (tileCoord) => `${PLANET_PM_TILES_URL}/${tileCoord[0]}/${tileCoord[1]}/${tileCoord[2]}`,
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
    return new VectorTileLayer({ source });
}

function planetStyleJson() {
    return {
        version: 8,
        name: "protomaps-planet",
        glyphs: PLANET_GLYPHS,
        sprite: PLANET_SPRITE,
        sources: {
            protomaps: {
                type: "vector",
                url: `pmtiles://${PLANET_PM_TILES_URL}`,
                attribution: PLANET_ATTRIBUTION,
            },
        },
        layers: basemapLayers("protomaps", namedFlavor("light"), { lang: "en" }),
    };
}

/**
 * Build the basemap layer group for the planet PMTiles archive.
 * Resolves once the archive header has been validated and the style
 * applied; throws if the archive is unreachable or not vector data.
 * @returns {Promise<LayerGroup>}
 */
export async function buildPlanetPmtilesBaseMapLayer() {
    const archive = await getArchive();
    const layer = createPlanetVectorTileLayer(archive);
    layer.set("mapbox-source", "protomaps");
    await applyStyle(layer, planetStyleJson(), {
        source: "protomaps",
        styleUrl: PLANET_PM_TILES_URL,
        updateSource: false,
    });
    return new LayerGroup({ layers: [layer] });
}
