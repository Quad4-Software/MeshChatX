// SPDX-License-Identifier: 0BSD

/** Room entry derived from a hub's known_rooms / available_rooms data. */
export interface RrcRoom {
    name: string;
    topic?: string;
    unread?: number;
    has_key?: boolean;
    [key: string]: unknown;
}

/** Available (not yet joined) room reported by a hub's ROOMS listing. */
export interface RrcAvailableRoom {
    name: string;
    topic?: string | null;
    has_key?: boolean;
    [key: string]: unknown;
}

/**
 * Client hub as returned by GET /api/v1/rrc/hubs (RRCHub.to_dict()).
 * status is numeric: 0 disconnected, 1 connecting, 2 connected, 3 failed.
 */
export interface RrcHub {
    hub_hash: string;
    dest_name?: string | null;
    name?: string;
    display_name?: string;
    custom_name?: string | null;
    hub_icon?: string | null;
    hub_name_announced?: string | null;
    status?: number;
    status_text?: string | null;
    connected?: boolean;
    hub_name?: string | null;
    hub_version?: string | null;
    motd?: string | null;
    rooms?: string[];
    known_rooms?: string[];
    unread_rooms?: string[];
    unread_counts?: Record<string, number>;
    total_unread?: number;
    mention_rooms?: string[];
    available_rooms?: Record<string, string | null>;
    available_keyed_rooms?: string[];
    stored_key_rooms?: string[];
    auto_reconnect?: boolean;
    auto_list?: boolean;
    auto_who?: boolean;
    nick_override?: string | null;
    max_msg_body_bytes?: number;
    [key: string]: unknown;
}

/**
 * Room message as returned by the backend. ts is milliseconds since epoch,
 * nick is the sender display name and src the sender identity hash hex.
 * mention is server-set; localMention is set client-side by highlight words.
 */
export interface RrcMessage {
    seq?: number | string;
    kind?: "msg" | "action" | "system" | "notice" | "error";
    ts: number;
    src?: string;
    nick?: string;
    room?: string;
    event?: string;
    text: string;
    mention?: boolean;
    localMention?: boolean;
    [key: string]: unknown;
}

export interface RrcTimelineEntry {
    type: "message" | "dateDivider" | "presenceGroup";
    id?: string;
    dayKey?: string;
    msg?: RrcMessage;
    messages?: RrcMessage[];
    joinedCount?: number;
    leftCount?: number;
    connectionCount?: number;
    [key: string]: unknown;
}

/** Room member as returned by GET .../rooms/{room}/messages ({hash, name}). */
export interface RrcMember {
    hash: string;
    name: string;
    [key: string]: unknown;
}

/** Hosted hub as returned by GET /api/v1/rrc/servers (manager.to_dict). */
export interface RrcHostedHub {
    id: string;
    name?: string;
    dest_hash?: string | null;
    enabled?: boolean;
    running?: boolean;
    announce?: boolean;
    announce_interval_seconds?: number;
    greeting?: string | null;
    uptime_seconds?: number;
    clients?: number;
    rooms?: { name: string; topic?: string | null; private?: boolean; registered?: boolean; members?: number }[];
    [key: string]: unknown;
}

/** Announce table row for rrc.hub aspect nodes. */
export interface RrcDiscoveredHub {
    destination_hash: string;
    aspect?: string;
    identity_hash?: string;
    display_name?: string | null;
    custom_display_name?: string | null;
    hops?: number;
    updated_at?: string;
    [key: string]: unknown;
}

export interface RrcBotConfig {
    hub?: string;
    rooms?: string[];
    nick?: string;
    mention_only?: boolean;
    prefix?: string;
    rate_seconds?: number;
    [key: string]: unknown;
}

export interface RrcBotRecord {
    id: string;
    name: string;
    running?: boolean;
    template?: string;
    template_id?: string;
    last_error?: string | null;
    rrc?: RrcBotConfig | null;
    [key: string]: unknown;
}

export interface RrcKnownHub {
    hash: string;
    name: string;
}

export interface RrcSearchHit {
    hub_hash: string;
    hub_name?: string;
    room: string;
    nick?: string;
    text: string;
    ts?: number | string;
    kind?: string;
    [key: string]: unknown;
}

/** Local-only ignored peer entry stored per identity. */
export interface RrcIgnoredPeer {
    hash: string;
    name: string;
}

/** Per-message translation state keyed by relayMessageKey. */
export interface RrcMessageTranslation {
    loading: boolean;
    text: string;
    from: string;
    to: string;
    showOriginal: boolean;
}
