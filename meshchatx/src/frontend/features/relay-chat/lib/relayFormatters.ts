// SPDX-License-Identifier: 0BSD

import { t } from "../../../js/i18n.js";
import { DEFAULT_RRC_HUB_ICON, normalizeMdiIconName } from "../../../js/mdiIconNames.js";
import { NAME_COLORS } from "./constants.js";
import type { RrcHub, RrcMember, RrcMessage } from "./types.js";

export interface RelayOfflineMember {
    hash: string;
    name: string;
    [key: string]: unknown;
}

/** Hub status codes from the backend RRCHub.STATUS_* constants. */
export const RRC_STATUS_DISCONNECTED = 0;
export const RRC_STATUS_CONNECTING = 1;
export const RRC_STATUS_CONNECTED = 2;
export const RRC_STATUS_FAILED = 3;

/** ts from the backend is already milliseconds since epoch. */
export function formatTime(ts: number | string | null | undefined): string {
    if (!ts) return "";
    try {
        return new Date(Number(ts)).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
        return "";
    }
}

export function formatUptime(seconds: number | null | undefined): string {
    if (seconds == null || seconds < 0) {
        return "-";
    }
    let s = Math.floor(seconds);
    if (s < 60) {
        return `${s}s`;
    }
    if (s < 3600) {
        return `${Math.floor(s / 60)}m`;
    }
    if (s < 86400) {
        return `${Math.floor(s / 3600)}h`;
    }
    if (s < 30 * 86400) {
        return `${Math.floor(s / 86400)}d`;
    }
    const yearSec = 365 * 86400;
    const monthSec = 30 * 86400;
    const years = Math.floor(s / yearSec);
    s -= years * yearSec;
    const months = Math.floor(s / monthSec);
    s -= months * monthSec;
    const days = Math.floor(s / 86400);
    const parts: string[] = [];
    if (years) {
        parts.push(`${years}y`);
    }
    if (months) {
        parts.push(`${months}mo`);
    }
    if (days) {
        parts.push(`${days}d`);
    }
    return parts.length ? parts.join(" ") : "0d";
}

export function formatUnreadBadge(count: number | string | null | undefined): string {
    const n = Number(count) || 0;
    if (n <= 0) {
        return "";
    }
    if (n >= 1000) {
        return "999+";
    }
    return String(n);
}

/** Joined rooms in display order, driven by the hub's known_rooms list. */
export function orderedKnownRoomNames(hub?: RrcHub | null): string[] {
    if (!hub || !Array.isArray(hub.known_rooms)) {
        return [];
    }
    return hub.known_rooms.filter((name): name is string => typeof name === "string" && name.length > 0);
}

export function roomUnreadCount(hub: RrcHub | null | undefined, roomName: string): number {
    const counts = hub?.unread_counts;
    if (counts && typeof counts === "object" && counts[roomName] != null) {
        return Number(counts[roomName]) || 0;
    }
    if (Array.isArray(hub?.unread_rooms) && hub.unread_rooms.includes(roomName)) {
        return 1;
    }
    return 0;
}

export function roomHasMention(hub: RrcHub | null | undefined, roomName: string): boolean {
    return Array.isArray(hub?.mention_rooms) && hub.mention_rooms.includes(roomName);
}

export function hubTotalUnreadCount(hub: RrcHub | null | undefined): number {
    if (!hub) {
        return 0;
    }
    if (typeof hub.total_unread === "number") {
        return hub.total_unread;
    }
    const counts = hub.unread_counts;
    if (counts && typeof counts === "object") {
        return Object.values(counts).reduce((a, b) => a + (Number(b) || 0), 0);
    }
    return hub.unread_rooms ? hub.unread_rooms.length : 0;
}

export function isHubConnected(hub?: RrcHub | null): boolean {
    if (!hub) {
        return false;
    }
    return hub.connected === true || hub.status === RRC_STATUS_CONNECTED;
}

export function statusLabel(status?: number | string): string {
    switch (status) {
        case RRC_STATUS_CONNECTING:
        case "connecting":
            return t("relay_chat.status_connecting");
        case RRC_STATUS_CONNECTED:
        case "connected":
            return t("relay_chat.status_connected");
        case RRC_STATUS_FAILED:
        case "failed":
        case "error":
            return t("relay_chat.status_failed");
        default:
            return t("relay_chat.status_disconnected");
    }
}

export function statusTextColor(status?: number | string): string {
    if (status === RRC_STATUS_CONNECTED || status === "connected") {
        return "text-sem-success";
    }
    if (status === RRC_STATUS_FAILED || status === "failed" || status === "error") {
        return "text-sem-danger";
    }
    return "text-sem-fg-muted";
}

export function statusIconColor(status?: number | string): string {
    if (status === RRC_STATUS_CONNECTED || status === "connected") {
        return "text-sem-success";
    }
    if (status === RRC_STATUS_CONNECTING || status === "connecting") {
        return "text-sem-warning";
    }
    return "text-sem-danger";
}

export function hubIconName(hub?: RrcHub | null): string {
    if (!hub) {
        return DEFAULT_RRC_HUB_ICON;
    }
    return normalizeMdiIconName(hub.hub_icon) || DEFAULT_RRC_HUB_ICON;
}

export function hubDisplayName(hub?: RrcHub | null): string {
    if (!hub) {
        return "";
    }
    if (hub.display_name) {
        return hub.display_name;
    }
    return hub.name || "";
}

export function displayName(msg?: RrcMessage | null): string {
    if (msg?.nick) {
        return msg.nick;
    }
    if (msg?.src) {
        return String(msg.src).slice(0, 12);
    }
    return t("relay_chat.system");
}

export function colorForHash(hash?: string | null): string {
    if (!hash) {
        return "inherit";
    }
    let sum = 0;
    for (let i = 0; i < hash.length; i++) {
        sum = (sum + hash.charCodeAt(i)) % NAME_COLORS.length;
    }
    return NAME_COLORS[sum];
}

export function nameStyle(msg?: { src?: string } | null): string {
    return `color: ${colorForHash(msg?.src)};`;
}

export function memberInitial(name?: string | null): string {
    const ch = String(name || "")
        .trim()
        .match(/[a-zA-Z0-9]/);
    return ch ? ch[0].toUpperCase() : "?";
}

export function memberAvatarStyle(hash?: string | null): Record<string, string> {
    const color = colorForHash(hash);
    return { backgroundColor: `${color}26`, color };
}

/**
 * Members who have spoken in this room's loaded history but are not in the
 * live member list. Sorted by name like the backend roster.
 */
export function deriveOfflineRelayMembers(
    onlineMembers: RrcMember[] | RelayOfflineMember[],
    messages: RrcMessage[]
): RelayOfflineMember[] {
    const onlineHashes = new Set(onlineMembers.map((member) => String(member?.hash || "")).filter(Boolean));
    const seen = new Map<string, RelayOfflineMember>();
    for (const msg of messages) {
        if (!msg.src || onlineHashes.has(msg.src) || seen.has(msg.src)) {
            continue;
        }
        seen.set(msg.src, { hash: msg.src, name: msg.nick || msg.src.slice(0, 12) });
    }
    return Array.from(seen.values()).sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
}
