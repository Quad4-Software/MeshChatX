// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import type { ConfiguredInterface, DiscoveredInterface, DiscoveredActiveInterface, InterfaceStats } from "./types.js";

export function formatFrequency(hz?: number | null): string {
    return Utils.formatFrequency(hz);
}

export function formatBitsPerSecond(bits?: number | null): string {
    return Utils.formatBitsPerSecond(bits);
}

export function formatBytes(bytes?: number | null): string {
    return Utils.formatBytes(bytes || 0);
}

export function parseBool(value: unknown): boolean {
    if (typeof value === "string") {
        return ["true", "yes", "1", "y", "on"].includes(value.toLowerCase());
    }
    return Boolean(value);
}

export function formatLastHeard(ts?: number | null): string {
    if (ts == null) return "";
    const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

export function getDiscoveryIcon(iface: { type?: string; port?: string | number }): string {
    switch (iface.type) {
        case "AutoInterface":
            return "home-automation";
        case "RNodeInterface":
            return iface.port && String(iface.port).startsWith("tcp://") ? "lan-connect" : "radio-tower";
        case "RNodeMultiInterface":
            return "access-point-network";
        case "TCPClientInterface":
        case "BackboneInterface":
            return "lan-connect";
        case "TCPServerInterface":
            return "lan";
        case "UDPInterface":
            return "wan";
        case "SerialInterface":
            return "usb-port";
        case "KISSInterface":
        case "AX25KISSInterface":
            return "antenna";
        case "I2PInterface":
            return "eye";
        case "PipeInterface":
            return "pipe";
        default:
            return "server-network";
    }
}

export function getInterfaceIcon(iface: { type?: string; port?: string | number }): string {
    switch (iface.type) {
        case "AutoInterface":
            return "home-automation";
        case "RNodeInterface":
            return iface.port && String(iface.port).startsWith("tcp://") ? "lan-connect" : "radio-tower";
        case "RNodeMultiInterface":
            return "access-point-network";
        case "TCPClientInterface":
            return "lan-connect";
        case "TCPServerInterface":
            return "lan";
        case "UDPInterface":
            return "wan";
        case "SerialInterface":
            return "usb-port";
        case "KISSInterface":
        case "AX25KISSInterface":
            return "antenna";
        case "I2PInterface":
            return "eye";
        case "PipeInterface":
            return "pipe";
        case "HTTPInterface":
            return "web";
        default:
            return "server-network";
    }
}

export function isBackboneIfacTunnel(iface: ConfiguredInterface): boolean {
    if (iface.type !== "BackboneInterface") {
        return false;
    }
    if (iface._stats?.ifac_signature) {
        return true;
    }
    return Boolean(iface.passphrase || iface.network_name || iface.ifac_netname || iface.ifac_netkey);
}

export function getInterfaceDescription(iface: ConfiguredInterface): string {
    if (iface.type === "TCPClientInterface") {
        return `${iface.target_host}:${iface.target_port}`;
    }
    if (iface.type === "HTTPInterface") {
        const tunnelMode = String(iface.mode || "").toLowerCase();
        if (tunnelMode === "server") {
            return `HTTP ${iface.listen_host || "0.0.0.0"}:${iface.listen_port}`;
        }
        return iface.server_url || "HTTP tunnel client";
    }
    if (iface.type === "TCPServerInterface" || iface.type === "UDPInterface") {
        return `${iface.listen_ip}:${iface.listen_port}`;
    }
    if (iface.type === "SerialInterface") {
        return `${iface.port} @ ${iface.speed || "9600"}bps`;
    }
    if (iface.type === "RNodeInterface" && iface.port && String(iface.port).startsWith("tcp://")) {
        return `RNode over IP @ ${String(iface.port).replace("tcp://", "")}`;
    }
    if (iface.type === "AutoInterface") {
        return "Auto-detect Ethernet and Wi-Fi peers";
    }
    if (iface.type === "BackboneInterface") {
        if (isBackboneIfacTunnel(iface)) {
            return "Backbone (IFAC tunnel)";
        }
        const remote = iface.remote || iface.target_host;
        const port = iface.target_port ?? iface.listen_port;
        if (remote && port != null && port !== "") {
            return `${remote}:${port}`;
        }
        const listenIp = iface.listen_ip;
        if ((listenIp || listenIp === "") && port != null && port !== "") {
            return `${listenIp || "0.0.0.0"}:${port}`;
        }
        return "Backbone (public relay)";
    }
    return iface.description || "Custom interface";
}

export function isDiscoverable(value: unknown): boolean {
    if (typeof value === "string") {
        return ["true", "yes", "1", "on"].includes(value.toLowerCase());
    }
    return Boolean(value);
}

export function isInterfaceEnabled(iface: ConfiguredInterface): boolean {
    return Utils.isInterfaceEnabled(iface);
}

export function getLinkStatus(
    iface: ConfiguredInterface,
    isReticulumRunning: boolean
): {
    key: "up" | "down" | null;
    labelKey: string;
    chipClass: string;
} {
    if (!isReticulumRunning || !isInterfaceEnabled(iface)) {
        return {
            key: null,
            labelKey: "interface.link_unknown",
            chipClass:
                "inline-flex items-center rounded-full bg-gray-100 text-gray-700 dark:bg-zinc-800 text-sem-fg-muted px-2 py-0.5 text-xs font-semibold",
        };
    }
    const st = iface._stats;
    if (!st || typeof st !== "object") {
        return {
            key: "down",
            labelKey: "interface.link_down",
            chipClass:
                "inline-flex items-center rounded-full bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100 px-2 py-0.5 text-xs font-semibold",
        };
    }
    let isUp: boolean | null = null;
    if ("status" in st) {
        const s = st.status;
        if (s === true) isUp = true;
        else if (s === false) isUp = false;
        else if (typeof s === "string") {
            const t = s.toLowerCase();
            if (t === "up") isUp = true;
            else if (t === "down") isUp = false;
        }
    }
    if (isUp === null) {
        if (st.connected === true || st.online === true) isUp = true;
        else if (st.connected === false || st.online === false) isUp = false;
    }

    if (isUp === true) {
        return {
            key: "up",
            labelKey: "interface.link_up",
            chipClass:
                "inline-flex items-center rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/45 dark:text-emerald-100 px-2 py-0.5 text-xs font-semibold",
        };
    }
    if (isUp === false) {
        return {
            key: "down",
            labelKey: "interface.link_down",
            chipClass:
                "inline-flex items-center rounded-full bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100 px-2 py-0.5 text-xs font-semibold",
        };
    }
    return {
        key: null,
        labelKey: "interface.link_unknown",
        chipClass:
            "inline-flex items-center rounded-full bg-gray-100 text-gray-700 dark:bg-zinc-800 text-sem-fg-muted px-2 py-0.5 text-xs font-semibold",
    };
}

export function normalizeDiscoveryPatternInput(value: unknown): string[] {
    if (!value) return [];
    return String(value)
        .replace(/\r?\n/g, ",")
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);
}

export function sanitizeDiscoveryPattern(value: unknown): string {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/[\r\n,]/g, "")
        .trim()
        .slice(0, 128);
}

export function discoveryFilterCandidates(iface: DiscoveredInterface): string[] {
    const values = [
        iface.name,
        iface.type,
        iface.reachable_on,
        iface.target_host,
        iface.remote,
        iface.listen_ip,
        iface.port,
        iface.target_port,
        iface.listen_port,
        iface.discovery_hash,
        iface.transport_id,
        iface.network_id,
    ]
        .map((value) => sanitizeDiscoveryPattern(value))
        .filter(Boolean);
    const host = sanitizeDiscoveryPattern(iface.reachable_on || iface.target_host || iface.remote || iface.listen_ip);
    const port = sanitizeDiscoveryPattern(iface.port || iface.target_port || iface.listen_port);
    if (host && port) {
        values.push(`${host}:${port}`);
    }
    return values.map((value) => value.toLowerCase());
}

export function matchesDiscoveryGlob(pattern: string, value: string): boolean {
    const escaped = String(pattern)
        .replace(/[.+^${}()|[\]\\]/g, "\\$&")
        .replace(/\*/g, ".*");
    /* eslint-disable-next-line security/detect-non-literal-regexp */
    const regex = new RegExp(`^${escaped}$`, "i");
    return regex.test(value);
}

export function isDiscoveredBlacklisted(iface: DiscoveredInterface, blacklistStr?: string): boolean {
    const blacklist = normalizeDiscoveryPatternInput(blacklistStr).map((pattern) =>
        sanitizeDiscoveryPattern(pattern).toLowerCase()
    );
    if (!blacklist.length) return false;
    const candidates = discoveryFilterCandidates(iface);
    return blacklist.some((pattern) => candidates.some((candidate) => matchesDiscoveryGlob(pattern, candidate)));
}

export function discoveryPatternToken(iface: DiscoveredInterface): string {
    const host = sanitizeDiscoveryPattern(iface.reachable_on || iface.target_host || iface.remote || iface.listen_ip);
    const port = sanitizeDiscoveryPattern(iface.port || iface.target_port || iface.listen_port);
    if (host && port) return `${host}:${port}`;
    return (
        host ||
        sanitizeDiscoveryPattern(iface.transport_id) ||
        sanitizeDiscoveryPattern(iface.network_id) ||
        sanitizeDiscoveryPattern(iface.name)
    );
}

export function discoveredNetworkName(iface?: DiscoveredInterface | null): string | null {
    if (!iface) return null;
    return iface.network_name || iface.ifac_netname || null;
}

export function discoveredPassphrase(iface?: DiscoveredInterface | null): string | null {
    if (!iface) return null;
    return iface.passphrase || iface.ifac_netkey || null;
}

export function maskPassphrase(value?: string | null): string {
    if (!value) return "";
    const str = String(value);
    if (str.length <= 4) return "*".repeat(str.length);
    return `${str.slice(0, 2)}${"*".repeat(Math.max(4, str.length - 4))}${str.slice(-2)}`;
}

export function discoveryKey(iface: DiscoveredInterface): string {
    return (
        iface.discovery_hash ||
        `${iface.reachable_on || iface.target_host || iface.remote || iface.listen_ip || iface.name || "unknown"}:${
            iface.port || iface.target_port || iface.listen_port || ""
        }`
    );
}

function interfaceStatLinkUp(s: Record<string, unknown> | null | undefined): boolean {
    if (!s || typeof s !== "object") return false;
    if (s.status === false || s.connected === false || s.online === false) return false;
    if (s.status === true || s.connected === true || s.online === true) return true;
    return true;
}

export function isDiscoveredConnected(
    iface: DiscoveredInterface,
    activeList: DiscoveredActiveInterface[],
    statsList: InterfaceStats[],
    activeTransportIds: Set<string>,
    metadataPresent: boolean
): boolean {
    const reach = iface.reachable_on;
    const port = iface.port;
    const nid = iface.network_id ? String(iface.network_id).toLowerCase() : null;
    if (iface.transport_id && activeTransportIds.has(String(iface.transport_id).toLowerCase())) {
        return true;
    }
    for (const a of activeList || []) {
        const host = a.target_host || a.remote || a.listen_ip;
        const p = a.target_port || a.listen_port;
        if (!host || p == null || !reach || port == null) continue;
        if (String(host) !== String(reach) || Number(p) !== Number(port)) continue;
        const asrc = a.autoconnect_source;
        if (asrc != null && asrc !== undefined) {
            if (nid !== null && String(asrc).toLowerCase() !== nid) continue;
            return true;
        }
        if (!metadataPresent) return true;
    }
    return (statsList || []).some((s) => {
        const hostMatch =
            (s.target_host && reach && s.target_host === reach) || (s.remote && reach && s.remote === reach);
        const portMatch =
            (s.target_port && port && Number(s.target_port) === Number(port)) ||
            (s.listen_port && port && Number(s.listen_port) === Number(port));
        if (!hostMatch || !portMatch || !interfaceStatLinkUp(s as Record<string, unknown>)) return false;
        const asrc = s.autoconnect_source;
        if (asrc != null && asrc !== undefined) {
            if (nid !== null) return String(asrc).toLowerCase() === nid;
            return true;
        }
        return !metadataPresent;
    });
}

export function discoveredBytes(
    iface: DiscoveredInterface,
    activeList: DiscoveredActiveInterface[],
    statsList: InterfaceStats[],
    activeTransportIds: Set<string>,
    metadataPresent: boolean
): { tx: string; rx: string } | null {
    if (!isDiscoveredConnected(iface, activeList, statsList, activeTransportIds, metadataPresent)) {
        return null;
    }

    const tid = iface.transport_id ? String(iface.transport_id).toLowerCase() : null;
    if (tid) {
        const byTid = (activeList || []).find((a) => {
            if (!a.transport_id) return false;
            if (String(a.transport_id).toLowerCase() !== tid) return false;
            return interfaceStatLinkUp(a as Record<string, unknown>);
        });
        if (byTid && (byTid.txb !== undefined || byTid.rxb !== undefined)) {
            return {
                tx: formatBytes(byTid.txb ?? 0),
                rx: formatBytes(byTid.rxb ?? 0),
            };
        }
    }

    const reach = iface.reachable_on;
    const port = iface.port;
    const nid = iface.network_id ? String(iface.network_id).toLowerCase() : null;

    const byActive = (activeList || []).find((a) => {
        const host = a.target_host || a.remote || a.listen_ip;
        const p = a.target_port || a.listen_port;
        if (!host || p == null || !reach || port == null) return false;
        if (String(host) !== String(reach) || Number(p) !== Number(port)) return false;
        if (!interfaceStatLinkUp(a as Record<string, unknown>)) return false;
        const asrc = a.autoconnect_source;
        if (asrc != null && asrc !== undefined) {
            if (nid !== null) return String(asrc).toLowerCase() === nid;
            return true;
        }
        return !metadataPresent;
    });
    if (byActive && (byActive.txb !== undefined || byActive.rxb !== undefined)) {
        return {
            tx: formatBytes(byActive.txb ?? 0),
            rx: formatBytes(byActive.rxb ?? 0),
        };
    }

    const match = (statsList || []).find((s) => {
        const host = s.target_host || s.remote || s.listen_ip;
        const p = s.target_port || s.listen_port;
        if (!host || !reach || port == null || p == null) return false;
        if (String(host) !== String(reach) || Number(p) !== Number(port)) return false;
        if (!interfaceStatLinkUp(s as Record<string, unknown>)) return false;
        const asrc = s.autoconnect_source;
        if (asrc != null && asrc !== undefined) {
            if (nid !== null) return String(asrc).toLowerCase() === nid;
            return true;
        }
        return !metadataPresent;
    });
    if (!match || (match.txb === undefined && match.rxb === undefined)) return null;
    return {
        tx: formatBytes(match.txb ?? 0),
        rx: formatBytes(match.rxb ?? 0),
    };
}

export function formatDiscoveredConfig(iface: DiscoveredInterface): string {
    if (iface.config_entry) {
        return iface.config_entry;
    }
    const lines = [`[[${iface.name || "Interface"}]]`];
    if (iface.type) lines.push(`  type = ${iface.type}`);
    lines.push("  enabled = yes");
    if (iface.reachable_on) {
        if (iface.type === "TCPClientInterface" || iface.type === "BackboneInterface") {
            lines.push(`  target_host = ${iface.reachable_on}`);
        } else if (iface.type === "UDPInterface") {
            lines.push(`  forward_ip = ${iface.reachable_on}`);
        }
    }
    if (iface.port) {
        if (iface.type === "TCPClientInterface" || iface.type === "BackboneInterface") {
            lines.push(`  target_port = ${iface.port}`);
        } else if (iface.type === "UDPInterface") {
            lines.push(`  forward_port = ${iface.port}`);
        }
    }
    const netName = discoveredNetworkName(iface);
    if (netName) lines.push(`  network_name = ${netName}`);
    const pass = discoveredPassphrase(iface);
    if (pass) lines.push(`  passphrase = ${pass}`);
    return lines.join("\n");
}
