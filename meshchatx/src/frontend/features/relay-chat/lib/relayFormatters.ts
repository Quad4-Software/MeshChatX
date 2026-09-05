// SPDX-License-Identifier: 0BSD

import { DEFAULT_RRC_HUB_ICON, normalizeMdiIconName } from "../../../js/mdiIconNames.js";
import { NAME_COLORS } from "./constants.js";
import type { RrcHub, RrcMember, RrcMessage } from "./types.js";

export interface RelayOfflineMember {
    hash: string;
    name: string;
}

export function formatTime(ts: number): string {
    if (!ts) return "";
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatUptime(seconds: number): string {
    if (!seconds || seconds <= 0) return "0s";
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (d > 0) return `${d}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

export function formatUnreadBadge(count: number): string {
    if (count > 99) return "99+";
    return String(count);
}

export function statusIconColor(status?: string): string {
    if (status === "connected") return "text-emerald-500";
    if (status === "connecting") return "text-amber-500 animate-pulse";
    if (status === "error") return "text-red-500";
    return "text-sem-fg-muted";
}

export function hubIconName(hub?: RrcHub | null): string {
    return normalizeMdiIconName(hub?.icon) || DEFAULT_RRC_HUB_ICON;
}

export function hubDisplayName(hub?: RrcHub | null): string {
    if (!hub) return "";
    return hub.custom_display_name || hub.display_name || hub.name || hub.hub_hash?.substring(0, 16) || "";
}

export function nameStyle(msg?: RrcMessage | null): string {
    if (!msg?.src && !msg?.nickname) return "color: var(--sem-fg);";
    const seed = msg.nickname || msg.src || "";
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
        hash = (hash << 5) - hash + seed.charCodeAt(i);
        hash |= 0;
    }
    const colorIndex = Math.abs(hash) % NAME_COLORS.length;
    return `color: ${NAME_COLORS[colorIndex]};`;
}

export function displayName(msg?: RrcMessage | null): string {
    if (!msg) return "";
    return msg.nickname || msg.src?.substring(0, 8) || "Unknown";
}

export function deriveOfflineRelayMembers(onlineMembers: RrcMember[], messages: RrcMessage[]): RelayOfflineMember[] {
    const onlineHashes = new Set(
        onlineMembers
            .map((member) => String(member.identity_hash || (member as { hash?: string }).hash || ""))
            .filter(Boolean)
    );
    const seen = new Map<string, RelayOfflineMember>();
    for (const msg of messages) {
        if (!msg.src || onlineHashes.has(msg.src) || seen.has(msg.src)) {
            continue;
        }
        const nick = msg.nickname || (msg as { nick?: string }).nick;
        seen.set(msg.src, {
            hash: msg.src,
            name: nick || msg.src.slice(0, 12),
        });
    }
    return Array.from(seen.values()).sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
}
