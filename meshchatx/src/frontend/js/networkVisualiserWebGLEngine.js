/**
 * WASM scene + WebGL2 engine for the network visualiser.
 * Falls back is handled by the caller (vis-network path).
 */

import { callVisualiserWasmJson, isVisualiserWebGLSceneReady } from "./VisualiserWasmLoader.js";
import {
    createNetworkVisualiserWebGL,
    mergeSceneNodesWithTextures,
    NODE_STRIDE,
    SCENE_NODE_STRIDE,
    tryCreateWebGL2Context,
} from "./networkVisualiserWebGL.js";

export { isVisualiserWebGLSceneReady };

export const KIND_ME = 0;
export const KIND_IFACE_ON = 1;
export const KIND_IFACE_OFF = 2;
export const KIND_PEER = 3;
export const KIND_DISCOVERED = 4;

/**
 * Distance between two CSS points.
 * @param {{x:number,y:number}} a
 * @param {{x:number,y:number}} b
 */
export function pointerDistance(a, b) {
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return Math.hypot(dx, dy);
}

/**
 * Midpoint of two CSS points.
 * @param {{x:number,y:number}} a
 * @param {{x:number,y:number}} b
 */
export function pointerMidpoint(a, b) {
    return { x: (a.x + b.x) * 0.5, y: (a.y + b.y) * 0.5 };
}

/**
 * @param {HTMLCanvasElement} [_canvas] optional host (capability is global)
 */
export function canUseVisualiserWebGL() {
    if (!isVisualiserWebGLSceneReady()) return false;
    if (typeof WebGL2RenderingContext === "undefined") return false;
    if (typeof document === "undefined") return false;
    const probe = document.createElement("canvas");
    return !!tryCreateWebGL2Context(probe);
}

function hexToRgb01(hex) {
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

function colorFromNode(node) {
    const c = node?.color;
    if (typeof c === "string") {
        const rgb = hexToRgb01(c);
        if (rgb) return rgb;
    }
    if (c && typeof c === "object") {
        const border = c.border || c.background;
        const rgb = hexToRgb01(border);
        if (rgb) return rgb;
    }
    return null;
}

function colorFromEdge(edge) {
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

function kindForNode(node) {
    const g = node?.group;
    if (g === "me" || node?.id === "me") return KIND_ME;
    if (g === "discovered") return KIND_DISCOVERED;
    if (g === "interface") {
        const img = String(node?.image || "");
        if (img.includes("disconnected")) return KIND_IFACE_OFF;
        const border = node?.color?.border || "";
        if (border === "#ef4444" || border === "#f87171") return KIND_IFACE_OFF;
        return KIND_IFACE_ON;
    }
    return KIND_PEER;
}

function sizeForNode(node, kind) {
    const s = Number(node?.size);
    if (Number.isFinite(s) && s > 0) {
        return Math.max(6, Math.min(28, s * 0.35));
    }
    if (kind === KIND_ME) return 18;
    if (kind === KIND_IFACE_ON || kind === KIND_IFACE_OFF) return 12;
    if (kind === KIND_DISCOVERED) return 9;
    return 10;
}

/**
 * Convert vis-style graph nodes/edges into WASM scene SetRequest payload.
 * @param {object[]} graphNodes
 * @param {object[]} graphEdges
 * @param {{width:number,height:number,camX?:number,camY?:number,zoom?:number}} view
 */
export function graphToSceneRequest(graphNodes, graphEdges, view) {
    const nodes = [];
    for (const n of graphNodes || []) {
        if (!n?.id) continue;
        const kind = kindForNode(n);
        const rgb = colorFromNode(n) || { r: 0.85, g: 0.85, b: 0.9 };
        nodes.push({
            id: String(n.id),
            x: Number.isFinite(n.x) ? n.x : 0,
            y: Number.isFinite(n.y) ? n.y : 0,
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
    const edges = [];
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
        zoom: view?.zoom > 0 ? view.zoom : 1,
    };
}

/**
 * @param {HTMLCanvasElement} canvas
 * @param {{
 *   getLiveLayout: () => boolean,
 *   isDark: () => boolean,
 *   onNodeActivate?: (id: string, meta: object|null) => void,
 *   onHover?: (id: string|null, meta: object|null, cssX: number, cssY: number) => void,
 * }} hooks
 */
export function createVisualiserWebGLEngine(canvas, hooks = {}) {
    const gl = tryCreateWebGL2Context(canvas);
    if (!gl) {
        throw new Error("WebGL2 unavailable");
    }
    if (!isVisualiserWebGLSceneReady()) {
        throw new Error("WASM scene unavailable");
    }

    const renderer = createNetworkVisualiserWebGL(canvas, gl);
    const metaById = new Map();
    const indexById = new Map();
    /** @type {(string|null)[]} */
    let imageByIndex = [];
    /** @type {{useTex:number,u:number,v:number}[]} */
    let texMeta = [];
    let drawNodeScratch = new Float32Array(0);
    let rafId = null;
    let running = true;
    let dirty = true;
    let pointerMode = null;
    let lastX = 0;
    let lastY = 0;
    let nodeCount = 0;
    let edgeCount = 0;
    /** @type {Map<number,{x:number,y:number}>} */
    const pointers = new Map();
    let pinchLastDist = 0;
    let iconLoadGen = 0;

    function cssPoint(ev) {
        const rect = canvas.getBoundingClientRect();
        return {
            x: ev.clientX - rect.left,
            y: ev.clientY - rect.top,
        };
    }

    function callScene(name, ...args) {
        const fn = globalThis[name];
        if (typeof fn !== "function") return null;
        try {
            return fn(...args);
        } catch (e) {
            console.warn("Visualiser scene call failed:", name, e);
            return null;
        }
    }

    function rebuildTexMeta() {
        texMeta = imageByIndex.map((url) => {
            if (!url) return { useTex: 0, u: 0, v: 0 };
            const slot = renderer.getIconSlot(url);
            if (slot == null) return { useTex: 0, u: 0, v: 0 };
            const uv = renderer.iconUv(slot);
            return { useTex: 1, u: uv.u, v: uv.v };
        });
    }

    async function loadIconsForCurrentGraph(generation) {
        const urls = [...new Set(imageByIndex.filter(Boolean))];
        await Promise.all(
            urls.map(async (url) => {
                await renderer.ensureIcon(url);
            })
        );
        if (!running || generation !== iconLoadGen) return;
        rebuildTexMeta();
        dirty = true;
    }

    function setGraph(graphNodes, graphEdges, viewOpts = {}) {
        metaById.clear();
        indexById.clear();
        imageByIndex = [];
        let idx = 0;
        for (const n of graphNodes || []) {
            if (!n?.id) continue;
            const id = String(n.id);
            metaById.set(id, {
                id,
                label: n.label || "",
                title: n.title || "",
                group: n.group || "",
                announce: n._announce || null,
            });
            indexById.set(id, idx);
            imageByIndex[idx] = typeof n.image === "string" && n.image ? n.image : null;
            idx += 1;
        }
        const size = renderer.resize();
        const preserveCamera = viewOpts.preserveCamera !== false && nodeCount > 0;
        const req = graphToSceneRequest(graphNodes, graphEdges, {
            width: size.width,
            height: size.height,
            camX: viewOpts.camX ?? 0,
            camY: viewOpts.camY ?? 0,
            zoom: preserveCamera ? 0 : viewOpts.zoom > 0 ? viewOpts.zoom : 1,
        });
        const got = callVisualiserWasmJson("meshchatxVisualiserSceneSet", JSON.stringify(req));
        if (!got || got.ok === false) {
            throw new Error(got?.error || "SceneSet failed");
        }
        nodeCount = got.nodes || 0;
        edgeCount = got.edges || 0;
        rebuildTexMeta();
        dirty = true;
        iconLoadGen += 1;
        void loadIconsForCurrentGraph(iconLoadGen);
    }

    /**
     * Apply deferred LXMF / custom icon URLs after paint.
     * @param {{id:string,image:string}[]} updates
     */
    function updateNodeImages(updates) {
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

    function getPositions() {
        const got = callVisualiserWasmJson("meshchatxVisualiserSceneGetPositions");
        return got?.positions && typeof got.positions === "object" ? got.positions : {};
    }

    function getCounts() {
        return { nodes: nodeCount, edges: edgeCount };
    }

    function setLiveLayout() {
        dirty = true;
    }

    function frame() {
        if (!running) return;
        rafId = requestAnimationFrame(frame);
        const live = typeof hooks.getLiveLayout === "function" ? hooks.getLiveLayout() : false;
        if (live && pointerMode !== "drag") {
            callScene("meshchatxVisualiserSceneTick", 2);
            dirty = true;
        }
        if (!dirty && !live) return;
        const buf = callScene("meshchatxVisualiserSceneGetDrawBuffers");
        if (!buf || buf.ok === false) return;
        const camera = {
            x: buf.camX || 0,
            y: buf.camY || 0,
            zoom: buf.zoom > 0 ? buf.zoom : 1,
        };
        const dark = typeof hooks.isDark === "function" ? hooks.isDark() : false;
        const sceneCount = buf.nodes && buf.nodes.length ? Math.floor(buf.nodes.length / SCENE_NODE_STRIDE) : 0;
        const need = sceneCount * NODE_STRIDE;
        if (drawNodeScratch.length < need) {
            drawNodeScratch = new Float32Array(need);
        }
        const drawNodes = mergeSceneNodesWithTextures(buf.nodes, texMeta, drawNodeScratch);
        const size = renderer.draw(drawNodes, buf.edges, camera, dark);
        callScene("meshchatxVisualiserSceneResize", size.width, size.height);
        nodeCount = buf.nodeCount || nodeCount;
        edgeCount = buf.edgeCount || edgeCount;
        dirty = false;
    }

    function activePointerPair() {
        if (pointers.size < 2) return null;
        const pts = [...pointers.values()];
        return { a: pts[0], b: pts[1] };
    }

    function onPointerDown(ev) {
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
        const id = callScene("meshchatxVisualiserScenePick", p.x, p.y, 16);
        if (id) {
            callScene("meshchatxVisualiserSceneDragStart", id);
            pointerMode = "drag";
        } else {
            pointerMode = "pan";
        }
        dirty = true;
    }

    function onPointerMove(ev) {
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
                const mid = pointerMidpoint(pair.a, pair.b);
                callScene("meshchatxVisualiserSceneZoomAt", mid.x, mid.y, factor);
                pinchLastDist = dist;
                dirty = true;
            }
            return;
        }
        if (pointerMode === "drag") {
            callScene("meshchatxVisualiserSceneDragTo", p.x, p.y);
            dirty = true;
        } else if (pointerMode === "pan") {
            const zoomBuf = callScene("meshchatxVisualiserSceneGetDrawBuffers");
            const zoom = zoomBuf?.zoom > 0 ? zoomBuf.zoom : 1;
            const dx = (lastX - p.x) / zoom;
            const dy = (lastY - p.y) / zoom;
            callScene("meshchatxVisualiserScenePanBy", dx, dy);
            lastX = p.x;
            lastY = p.y;
            dirty = true;
        } else if (typeof hooks.onHover === "function") {
            const id = callScene("meshchatxVisualiserScenePick", p.x, p.y, 14) || null;
            hooks.onHover(id, id ? metaById.get(id) || null : null, p.x, p.y);
        }
    }

    function onPointerUp(ev) {
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

    function onDblClick(ev) {
        const p = cssPoint(ev);
        const id = callScene("meshchatxVisualiserScenePick", p.x, p.y, 16);
        if (!id) return;
        if (typeof hooks.onNodeActivate === "function") {
            hooks.onNodeActivate(id, metaById.get(id) || null);
        }
    }

    function onWheel(ev) {
        ev.preventDefault();
        const p = cssPoint(ev);
        const factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
        callScene("meshchatxVisualiserSceneZoomAt", p.x, p.y, factor);
        dirty = true;
    }

    function onResize() {
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

    function destroy() {
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
        texMeta = [];
    }

    return {
        setGraph,
        updateNodeImages,
        getPositions,
        getCounts,
        setLiveLayout,
        destroy,
        requestRedraw: () => {
            dirty = true;
        },
    };
}
