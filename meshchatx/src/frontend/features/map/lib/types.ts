// SPDX-License-Identifier: 0BSD

import type Feature from "ol/Feature.js";

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
    place_id?: string | number;
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
    features?: unknown[];
    updated_at: string | number;
    [key: string]: unknown;
}

export interface MBTilesEntry {
    name: string;
    size?: number;
    is_active?: boolean;
    [key: string]: unknown;
}

/** Remote overlay row from the map overlays API. */
export interface RemoteOverlayEntry {
    id: string | number;
    name?: string;
    kind?: string;
    url?: string;
    status?: string;
    visible?: boolean;
    format?: string;
    last_error?: string;
    content_sha256?: string;
    features?: unknown[];
    [key: string]: unknown;
}

export interface TelemetryLocation {
    latitude: number;
    longitude: number;
    altitude?: number;
    speed?: number;
    heading?: number;
}

export interface TelemetryPeer {
    destination_hash?: string;
    display_name?: string;
    is_stale?: boolean;
    is_tracking?: boolean;
    updated_at?: string;
    timestamp?: number;
    telemetry?: {
        location?: TelemetryLocation;
        note?: string;
        timestamp?: number;
        [key: string]: unknown;
    };
    [key: string]: unknown;
}

export interface MapPeerIcon {
    background_colour?: string;
    foreground_colour?: string;
    [key: string]: unknown;
}

/** LXMF conversation peer fields used for map marker styling. */
export interface MapPeer {
    destination_hash?: string;
    display_name?: string;
    lxmf_user_icon?: MapPeerIcon;
    [key: string]: unknown;
}

export interface DiscoveredMapNode {
    latitude?: number;
    longitude?: number;
    name?: string;
    last_heard?: number;
    interface?: string;
    via?: string;
    [key: string]: unknown;
}

export interface PeerMarkerStyleSource {
    display_name?: string;
    custom_display_name?: string;
    background_colour?: string;
    custom_background_colour?: string;
    foreground_colour?: string;
    custom_foreground_colour?: string;
    is_stale?: boolean;
}

export interface MapMarkerItem {
    latitude?: number;
    longitude?: number;
    lat?: number;
    lon?: number;
    destination_hash?: string;
    dest_hash?: string;
    display_name?: string;
    custom_display_name?: string;
    name?: string;
    [key: string]: unknown;
}

export interface MarkerPanelPayload {
    telemetry?: TelemetryPeer | null;
    peer?: MapPeer | null;
    discovered?: DiscoveredMapNode | null;
}

export interface DrawFeatureEditPayload {
    name: string;
    description: string;
    descriptionIsHtml: boolean;
    extended: Array<{ key: string; value: string }>;
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
    feature?: Feature | null;
}

export interface MapExportStartPayload {
    [key: string]: unknown;
}

/** Loose API body that may be top-level or nested under data. */
export type ApiDataEnvelope<T extends object> = T & { data?: T };
