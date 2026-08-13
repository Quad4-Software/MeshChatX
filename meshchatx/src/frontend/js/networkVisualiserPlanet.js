// SPDX-License-Identifier: 0BSD

/**
 * Planet view for the WebGL network visualiser.
 * Maps the 2D force layout onto a unit sphere (local node at the front)
 * and projects with an orbit camera. Pixel draw stays in the 2D WebGL path.
 */

import { EDGE_STRIDE, NODE_STRIDE } from "./networkVisualiserWebGL.js";

export const PLANET_VIEW = "planet";
export const FLAT_VIEW = "flat";

export const PLANET_FOV_Y = (50 * Math.PI) / 180;
export const PLANET_NEAR = 0.12;
export const PLANET_FAR = 24;
export const PLANET_DIST_MIN = 1.65;
export const PLANET_DIST_MAX = 8.5;
export const PLANET_PITCH_LIMIT = 1.18;
export const DEFAULT_ORBIT_YAW = 0.55;
export const DEFAULT_ORBIT_PITCH = 0.32;
export const DEFAULT_ORBIT_DIST = 3.05;
export const LAYOUT_SCALE_FLOOR = 160;
/** Scale above max layout radius so the farthest node stays on the back hemisphere. */
export const LAYOUT_SCALE_FIT = 1.08;

const meridians = 18;
const parallels = 8;
const gridSegs = 24;

/** @type {{x1:number,y1:number,z1:number,x2:number,y2:number,z2:number}[]|null} */
let globeGridCache = null;

let nodeScratch = new Float32Array(0);
let edgeScratch = new Float32Array(0);
let depthScratch = new Float32Array(0);

/**
 * @param {unknown} raw
 * @returns {"flat"|"planet"}
 */
export function normalizeVisualiserViewMode(raw) {
    return raw === PLANET_VIEW ? PLANET_VIEW : FLAT_VIEW;
}

/**
 * @param {number} yaw
 * @param {number} pitch
 * @param {number} dist
 */
export function clampOrbit(yaw, pitch, dist) {
    let y = Number.isFinite(yaw) ? yaw : DEFAULT_ORBIT_YAW;
    let p = Number.isFinite(pitch) ? pitch : DEFAULT_ORBIT_PITCH;
    if (p < -PLANET_PITCH_LIMIT) p = -PLANET_PITCH_LIMIT;
    if (p > PLANET_PITCH_LIMIT) p = PLANET_PITCH_LIMIT;
    let d = Number.isFinite(dist) && dist > 0 ? dist : DEFAULT_ORBIT_DIST;
    if (d < PLANET_DIST_MIN) d = PLANET_DIST_MIN;
    if (d > PLANET_DIST_MAX) d = PLANET_DIST_MAX;
    return { yaw: y, pitch: p, dist: d };
}

/**
 * Max layout radius used to wrap the graph onto the sphere.
 * @param {Float32Array|number[]|null|undefined} nodes NODE_STRIDE or SCENE stride with x,y at 0,1
 * @param {number} stride
 */
export function computeLayoutScale(nodes, stride = NODE_STRIDE) {
    const step = stride > 0 ? stride : NODE_STRIDE;
    const n = nodes && nodes.length ? Math.floor(nodes.length / step) : 0;
    let maxR = 0;
    for (let i = 0; i < n; i++) {
        const o = i * step;
        const r = Math.hypot(nodes[o] || 0, nodes[o + 1] || 0);
        if (r > maxR) maxR = r;
    }
    return Math.max(maxR * LAYOUT_SCALE_FIT, LAYOUT_SCALE_FLOOR);
}

/**
 * Local node (origin) sits on the front of the globe. Distance wraps toward the back.
 * @param {number} x
 * @param {number} y
 * @param {number} layoutScale
 * @returns {{x:number,y:number,z:number,theta:number,phi:number}}
 */
export function layoutToSphere(x, y, layoutScale) {
    const scale = layoutScale > 1e-6 ? layoutScale : LAYOUT_SCALE_FLOOR;
    const lx = Number.isFinite(x) ? x : 0;
    const ly = Number.isFinite(y) ? y : 0;
    const theta = Math.atan2(ly, lx);
    const r = Math.hypot(lx, ly) / scale;
    const phi = Math.min(r, 1) * Math.PI;
    const sp = Math.sin(phi);
    return {
        x: sp * Math.cos(theta),
        y: sp * Math.sin(theta),
        z: Math.cos(phi),
        theta,
        phi,
    };
}

/**
 * Inverse of layoutToSphere. Point should lie on the unit sphere.
 * @param {number} x
 * @param {number} y
 * @param {number} z
 * @param {number} layoutScale
 */
export function sphereToLayout(x, y, z, layoutScale) {
    const scale = layoutScale > 1e-6 ? layoutScale : LAYOUT_SCALE_FLOOR;
    const len = Math.hypot(x, y, z);
    if (len < 1e-8) return { x: 0, y: 0 };
    const nx = x / len;
    const ny = y / len;
    const nz = z / len;
    const phi = Math.acos(Math.max(-1, Math.min(1, nz)));
    const theta = Math.atan2(ny, nx);
    const r = (phi / Math.PI) * scale;
    return { x: r * Math.cos(theta), y: r * Math.sin(theta) };
}

/**
 * Camera position looking at the origin.
 * @param {number} yaw
 * @param {number} pitch
 * @param {number} dist
 */
export function orbitEye(yaw, pitch, dist) {
    const cp = Math.cos(pitch);
    return {
        x: dist * cp * Math.sin(yaw),
        y: dist * Math.sin(pitch),
        z: dist * cp * Math.cos(yaw),
    };
}

/**
 * @param {{x:number,y:number,z:number}} eye
 * @returns {{forward:{x:number,y:number,z:number}, right:{x:number,y:number,z:number}, up:{x:number,y:number,z:number}}}
 */
export function cameraBasis(eye) {
    const fl = Math.hypot(eye.x, eye.y, eye.z) || 1;
    const forward = { x: -eye.x / fl, y: -eye.y / fl, z: -eye.z / fl };
    let cx = forward.y * 0 - forward.z * 1;
    let cy = forward.z * 0 - forward.x * 0;
    let cz = forward.x * 1 - forward.y * 0;
    let rl = Math.hypot(cx, cy, cz);
    if (rl < 1e-6) {
        cx = 1;
        cy = 0;
        cz = 0;
        rl = 1;
    }
    const right = { x: cx / rl, y: cy / rl, z: cz / rl };
    const up = {
        x: right.y * forward.z - right.z * forward.y,
        y: right.z * forward.x - right.x * forward.z,
        z: right.x * forward.y - right.y * forward.x,
    };
    return { forward, right, up };
}

/**
 * @param {{x:number,y:number,z:number}} eye
 * @returns {Float32Array} column-major 4x4 view matrix
 */
export function lookAtOrigin(eye) {
    const { forward, right, up } = cameraBasis(eye);
    const out = new Float32Array(16);
    out[0] = right.x;
    out[1] = up.x;
    out[2] = -forward.x;
    out[3] = 0;
    out[4] = right.y;
    out[5] = up.y;
    out[6] = -forward.y;
    out[7] = 0;
    out[8] = right.z;
    out[9] = up.z;
    out[10] = -forward.z;
    out[11] = 0;
    out[12] = -(right.x * eye.x + right.y * eye.y + right.z * eye.z);
    out[13] = -(up.x * eye.x + up.y * eye.y + up.z * eye.z);
    out[14] = forward.x * eye.x + forward.y * eye.y + forward.z * eye.z;
    out[15] = 1;
    return out;
}

/**
 * @param {number} fovY
 * @param {number} aspect
 * @param {number} near
 * @param {number} far
 * @returns {Float32Array} column-major 4x4
 */
export function perspective(fovY, aspect, near, far) {
    const out = new Float32Array(16);
    const f = 1 / Math.tan(fovY * 0.5);
    const a = aspect > 1e-6 ? aspect : 1;
    const nf = 1 / (near - far);
    out[0] = f / a;
    out[5] = f;
    out[10] = (far + near) * nf;
    out[11] = -1;
    out[14] = 2 * far * near * nf;
    return out;
}

/**
 * @param {Float32Array} a
 * @param {Float32Array} b
 */
export function mat4Multiply(a, b) {
    const out = new Float32Array(16);
    for (let col = 0; col < 4; col++) {
        const b0 = b[col * 4];
        const b1 = b[col * 4 + 1];
        const b2 = b[col * 4 + 2];
        const b3 = b[col * 4 + 3];
        out[col * 4] = a[0] * b0 + a[4] * b1 + a[8] * b2 + a[12] * b3;
        out[col * 4 + 1] = a[1] * b0 + a[5] * b1 + a[9] * b2 + a[13] * b3;
        out[col * 4 + 2] = a[2] * b0 + a[6] * b1 + a[10] * b2 + a[14] * b3;
        out[col * 4 + 3] = a[3] * b0 + a[7] * b1 + a[11] * b2 + a[15] * b3;
    }
    return out;
}

/**
 * @param {Float32Array} m
 * @param {number} x
 * @param {number} y
 * @param {number} z
 */
export function transformPoint(m, x, y, z) {
    return {
        x: m[0] * x + m[4] * y + m[8] * z + m[12],
        y: m[1] * x + m[5] * y + m[9] * z + m[13],
        z: m[2] * x + m[6] * y + m[10] * z + m[14],
        w: m[3] * x + m[7] * y + m[11] * z + m[15],
    };
}

/**
 * Front of the globe faces the camera when dot(p, eye) > 1 on the unit sphere.
 * @param {number} px
 * @param {number} py
 * @param {number} pz
 * @param {{x:number,y:number,z:number}} eye
 */
export function sphereFacing(px, py, pz, eye) {
    return px * eye.x + py * eye.y + pz * eye.z - 1;
}

/**
 * @param {number} clipX
 * @param {number} clipY
 * @param {number} clipW
 * @param {number} width
 * @param {number} height
 */
export function clipToScreen(clipX, clipY, clipW, width, height) {
    if (!(Math.abs(clipW) > 1e-8)) {
        return { x: width * 0.5, y: height * 0.5, ok: false };
    }
    const ndcX = clipX / clipW;
    const ndcY = clipY / clipW;
    return {
        x: (ndcX * 0.5 + 0.5) * width,
        y: (1 - (ndcY * 0.5 + 0.5)) * height,
        ok: clipW > 0,
    };
}

/**
 * World (origin-centered, y-down like the 2D shader) from CSS pixels at zoom 1 cam 0.
 * @param {number} sx
 * @param {number} sy
 * @param {number} width
 * @param {number} height
 */
export function screenToDrawWorld(sx, sy, width, height) {
    return { x: sx - width * 0.5, y: sy - height * 0.5 };
}

/**
 * Pixel radius of the unit sphere silhouette.
 * @param {number} dist
 * @param {number} fovY
 * @param {number} height
 */
export function projectedSphereRadiusPx(dist, fovY, height) {
    const d = Math.max(dist, 1.001);
    const ang = Math.asin(Math.min(0.999, 1 / d));
    const half = Math.tan(fovY * 0.5);
    if (!(half > 0)) return height * 0.25;
    return (Math.tan(ang) / half) * (height * 0.5);
}

/**
 * Zoom stand-in for 2D LOD bands. Default distance maps to zoom 1 (high).
 * @param {number} dist
 */
export function planetLodZoom(dist) {
    const d = dist > 0.2 ? dist : DEFAULT_ORBIT_DIST;
    return DEFAULT_ORBIT_DIST / d;
}

function sph(lon, lat) {
    const cl = Math.cos(lat);
    return { x: cl * Math.cos(lon), y: Math.sin(lat), z: cl * Math.sin(lon) };
}

/**
 * Lat/lon line segments on the unit sphere (Y up).
 */
export function buildGlobeGrid() {
    if (globeGridCache) return globeGridCache;
    const lines = [];
    for (let i = 0; i < meridians; i++) {
        const lon = (i / meridians) * Math.PI * 2;
        let prev = null;
        for (let s = 0; s <= gridSegs; s++) {
            const lat = Math.PI / 2 - (s / gridSegs) * Math.PI;
            const p = sph(lon, lat);
            if (prev) {
                lines.push({ x1: prev.x, y1: prev.y, z1: prev.z, x2: p.x, y2: p.y, z2: p.z });
            }
            prev = p;
        }
    }
    for (let j = 1; j <= parallels; j++) {
        const lat = Math.PI / 2 - (j / (parallels + 1)) * Math.PI;
        let prev = null;
        const first = sph(0, lat);
        for (let s = 1; s <= gridSegs; s++) {
            const lon = (s / gridSegs) * Math.PI * 2;
            const p = s === gridSegs ? first : sph(lon, lat);
            if (prev) {
                lines.push({ x1: prev.x, y1: prev.y, z1: prev.z, x2: p.x, y2: p.y, z2: p.z });
            }
            prev = p;
        }
    }
    globeGridCache = lines;
    return lines;
}

/**
 * Camera ray from a CSS pixel.
 * @param {number} cssX
 * @param {number} cssY
 * @param {number} width
 * @param {number} height
 * @param {{x:number,y:number,z:number}} eye
 */
export function screenRay(cssX, cssY, width, height, eye) {
    const { forward, right, up } = cameraBasis(eye);
    const aspect = height > 0 ? width / height : 1;
    const tanHalf = Math.tan(PLANET_FOV_Y * 0.5);
    const nx = (cssX / Math.max(width, 1)) * 2 - 1;
    const ny = 1 - (cssY / Math.max(height, 1)) * 2;
    const vx = right.x * nx * tanHalf * aspect + up.x * ny * tanHalf + forward.x;
    const vy = right.y * nx * tanHalf * aspect + up.y * ny * tanHalf + forward.y;
    const vz = right.z * nx * tanHalf * aspect + up.z * ny * tanHalf + forward.z;
    const len = Math.hypot(vx, vy, vz) || 1;
    return {
        origin: eye,
        dir: { x: vx / len, y: vy / len, z: vz / len },
    };
}

/**
 * Nearest hit of a ray with the unit sphere at the origin, or null.
 * @param {{x:number,y:number,z:number}} origin
 * @param {{x:number,y:number,z:number}} dir
 * @param {number} [radius]
 */
export function raySphere(origin, dir, radius = 1) {
    const r2 = radius * radius;
    const ox = origin.x;
    const oy = origin.y;
    const oz = origin.z;
    const dx = dir.x;
    const dy = dir.y;
    const dz = dir.z;
    const b = ox * dx + oy * dy + oz * dz;
    const c = ox * ox + oy * oy + oz * oz - r2;
    const disc = b * b - c;
    if (disc < 0) return null;
    const s = Math.sqrt(disc);
    const t0 = -b - s;
    const t1 = -b + s;
    const t = t0 > 1e-4 ? t0 : t1 > 1e-4 ? t1 : null;
    if (t == null) return null;
    return { x: ox + dx * t, y: oy + dy * t, z: oz + dz * t, t };
}

/**
 * 2D layout under a planet-mode pointer, or null if the ray misses the globe.
 */
export function pointerToLayout(cssX, cssY, width, height, eye, layoutScale) {
    const ray = screenRay(cssX, cssY, width, height, eye);
    const hit = raySphere(ray.origin, ray.dir, 1);
    if (!hit) return null;
    return sphereToLayout(hit.x, hit.y, hit.z, layoutScale);
}

/**
 * WASM DragTo screen point for a 2D layout coordinate.
 * @param {number} lx
 * @param {number} ly
 * @param {number} width
 * @param {number} height
 * @param {{x?:number,y?:number,zoom?:number}|null} [cam]
 */
export function layoutToWasmScreen(lx, ly, width, height, cam = null) {
    const zoom = cam?.zoom > 0 ? cam.zoom : 1;
    return {
        x: (lx - (cam?.x || 0)) * zoom + width * 0.5,
        y: (ly - (cam?.y || 0)) * zoom + height * 0.5,
    };
}

/**
 * Project the 2D graph onto the globe and into the 2D draw buffers.
 *
 * @param {{
 *   nodes: Float32Array,
 *   edges: Float32Array|null|undefined,
 *   width: number,
 *   height: number,
 *   yaw: number,
 *   pitch: number,
 *   dist: number,
 *   dark: boolean,
 *   idByIndex?: (string|null|undefined)[],
 * }} opts
 * @returns {{
 *   nodes: Float32Array,
 *   edges: Float32Array,
 *   pick: {id:string,sx:number,sy:number,size:number}[],
 *   projected: {sx:number,sy:number,size:number,facing:number,front:boolean}[],
 *   layoutScale: number,
 *   camera: {x:number,y:number,zoom:number},
 * }}
 */
export function projectPlanetScene(opts) {
    const width = Math.max(1, opts?.width || 1);
    const height = Math.max(1, opts?.height || 1);
    const orbit = clampOrbit(opts?.yaw ?? DEFAULT_ORBIT_YAW, opts?.pitch ?? DEFAULT_ORBIT_PITCH, opts?.dist ?? DEFAULT_ORBIT_DIST);
    const eye = orbitEye(orbit.yaw, orbit.pitch, orbit.dist);
    const view = lookAtOrigin(eye);
    const proj = perspective(PLANET_FOV_Y, width / height, PLANET_NEAR, PLANET_FAR);
    const viewProj = mat4Multiply(proj, view);
    const srcNodes = opts?.nodes;
    const srcCount = srcNodes && srcNodes.length ? Math.floor(srcNodes.length / NODE_STRIDE) : 0;
    const layoutScale = computeLayoutScale(srcNodes, NODE_STRIDE);
    const idByIndex = opts?.idByIndex || [];
    const dark = opts?.dark === true;

    const grid = buildGlobeGrid();
    const srcEdges = opts?.edges;
    const srcEdgeCount = srcEdges && srcEdges.length ? Math.floor(srcEdges.length / EDGE_STRIDE) : 0;

    const globeR = projectedSphereRadiusPx(orbit.dist, PLANET_FOV_Y, height);
    const originClip = transformPoint(viewProj, 0, 0, 0);
    const originScreen = clipToScreen(originClip.x, originClip.y, originClip.w, width, height);
    const originDraw = screenToDrawWorld(originScreen.x, originScreen.y, width, height);

    const outNodeCount = srcCount + 1;
    const nodeNeed = outNodeCount * NODE_STRIDE;
    if (nodeScratch.length < nodeNeed) {
        nodeScratch = new Float32Array(nodeNeed);
    }
    const fill = dark ? [0.06, 0.14, 0.26, 0.92] : [0.76, 0.88, 0.97, 0.94];
    nodeScratch[0] = originDraw.x;
    nodeScratch[1] = originDraw.y;
    nodeScratch[2] = Math.max(24, globeR);
    nodeScratch[3] = fill[0];
    nodeScratch[4] = fill[1];
    nodeScratch[5] = fill[2];
    nodeScratch[6] = fill[3];
    nodeScratch[7] = 0;
    nodeScratch[8] = 0;
    nodeScratch[9] = 0;

    const projected = [];
    const pick = [];
    const refDist = Math.hypot(eye.x, eye.y, eye.z - 1) || orbit.dist;

    for (let i = 0; i < srcCount; i++) {
        const o = i * NODE_STRIDE;
        const sphP = layoutToSphere(srcNodes[o], srcNodes[o + 1], layoutScale);
        const facing = sphereFacing(sphP.x, sphP.y, sphP.z, eye);
        const clip = transformPoint(viewProj, sphP.x, sphP.y, sphP.z);
        const screen = clipToScreen(clip.x, clip.y, clip.w, width, height);
        const viewZ = Math.hypot(sphP.x - eye.x, sphP.y - eye.y, sphP.z - eye.z);
        const persp = Math.max(0.35, Math.min(2.4, refDist / Math.max(viewZ, 0.2)));
        const size = Math.max(6, (srcNodes[o + 2] || 18) * persp);
        const front = facing > 0 && screen.ok;
        const draw = screenToDrawWorld(screen.x, screen.y, width, height);
        const d = (i + 1) * NODE_STRIDE;
        const a = front ? srcNodes[o + 6] || 1 : Math.max(0.08, (srcNodes[o + 6] || 1) * 0.18);
        nodeScratch[d] = draw.x;
        nodeScratch[d + 1] = draw.y;
        nodeScratch[d + 2] = front ? size : size * 0.55;
        nodeScratch[d + 3] = srcNodes[o + 3];
        nodeScratch[d + 4] = srcNodes[o + 4];
        nodeScratch[d + 5] = srcNodes[o + 5];
        nodeScratch[d + 6] = a;
        nodeScratch[d + 7] = front ? srcNodes[o + 7] : 0;
        nodeScratch[d + 8] = srcNodes[o + 8];
        nodeScratch[d + 9] = srcNodes[o + 9];
        const rec = { sx: screen.x, sy: screen.y, size, facing, front };
        projected.push(rec);
        const id = idByIndex[i];
        if (front && id) {
            pick.push({ id: String(id), sx: screen.x, sy: screen.y, size });
        }
    }

    if (srcCount > 1) {
        const order = new Array(srcCount);
        for (let i = 0; i < srcCount; i++) order[i] = i;
        order.sort((a, b) => projected[a].facing - projected[b].facing);
        const bodyNeed = srcCount * NODE_STRIDE;
        if (depthScratch.length < bodyNeed) {
            depthScratch = new Float32Array(bodyNeed);
        }
        depthScratch.set(nodeScratch.subarray(NODE_STRIDE, NODE_STRIDE + bodyNeed));
        for (let s = 0; s < srcCount; s++) {
            const i = order[s];
            nodeScratch.set(
                depthScratch.subarray(i * NODE_STRIDE, (i + 1) * NODE_STRIDE),
                (s + 1) * NODE_STRIDE
            );
        }
    }

    const gridColor = dark ? [0.28, 0.62, 0.82, 0.38] : [0.32, 0.52, 0.72, 0.42];
    const edgeNeed = (grid.length + srcEdgeCount) * EDGE_STRIDE;
    if (edgeScratch.length < edgeNeed) {
        edgeScratch = new Float32Array(Math.max(edgeNeed, 64));
    }
    let w = 0;
    const writeSeg = (x1, y1, z1, x2, y2, z2, r, g, b, a, requireFront) => {
        const f1 = sphereFacing(x1, y1, z1, eye);
        const f2 = sphereFacing(x2, y2, z2, eye);
        if (requireFront && f1 <= 0 && f2 <= 0) return;
        const c1 = transformPoint(viewProj, x1, y1, z1);
        const c2 = transformPoint(viewProj, x2, y2, z2);
        const s1 = clipToScreen(c1.x, c1.y, c1.w, width, height);
        const s2 = clipToScreen(c2.x, c2.y, c2.w, width, height);
        if (!s1.ok && !s2.ok) return;
        const d1 = screenToDrawWorld(s1.x, s1.y, width, height);
        const d2 = screenToDrawWorld(s2.x, s2.y, width, height);
        const o = w * EDGE_STRIDE;
        const fade = f1 > 0 || f2 > 0 ? 1 : 0.2;
        edgeScratch[o] = d1.x;
        edgeScratch[o + 1] = d1.y;
        edgeScratch[o + 2] = d2.x;
        edgeScratch[o + 3] = d2.y;
        edgeScratch[o + 4] = r;
        edgeScratch[o + 5] = g;
        edgeScratch[o + 6] = b;
        edgeScratch[o + 7] = a * fade;
        w += 1;
    };

    for (let i = 0; i < grid.length; i++) {
        const ln = grid[i];
        writeSeg(ln.x1, ln.y1, ln.z1, ln.x2, ln.y2, ln.z2, gridColor[0], gridColor[1], gridColor[2], gridColor[3], true);
    }
    for (let i = 0; i < srcEdgeCount; i++) {
        const o = i * EDGE_STRIDE;
        const a = layoutToSphere(srcEdges[o], srcEdges[o + 1], layoutScale);
        const b = layoutToSphere(srcEdges[o + 2], srcEdges[o + 3], layoutScale);
        writeSeg(a.x, a.y, a.z, b.x, b.y, b.z, srcEdges[o + 4], srcEdges[o + 5], srcEdges[o + 6], srcEdges[o + 7] || 0.45, false);
    }

    return {
        nodes: nodeScratch.subarray(0, nodeNeed),
        edges: edgeScratch.subarray(0, w * EDGE_STRIDE),
        pick,
        projected,
        layoutScale,
        camera: { x: 0, y: 0, zoom: 1 },
    };
}

/**
 * Nearest front-facing node under a CSS point.
 * @param {{id:string,sx:number,sy:number,size:number}[]} pick
 * @param {number} cssX
 * @param {number} cssY
 * @param {number} [pad]
 */
export function pickPlanetNode(pick, cssX, cssY, pad = 10) {
    if (!Array.isArray(pick) || !pick.length) return null;
    let best = null;
    let bestD = Infinity;
    for (let i = 0; i < pick.length; i++) {
        const n = pick[i];
        const d = Math.hypot((n.sx || 0) - cssX, (n.sy || 0) - cssY);
        const hit = Math.max(n.size || 10, pad);
        if (d <= hit && d < bestD) {
            bestD = d;
            best = n.id;
        }
    }
    return best;
}
