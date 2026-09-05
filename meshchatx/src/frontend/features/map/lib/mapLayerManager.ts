// SPDX-License-Identifier: 0BSD

import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import XYZ from "ol/source/XYZ.js";
import VectorSource from "ol/source/Vector.js";
import TileCache from "../../../js/TileCache.js";
import { TILE_PROVIDER_URLS, DEFAULT_TILE_SERVER_URL } from "../../../js/mapTileProviders.js";

export interface MapLayersState {
    tileLayer: TileLayer<XYZ>;
    drawLayer: VectorLayer<VectorSource>;
    drawSource: VectorSource;
    markerLayer: VectorLayer<VectorSource>;
    markerSource: VectorSource;
}

export function createMapLayers(offlineEnabled: boolean, providerId = "osm"): MapLayersState {
    const drawSource = new VectorSource();
    const drawLayer = new VectorLayer({
        source: drawSource,
        zIndex: 10,
    });

    const markerSource = new VectorSource();
    const markerLayer = new VectorLayer({
        source: markerSource,
        zIndex: 20,
    });

    const tileSource = createTileSource(offlineEnabled, providerId);
    const tileLayer = new TileLayer({
        source: tileSource,
        zIndex: 1,
    });

    return {
        tileLayer,
        drawLayer,
        drawSource,
        markerLayer,
        markerSource,
    };
}

export function createTileSource(offlineEnabled: boolean, providerId = "osm"): XYZ {
    const url = offlineEnabled
        ? "/api/v1/map/tiles/{z}/{x}/{y}.png"
        : TILE_PROVIDER_URLS[providerId] || DEFAULT_TILE_SERVER_URL;

    const source = new XYZ({
        url,
        maxZoom: 19,
    });

    const originalLoader = source.getTileLoadFunction();
    source.setTileLoadFunction(async (imageTile: any, src: string) => {
        try {
            const cached = await TileCache.getTile(src);
            if (cached) {
                const img = imageTile.getImage() as HTMLImageElement;
                img.src = cached;
                return;
            }
        } catch {
            // cache read error fallback
        }
        originalLoader(imageTile, src);
    });

    return source;
}
