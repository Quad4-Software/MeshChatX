// SPDX-License-Identifier: 0BSD

export type RendererMode = "vis" | "webgl";
export type EngineMode = "checking" | "wasm" | "fallback" | "webgl";
export type ViewMode = "flat" | "planet";
export type PreferredRenderer = "auto" | "webgl" | "vis";

export interface PathTableEntry {
    hash: string;
    interface?: string;
    hops?: number | null;
    via?: string;
    expires?: number;
    state?: number;
    [key: string]: unknown;
}

export interface AnnounceEntry {
    destination_hash?: string;
    aspect?: string;
    display_name?: string | null;
    custom_display_name?: string;
    identity_hash?: string;
    updated_at?: string;
    [key: string]: unknown;
}

export interface InterfaceEntry {
    name: string;
    status?: boolean;
    bitrate?: number;
    txb?: number;
    rxb?: number;
    interface_name?: string;
    type?: string;
    parent_interface_name?: string | null;
    [key: string]: unknown;
}

export interface DiscoveredInterfaceEntry {
    name?: string;
    reachable_on?: string;
    transport_id?: string;
    discovery_hash?: string;
    type?: string;
    hops?: number | null;
    status?: string;
    port?: number | string;
    [key: string]: unknown;
}

export interface DiscoveredActiveEntry {
    target_host?: string;
    remote?: string;
    listen_ip?: string;
    target_port?: number | string;
    listen_port?: number | string;
    [key: string]: unknown;
}

export interface ConversationEntry {
    destination_hash: string;
    lxmf_user_icon?: Record<string, unknown>;
    [key: string]: unknown;
}

export interface VisualiserConfig {
    display_name?: string;
    identity_hash?: string;
    [key: string]: unknown;
}

export interface IconQueueEntry {
    nodeId: string;
    cacheKey: string;
    iconName: string;
    fg: string;
    bg: string;
    size: number;
    generation: number;
}
