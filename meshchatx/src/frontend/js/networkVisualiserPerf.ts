// SPDX-License-Identifier: 0BSD

/**
 * Network visualiser hot-path helpers.
 * Prefers Go WASM when available, otherwise uses the pure JS implementations below.
 */

import { callVisualiserWasmJson, isVisualiserWasmReady, preloadVisualiserWasm } from "./VisualiserWasmLoader.js";

export const VIZ_ANNOUNCE_ASPECTS = ["lxmf.delivery", "nomadnetwork.node"] as const;

export const ANNOUNCE_HASH_CHUNK_SIZE = 500;

/** Must match visualiser-wasm layout.DefaultHubSpringLen. */
export const VIZ_HUB_SPRING_LEN = 200;

/** Must match visualiser-wasm layout.DefaultSpringLen. */
export const VIZ_PEER_SPRING_LEN = 240;

/** Soft cap for client-side path table rows kept in the visualiser. */
export const VIZ_PATH_TABLE_SOFT_CAP = 20_000;

/** Soft cap for announce map entries keyed by destination hash. */
export const VIZ_ANNOUNCE_SOFT_CAP = 10_000;

export type VizLodLevel = "low" | "medium" | "high";

export type VizPathTableEntry = {
    hash?: string;
    hops?: number | null;
    interface?: string;
    [key: string]: unknown;
};

export type VizAnnounceRecord = {
    aspect?: string;
    display_name?: string;
    custom_display_name?: string | null;
    destination_hash?: string;
    identity_hash?: string;
    last_seen?: string;
    [key: string]: unknown;
};

export type VizLxmfUserIcon = {
    icon_name?: string;
    foreground_colour?: string;
    background_colour?: string;
};

export type VizConversationRecord = {
    lxmf_user_icon?: VizLxmfUserIcon | null;
    [key: string]: unknown;
};

export type VizNodeColor = {
    border: string;
    background: string;
    highlight: { border: string; background: string };
    hover: { border: string; background: string };
};

export type VizGraphNode = {
    id: string;
    group?: string;
    size?: number;
    _originalSize?: number;
    _originalShape?: string;
    shape?: string;
    font?: { size?: number; color?: string };
    x?: number;
    y?: number;
    label?: string;
    title?: string;
    image?: string;
    color?: VizNodeColor | string;
    _parentInterface?: string;
    [key: string]: unknown;
};

export type VizGraphEdge = {
    id?: string;
    from?: string;
    to?: string;
    color?: { color?: string; opacity?: number } | string;
    width?: number;
    hidden?: boolean;
    [key: string]: unknown;
};

export type VizIconQueueItem = {
    nodeId: string;
    cacheKey: string;
    iconName: string;
    fg: string;
    bg: string;
    size: number;
    generation: number;
};

export type VizIconQueueBucket = {
    cacheKey: string;
    nodeIds: string[];
    iconName: string;
    fg: string;
    bg: string;
    size: number;
    generation: number;
};

export type VizPositionsMap = Record<string, { x?: number; y?: number } | undefined>;

export type VizPathGraphRequest = {
    path_table?: VizPathTableEntry[];
    announces?: Record<string, VizAnnounceRecord | undefined>;
    conversations?: Record<string, VizConversationRecord | undefined>;
    icon_cache?: Record<string, string | undefined>;
    positions?: VizPositionsMap;
    hop_max?: number | null;
    search?: string;
    dark_mode?: boolean;
    lod?: VizLodLevel | string;
    aspects?: string[];
    queue_icons?: boolean;
    icon_generation?: number;
    [key: string]: unknown;
};

export type VizPathGraphResult = {
    nodes: VizGraphNode[];
    edges: VizGraphEdge[];
    icon_queue: VizIconQueueItem[];
    processed_node_ids: string[];
    processed_edge_ids: string[];
};

export type VizLayoutNode = {
    id: string;
    x: number;
    y: number;
    mass: number;
    fixed: boolean;
    radius: number;
};

export type VizLayoutEdge = {
    from: string;
    to: string;
    length: number;
};

export type VizFullGraphResult = VizPathGraphResult & {
    layout_nodes: VizLayoutNode[];
    layout_edges: VizLayoutEdge[];
};

export type VizSettleLayoutRequest = {
    nodes: Array<{ id?: string; x?: number; y?: number } | null | undefined>;
    edges: unknown[];
    iterations?: number;
};

export type VizSettleLayoutResult = {
    positions: Record<string, { x: number; y: number }>;
    iterations: number;
};

export type VizLodUpdate = {
    id: string;
    shape: string;
    size: number;
    font: { size: number; color?: string };
    color?: VizNodeColor;
};

declare global {
    // Optional WASM LOD helper injected by the visualiser module.

    var meshchatxVisualiserLODLevel: ((scale: number) => string) | undefined;
}

/** vis-style edge width to WASM spring rest length. */
export function layoutSpringLength(width: number): number {
    return Number(width) >= 2.5 ? VIZ_HUB_SPRING_LEN : VIZ_PEER_SPRING_LEN;
}

export function pathHashesWithinHopFilterJs(pathTable: unknown[], hopMax: number | null | undefined): string[] {
    if (!Array.isArray(pathTable) || pathTable.length === 0) {
        return [];
    }
    const out = new Set<string>();
    for (const entry of pathTable) {
        if (!entry || typeof entry !== "object") {
            continue;
        }
        const row = entry as VizPathTableEntry;
        const hops = row.hops;
        if (hops == null) {
            continue;
        }
        if (hopMax != null && hops > hopMax) {
            continue;
        }
        const hash = row.hash;
        if (typeof hash === "string" && hash) {
            out.add(hash);
        }
    }
    return Array.from(out);
}

export function pathHashesWithinHopFilter(pathTable: unknown[], hopMax: number | null | undefined): string[] {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson(
            "meshchatxVisualiserPathHashes",
            JSON.stringify(pathTable),
            hopMax == null ? null : hopMax
        );
        if (Array.isArray(got)) {
            return got as string[];
        }
    }
    return pathHashesWithinHopFilterJs(pathTable, hopMax);
}

/** Collapse deferred icon work so each unique cacheKey is painted once. */
export function dedupeIconQueueEntriesJs(queue: unknown[]): VizIconQueueBucket[] {
    if (!Array.isArray(queue) || queue.length === 0) {
        return [];
    }
    const byKey = new Map<string, VizIconQueueBucket>();
    const seenByKey = new Map<string, Set<string>>();
    for (const item of queue) {
        if (!item || typeof item !== "object") {
            continue;
        }
        const row = item as Partial<VizIconQueueItem>;
        if (!row.cacheKey || !row.nodeId) {
            continue;
        }
        let bucket = byKey.get(row.cacheKey);
        if (!bucket) {
            bucket = {
                cacheKey: row.cacheKey,
                nodeIds: [],
                iconName: String(row.iconName ?? ""),
                fg: String(row.fg ?? ""),
                bg: String(row.bg ?? ""),
                size: Number(row.size) || 0,
                generation: Number(row.generation) || 0,
            };
            byKey.set(row.cacheKey, bucket);
            seenByKey.set(row.cacheKey, new Set());
        }
        const seen = seenByKey.get(row.cacheKey)!;
        if (!seen.has(row.nodeId)) {
            seen.add(row.nodeId);
            bucket.nodeIds.push(row.nodeId);
        }
    }
    return Array.from(byKey.values());
}

export function dedupeIconQueueEntries(queue: unknown[]): VizIconQueueBucket[] {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson("meshchatxVisualiserDedupeIcons", JSON.stringify(queue));
        if (Array.isArray(got)) {
            return got as VizIconQueueBucket[];
        }
    }
    return dedupeIconQueueEntriesJs(queue);
}

/** Parallel path/announce fetch concurrency scaled to hardware. */
export function pickAdaptiveFetchConcurrency(): number {
    const cores = (typeof navigator !== "undefined" && navigator.hardwareConcurrency) || 4;
    if (cores <= 2) return 2;
    if (cores <= 4) return 3;
    if (cores <= 6) return 4;
    return 6;
}

/** FNV-1a style deterministic unit fraction for stable layout without Math.random. */
function hash01(id: string, salt = ""): number {
    let h = 2166136261;
    const s = String(id) + "\0" + String(salt);
    for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return ((h >>> 0) % 10000) / 10000;
}

function hashAngle(id: string): number {
    return hash01(id) * Math.PI * 2;
}

function nodeColor(border: string, background: string): VizNodeColor {
    return {
        border,
        background,
        highlight: { border, background },
        hover: { border, background },
    };
}

function edgeColor(direct: boolean, darkMode: boolean): { color: string; opacity: number } {
    if (direct) {
        return { color: darkMode ? "#34d399" : "#10b981", opacity: 1 };
    }
    return { color: darkMode ? "#60a5fa" : "#3b82f6", opacity: 0.5 };
}

function applyLodToAnnounceNode(node: VizGraphNode, lod: string, fontColor: string): void {
    if (lod === "low") {
        node.shape = "dot";
        node.size = node.id === "me" ? 15 : 10;
        node.font = { size: 0 };
        return;
    }
    if (lod === "medium") {
        node.shape = node._originalShape || "circularImage";
        node.size = node._originalSize || 25;
        node.font = { size: 0 };
        return;
    }
    node.shape = node._originalShape || "circularImage";
    node.size = node._originalSize || 25;
    node.font = { size: node.id === "me" ? 16 : 11, color: fontColor };
}

/** Pure JS path-table graph builder (fallback when WASM is unavailable). */
export function buildPathGraphJs(req: VizPathGraphRequest): VizPathGraphResult {
    const pathTable = Array.isArray(req?.path_table) ? req.path_table : [];
    const announces = req?.announces && typeof req.announces === "object" ? req.announces : {};
    const conversations = req?.conversations && typeof req.conversations === "object" ? req.conversations : {};
    const iconCache = req?.icon_cache && typeof req.icon_cache === "object" ? req.icon_cache : {};
    const positions: VizPositionsMap = {
        ...(req?.positions && typeof req.positions === "object" ? req.positions : {}),
    };
    const hopMax = req?.hop_max;
    const searchLower = String(req?.search || "").toLowerCase();
    const darkMode = !!req?.dark_mode;
    const lod = req?.lod || "high";
    const aspects = Array.isArray(req?.aspects) && req.aspects.length > 0 ? req.aspects : [...VIZ_ANNOUNCE_ASPECTS];
    const aspectSet = new Set(aspects);
    const queueIcons = !!req?.queue_icons;
    const iconGeneration = req?.icon_generation || 0;
    const fontColor = darkMode ? "#ffffff" : "#000000";
    const matchesSearch = (text: unknown) =>
        !searchLower || (text != null && String(text).toLowerCase().includes(searchLower));

    const nodes: VizGraphNode[] = [];
    const edges: VizGraphEdge[] = [];
    const iconQueue: VizIconQueueItem[] = [];
    const processedNodeIds: string[] = [];
    const processedEdgeIds: string[] = [];

    for (const entry of pathTable) {
        if (!entry || entry.hops == null || !entry.hash) continue;
        if (hopMax != null && entry.hops > hopMax) continue;
        const announce = announces[entry.hash];
        if (!announce || !aspectSet.has(announce.aspect || "")) continue;

        const displayName = announce.custom_display_name ?? announce.display_name;
        if (
            !matchesSearch(displayName) &&
            !matchesSearch(announce.destination_hash) &&
            !matchesSearch(announce.identity_hash)
        ) {
            continue;
        }

        let x: number;
        let y: number;
        const prev = positions[entry.hash];
        if (prev && Number.isFinite(prev.x) && Number.isFinite(prev.y)) {
            x = prev.x as number;
            y = prev.y as number;
        } else {
            const ifaceKey = entry.interface;
            const ip = ifaceKey ? positions[ifaceKey] : undefined;
            const angle = hashAngle(entry.hash);
            if (ip && Number.isFinite(ip.x) && Number.isFinite(ip.y)) {
                const dist = 140 + hash01(entry.hash, "r") * 90;
                x = (ip.x as number) + Math.cos(angle) * dist;
                y = (ip.y as number) + Math.sin(angle) * dist;
            } else {
                const dist = 400 + hash01(entry.hash, "r") * 160;
                x = Math.cos(angle) * dist;
                y = Math.sin(angle) * dist;
            }
            positions[entry.hash] = { x, y };
        }

        const edgeId = `${entry.interface}~${entry.hash}`;
        const direct = entry.hops === 1;
        const conversation = announce.destination_hash ? conversations[announce.destination_hash] : undefined;

        const node: VizGraphNode = {
            id: entry.hash,
            group: "announce",
            size: 25,
            _originalSize: 25,
            font: { color: fontColor, size: 11 },
            x,
            y,
            label: displayName,
            title: `${displayName}\nAspect: ${announce.aspect}\nHops: ${entry.hops}\nVia: ${entry.interface}\nLast Seen: ${announce.last_seen || ""}`,
            _parentInterface: entry.interface,
        };

        if (announce.aspect === "lxmf.delivery") {
            node.shape = "circularImage";
            node._originalShape = "circularImage";
            if (conversation?.lxmf_user_icon) {
                const ic = conversation.lxmf_user_icon;
                const cacheKey = `${ic.icon_name}-${ic.foreground_colour}-${ic.background_colour}-64`;
                if (iconCache[cacheKey]) {
                    node.image = iconCache[cacheKey];
                } else {
                    node.image = direct
                        ? "/assets/images/network-visualiser/user_1hop.png"
                        : "/assets/images/network-visualiser/user.png";
                    if (queueIcons) {
                        iconQueue.push({
                            nodeId: node.id,
                            cacheKey,
                            iconName: String(ic.icon_name ?? ""),
                            fg: String(ic.foreground_colour ?? ""),
                            bg: String(ic.background_colour ?? ""),
                            size: 64,
                            generation: iconGeneration,
                        });
                    }
                }
                node.size = 30;
                node._originalSize = 30;
            } else {
                node.image = direct
                    ? "/assets/images/network-visualiser/user_1hop.png"
                    : "/assets/images/network-visualiser/user.png";
            }
            node.color = nodeColor(
                direct ? "#10b981" : "#3b82f6",
                direct ? (darkMode ? "#064e3b" : "#ecfdf5") : darkMode ? "#1e40af" : "#eff6ff"
            );
        } else if (announce.aspect === "nomadnetwork.node") {
            node.shape = "circularImage";
            node._originalShape = "circularImage";
            node.image = direct
                ? "/assets/images/network-visualiser/server_1hop.png"
                : "/assets/images/network-visualiser/server.png";
            node.color = nodeColor(
                direct ? "#10b981" : "#8b5cf6",
                direct ? (darkMode ? "#064e3b" : "#ecfdf5") : darkMode ? "#4c1d95" : "#f5f3ff"
            );
        }

        applyLodToAnnounceNode(node, String(lod), fontColor);
        nodes.push(node);
        processedNodeIds.push(node.id);
        edges.push({
            id: edgeId,
            from: entry.interface,
            to: entry.hash,
            color: edgeColor(direct, darkMode),
            width: direct ? 2.5 : 1,
            hidden: false,
        });
        processedEdgeIds.push(edgeId);
    }

    return {
        nodes,
        edges,
        icon_queue: iconQueue,
        processed_node_ids: processedNodeIds,
        processed_edge_ids: processedEdgeIds,
    };
}

/** Build announce nodes/edges from the path table via WASM or JS fallback. */
export function buildPathGraph(req: VizPathGraphRequest): VizPathGraphResult {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson("meshchatxVisualiserBuildPathGraph", JSON.stringify(req));
        if (
            got &&
            Array.isArray((got as VizPathGraphResult).nodes) &&
            Array.isArray((got as VizPathGraphResult).edges)
        ) {
            return got as VizPathGraphResult;
        }
    }
    return buildPathGraphJs(req);
}

/** Full mesh graph (me + interfaces + discovered + announces) via WASM or JS. */
export function buildFullGraph(req: VizPathGraphRequest): VizFullGraphResult | VizPathGraphResult {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson("meshchatxVisualiserBuildFullGraph", JSON.stringify(req));
        if (
            got &&
            Array.isArray((got as VizPathGraphResult).nodes) &&
            Array.isArray((got as VizPathGraphResult).edges)
        ) {
            return got as VizFullGraphResult;
        }
    }
    // Fallback: path graph only, caller still builds me/ifaces for older paths.
    const path = buildPathGraphJs({
        path_table: req.path_table,
        announces: req.announces,
        conversations: req.conversations,
        icon_cache: req.icon_cache,
        positions: req.positions,
        hop_max: req.hop_max,
        search: req.search,
        dark_mode: req.dark_mode,
        lod: req.lod,
        aspects: req.aspects,
        queue_icons: req.queue_icons,
        icon_generation: req.icon_generation,
    });
    return {
        ...path,
        layout_nodes: (path.nodes || []).map((n) => ({
            id: n.id,
            x: n.x ?? 0,
            y: n.y ?? 0,
            mass: n.group === "me" ? 4 : n.group === "interface" ? 2.5 : 1,
            fixed: n.id === "me",
            radius: Number.isFinite(n.size) ? (n.size as number) : 22,
        })),
        layout_edges: (path.edges || []).map((e) => ({
            from: String(e.from ?? ""),
            to: String(e.to ?? ""),
            length: layoutSpringLength(Number(e.width) || 0),
        })),
    };
}

/** Settle layout positions in WASM (or no-op passthrough when unavailable). */
export function settleLayout(req: VizSettleLayoutRequest): VizSettleLayoutResult {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson("meshchatxVisualiserLayout", JSON.stringify(req)) as
            VizSettleLayoutResult | null | undefined;
        if (got && got.positions && typeof got.positions === "object") {
            return got;
        }
    }
    const positions: Record<string, { x: number; y: number }> = {};
    for (const n of req?.nodes || []) {
        if (n?.id) positions[n.id] = { x: n.x || 0, y: n.y || 0 };
    }
    return { positions, iterations: 0 };
}

export function computeLodUpdatesJs(
    nodes: Array<VizGraphNode | null | undefined>,
    lod: string,
    darkMode: boolean
): VizLodUpdate[] {
    if (!Array.isArray(nodes) || nodes.length === 0) {
        return [];
    }
    const fontColor = darkMode ? "#ffffff" : "#000000";
    const blueBorder = "#3b82f6";
    const blueBg = darkMode ? "#1e40af" : "#eff6ff";
    const updates: VizLodUpdate[] = [];

    for (const node of nodes) {
        if (!node || !node.id) continue;
        let next: VizLodUpdate;
        if (lod === "low") {
            const isInterface = node.group === "interface";
            const baseColor =
                isInterface && node.color && typeof node.color === "object"
                    ? (node.color as VizNodeColor)
                    : nodeColor(blueBorder, blueBg);
            next = {
                id: node.id,
                shape: "dot",
                size: node.id === "me" ? 15 : 10,
                font: { size: 0 },
                color: baseColor,
            };
        } else if (lod === "medium") {
            next = {
                id: node.id,
                shape: node._originalShape || "circularImage",
                size: node._originalSize || (node.id === "me" ? 50 : 25),
                font: { size: 0 },
            };
        } else {
            next = {
                id: node.id,
                shape: node._originalShape || "circularImage",
                size: node._originalSize || (node.id === "me" ? 50 : 25),
                font: { size: node.id === "me" ? 16 : 11, color: fontColor },
            };
        }
        const shapeChanged = next.shape != null && next.shape !== node.shape;
        const sizeChanged = next.size != null && next.size !== node.size;
        const fontSize = next.font?.size;
        const fontChanged = fontSize != null && fontSize !== (node.font?.size ?? null);
        if (shapeChanged || sizeChanged || fontChanged) {
            updates.push(next);
        }
    }
    return updates;
}

export function computeLodUpdates(
    nodes: Array<VizGraphNode | null | undefined>,
    lod: string,
    darkMode: boolean
): VizLodUpdate[] {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson(
            "meshchatxVisualiserLODUpdates",
            JSON.stringify({ nodes, lod, dark_mode: !!darkMode })
        );
        if (Array.isArray(got)) {
            return got as VizLodUpdate[];
        }
    }
    return computeLodUpdatesJs(nodes, lod, darkMode);
}

/** Map camera scale to LOD level (WASM when ready). */
export function lodLevelFromScale(scale: number): VizLodLevel {
    if (isVisualiserWasmReady() && typeof globalThis.meshchatxVisualiserLODLevel === "function") {
        try {
            const v = globalThis.meshchatxVisualiserLODLevel(scale);
            if (v === "low" || v === "medium" || v === "high") {
                return v;
            }
        } catch {
            /* fall through */
        }
    }
    if (scale < 0.2) return "low";
    if (scale < 0.5) return "medium";
    return "high";
}

/** Warm the WASM module early. Safe to ignore the result. */
export function warmVisualiserWasm(): Promise<boolean> {
    return preloadVisualiserWasm()?.catch(() => false) ?? Promise.resolve(false);
}
