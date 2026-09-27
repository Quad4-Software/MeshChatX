// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import { isVisualiserWasmReady } from "../../../js/VisualiserWasmLoader.js";
import {
    buildFullGraph,
    computeRadialPositions,
    hashposXY,
    layoutSpringLength,
    VIZ_ANNOUNCE_ASPECTS,
} from "../../../js/networkVisualiserPerf.js";
import { DEFAULT_RETICULUM_LOGO_PATH, INTERFACE_CONNECTED_IMAGE, INTERFACE_DISCONNECTED_IMAGE } from "./constants.js";
import type {
    PathTableEntry,
    AnnounceEntry,
    InterfaceEntry,
    DiscoveredInterfaceEntry,
    DiscoveredActiveEntry,
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
    discoveredActive?: DiscoveredActiveEntry[];
    iconCache?: Record<string, string>;
    iconGeneration?: number;
    radial?: boolean;
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
        const activeEndpoints = new Set<string>();
        for (const a of options.discoveredActive || []) {
            const aHost = a.target_host || a.remote || a.listen_ip;
            const aPort = a.target_port || a.listen_port;
            if (aHost && aPort != null) activeEndpoints.add(`${aHost}:${aPort}`);
        }
        for (const disc of discoveredInterfaces) {
            const discId = `discovered~${disc.discovery_hash || disc.name}`;
            const discLabel = disc.name || disc.reachable_on || "Unknown";
            if (!matchesSearch(discLabel) && !matchesSearch(disc.reachable_on) && !matchesSearch(disc.transport_id)) {
                continue;
            }
            const isConnected =
                disc.reachable_on != null &&
                disc.port != null &&
                activeEndpoints.has(`${disc.reachable_on}:${disc.port}`);
            discPayload.push({
                id: discId,
                label: discLabel,
                title: `Discovered: ${discLabel}\nType: ${disc.type || "Unknown"}\nHops: ${disc.hops ?? "?"}\nStatus: ${isConnected ? "Connected" : disc.status || "Available"}${disc.reachable_on ? `\nAddress: ${disc.reachable_on}:${disc.port}` : ""}`,
                connected: isConnected,
                hops: disc.hops ?? null,
                reachable_on: disc.reachable_on ?? null,
                transport_id: disc.transport_id ?? null,
            });
        }
    }

    const myName = config?.display_name || "My Node";
    const myTitle = `This Node (${myName})\nIdentity: ${config?.identity_hash || "Unknown"}`;

    const radial = options.radial === true;
    const positionsIn = radial
        ? {
              // Radial view overrides every position with deterministic hop
              // rings around me, so nothing is missing and settle is skipped.
              ...positions,
              ...computeRadialPositions({
                  interfaces: [...interfacesPayload.map((i) => i.name), ...pathOnlyPayload.map((i) => i.name)],
                  discovered: discPayload.map((d) => d.id).filter(Boolean),
                  pathTable,
                  hopMax: hopMaxFilter,
              }),
          }
        : positions;

    // WASM emits the whole graph; the JS fallback only emits path nodes,
    // so me/ifaces/discovered are synthesized below. Keys match the
    // visualiser-wasm FullRequest contract.
    const fullReq = {
        me_label: myName,
        me_title: myTitle,
        me_image: DEFAULT_RETICULUM_LOGO_PATH,
        identity_hash: config?.identity_hash ?? "",
        interfaces: interfacesPayload,
        path_only_interfaces: pathOnlyPayload,
        discovered: discPayload,
        path_table: pathTable,
        announces: announcePayload,
        conversations: conversationPayload,
        icon_cache: options.iconCache || {},
        positions: positionsIn,
        hop_max: hopMaxFilter,
        search: searchQuery,
        dark_mode: isDarkMode,
        lod: currentLOD,
        aspects: [...VIZ_ANNOUNCE_ASPECTS],
        queue_icons: currentLOD !== "low",
        icon_generation: options.iconGeneration ?? 0,
        show_discovered: showDiscoveredInterfaces,
    };

    const rawGraph = buildFullGraph(fullReq as any) as {
        nodes?: any[];
        edges?: any[];
        layout_nodes?: any[];
        layout_edges?: any[];
        icon_queue?: any[];
        processed_node_ids?: any[];
        processed_edge_ids?: any[];
    } | null;

    let graphNodes = Array.isArray(rawGraph?.nodes) ? rawGraph.nodes : [];
    let graphEdges = Array.isArray(rawGraph?.edges) ? rawGraph.edges : [];
    let layoutNodes: any[] = Array.isArray(rawGraph?.layout_nodes) ? rawGraph.layout_nodes : [];
    let layoutEdges: any[] = Array.isArray(rawGraph?.layout_edges) ? rawGraph.layout_edges : [];

    // When WASM full-graph is unavailable, synthesize me/ifaces/discovered
    // in JS. Mirrors visualiser-wasm internal/graph/full.go BuildFullGraph.
    if (!isVisualiserWasmReady()) {
        const localNodes: any[] = [];
        const localEdges: any[] = [];
        const posByIdRef = positionsIn;
        const pickStablePosition = (id: string, initial: () => { x: number; y: number }): { x: number; y: number } => {
            const prev = posByIdRef[id];
            if (prev && Number.isFinite(prev.x) && Number.isFinite(prev.y)) {
                return { x: prev.x, y: prev.y };
            }
            return initial();
        };
        let meAdded = false;
        if (matchesSearch(myName) || matchesSearch(config?.identity_hash)) {
            const mp = pickStablePosition("me", () => ({ x: 0, y: 0 }));
            let meNode: any = {
                id: "me",
                group: "me",
                size: 50,
                _originalSize: 50,
                shape: "circularImage",
                _originalShape: "circularImage",
                image: DEFAULT_RETICULUM_LOGO_PATH,
                label: myName,
                title: fullReq.me_title,
                color: vizNodeColor("#3b82f6", isDarkMode ? "#1e40af" : "#eff6ff"),
                font: { color: isDarkMode ? "#ffffff" : "#000000", size: 16, bold: true },
                x: mp.x,
                y: mp.y,
            };
            meNode = {
                ...meNode,
                _originalColor: meNode.color,
                ...nodeLodProps(meNode, currentLOD, isDarkMode),
            };
            localNodes.push(meNode);
            meAdded = true;
        }
        // New interfaces spread on a circle like the WASM builder.
        const ifaceRadius = 210;
        interfacesPayload.forEach((entry, j) => {
            const angle = (j / interfacesPayload.length) * Math.PI * 2;
            const pos = pickStablePosition(entry.name, () => ({
                x: Math.cos(angle) * ifaceRadius,
                y: Math.sin(angle) * ifaceRadius,
            }));
            let n: any = {
                id: entry.name,
                group: "interface",
                label: entry.label,
                title: entry.title,
                size: 35,
                _originalSize: 35,
                shape: "circularImage",
                _originalShape: "circularImage",
                image: entry.online ? INTERFACE_CONNECTED_IMAGE : INTERFACE_DISCONNECTED_IMAGE,
                color: entry.online
                    ? vizNodeColor("#10b981", isDarkMode ? "#064e3b" : "#ecfdf5")
                    : vizNodeColor("#ef4444", isDarkMode ? "#7f1d1d" : "#fef2f2"),
                font: { color: isDarkMode ? "#ffffff" : "#000000", size: 12, bold: true },
                x: pos.x,
                y: pos.y,
            };
            n = { ...n, _originalColor: n.color, ...nodeLodProps(n, currentLOD, isDarkMode) };
            localNodes.push(n);
            if (meAdded) {
                localEdges.push({
                    id: `me~${entry.name}`,
                    from: "me",
                    to: entry.name,
                    color: entry.online
                        ? vizDirectEdgeColor(isDarkMode)
                        : { color: isDarkMode ? "#f87171" : "#ef4444", opacity: 1 },
                    width: 3,
                    hidden: false,
                });
            }
        });
        pathOnlyPayload.forEach((entry, j) => {
            const angle = (j / pathOnlyPayload.length) * Math.PI * 2;
            const pos = pickStablePosition(entry.name, () => ({
                x: Math.cos(angle) * ifaceRadius,
                y: Math.sin(angle) * ifaceRadius,
            }));
            let n: any = {
                id: entry.name,
                group: "interface",
                label: entry.label,
                title: entry.title,
                size: 35,
                _originalSize: 35,
                shape: "circularImage",
                _originalShape: "circularImage",
                image: INTERFACE_CONNECTED_IMAGE,
                color: vizNodeColor("#10b981", isDarkMode ? "#064e3b" : "#ecfdf5"),
                font: { color: isDarkMode ? "#ffffff" : "#000000", size: 12, bold: true },
                x: pos.x,
                y: pos.y,
            };
            n = { ...n, _originalColor: n.color, ...nodeLodProps(n, currentLOD, isDarkMode) };
            localNodes.push(n);
            if (meAdded) {
                localEdges.push({
                    id: `me~${entry.name}`,
                    from: "me",
                    to: entry.name,
                    color: vizDirectEdgeColor(isDarkMode),
                    width: 3,
                    hidden: false,
                });
            }
        });
        if (showDiscoveredInterfaces) {
            for (const disc of discPayload) {
                if (hopMaxFilter != null && disc.hops != null && disc.hops > hopMaxFilter) continue;
                const pos = pickStablePosition(disc.id, () => hashposXY(disc.id, 560, 240));
                let n: any = {
                    id: disc.id,
                    group: "discovered",
                    label: disc.label,
                    title: disc.title,
                    size: 25,
                    _originalSize: 25,
                    shape: "circularImage",
                    _originalShape: "circularImage",
                    image: disc.connected ? INTERFACE_CONNECTED_IMAGE : INTERFACE_DISCONNECTED_IMAGE,
                    color: disc.connected
                        ? vizNodeColor("#06b6d4", isDarkMode ? "#164e63" : "#ecfeff")
                        : vizNodeColor("#64748b", isDarkMode ? "#1e293b" : "#f1f5f9"),
                    font: { color: isDarkMode ? "#ffffff" : "#000000", size: 10 },
                    x: pos.x,
                    y: pos.y,
                };
                n = { ...n, _originalColor: n.color, ...nodeLodProps(n, currentLOD, isDarkMode) };
                localNodes.push(n);
                if (meAdded) {
                    localEdges.push({
                        id: `me~${disc.id}`,
                        from: "me",
                        to: disc.id,
                        color: { color: isDarkMode ? "#155e75" : "#06b6d4", opacity: 0.35 },
                        width: 1,
                        hidden: false,
                    });
                }
            }
        }
        graphNodes = [...localNodes, ...graphNodes];
        graphEdges = [...localEdges, ...graphEdges];
        // Path edges can point at interface nodes the search filter dropped.
        // Drop them before the layout edge list is built.
        const mergedNodeIds = new Set<string>();
        for (const n of graphNodes) {
            if (n?.id) mergedNodeIds.add(n.id);
        }
        graphEdges = graphEdges.filter((e) => e && mergedNodeIds.has(e.from) && mergedNodeIds.has(e.to));
        layoutNodes = graphNodes.map((n) => ({
            id: n.id,
            x: n.x,
            y: n.y,
            mass: n.group === "me" ? 4 : n.group === "interface" ? 2.5 : n.group === "discovered" ? 1.2 : 1,
            fixed: radial || n.id === "me",
            radius: Number.isFinite(n.size) ? n.size : 22,
        }));
        layoutEdges = graphEdges.map((e) => ({
            from: e.from,
            to: e.to,
            length: layoutSpringLength(e.width),
        }));
    }

    // Path edges can point at interface nodes the search filter dropped. A
    // dangling endpoint breaks vis-network updates and skews the WebGL edge
    // count, so drop those edges here.
    const graphNodeIds = new Set<string>();
    for (const n of graphNodes) {
        if (n?.id) graphNodeIds.add(n.id);
    }
    graphEdges = graphEdges.filter((e) => e && graphNodeIds.has(e.from) && graphNodeIds.has(e.to));

    // Radial pins every node so hop rings stay put under live layout and
    // scene ticks. Flat must emit fixed explicitly: vis-network deep-merges
    // node updates, so a stale fixed pin from radial would otherwise survive
    // the switch back.
    for (const node of graphNodes) {
        if (node) node.fixed = radial || node.id === "me";
    }
    for (const body of layoutNodes) {
        if (body) body.fixed = radial || body.id === "me";
    }

    return {
        nodes: graphNodes,
        edges: graphEdges,
        layout_nodes: layoutNodes,
        layout_edges: layoutEdges,
        icon_queue: Array.isArray(rawGraph?.icon_queue) ? rawGraph.icon_queue : [],
        processed_node_ids: Array.isArray(rawGraph?.processed_node_ids) ? rawGraph.processed_node_ids : [],
        processed_edge_ids: Array.isArray(rawGraph?.processed_edge_ids) ? rawGraph.processed_edge_ids : [],
    };
}
function vizNodeColor(border: string, background: string) {
    return {
        border,
        background,
        highlight: { border, background },
        hover: { border, background },
    };
}

function vizDirectEdgeColor(isDarkMode: boolean) {
    return { color: isDarkMode ? "#34d399" : "#10b981", opacity: 1 };
}

/** LOD props for a synthesized node; mirrors computeLodUpdatesJs for one node. */
function nodeLodProps(node: Record<string, any>, lod: string, isDarkMode: boolean): Record<string, any> {
    const fontColor = isDarkMode ? "#ffffff" : "#000000";
    const blueBorder = "#3b82f6";
    const blueBg = isDarkMode ? "#1e40af" : "#eff6ff";

    if (lod === "low") {
        const isInterface = node.group === "interface";
        const baseColor = isInterface && node.color ? node.color : vizNodeColor(blueBorder, blueBg);
        return {
            id: node.id,
            shape: "dot",
            size: node.id === "me" ? 15 : 10,
            font: { size: 0 },
            color: baseColor,
        };
    }
    if (lod === "medium") {
        const props: Record<string, any> = {
            id: node.id,
            shape: node._originalShape || "circularImage",
            size: node._originalSize || (node.id === "me" ? 50 : 25),
            font: { size: 0 },
        };
        // Low LOD stamps a generic blue over node.color; hand back the
        // semantic color stashed at build time.
        const semantic = node._originalColor || node.color;
        if (semantic) props.color = semantic;
        return props;
    }
    const props: Record<string, any> = {
        id: node.id,
        shape: node._originalShape || "circularImage",
        size: node._originalSize || (node.id === "me" ? 50 : 25),
        font: { size: node.id === "me" ? 16 : 11, color: fontColor },
    };
    const semantic = node._originalColor || node.color;
    if (semantic) props.color = semantic;
    return props;
}
