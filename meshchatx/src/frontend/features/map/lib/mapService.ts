// SPDX-License-Identifier: 0BSD

import type { DrawingEntry, MBTilesEntry, MapExportStatus } from "./types.js";

export async function fetchTelemetryMarkers(): Promise<any[]> {
    try {
        const response: any = await window.api.get("/api/v1/map/telemetry");
        return response?.telemetry || response?.data?.telemetry || [];
    } catch {
        return [];
    }
}

export async function fetchPeers(): Promise<Record<string, any>> {
    try {
        const response: any = await window.api.get("/api/v1/lxmf/conversations", {
            params: { limit: 2000 },
        });
        const convs = response?.conversations || response?.data?.conversations || [];
        const map: Record<string, any> = {};
        for (const c of convs) {
            if (c.destination_hash) {
                map[c.destination_hash] = c;
            }
        }
        return map;
    } catch {
        return {};
    }
}

export async function fetchDiscoveredNodes(): Promise<any[]> {
    try {
        const response: any = await window.api.get("/api/v1/interfaces/discovered");
        return response?.discovered_interfaces || response?.data?.discovered_interfaces || [];
    } catch {
        return [];
    }
}

export async function loadMBTilesList(): Promise<MBTilesEntry[]> {
    try {
        const response: any = await window.api.get("/api/v1/map/mbtiles");
        return response?.files || response?.data?.files || [];
    } catch {
        return [];
    }
}

export async function setActiveMBTiles(filename: string): Promise<any> {
    return window.api.post("/api/v1/map/mbtiles/active", { filename });
}

export async function deleteMBTiles(filename: string): Promise<any> {
    return window.api.delete(`/api/v1/map/mbtiles/${encodeURIComponent(filename)}`);
}

export async function restoreStarterTiles(): Promise<any> {
    return window.api.post("/api/v1/map/mbtiles/starter", {});
}

export async function saveMBTilesDir(directory: string): Promise<any> {
    return window.api.patch("/api/v1/config", { mbtiles_directory: directory });
}

export async function loadDrawings(): Promise<DrawingEntry[]> {
    try {
        const response: any = await window.api.get("/api/v1/map/drawings");
        return response?.drawings || response?.data?.drawings || [];
    } catch {
        return [];
    }
}

export async function saveDrawing(name: string, features: any[]): Promise<any> {
    return window.api.post("/api/v1/map/drawings", { name, features });
}

export async function deleteDrawing(id: string | number): Promise<any> {
    return window.api.delete(`/api/v1/map/drawings/${id}`);
}

export async function startExport(payload: Record<string, any>): Promise<any> {
    return window.api.post("/api/v1/map/export", payload);
}

export async function cancelExport(id: string | number): Promise<any> {
    return window.api.post(`/api/v1/map/export/${id}/cancel`, {});
}

export async function getExportStatus(id: string | number): Promise<MapExportStatus | null> {
    try {
        const res = await window.api.get(`/api/v1/map/export/${id}`);
        return res?.data || res || null;
    } catch {
        return null;
    }
}

export async function sendMapPing(destinationHash: string, lat: number, lon: number, zoom: number): Promise<any> {
    const uri = `meshchatx://map?lat=${lat.toFixed(6)}&lon=${lon.toFixed(6)}&z=${Math.round(zoom)}`;
    const content = `Location share:\n${uri}`;
    return window.api.post("/api/v1/lxmf/messages/send", {
        destination_hash: destinationHash,
        content,
        fields: {
            map_share: {
                latitude: lat,
                longitude: lon,
                zoom: Math.round(zoom),
            },
        },
    });
}
