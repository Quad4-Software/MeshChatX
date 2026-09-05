// SPDX-License-Identifier: 0BSD

export interface MapMetadata {
    name?: string;
    attribution?: string;
    [key: string]: unknown;
}

export interface SearchResult {
    display_name: string;
    lat?: string | number;
    lon?: string | number;
    boundingbox?: [string, string, string, string];
    type?: string;
    [key: string]: unknown;
}

export type MapSearchResult = SearchResult;

export interface DrawingTool {
    type: string;
    icon: string;
}

export interface DrawingEntry {
    id: string | number;
    name: string;
    features?: any[];
    updated_at: string | number;
    [key: string]: unknown;
}

export interface MBTilesEntry {
    name: string;
    size?: number;
    is_active?: boolean;
    [key: string]: unknown;
}

export interface RemoteOverlayEntry {
    id: string | number;
    name?: string;
    kind?: string;
    url?: string;
    status?: string;
    visible?: boolean;
    format?: string;
    last_error?: string;
    features?: any[];
    [key: string]: unknown;
}

export interface TelemetryPeer {
    destination_hash: string;
    display_name?: string;
    telemetry?: {
        location?: {
            latitude: number;
            longitude: number;
            altitude?: number;
            speed?: number;
            heading?: number;
        };
        note?: string;
        timestamp?: number;
        [key: string]: unknown;
    };
    [key: string]: unknown;
}

export interface MapExportStatus {
    status: string;
    message?: string;
    progress?: number;
    current?: number;
    total?: number;
    error?: string;
    [key: string]: unknown;
}

export interface ExportPreset {
    id: string;
    label: string;
    radiusKm: number;
    minZoom: number;
    maxZoom: number;
}

export interface MapTab {
    id: number;
    storageId: string;
    title: string;
    tabNumber: number;
    userRenamed: boolean;
}

export interface MapAnnounceItem {
    destination_hash: string;
    display_name?: string;
    custom_display_name?: string;
    name?: string;
    latitude?: number;
    longitude?: number;
    lat?: number;
    lon?: number;
    aspect?: string;
    hops?: number;
    [key: string]: unknown;
}

export interface MapDrawFeatureInfo {
    id?: string | number;
    name?: string;
    description?: string;
    descriptionIsHtml?: boolean;
    type?: string;
    iconSrc?: string | null;
    extended?: Array<{ key: string; value: string }>;
    rawProperties?: Record<string, unknown>;
    feature?: unknown;
}
