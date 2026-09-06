// SPDX-License-Identifier: 0BSD

import { Style, Fill, Stroke, Circle as CircleStyle, Text } from "ol/style";
import type Feature from "ol/Feature";
import type { StyleFunction } from "ol/style/Style";
import XYZ from "ol/source/XYZ";
import TileGrid from "ol/tilegrid/TileGrid";
import type ImageTile from "ol/ImageTile";
import { resolveRasterTileUrl } from "./mapTileUtils.js";
import TileCache from "../../../js/TileCache.js";

export function createDrawingStyle(): StyleFunction {
    return ((feature: Feature) => {
        const geom = feature.getGeometry();
        const type = geom ? geom.getType() : "";
        const textVal = feature.get("text") || "";
        const isNote = Boolean(feature.get("note"));

        if (type === "Point") {
            if (textVal) {
                return new Style({
                    text: new Text({
                        text: String(textVal),
                        font: "bold 13px sans-serif",
                        fill: new Fill({ color: "#1e293b" }),
                        stroke: new Stroke({ color: "#ffffff", width: 3 }),
                        offsetY: -10,
                    }),
                });
            }
            return new Style({
                image: new CircleStyle({
                    radius: isNote ? 7 : 6,
                    fill: new Fill({ color: isNote ? "#f59e0b" : "#3b82f6" }),
                    stroke: new Stroke({ color: "#ffffff", width: 2 }),
                }),
            });
        }

        if (type === "LineString") {
            return new Style({
                stroke: new Stroke({
                    color: "#3b82f6",
                    width: 3,
                }),
            });
        }

        if (type === "Polygon") {
            return new Style({
                stroke: new Stroke({
                    color: "#3b82f6",
                    width: 2,
                }),
                fill: new Fill({
                    color: "rgba(59, 130, 246, 0.2)",
                }),
            });
        }

        if (type === "Circle") {
            return new Style({
                stroke: new Stroke({
                    color: "#3b82f6",
                    width: 2,
                }),
                fill: new Fill({
                    color: "rgba(59, 130, 246, 0.2)",
                }),
            });
        }

        return new Style({
            stroke: new Stroke({
                color: "#3b82f6",
                width: 2,
            }),
            fill: new Fill({
                color: "rgba(59, 130, 246, 0.1)",
            }),
        });
    }) as StyleFunction;
}

export function createMeasureStyle(): Style {
    return new Style({
        fill: new Fill({
            color: "rgba(239, 68, 68, 0.2)",
        }),
        stroke: new Stroke({
            color: "#ef4444",
            lineDash: [10, 10],
            width: 2,
        }),
        image: new CircleStyle({
            radius: 5,
            stroke: new Stroke({
                color: "rgba(0, 0, 0, 0.7)",
            }),
            fill: new Fill({
                color: "rgba(255, 255, 255, 0.2)",
            }),
        }),
    });
}

function tileImageElement(tile: ImageTile): HTMLImageElement {
    return tile.getImage() as HTMLImageElement;
}

export function createOnlineTileSource(
    tileServerUrl?: string | null,
    cachingEnabled: boolean = true,
    onTileError?: () => void
): XYZ {
    const url = resolveRasterTileUrl(tileServerUrl);
    return new XYZ({
        url,
        crossOrigin: "anonymous",
        maxZoom: 19,
        tileLoadFunction: (tile, src: string) => {
            const img = tileImageElement(tile as ImageTile);
            if (onTileError) {
                img.onerror = () => onTileError();
            }
            if (!cachingEnabled) {
                img.src = src;
                return;
            }
            TileCache.getTile(src)
                .then((blob) => {
                    if (blob) {
                        img.src = URL.createObjectURL(blob);
                    } else {
                        img.src = src;
                        fetch(src)
                            .then((res) => {
                                if (res.ok) return res.blob();
                                return null;
                            })
                            .then((newBlob) => {
                                if (newBlob) TileCache.setTile(src, newBlob);
                            })
                            .catch(() => {});
                    }
                })
                .catch(() => {
                    img.src = src;
                });
        },
    });
}

export function createOfflineMBTilesSource(): XYZ {
    const tileGrid = new TileGrid({
        extent: [-20037508.34, -20037508.34, 20037508.34, 20037508.34],
        resolutions: Array.from({ length: 20 }, (_, z) => 156543.03392804097 / Math.pow(2, z)),
        tileSize: [256, 256],
    });

    return new XYZ({
        tileGrid,
        maxZoom: 19,
        tileUrlFunction: (tileCoord) => {
            const z = tileCoord[0];
            const x = tileCoord[1];
            const y = Math.max(0, -tileCoord[2] - 1);
            return `/api/v1/map/tiles/${z}/${x}/${y}`;
        },
        tileLoadFunction: (tile, src: string) => {
            const img = tileImageElement(tile as ImageTile);
            TileCache.getTile(src)
                .then((blob) => {
                    if (blob) {
                        img.src = URL.createObjectURL(blob);
                    } else {
                        img.src = src;
                        fetch(src)
                            .then((res) => (res.ok ? res.blob() : null))
                            .then((b) => {
                                if (b) TileCache.setTile(src, b);
                            })
                            .catch(() => {});
                    }
                })
                .catch(() => {
                    img.src = src;
                });
        },
    });
}
