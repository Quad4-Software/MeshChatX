// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import { buildFullGraph } from "../../../js/networkVisualiserPerf.js";
import { DEFAULT_RETICULUM_LOGO_PATH, INTERFACE_CONNECTED_IMAGE, INTERFACE_DISCONNECTED_IMAGE } from "./constants.js";
import type {
    PathTableEntry,
    AnnounceEntry,
    InterfaceEntry,
    DiscoveredInterfaceEntry,
    ConversationEntry,
    VisualiserConfig,
} from "./types.js";

export function pathTableInterfaceNames(pathTable: PathTableEntry[], hopMaxFilter: number | null): Set<string> {
    const names = new Set<string>();
    for (const entry of pathTable) {
        if (!entry?.interface || entry.hops == null) {
            continue;
        }
        if (hopMaxFilter != null && entry.hops > hopMaxFilter) {
            continue;
        }
        names.add(entry.interface);
    }
    return names;
}

export function interfaceDisplayLabel(name: string): string {
    if (!name) {
        return "Interface";
    }
    const bracket = name.match(/\[([^\]]+)\]/);
    if (bracket) {
        return bracket[1];
    }
    if (name.length > 28) {
        return `${name.slice(0, 25)}...`;
    }
    return name;
}

export function collectVisualiserPositions(options: {
    cachedPositions?: Record<string, { x: number; y: number }>;
    webglEngine?: { getPositions?: () => Record<string, { x: number; y: number }> } | null;
    network?: { getPositions?: (ids: string[]) => Record<string, { x: number; y: number }> } | null;
    existingNodeIds?: string[];
}): Record<string, { x: number; y: number }> {
    const posById: Record<string, { x: number; y: number }> = {};
    const { cachedPositions, webglEngine, network, existingNodeIds = [] } = options;

    for (const [id, p] of Object.entries(cachedPositions || {})) {
        if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
            posById[id] = { x: p.x, y: p.y };
        }
    }

    if (webglEngine && typeof webglEngine.getPositions === "function") {
        const snap = webglEngine.getPositions() || {};
        for (const [id, p] of Object.entries(snap)) {
            if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                posById[id] = { x: p.x, y: p.y };
            }
        }
    } else if (network && typeof network.getPositions === "function") {
        const snap = network.getPositions(existingNodeIds);
        if (snap) {
            for (const id of existingNodeIds) {
                const p = snap[id];
                if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                    posById[id] = { x: p.x, y: p.y };
                }
            }
        }
    }

    return posById;
}

export function buildVisualiserGraph(options: {
    config: VisualiserConfig | null;
    interfaces: InterfaceEntry[];
    discoveredInterfaces: DiscoveredInterfaceEntry[];
    pathTable: PathTableEntry[];
    announces: Record<string, AnnounceEntry>;
    conversations: Record<string, ConversationEntry>;
    showDisabledInterfaces: boolean;
    showDiscoveredInterfaces: boolean;
    searchQuery: string;
    hopMaxFilter: number | null;
    positions: Record<string, { x: number; y: number }>;
    isDarkMode: boolean;
    currentLOD: string;
    batterySaverPrefs?: { enabled?: boolean; maxVisualiserInterfaces?: number };
}) {
    const {
        config,
        interfaces,
        discoveredInterfaces,
        pathTable,
        announces,
        conversations,
        showDisabledInterfaces,
        showDiscoveredInterfaces,
        searchQuery,
        hopMaxFilter,
        positions,
        isDarkMode,
        currentLOD,
        batterySaverPrefs,
    } = options;

    const announcePayload: Record<string, any> = {};
    for (const [hash, announce] of Object.entries(announces || {})) {
        if (!announce) continue;
        announcePayload[hash] = {
            destination_hash: announce.destination_hash,
            aspect: announce.aspect,
            display_name: announce.display_name,
            custom_display_name: announce.custom_display_name,
            identity_hash: announce.identity_hash,
            last_seen: announce.updated_at
                ? Utils.convertDateTimeToLocalDateTimeString(new Date(announce.updated_at))
                : "",
        };
    }

    const conversationPayload: Record<string, any> = {};
    for (const [hash, conv] of Object.entries(conversations || {})) {
        if (!conv?.lxmf_user_icon) continue;
        conversationPayload[hash] = { lxmf_user_icon: conv.lxmf_user_icon };
    }

    const searchLower = searchQuery.toLowerCase();
    const matchesSearch = (text?: string | null) => !searchQuery || (text && text.toLowerCase().includes(searchLower));

    const interfacesPayload: any[] = [];
    for (const entry of interfaces) {
        if (!showDisabledInterfaces && !entry.status) continue;
        let label = entry.interface_name ?? entry.name;
        if (entry.type === "LocalServerInterface" || entry.parent_interface_name != null) {
            label = entry.name;
        }
        if (!matchesSearch(label) && !matchesSearch(entry.name)) continue;
        interfacesPayload.push({
            name: entry.name,
            label,
            title: `${entry.name}\nState: ${entry.status ? "Online" : "Offline"}\nBitrate: ${Utils.formatBitsPerSecond(entry.bitrate ?? 0)}\nTX: ${Utils.formatBytes(entry.txb ?? 0)}\nRX: ${Utils.formatBytes(entry.rxb ?? 0)}`,
            online: !!entry.status,
        });
    }

    if (
        batterySaverPrefs?.enabled &&
        (batterySaverPrefs.maxVisualiserInterfaces ?? 0) > 0 &&
        interfacesPayload.length > (batterySaverPrefs.maxVisualiserInterfaces ?? 0)
    ) {
        interfacesPayload.sort((a, b) => Number(b.online) - Number(a.online));
        interfacesPayload.length = batterySaverPrefs.maxVisualiserInterfaces ?? 0;
    }

    const seenIface = new Set(interfacesPayload.map((i) => i.name));
    const pathOnlyPayload: any[] = [];
    for (const name of pathTableInterfaceNames(pathTable, hopMaxFilter)) {
        if (seenIface.has(name)) continue;
        if (!matchesSearch(name) && !matchesSearch(interfaceDisplayLabel(name))) continue;
        pathOnlyPayload.push({
            name,
            label: interfaceDisplayLabel(name),
            title: `${name}\nState: Active (path table)\nUsed as next-hop for known routes`,
            online: true,
        });
    }

    const discPayload: any[] = [];
    if (showDiscoveredInterfaces) {
        for (const disc of discoveredInterfaces) {
            const discName = disc.name || disc.reachable_on || disc.transport_id || disc.discovery_hash || "";
            if (!matchesSearch(discName)) continue;
            discPayload.push({
                name: discName,
                label: discName,
                title: `Discovered: ${discName}\nType: ${disc.type || "Unknown"}\nHops: ${disc.hops ?? "Direct"}\nState: ${disc.status || "Discovered"}\nPort: ${disc.port || "Default"}`,
                connected: false,
                parent_interface: disc.reachable_on || null,
            });
        }
    }

    const myName = config?.display_name || "My Node";
    const myTitle = `This Node (${myName})\nIdentity: ${config?.identity_hash || "Unknown"}`;

    return buildFullGraph({
        myNode: { name: myName, title: myTitle, image: DEFAULT_RETICULUM_LOGO_PATH },
        interfaces: interfacesPayload,
        pathOnlyInterfaces: pathOnlyPayload,
        discoveredInterfaces: discPayload,
        pathTable,
        announces: announcePayload,
        conversations: conversationPayload,
        positions,
        isDarkMode,
        currentLOD,
        searchQuery,
        hopMaxFilter,
        connectedInterfaceImage: INTERFACE_CONNECTED_IMAGE,
        disconnectedInterfaceImage: INTERFACE_DISCONNECTED_IMAGE,
    });
}
