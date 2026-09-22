// SPDX-License-Identifier: 0BSD AND MIT

/**
 * Network visualiser hot-path helpers.
 * Prefers Go WASM when available, otherwise uses the pure JS implementations below.
 */

import { callVisualiserWasmJson, isVisualiserWasmReady, preloadVisualiserWasm } from "./VisualiserWasmLoader.js";

export const VIZ_ANNOUNCE_ASPECTS = ["lxmf.delivery", "nomadnetwork.node"];

export const ANNOUNCE_HASH_CHUNK_SIZE = 500;

/** Must match visualiser-wasm layout.DefaultHubSpringLen. */
export const VIZ_HUB_SPRING_LEN = 250;

/** Must match visualiser-wasm layout.DefaultSpringLen. */
export const VIZ_PEER_SPRING_LEN = 300;

/**
 * vis-style edge width to WASM spring rest length.
 * @param {number} width
 * @returns {number}
 */
export function layoutSpringLength(width) {
    return Number(width) >= 2.5 ? VIZ_HUB_SPRING_LEN : VIZ_PEER_SPRING_LEN;
}

/** Soft cap for client-side path table rows kept in the visualiser. */
export const VIZ_PATH_TABLE_SOFT_CAP = 20_000;

/** Soft cap for announce map entries keyed by destination hash. */
export const VIZ_ANNOUNCE_SOFT_CAP = 10_000;

/**
 * @param {unknown[]} pathTable
 * @param {number|null|undefined} hopMax
 * @returns {string[]}
 */
export function pathHashesWithinHopFilterJs(pathTable, hopMax) {
    if (!Array.isArray(pathTable) || pathTable.length === 0) {
        return [];
    }
    const out = new Set();
    for (const entry of pathTable) {
        if (!entry || typeof entry !== "object") {
            continue;
        }
        const hops = entry.hops;
        if (hops == null) {
            continue;
        }
        if (hopMax != null && hops > hopMax) {
            continue;
        }
        const hash = entry.hash;
        if (typeof hash === "string" && hash) {
            out.add(hash);
        }
    }
    return Array.from(out);
}

/**
 * @param {unknown[]} pathTable
 * @param {number|null|undefined} hopMax
 * @returns {string[]}
 */
export function pathHashesWithinHopFilter(pathTable, hopMax) {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson(
            "meshchatxVisualiserPathHashes",
            JSON.stringify(pathTable),
            hopMax == null ? null : hopMax
        );
        if (Array.isArray(got)) {
            return got;
        }
    }
    return pathHashesWithinHopFilterJs(pathTable, hopMax);
}

/**
 * Collapse deferred icon work so each unique cacheKey is painted once.
 * @param {unknown[]} queue
 * @returns {{ cacheKey: string, nodeIds: string[], iconName: string, fg: string, bg: string, size: number, generation: number }[]}
 */
export function dedupeIconQueueEntriesJs(queue) {
    if (!Array.isArray(queue) || queue.length === 0) {
        return [];
    }
    const byKey = new Map();
    const seenByKey = new Map();
    for (const item of queue) {
        if (!item || typeof item !== "object" || !item.cacheKey || !item.nodeId) {
            continue;
        }
        let bucket = byKey.get(item.cacheKey);
        if (!bucket) {
            bucket = {
                cacheKey: item.cacheKey,
                nodeIds: [],
                iconName: item.iconName,
                fg: item.fg,
                bg: item.bg,
                size: item.size,
                generation: item.generation,
            };
            byKey.set(item.cacheKey, bucket);
            seenByKey.set(item.cacheKey, new Set());
        }
        const seen = seenByKey.get(item.cacheKey);
        if (!seen.has(item.nodeId)) {
            seen.add(item.nodeId);
            bucket.nodeIds.push(item.nodeId);
        }
    }
    return Array.from(byKey.values());
}

/**
 * @param {unknown[]} queue
 * @returns {{ cacheKey: string, nodeIds: string[], iconName: string, fg: string, bg: string, size: number, generation: number }[]}
 */
export function dedupeIconQueueEntries(queue) {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson("meshchatxVisualiserDedupeIcons", JSON.stringify(queue));
        if (Array.isArray(got)) {
            return got;
        }
    }
    return dedupeIconQueueEntriesJs(queue);
}

/**
 * Parallel path/announce fetch concurrency scaled to hardware.
 * @returns {number}
 */
export function pickAdaptiveFetchConcurrency() {
    const cores = (typeof navigator !== "undefined" && navigator.hardwareConcurrency) || 4;
    if (cores <= 2) return 2;
    if (cores <= 4) return 3;
    if (cores <= 6) return 4;
    return 6;
}

/** FNV-1a style deterministic unit fraction for stable layout without Math.random. */
function hash01(id, salt = "") {
    let h = 2166136261;
    const s = String(id) + "\0" + String(salt);
    for (let i = 0; i < s.length; i++) {
        h ^= s.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return ((h >>> 0) % 10000) / 10000;
}

function hashAngle(id) {
    return hash01(id) * Math.PI * 2;
}

function nodeColor(border, background) {
    return {
        border,
        background,
        highlight: { border, background },
        hover: { border, background },
    };
}

function edgeColor(direct, darkMode) {
    if (direct) {
        return { color: darkMode ? "#34d399" : "#10b981", opacity: 1 };
    }
    return { color: darkMode ? "#60a5fa" : "#3b82f6", opacity: 0.5 };
}

function applyLodToAnnounceNode(node, lod, fontColor) {
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

/**
 * Pure JS path-table graph builder (fallback when WASM is unavailable).
 * @param {object} req
 * @returns {{ nodes: object[], edges: object[], icon_queue: object[], processed_node_ids: string[], processed_edge_ids: string[] }}
 */
export function buildPathGraphJs(req) {
    const pathTable = Array.isArray(req?.path_table) ? req.path_table : [];
    const announces = req?.announces && typeof req.announces === "object" ? req.announces : {};
    const conversations = req?.conversations && typeof req.conversations === "object" ? req.conversations : {};
    const iconCache = req?.icon_cache && typeof req.icon_cache === "object" ? req.icon_cache : {};
    const positions = { ...(req?.positions && typeof req.positions === "object" ? req.positions : {}) };
    const hopMax = req?.hop_max;
    const searchLower = String(req?.search || "").toLowerCase();
    const darkMode = !!req?.dark_mode;
    const lod = req?.lod || "high";
    const aspects = Array.isArray(req?.aspects) && req.aspects.length > 0 ? req.aspects : VIZ_ANNOUNCE_ASPECTS;
    const aspectSet = new Set(aspects);
    const queueIcons = !!req?.queue_icons;
    const iconGeneration = req?.icon_generation || 0;
    const fontColor = darkMode ? "#ffffff" : "#000000";
    const matchesSearch = (text) => !searchLower || (text && String(text).toLowerCase().includes(searchLower));

    const nodes = [];
    const edges = [];
    const iconQueue = [];
    const processedNodeIds = [];
    const processedEdgeIds = [];

    for (const entry of pathTable) {
        if (!entry || entry.hops == null || !entry.hash) continue;
        if (hopMax != null && entry.hops > hopMax) continue;
        const announce = announces[entry.hash];
        if (!announce || !aspectSet.has(announce.aspect)) continue;

        const displayName = announce.custom_display_name ?? announce.display_name;
        if (
            !matchesSearch(displayName) &&
            !matchesSearch(announce.destination_hash) &&
            !matchesSearch(announce.identity_hash)
        ) {
            continue;
        }

        let x;
        let y;
        const prev = positions[entry.hash];
        if (prev && Number.isFinite(prev.x) && Number.isFinite(prev.y)) {
            x = prev.x;
            y = prev.y;
        } else {
            const ip = positions[entry.interface];
            const angle = hashAngle(entry.hash);
            if (ip && Number.isFinite(ip.x) && Number.isFinite(ip.y)) {
                const dist = 200 + hash01(entry.hash, "r") * 140;
                x = ip.x + Math.cos(angle) * dist;
                y = ip.y + Math.sin(angle) * dist;
            } else {
                const dist = 560 + hash01(entry.hash, "r") * 240;
                x = Math.cos(angle) * dist;
                y = Math.sin(angle) * dist;
            }
            positions[entry.hash] = { x, y };
        }

        const edgeId = `${entry.interface}~${entry.hash}`;
        const direct = entry.hops === 1;
        const conversation = conversations[announce.destination_hash];

        let node = {
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
                            iconName: ic.icon_name,
                            fg: ic.foreground_colour,
                            bg: ic.background_colour,
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

        applyLodToAnnounceNode(node, lod, fontColor);
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

/**
 * Build announce nodes/edges from the path table via WASM or JS fallback.
 * @param {object} req
 */
export function buildPathGraph(req) {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson("meshchatxVisualiserBuildPathGraph", JSON.stringify(req));
        if (got && Array.isArray(got.nodes) && Array.isArray(got.edges)) {
            return got;
        }
    }
    return buildPathGraphJs(req);
}

/**
 * Full mesh graph (me + interfaces + discovered + announces) via WASM or JS.
 * @param {object} req
 */
export function buildFullGraph(req) {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson("meshchatxVisualiserBuildFullGraph", JSON.stringify(req));
        if (got && Array.isArray(got.nodes) && Array.isArray(got.edges)) {
            return got;
        }
    }
    // Fallback: path graph only, caller still builds me/ifaces in Vue for older paths.
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
            x: n.x,
            y: n.y,
            mass: n.group === "me" ? 4 : n.group === "interface" ? 2.5 : 1,
            fixed: n.id === "me",
            radius: Number.isFinite(n.size) ? n.size : 22,
        })),
        layout_edges: (path.edges || []).map((e) => ({
            from: e.from,
            to: e.to,
            length: layoutSpringLength(e.width),
        })),
    };
}

/**
 * Settle layout positions in WASM (or no-op passthrough when unavailable).
 * @param {{ nodes: object[], edges: object[], iterations?: number }} req
 */
export function settleLayout(req) {
    if (isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson("meshchatxVisualiserLayout", JSON.stringify(req));
        if (got && got.positions && typeof got.positions === "object") {
            return got;
        }
    }
    const positions = {};
    for (const n of req?.nodes || []) {
        if (n?.id) positions[n.id] = { x: n.x || 0, y: n.y || 0 };
    }
    return { positions, iterations: 0 };
}

/**
 * @param {object[]} nodes
 * @param {string} lod
 * @param {boolean} darkMode
 * @param {Set<string>|null|undefined} labelAllow when set at high LOD, only
 * listed node ids keep their label so dense clusters stay readable
 * @returns {object[]}
 */
export function computeLodUpdatesJs(nodes, lod, darkMode, labelAllow) {
    if (!Array.isArray(nodes) || nodes.length === 0) {
        return [];
    }
    const fontColor = darkMode ? "#ffffff" : "#000000";
    const blueBorder = "#3b82f6";
    const blueBg = darkMode ? "#1e40af" : "#eff6ff";
    const updates = [];

    for (const node of nodes) {
        if (!node || !node.id) continue;
        let next;
        if (lod === "low") {
            const isInterface = node.group === "interface";
            const baseColor = isInterface && node.color ? node.color : nodeColor(blueBorder, blueBg);
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
            const showLabel = labelAllow == null || labelAllow.has(node.id);
            next = {
                id: node.id,
                shape: node._originalShape || "circularImage",
                size: node._originalSize || (node.id === "me" ? 50 : 25),
                font: { size: showLabel ? (node.id === "me" ? 16 : 11) : 0, color: fontColor },
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

/**
 * @param {object[]} nodes
 * @param {string} lod
 * @param {boolean} darkMode
 * @param {Set<string>|null|undefined} labelAllow label allowlist; forces the
 * JS path because the WASM LOD call does not accept one
 */
export function computeLodUpdates(nodes, lod, darkMode, labelAllow) {
    if (labelAllow == null && isVisualiserWasmReady()) {
        const got = callVisualiserWasmJson(
            "meshchatxVisualiserLODUpdates",
            JSON.stringify({ nodes, lod, dark_mode: !!darkMode })
        );
        if (Array.isArray(got)) {
            return got;
        }
    }
    return computeLodUpdatesJs(nodes, lod, darkMode, labelAllow);
}

/**
 * Greedy screen-space label declutter. Items are tried in order, so callers
 * should sort by importance first; the first label to claim a spot wins.
 * @param {{id: string, sx: number, sy: number, w: number, h: number}[]} items
 *   label boxes centred on (sx, sy) in screen pixels
 * @param {number} spacing extra padding around each placed box
 * @returns {Set<string>} ids of labels that did not collide
 */
export function declutterLabelBoxes(items, spacing = 6) {
    const keep = new Set();
    if (!Array.isArray(items) || items.length === 0) {
        return keep;
    }
    const cell = 96;
    const grid = new Map();
    for (const it of items) {
        if (!it || it.id == null) continue;
        const w = Number(it.w) || 0;
        const h = Number(it.h) || 0;
        const l = it.sx - w / 2 - spacing;
        const r = it.sx + w / 2 + spacing;
        const t = it.sy - h / 2 - spacing;
        const b = it.sy + h / 2 + spacing;
        const cx0 = Math.floor(l / cell);
        const cx1 = Math.floor(r / cell);
        const cy0 = Math.floor(t / cell);
        const cy1 = Math.floor(b / cell);
        let hit = false;
        for (let cy = cy0; cy <= cy1 && !hit; cy++) {
            for (let cx = cx0; cx <= cx1 && !hit; cx++) {
                const bucket = grid.get(`${cx},${cy}`);
                if (!bucket) continue;
                for (const p of bucket) {
                    if (l < p.r && r > p.l && t < p.b && b > p.t) {
                        hit = true;
                        break;
                    }
                }
            }
        }
        if (hit) continue;
        keep.add(it.id);
        const rect = { l, r, t, b };
        for (let cy = cy0; cy <= cy1; cy++) {
            for (let cx = cx0; cx <= cx1; cx++) {
                const key = `${cx},${cy}`;
                let bucket = grid.get(key);
                if (!bucket) {
                    bucket = [];
                    grid.set(key, bucket);
                }
                bucket.push(rect);
            }
        }
    }
    return keep;
}

/**
 * Deterministic radial layout: me at the centre, interfaces and discovered
 * nodes on the first ring, then announce peers grouped into one ring per hop
 * count. Returns a positions map for injection into the graph builders.
 * @param {{interfaces?: string[], discovered?: string[], pathTable?: object[], hopMax?: number|null}} req
 * @returns {Record<string, {x: number, y: number}>}
 */
export function computeRadialPositions(req) {
    const positions = { me: { x: 0, y: 0 } };
    const inner = [];
    for (const id of req?.interfaces || []) {
        if (typeof id === "string" && id) inner.push(id);
    }
    for (const id of req?.discovered || []) {
        if (typeof id === "string" && id) inner.push(id);
    }
    const innerRadius = 300;
    inner.forEach((id, i) => {
        const a = (i / inner.length) * Math.PI * 2 - Math.PI / 2;
        positions[id] = { x: Math.cos(a) * innerRadius, y: Math.sin(a) * innerRadius };
    });

    const hopMax = req?.hopMax;
    const byHop = new Map();
    for (const entry of req?.pathTable || []) {
        if (!entry || !entry.hash || entry.hops == null) continue;
        if (hopMax != null && entry.hops > hopMax) continue;
        const hops = Math.max(1, Math.round(entry.hops));
        let ring = byHop.get(hops);
        if (!ring) {
            ring = [];
            byHop.set(hops, ring);
        }
        ring.push(entry);
    }
    const baseRadius = 560;
    const ringStep = 230;
    for (const [hops, entries] of [...byHop.entries()].sort((a, b) => a[0] - b[0])) {
        // Sort by parent interface then hash so same-interface peers cluster.
        entries.sort(
            (a, b) =>
                String(a.interface).localeCompare(String(b.interface)) || String(a.hash).localeCompare(String(b.hash))
        );
        const r = baseRadius + (hops - 1) * ringStep;
        const offset = ((hops * 137.508) % 360) * (Math.PI / 180);
        entries.forEach((entry, i) => {
            const a = offset + (i / entries.length) * Math.PI * 2;
            positions[entry.hash] = { x: Math.cos(a) * r, y: Math.sin(a) * r };
        });
    }
    return positions;
}

/**
 * Map camera scale to LOD level (WASM when ready).
 * @param {number} scale
 * @returns {"low"|"medium"|"high"}
 */
export function lodLevelFromScale(scale) {
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
export function warmVisualiserWasm() {
    return preloadVisualiserWasm().catch(() => false);
}
