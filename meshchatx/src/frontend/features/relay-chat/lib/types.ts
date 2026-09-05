// SPDX-License-Identifier: 0BSD

export interface RrcRoom {
    name: string;
    topic?: string;
    unread?: number;
    mentions?: number;
    joined?: boolean;
    has_key?: boolean;
    member_count?: number;
    key?: string;
    [key: string]: unknown;
}

export interface RrcHub {
    hub_hash: string;
    name?: string;
    display_name?: string;
    custom_display_name?: string | null;
    status?: "connected" | "connecting" | "disconnected" | "error" | string;
    auto_reconnect?: boolean;
    icon?: string;
    rooms?: Record<string, RrcRoom> | RrcRoom[];
    unread?: number;
    mentions?: number;
    is_operator?: boolean;
    is_founder?: boolean;
    connected_at?: number;
    motd?: string | null;
    [key: string]: unknown;
}

export interface RrcMessage {
    seq?: number | string;
    kind?: "msg" | "action" | "system" | "notice" | "error";
    ts: number;
    src?: string;
    nickname?: string;
    text: string;
    mention?: boolean;
    [key: string]: unknown;
}

export interface RrcTimelineEntry {
    type: "message" | "dateDivider" | "presenceGroup";
    id?: string;
    dayKey?: string;
    msg?: RrcMessage;
    messages?: RrcMessage[];
    [key: string]: unknown;
}

export interface RrcMember {
    identity_hash?: string;
    nickname?: string;
    is_operator?: boolean;
    is_founder?: boolean;
    has_voice?: boolean;
    [key: string]: unknown;
}

export interface RrcHostedHub {
    hub_hash: string;
    name: string;
    running: boolean;
    port?: number;
    announce_interval?: number;
    rooms_count?: number;
    members_count?: number;
    uptime_seconds?: number;
    started_at?: number;
    [key: string]: unknown;
}

export interface RrcDiscoveredHub {
    hub_hash?: string;
    name?: string;
    display_name?: string;
    custom_display_name?: string | null;
    destination_hash?: string;
    hops?: number;
    last_heard?: number | string;
    [key: string]: unknown;
}
