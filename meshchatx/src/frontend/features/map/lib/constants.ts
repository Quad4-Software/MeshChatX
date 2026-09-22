// SPDX-License-Identifier: 0BSD

export const MAX_MAP_TABS = 8;
export const DOUBLE_TAP_MS = 400;

export const DEFAULT_MAP_CENTER = [0, 0];
export const DEFAULT_MAP_ZOOM = 2;
export const MAX_MAP_ZOOM = 19;
export const MIN_MAP_ZOOM = 0;

export const MAP_DATA_ASPECT = "map-data-v1";
export const MAP_ANNOUNCE_INTERVAL = 900;

export const MAX_EXPORT_TILES = 200000;
export const WORLD_MBTILES_BBOX: [number, number, number, number] = [-180, -85.051129, 180, 85.051129];

export interface ExportRegionPreset {
    id: string;
    bbox: [number, number, number, number];
    minZoom: number;
    maxZoom: number;
}

export const EXPORT_REGION_PRESETS: ExportRegionPreset[] = [
    { id: "world", bbox: [...WORLD_MBTILES_BBOX], minZoom: 0, maxZoom: 4 },
    { id: "europe", bbox: [-12, 35, 40, 72], minZoom: 0, maxZoom: 10 },
    { id: "north_america", bbox: [-170, 15, -50, 72], minZoom: 0, maxZoom: 10 },
    { id: "south_america", bbox: [-82, -56, -34, 14], minZoom: 0, maxZoom: 10 },
    { id: "africa", bbox: [-20, -36, 52, 38], minZoom: 0, maxZoom: 10 },
    { id: "asia", bbox: [25, -12, 145, 55], minZoom: 0, maxZoom: 10 },
    { id: "oceania", bbox: [110, -48, 179, 0], minZoom: 0, maxZoom: 10 },
];
