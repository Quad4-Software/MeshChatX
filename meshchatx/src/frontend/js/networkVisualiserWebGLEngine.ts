// SPDX-License-Identifier: 0BSD

/**
 * WASM scene + WebGL2 engine for the network visualiser.
 * Falls back is handled by the caller (vis-network path).
 */

import { callVisualiserWasmJson, isVisualiserWebGLSceneReady } from "./VisualiserWasmLoader.js";
import { lodLevelFromScale } from "./networkVisualiserPerf.js";
import {
    createNetworkVisualiserWebGL,
    mergeSceneNodesWithTextures,
    NODE_STRIDE,
    SCENE_NODE_STRIDE,
    tryCreateWebGL2Context,
} from "./networkVisualiserWebGL.js";
import {
    DEFAULT_ORBIT_DIST,
    DEFAULT_ORBIT_PITCH,
    DEFAULT_ORBIT_YAW,
    FLAT_VIEW,
    PLANET_VIEW,
    clampOrbit,
    layoutToWasmScreen,
    normalizeVisualiserViewMode,
    orbitEye,
    pickPlanetNode,
    planetLodZoom,
    pointerToLayout,
    projectPlanetScene,
    screenToDrawWorld,
} from "./networkVisualiserPlanet.js";
import type { NodeTexMeta, VisualiserCamera, VisualiserLabel } from "./networkVisualiserWebGL.js";
import type { PlanetBody, PlanetPickEntry, PlanetProjectedNode } from "./networkVisualiserPlanet.js";
import type { VizGraphEdge, VizGraphNode } from "./networkVisualiserPerf.js";

export { isVisualiserWebGLSceneReady };

export type CssPoint = { x: number; y: number };

export type WebGLLabelOpts = {
    zoom?: number;
    sceneCount?: number;
    nodes: Float32Array | number[] | null | undefined;
    labelByIndex: Array<string | null | undefined>;
    idByIndex: Array<string | null | undefined>;
    hoverId?: string | null;
};

export type WebGLLabel = {
    x: number;
    y: number;
    size: number;
    text: string;
    fontSize: number;
};

export type Rgb01 = { r: number; g: number; b: number };
export type Rgba01 = { r: number; g: number; b: number; a: number };

export type SceneView = {
    width: number;
    height: number;
    camX?: number;
    camY?: number;
    zoom?: number;
};

export type SceneNodePayload = {
    id: string;
    x: number;
    y: number;
    mass: number;
    fixed: boolean;
    kind: number;
    size: number;
    r: number;
    g: number;
    b: number;
    a: number;
};

export type SceneEdgePayload = {
    from: string;
    to: string;
    width: number;
    r: number;
    g: number;
    b: number;
    a: number;
};

export type SceneSetRequest = {
    nodes: SceneNodePayload[];
    edges: SceneEdgePayload[];
    width: number;
    height: number;
    cam_x: number;
    cam_y: number;
    zoom: number;
};

export type NodeMeta = {
    id: string;
    label: string;
    title: string;
    group: string;
    announce: unknown;
};

export type VisualiserWebGLEngineHooks = {
    getLiveLayout: () => boolean;
    isDark: () => boolean;
    onNodeActivate?: (id: string, meta: NodeMeta | null) => void;
    onHover?: (id: string | null, meta: NodeMeta | null, cssX: number, cssY: number) => void;
};

export type GraphViewOpts = {
    preserveCamera?: boolean;
    camX?: number;
    camY?: number;
    zoom?: number;
};

export type NodeImageUpdate = {
    id: string;
    image: string;
};

export type VisualiserWebGLEngine = {
    setGraph: (
        graphNodes: Array<VizGraphNode | null | undefined> | null | undefined,
        graphEdges: Array<VizGraphEdge | null | undefined> | null | undefined,
        viewOpts?: GraphViewOpts
    ) => void;
    updateNodeImages: (updates: NodeImageUpdate[] | null | undefined) => void;
    getPositions: () => Record<string, { x?: number; y?: number }>;
    getCounts: () => { nodes: number; edges: number };
    setLiveLayout: () => void;
    setViewMode: (mode: unknown) => void;
    destroy: () => void;
    requestRedraw: () => void;
};

export const KIND_ME = 0;
export const KIND_IFACE_ON = 1;
export const KIND_IFACE_OFF = 2;
export const KIND_PEER = 3;
export const KIND_DISCOVERED = 4;

/** Max characters drawn on a WebGL node label before ellipsis. */
export const WEBGL_LABEL_MAX_CHARS = 28;

/**
 * Truncate a node label for the WebGL overlay.
 */
export function truncateWebGLLabel(text: string | null | undefined, maxChars = WEBGL_LABEL_MAX_CHARS): string | null {
    if (typeof text !== "string" || !text) return null;
    const limit = Number.isFinite(maxChars) && maxChars > 1 ? Math.floor(maxChars) : WEBGL_LABEL_MAX_CHARS;
    if (text.length <= limit) return text;
    return `${text.slice(0, Math.max(1, limit - 3))}...`;
}

/**
 * Build overlay labels using the same LOD bands as the vis-network canvas path.
 * low: none, medium: me + hover only, high: all in-scene labels.
 */
export function collectWebGLLabels(opts: {
    zoom?: number;
    sceneCount?: number;
    nodes?: Float32Array | number[] | null;
    labelByIndex?: (string | null | undefined)[];
    idByIndex?: (string | null | undefined)[];
    hoverId?: string | null;
}): { x: number; y: number; size: number; text: string; fontSize: number }[] {
    const zoomRaw = opts?.zoom;
    const zoom = zoomRaw != null && zoomRaw > 0 ? zoomRaw : 1;
    const lod = lodLevelFromScale(zoom);
    if (lod === "low") return [];

    const sceneCount = Math.max(0, (opts?.sceneCount ?? 0) | 0);
    const nodes = opts?.nodes;
    const labelByIndex = opts?.labelByIndex || [];
    const idByIndex = opts?.idByIndex || [];
    const hoverId = opts?.hoverId ? String(opts.hoverId) : null;
    const out: WebGLLabel[] = [];

    for (let i = 0; i < sceneCount; i++) {
        const id = idByIndex[i] != null ? String(idByIndex[i]) : null;
        const isMe = id === "me";
        const isHover = hoverId != null && id === hoverId;
        if (lod === "medium" && !isMe && !isHover) continue;

        const raw = labelByIndex[i];
        const text = truncateWebGLLabel(raw);
        if (!text) continue;

        const o = i * SCENE_NODE_STRIDE;
        out.push({
            x: nodes?.[o] ?? 0,
            y: nodes?.[o + 1] ?? 0,
            size: nodes?.[o + 2] ?? 10,
            text,
            fontSize: isMe ? 16 : 11,
        });
    }
    return out;
}

const DEFAULT_ICON_BY_KIND: Record<number, string> = {
    [KIND_ME]: "/assets/images/reticulum_logo_512.png",
    [KIND_IFACE_ON]: "/assets/images/network-visualiser/interface_connected.png",
    [KIND_IFACE_OFF]: "/assets/images/network-visualiser/interface_disconnected.png",
    [KIND_PEER]: "/assets/images/network-visualiser/user.png",
    [KIND_DISCOVERED]: "/assets/images/network-visualiser/interface_connected.png",
};

/**
 * Distance between two CSS points.
 */
export function pointerDistance(a: CssPoint, b: CssPoint): number {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.hypot(dx, dy);
}

/**
 * Midpoint of two CSS points.
 */
export function pointerMidpoint(a: CssPoint, b: CssPoint): CssPoint {
    return { x: (a.x + b.x) * 0.5, y: (a.y + b.y) * 0.5 };
}

export function canUseVisualiserWebGL(_canvas?: HTMLCanvasElement): boolean {
    if (!isVisualiserWebGLSceneReady()) return false;
    if (typeof WebGL2RenderingContext === "undefined") return false;
    if (typeof document === "undefined") return false;
    const probe = document.createElement("canvas");
    return !!tryCreateWebGL2Context(probe);
}

function hexToRgb01(hex: unknown): Rgb01 | null {
    if (typeof hex !== "string") return null;
    let h = hex.trim();
    if (h.startsWith("#")) h = h.slice(1);
    if (h.length === 3) {
        h = `${h[0]}${h[0]}${h[1]}${h[1]}${h[2]}${h[2]}`;
    }
    if (h.length !== 6) return null;
    const n = Number.parseInt(h, 16);
    if (!Number.isFinite(n)) return null;
    return {
        r: ((n >> 16) & 255) / 255,
        g: ((n >> 8) & 255) / 255,
        b: (n & 255) / 255,
    };
}

function colorFromNode(node: VizGraphNode | null | undefined): Rgb01 | null {
    const c = node?.color;
    if (typeof c === "string") {
        const rgb = hexToRgb01(c);
        if (rgb) return rgb;
    }
    if (c && typeof c === "object") {
        // Border is the vivid badge color. Background is a pale tint for vis-network.
        const fill = c.border || c.background;
        const rgb = hexToRgb01(fill);
        if (rgb) return rgb;
    }
    return null;
}

function colorFromEdge(edge: VizGraphEdge | null | undefined): Rgba01 {
    const c = edge?.color;
    if (typeof c === "string") {
        const rgb = hexToRgb01(c);
        if (rgb) return { ...rgb, a: 0.55 };
    }
    if (c && typeof c === "object") {
        const rgb = hexToRgb01(c.color);
        const a = typeof c.opacity === "number" ? c.opacity : 0.55;
        if (rgb) return { ...rgb, a };
    }
    return { r: 0.45, g: 0.45, b: 0.55, a: 0.45 };
}

function kindForNode(node: VizGraphNode | null | undefined): number {
    const g = node?.group;
    if (g === "me" || node?.id === "me") return KIND_ME;
    if (g === "discovered") return KIND_DISCOVERED;
    if (g === "interface") {
        const img = String(node?.image || "");
        if (img.includes("disconnected")) return KIND_IFACE_OFF;
        const colorObj = node?.color && typeof node.color === "object" ? node.color : null;
        const border = colorObj?.border || "";
        if (border === "#ef4444" || border === "#f87171") return KIND_IFACE_OFF;
        return KIND_IFACE_ON;
    }
    return KIND_PEER;
}

function sizeForNode(node: VizGraphNode | null | undefined, kind: number): number {
    const s = Number(node?.size);
    if (Number.isFinite(s) && s > 0) {
        // Keep WebGL radii close to vis-network so glyphs stay readable.
        return Math.max(18, Math.min(48, s * 0.9));
    }
    if (kind === KIND_ME) return 32;
    if (kind === KIND_IFACE_ON || kind === KIND_IFACE_OFF) return 24;
    if (kind === KIND_DISCOVERED) return 20;
    return 22;
}

/** Exported for unit tests. */
export function webglNodeSizeFor(node: VizGraphNode | null | undefined, kind?: number | null): number {
    return sizeForNode(node, kind == null ? kindForNode(node) : kind);
}

function imageForNode(node: VizGraphNode | null | undefined, kind: number): string | null {
    if (typeof node?.image === "string" && node.image) {
        return node.image;
    }
    return DEFAULT_ICON_BY_KIND[kind] || null;
}

/**
 * Convert vis-style graph nodes/edges into WASM scene SetRequest payload.
 */
export function graphToSceneRequest(
    graphNodes: Array<VizGraphNode | null | undefined> | null | undefined,
    graphEdges: Array<VizGraphEdge | null | undefined> | null | undefined,
    view: SceneView | null | undefined
): SceneSetRequest {
    const nodes: SceneNodePayload[] = [];
    for (const n of graphNodes || []) {
        if (!n?.id) continue;
        const kind = kindForNode(n);
        const rgb = colorFromNode(n) || { r: 0.85, g: 0.85, b: 0.9 };
        nodes.push({
            id: String(n.id),
            x: Number.isFinite(n.x) ? (n.x as number) : 0,
            y: Number.isFinite(n.y) ? (n.y as number) : 0,
            mass: n.id === "me" ? 4 : n.group === "interface" ? 2.5 : 1,
            fixed: n.id === "me",
            kind,
            size: sizeForNode(n, kind),
            r: rgb.r,
            g: rgb.g,
            b: rgb.b,
            a: 1,
        });
    }
    const edges: SceneEdgePayload[] = [];
    for (const e of graphEdges || []) {
        if (!e?.from || !e?.to) continue;
        const rgb = colorFromEdge(e);
        edges.push({
            from: String(e.from),
            to: String(e.to),
            width: Number(e.width) || 1,
            r: rgb.r,
            g: rgb.g,
            b: rgb.b,
            a: rgb.a,
        });
    }
    return {
        nodes,
        edges,
        width: view?.width || 800,
        height: view?.height || 600,
        cam_x: view?.camX ?? 0,
        cam_y: view?.camY ?? 0,
        // zoom === 0 means "preserve camera" for Scene.Set. Do not coerce to 1.
        zoom: typeof view?.zoom === "number" ? view.zoom : 1,
    };
}

export function createVisualiserWebGLEngine(
    canvas: HTMLCanvasElement,
    hooks: Partial<VisualiserWebGLEngineHooks> = {}
): VisualiserWebGLEngine {
    const gl = tryCreateWebGL2Context(canvas);
    if (!gl) {
        throw new Error("WebGL2 unavailable");
    }
    if (!isVisualiserWebGLSceneReady()) {
        throw new Error("WASM scene unavailable");
    }

    const renderer = createNetworkVisualiserWebGL(canvas, gl);
    const metaById = new Map<string, NodeMeta>();
    const indexById = new Map<string, number>();
    let imageByIndex: (string | null)[] = [];
    let labelByIndex: (string | null)[] = [];
    let idByIndex: (string | null)[] = [];
    let texMeta: NodeTexMeta[] = [];
    let drawNodeScratch = new Float32Array(0);
    let rafId: number | null = null;
    let running = true;
    let dirty = true;
    let pointerMode: "drag" | "pan" | "pinch" | null = null;
    let lastX = 0;
    let lastY = 0;
    let nodeCount = 0;
    let edgeCount = 0;
    let hoverId: string | null = null;
    const pointers = new Map<number, { x: number; y: number }>();
    let pinchLastDist = 0;
    let iconLoadGen = 0;
    let viewMode = FLAT_VIEW;
    let orbitYaw = DEFAULT_ORBIT_YAW;
    let orbitPitch = DEFAULT_ORBIT_PITCH;
    let orbitDist = DEFAULT_ORBIT_DIST;
    let planetLayoutScale = 400;
    let planetPick: PlanetPickEntry[] = [];
    let planetProjected: Array<PlanetProjectedNode | undefined> = [];
    let lastPlanets: PlanetBody[] = [];
    let planetHomeById: Record<string, string> = Object.create(null);
    let kindByIndexScratch: number[] = [];

    function cssPoint(ev: PointerEvent | MouseEvent): CssPoint {
        const rect = canvas.getBoundingClientRect();
        return {
            x: ev.clientX - rect.left,
            y: ev.clientY - rect.top,
        };
    }

    function callScene(name: string, ...args: unknown[]): unknown {
        const fn = (globalThis as Record<string, unknown>)[name];
        if (typeof fn !== "function") return null;
        try {
            return (fn as (...a: unknown[]) => unknown)(...args);
        } catch (e) {
            console.warn("Visualiser scene call failed:", name, e);
            return null;
        }
    }

    function rebuildTexMeta(): void {
        texMeta = imageByIndex.map((url) => {
            if (!url) return { useTex: 0, u: 0, v: 0 };
            const slot = renderer.getIconSlot(url);
            if (slot == null) return { useTex: 0, u: 0, v: 0 };
            const uv = renderer.iconUv(slot);
            return { useTex: 1, u: uv.u, v: uv.v };
        });
    }

    async function loadIconsForCurrentGraph(generation: number): Promise<void> {
        const urls = [...new Set(imageByIndex.filter((u): u is string => !!u))];
        await Promise.all(
            urls.map(async (url) => {
                await renderer.ensureIcon(url);
            })
        );
        if (!running || generation !== iconLoadGen) return;
        rebuildTexMeta();
        dirty = true;
    }

    function setGraph(
        graphNodes: Array<VizGraphNode | null | undefined> | null | undefined,
        graphEdges: Array<VizGraphEdge | null | undefined> | null | undefined,
        viewOpts: GraphViewOpts = {}
    ): void {
        metaById.clear();
        indexById.clear();
        imageByIndex = [];
        labelByIndex = [];
        idByIndex = [];
        hoverId = null;
        let idx = 0;
        for (const n of graphNodes || []) {
            if (!n?.id) continue;
            const id = String(n.id);
            const kind = kindForNode(n);
            metaById.set(id, {
                id,
                label: n.label || "",
                title: n.title || "",
                group: n.group || "",
                announce: n._announce || null,
            });
            indexById.set(id, idx);
            idByIndex[idx] = id;
            imageByIndex[idx] = imageForNode(n, kind);
            labelByIndex[idx] = typeof n.label === "string" && n.label ? n.label : null;
            idx += 1;
        }
        const size = renderer.resize();
        const preserveCamera = viewOpts.preserveCamera !== false && nodeCount > 0;
        let prevCam: { x: number; y: number; zoom: number } | null = null;
        if (preserveCamera) {
            const buf = callScene("meshchatxVisualiserSceneGetDrawBuffers") as {
                ok?: boolean;
                camX?: number;
                camY?: number;
                zoom?: number;
            } | null;
            if (buf && buf.ok !== false) {
                prevCam = {
                    x: buf.camX || 0,
                    y: buf.camY || 0,
                    zoom: (buf.zoom ?? 0) > 0 ? (buf.zoom as number) : 1,
                };
            }
        }
        const req = graphToSceneRequest(graphNodes, graphEdges, {
            width: size.width,
            height: size.height,
            camX: viewOpts.camX ?? 0,
            camY: viewOpts.camY ?? 0,
            // 0 = Scene.Set keeps the current pan/zoom (auto-refresh must not reset).
            zoom: preserveCamera ? 0 : viewOpts.zoom != null && viewOpts.zoom > 0 ? viewOpts.zoom : 1,
        });
        const got = callVisualiserWasmJson("meshchatxVisualiserSceneSet", JSON.stringify(req)) as
            | {
                  ok?: boolean;
                  error?: string;
                  nodes?: number;
                  edges?: number;
              }
            | null
            | undefined;
        if (!got || got.ok === false) {
            throw new Error(got?.error || "SceneSet failed");
        }
        nodeCount = got.nodes || 0;
        edgeCount = got.edges || 0;
        if (preserveCamera && prevCam) {
            callScene("meshchatxVisualiserSceneSetCamera", prevCam.x, prevCam.y, prevCam.zoom);
        }
        rebuildTexMeta();
        dirty = true;
        iconLoadGen += 1;
        void loadIconsForCurrentGraph(iconLoadGen);
    }

    /**
     * Apply deferred LXMF / custom icon URLs after paint.
     */
    function updateNodeImages(updates: NodeImageUpdate[] | null | undefined): void {
        let changed = false;
        for (const u of updates || []) {
            if (!u?.id || !u?.image) continue;
            const i = indexById.get(String(u.id));
            if (i == null) continue;
            if (imageByIndex[i] === u.image) continue;
            imageByIndex[i] = u.image;
            changed = true;
        }
        if (!changed) return;
        iconLoadGen += 1;
        void loadIconsForCurrentGraph(iconLoadGen);
    }

    function getPositions(): Record<string, { x?: number; y?: number }> {
        const got = callVisualiserWasmJson("meshchatxVisualiserSceneGetPositions") as
            { positions?: Record<string, { x?: number; y?: number }> } | null | undefined;
        return got?.positions && typeof got.positions === "object" ? got.positions : {};
    }

    function getCounts(): { nodes: number; edges: number } {
        return { nodes: nodeCount, edges: edgeCount };
    }

    function setLiveLayout(): void {
        dirty = true;
    }

    function setViewMode(mode: unknown): void {
        const next = normalizeVisualiserViewMode(mode);
        if (next === viewMode) {
            dirty = true;
            return;
        }
        viewMode = next;
        dirty = true;
    }

    function isPlanet(): boolean {
        return viewMode === PLANET_VIEW;
    }

    function pickNodeAt(cssX: number, cssY: number, pad?: number): string | null {
        if (isPlanet()) {
            return pickPlanetNode(planetPick, cssX, cssY, pad || 14);
        }
        return (callScene("meshchatxVisualiserScenePick", cssX, cssY, pad || 16) as string | null | undefined) || null;
    }

    function applyPlanetOrbit(nextYaw: number, nextPitch: number, nextDist: number): void {
        let maxR = 0;
        for (let i = 0; i < lastPlanets.length; i++) {
            const r = lastPlanets[i].radius;
            if (r > maxR) maxR = r;
        }
        const c = clampOrbit(nextYaw, nextPitch, nextDist, lastPlanets.length, maxR);
        orbitYaw = c.yaw;
        orbitPitch = c.pitch;
        orbitDist = c.dist;
        dirty = true;
    }

    function frame(): void {
        if (!running) return;
        rafId = requestAnimationFrame(frame);
        const live = typeof hooks.getLiveLayout === "function" ? hooks.getLiveLayout() : false;
        if (live && pointerMode !== "drag" && !isPlanet()) {
            const moved = callScene("meshchatxVisualiserSceneTick", 1);
            // false means the WASM solver is asleep. null/undefined is an older
            // wasm or stub, keep drawing.
            if (moved !== false) dirty = true;
        }
        if (!dirty) return;
        const dark = typeof hooks.isDark === "function" ? hooks.isDark() : false;
        const buf = callScene("meshchatxVisualiserSceneGetDrawBuffers") as {
            ok?: boolean;
            nodes?: Float32Array;
            edges?: Float32Array;
            camX?: number;
            camY?: number;
            zoom?: number;
            nodeCount?: number;
            edgeCount?: number;
        } | null;
        if (!buf || buf.ok === false) {
            renderer.clearBackground(dark);
            return;
        }
        const sceneCount = buf.nodes && buf.nodes.length ? Math.floor(buf.nodes.length / SCENE_NODE_STRIDE) : 0;
        const need = sceneCount * NODE_STRIDE;
        if (drawNodeScratch.length < need) {
            drawNodeScratch = new Float32Array(need);
        }
        const drawNodes = mergeSceneNodesWithTextures(buf.nodes, texMeta, drawNodeScratch);
        let camera: VisualiserCamera = {
            x: buf.camX || 0,
            y: buf.camY || 0,
            zoom: buf.zoom != null && buf.zoom > 0 ? buf.zoom : 1,
        };
        let drawEdges = buf.edges;
        let paintNodes = drawNodes;
        const css = renderer.getCssSize();
        if (isPlanet()) {
            if (kindByIndexScratch.length < sceneCount) kindByIndexScratch.length = sceneCount;
            const sceneNodes = buf.nodes || new Float32Array(0);
            for (let i = 0; i < sceneCount; i++) {
                kindByIndexScratch[i] = sceneNodes[i * SCENE_NODE_STRIDE + 7] | 0;
            }
            const planet = projectPlanetScene({
                nodes: drawNodes,
                edges: buf.edges,
                width: css.width,
                height: css.height,
                yaw: orbitYaw,
                pitch: orbitPitch,
                dist: orbitDist,
                dark,
                idByIndex,
                kindByIndex: kindByIndexScratch,
                prevPlanets: lastPlanets,
                prevHomeById: planetHomeById,
            });
            paintNodes = planet.nodes;
            drawEdges = planet.edges;
            camera = planet.camera;
            planetPick = planet.pick;
            planetProjected = planet.projected;
            planetLayoutScale = planet.layoutScale;
            lastPlanets = planet.planets || [];
            planetHomeById = planet.homeById || planetHomeById;
            if (planet.orbit) {
                orbitYaw = planet.orbit.yaw;
                orbitPitch = planet.orbit.pitch;
                orbitDist = planet.orbit.dist;
            }
        } else {
            planetPick = [];
            planetProjected = [];
            lastPlanets = [];
        }
        const labelZoom = isPlanet() ? planetLodZoom(orbitDist) : camera.zoom;
        let paintLabels: VisualiserLabel[];
        if (isPlanet()) {
            paintLabels = [];
            const lod = lodLevelFromScale(labelZoom);
            if (lod !== "low") {
                for (let i = 0; i < planetProjected.length; i++) {
                    const rec = planetProjected[i];
                    if (!rec?.front) continue;
                    const id = idByIndex[i] != null ? String(idByIndex[i]) : null;
                    const isMe = id === "me";
                    const isHover = hoverId != null && id === hoverId;
                    const isIface =
                        rec.kind === KIND_IFACE_ON || rec.kind === KIND_IFACE_OFF || rec.kind === KIND_DISCOVERED;
                    if (lod === "medium" && !isMe && !isIface && !isHover) continue;
                    const text = truncateWebGLLabel(labelByIndex[i]);
                    if (!text) continue;
                    const draw = screenToDrawWorld(rec.sx, rec.sy, css.width, css.height);
                    paintLabels.push({
                        x: draw.x,
                        y: draw.y,
                        size: rec.size,
                        text,
                        fontSize: isMe ? 16 : isIface ? 13 : 11,
                    });
                }
            }
        } else {
            paintLabels = collectWebGLLabels({
                zoom: labelZoom,
                sceneCount,
                nodes: buf.nodes,
                labelByIndex,
                idByIndex,
                hoverId,
            });
        }
        const size = renderer.draw(paintNodes, drawEdges, camera, dark, paintLabels);
        callScene("meshchatxVisualiserSceneResize", size.width, size.height);
        nodeCount = buf.nodeCount || nodeCount;
        edgeCount = buf.edgeCount || edgeCount;
        dirty = false;
    }

    function activePointerPair(): { a: CssPoint; b: CssPoint } | null {
        if (pointers.size < 2) return null;
        const pts = [...pointers.values()];
        return { a: pts[0], b: pts[1] };
    }

    function onPointerDown(ev: PointerEvent): void {
        if (ev.pointerType === "mouse" && ev.button !== 0) return;
        canvas.setPointerCapture?.(ev.pointerId);
        const p = cssPoint(ev);
        pointers.set(ev.pointerId, p);
        if (pointers.size >= 2) {
            if (pointerMode === "drag") {
                callScene("meshchatxVisualiserSceneDragEnd");
            }
            pointerMode = "pinch";
            const pair = activePointerPair();
            pinchLastDist = pair ? pointerDistance(pair.a, pair.b) : 0;
            dirty = true;
            return;
        }
        lastX = p.x;
        lastY = p.y;
        const id = pickNodeAt(p.x, p.y, 16);
        if (id) {
            callScene("meshchatxVisualiserSceneDragStart", id);
            pointerMode = "drag";
        } else {
            pointerMode = "pan";
        }
        dirty = true;
    }

    function onPointerMove(ev: PointerEvent): void {
        const p = cssPoint(ev);
        if (pointers.has(ev.pointerId)) {
            pointers.set(ev.pointerId, p);
        }
        if (pointerMode === "pinch") {
            const pair = activePointerPair();
            if (!pair || pinchLastDist <= 0) return;
            const dist = pointerDistance(pair.a, pair.b);
            if (dist <= 0) return;
            const factor = dist / pinchLastDist;
            if (Math.abs(factor - 1) > 0.001) {
                if (isPlanet()) {
                    applyPlanetOrbit(orbitYaw, orbitPitch, orbitDist / factor);
                } else {
                    const mid = pointerMidpoint(pair.a, pair.b);
                    callScene("meshchatxVisualiserSceneZoomAt", mid.x, mid.y, factor);
                    dirty = true;
                }
                pinchLastDist = dist;
            }
            return;
        }
        if (pointerMode === "drag") {
            if (isPlanet()) {
                const css = renderer.getCssSize();
                const eye = orbitEye(orbitYaw, orbitPitch, orbitDist);
                const layout = pointerToLayout(p.x, p.y, css.width, css.height, eye, planetLayoutScale, lastPlanets);
                if (layout) {
                    const zoomBuf = callScene("meshchatxVisualiserSceneGetDrawBuffers") as {
                        camX?: number;
                        camY?: number;
                        zoom?: number;
                    } | null;
                    const screen = layoutToWasmScreen(layout.x, layout.y, css.width, css.height, {
                        x: zoomBuf?.camX || 0,
                        y: zoomBuf?.camY || 0,
                        zoom: (zoomBuf?.zoom ?? 0) > 0 ? (zoomBuf!.zoom as number) : 1,
                    });
                    callScene("meshchatxVisualiserSceneDragTo", screen.x, screen.y);
                    dirty = true;
                }
            } else {
                callScene("meshchatxVisualiserSceneDragTo", p.x, p.y);
                dirty = true;
            }
        } else if (pointerMode === "pan") {
            if (isPlanet()) {
                applyPlanetOrbit(orbitYaw - (p.x - lastX) * 0.008, orbitPitch + (p.y - lastY) * 0.008, orbitDist);
                lastX = p.x;
                lastY = p.y;
            } else {
                const zoomBuf = callScene("meshchatxVisualiserSceneGetDrawBuffers") as { zoom?: number } | null;
                const zoom = (zoomBuf?.zoom ?? 0) > 0 ? (zoomBuf!.zoom as number) : 1;
                const dx = (lastX - p.x) / zoom;
                const dy = (lastY - p.y) / zoom;
                callScene("meshchatxVisualiserScenePanBy", dx, dy);
                lastX = p.x;
                lastY = p.y;
                dirty = true;
            }
        } else {
            const id = pickNodeAt(p.x, p.y, 14);
            if (id !== hoverId) {
                hoverId = id;
                dirty = true;
            }
            if (typeof hooks.onHover === "function") {
                hooks.onHover(id, id ? metaById.get(id) || null : null, p.x, p.y);
            }
        }
    }

    function onPointerUp(ev: PointerEvent): void {
        pointers.delete(ev.pointerId);
        try {
            canvas.releasePointerCapture?.(ev.pointerId);
        } catch {
            /* ignore */
        }
        if (pointerMode === "pinch") {
            if (pointers.size >= 2) {
                const pair = activePointerPair();
                pinchLastDist = pair ? pointerDistance(pair.a, pair.b) : 0;
            } else if (pointers.size === 1) {
                const remaining = [...pointers.values()][0];
                lastX = remaining.x;
                lastY = remaining.y;
                pointerMode = "pan";
            } else {
                pointerMode = null;
            }
            dirty = true;
            return;
        }
        if (pointerMode === "drag") {
            callScene("meshchatxVisualiserSceneDragEnd");
        }
        if (pointers.size === 0) {
            pointerMode = null;
        }
        dirty = true;
    }

    function onDblClick(ev: MouseEvent): void {
        const p = cssPoint(ev);
        const id = pickNodeAt(p.x, p.y, 16);
        if (!id) return;
        if (typeof hooks.onNodeActivate === "function") {
            hooks.onNodeActivate(id, metaById.get(id) || null);
        }
    }

    function onWheel(ev: WheelEvent): void {
        ev.preventDefault();
        const factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
        if (isPlanet()) {
            applyPlanetOrbit(orbitYaw, orbitPitch, orbitDist / factor);
            return;
        }
        const p = cssPoint(ev);
        callScene("meshchatxVisualiserSceneZoomAt", p.x, p.y, factor);
        dirty = true;
    }

    function onResize(): void {
        const size = renderer.resize();
        callScene("meshchatxVisualiserSceneResize", size.width, size.height);
        dirty = true;
    }

    canvas.style.touchAction = "none";
    canvas.addEventListener("pointerdown", onPointerDown);
    canvas.addEventListener("pointermove", onPointerMove);
    canvas.addEventListener("pointerup", onPointerUp);
    canvas.addEventListener("pointercancel", onPointerUp);
    canvas.addEventListener("dblclick", onDblClick);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("resize", onResize);

    rafId = requestAnimationFrame(frame);

    function destroy(): void {
        running = false;
        iconLoadGen += 1;
        if (rafId != null) cancelAnimationFrame(rafId);
        rafId = null;
        canvas.removeEventListener("pointerdown", onPointerDown);
        canvas.removeEventListener("pointermove", onPointerMove);
        canvas.removeEventListener("pointerup", onPointerUp);
        canvas.removeEventListener("pointercancel", onPointerUp);
        canvas.removeEventListener("dblclick", onDblClick);
        canvas.removeEventListener("wheel", onWheel);
        window.removeEventListener("resize", onResize);
        pointers.clear();
        renderer.destroy();
        metaById.clear();
        indexById.clear();
        imageByIndex = [];
        labelByIndex = [];
        idByIndex = [];
        hoverId = null;
        texMeta = [];
        lastPlanets = [];
        planetHomeById = Object.create(null);
    }

    return {
        setGraph,
        updateNodeImages,
        getPositions,
        getCounts,
        setLiveLayout,
        setViewMode,
        destroy,
        requestRedraw: () => {
            dirty = true;
        },
    };
}
