// SPDX-License-Identifier: 0BSD

import { buildMeshchatMapUri } from "../../../js/mapLinkUtils.js";
import type {
    ApiDataEnvelope,
    DrawingEntry,
    MapExportStartPayload,
    MapExportStatus,
    MapPeer,
    MBTilesEntry,
    TelemetryPeer,
} from "./types.js";

type TelemetryListPayload = ApiDataEnvelope<{ telemetry?: TelemetryPeer[] }>;
type ConversationsPayload = ApiDataEnvelope<{
    conversations?: Array<MapPeer & { destination_hash?: string }>;
}>;
type DiscoveredInterfacesPayload = ApiDataEnvelope<{ interfaces?: DiscoveredInterfaceRow[] }>;
type TrackingTogglePayload = ApiDataEnvelope<{ is_tracking?: boolean }>;
type MbtilesListPayload = ApiDataEnvelope<{ files?: MBTilesEntry[] }>;
type DrawingsListPayload = ApiDataEnvelope<{ drawings?: DrawingEntry[] }>;

export interface DiscoveredInterfaceRow {
    name?: string;
    latitude?: number;
    longitude?: number;
    last_heard?: number;
    interface?: string;
    via?: string;
    [key: string]: unknown;
}

export async function fetchTelemetryMarkers(): Promise<TelemetryPeer[]> {
    try {
        const response = (await window.api.get("/api/v1/telemetry/peers")) as TelemetryListPayload;
        return response?.telemetry || response?.data?.telemetry || [];
    } catch {
        return [];
    }
}

export async function fetchPeers(): Promise<Record<string, MapPeer>> {
    try {
        const response = (await window.api.get("/api/v1/lxmf/conversations", {
            params: { limit: 2000 },
        })) as ConversationsPayload;
        const convs = response?.conversations || response?.data?.conversations || [];
        const map: Record<string, MapPeer> = {};
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

export async function fetchDiscoveredNodes(): Promise<DiscoveredInterfaceRow[]> {
    try {
        const response = (await window.api.get(
            "/api/v1/reticulum/discovered-interfaces"
        )) as DiscoveredInterfacesPayload;
        return response?.interfaces || response?.data?.interfaces || [];
    } catch {
        return [];
    }
}

export async function toggleTelemetryTracking(destinationHash: string, isTracking: boolean): Promise<boolean | null> {
    try {
        const response = (await window.api.post(`/api/v1/telemetry/tracking/${destinationHash}/toggle`, {
            is_tracking: isTracking,
        })) as TrackingTogglePayload;
        const next = response?.is_tracking ?? response?.data?.is_tracking;
        return typeof next === "boolean" ? next : null;
    } catch {
        return null;
    }
}

export async function fetchTelemetryHistory(destinationHash: string, limit: number = 50): Promise<TelemetryPeer[]> {
    try {
        const response = (await window.api.get(
            `/api/v1/telemetry/history/${destinationHash}?limit=${limit}`
        )) as TelemetryListPayload;
        return response?.telemetry || response?.data?.telemetry || [];
    } catch {
        return [];
    }
}

export async function patchAnnounceStoreMapData(enabled: boolean): Promise<unknown> {
    return window.api.patch("/api/v1/config", {
        announce_store_map_data: Boolean(enabled),
    });
}

export async function uploadMbtilesFile(file: File): Promise<unknown> {
    const formData = new FormData();
    formData.append("file", file, file.name);
    return window.api.post("/api/v1/map/offline", formData);
}

export async function loadMBTilesList(): Promise<MBTilesEntry[]> {
    try {
        const response = (await window.api.get("/api/v1/map/mbtiles")) as MbtilesListPayload;
        return response?.files || response?.data?.files || [];
    } catch {
        return [];
    }
}

export async function setActiveMBTiles(filename: string): Promise<unknown> {
    return window.api.post("/api/v1/map/mbtiles/active", { filename });
}

export async function deleteMBTiles(filename: string): Promise<unknown> {
    return window.api.delete(`/api/v1/map/mbtiles/${encodeURIComponent(filename)}`);
}

export async function restoreStarterTiles(): Promise<unknown> {
    return window.api.post("/api/v1/map/mbtiles/restore-starter", {});
}

export async function saveMBTilesDir(directory: string): Promise<unknown> {
    return window.api.patch("/api/v1/config", { mbtiles_directory: directory });
}

export async function loadDrawings(): Promise<DrawingEntry[]> {
    try {
        const response = (await window.api.get("/api/v1/map/drawings")) as DrawingsListPayload;
        return response?.drawings || response?.data?.drawings || [];
    } catch {
        return [];
    }
}

export async function saveDrawing(name: string, features: unknown[]): Promise<unknown> {
    return window.api.post("/api/v1/map/drawings", { name, features });
}

export async function deleteDrawing(id: string | number): Promise<unknown> {
    return window.api.delete(`/api/v1/map/drawings/${id}`);
}

export async function startExport(payload: MapExportStartPayload): Promise<unknown> {
    return window.api.post("/api/v1/map/export", payload);
}

export async function cancelExport(id: string | number): Promise<unknown> {
    return window.api.post(`/api/v1/map/export/${id}/cancel`, {});
}

export async function getExportStatus(id: string | number): Promise<MapExportStatus | null> {
    try {
        const res = (await window.api.get(`/api/v1/map/export/${id}`)) as unknown as ApiDataEnvelope<MapExportStatus> &
            MapExportStatus;
        return res?.data || res || null;
    } catch {
        return null;
    }
}

export async function sendMapPing(opts: {
    destinationHash: string;
    lat: number;
    lon: number;
    zoom: number;
    layers?: string;
    contentPrefix: string;
}): Promise<unknown> {
    const hash = (opts.destinationHash || "").trim();
    if (!hash || hash.length !== 32) {
        throw new Error("invalid_destination");
    }
    const uri = buildMeshchatMapUri({
        lat: opts.lat,
        lon: opts.lon,
        zoom: opts.zoom,
        layers: opts.layers || "",
        label: "Ping",
    });
    const content = `${opts.contentPrefix} ${uri}`;
    return window.api.post("/api/v1/lxmf-messages/send", {
        lxmf_message: {
            destination_hash: hash,
            content,
        },
    });
}
