// SPDX-License-Identifier: 0BSD

/**
 * Planet view for the WebGL network visualiser.
 * Each interface is a globe around the local node. Peers sit on the
 * interface they use. Pixel draw stays in the 2D WebGL path.
 */

import { EDGE_STRIDE, NODE_STRIDE } from "./networkVisualiserWebGL.js";

export const PLANET_VIEW = "planet";
export const FLAT_VIEW = "flat";

export const PLANET_FOV_Y = (48 * Math.PI) / 180;
export const PLANET_NEAR = 0.18;
export const PLANET_FAR = 40;
export const PLANET_DIST_MIN = 2.6;
export const PLANET_DIST_MAX = 16;
export const PLANET_PITCH_LIMIT = 1.18;
export const DEFAULT_ORBIT_YAW = 0.62;
export const DEFAULT_ORBIT_PITCH = 0.38;
export const DEFAULT_ORBIT_DIST = 6.2;
export const LAYOUT_SCALE_FLOOR = 160;
/** Scale above max layout radius so the farthest node stays on the back hemisphere. */
export const LAYOUT_SCALE_FIT = 1.05;
/** Minimum wrap scale. A large floor piles a tight cluster onto the front pole. */
export const PLANET_CLUSTER_SCALE_FLOOR = 48;
export const PLANET_RADIUS_MIN = 0.5;
export const PLANET_RADIUS_MAX = 2.65;
export const PLANET_HUB_GAP = 0.42;
/** Keep a peer on its globe unless another interface is this much closer. */
export const PLANET_HOME_STICKY = 48;
const CLIP_W_MIN = 1e-3;
const SCALE_HOLD_LO = 0.72;
const SCALE_HOLD_HI = 1.35;
const GOLDEN_ANGLE = 2.399963229728653;

export const PLANET_KIND_ME = 0;
export const PLANET_KIND_IFACE_ON = 1;
export const PLANET_KIND_IFACE_OFF = 2;
export const PLANET_KIND_PEER = 3;
export const PLANET_KIND_DISCOVERED = 4;

const ringSegs = 64;

const PLANET_PALETTE = [
    [0.2, 0.48, 0.78],
    [0.14, 0.58, 0.5],
    [0.48, 0.34, 0.7],
    [0.7, 0.42, 0.18],
    [0.22, 0.55, 0.34],
    [0.66, 0.26, 0.36],
    [0.22, 0.4, 0.56],
    [0.55, 0.52, 0.2],
];

/** @type {Map<string, {x1:number,y1:number,z1:number,x2:number,y2:number,z2:number}[]>} */
const globeGridCache = new Map();

let nodeScratch = new Float32Array(0);
let edgeScratch = new Float32Array(0);
const clipA: any = { x: 0, y: 0, z: 0, w: 0 };
const clipB: any = { x: 0, y: 0, z: 0, w: 0 };
let spriteScratch = [];
let worldScratch = [];

/**
 * @param {unknown} raw
 * @returns {"flat"|"planet"}
 */
export function normalizeVisualiserViewMode(raw) {
    return raw === PLANET_VIEW ? PLANET_VIEW : FLAT_VIEW;
}

/**
 * @param {number} kind
 */
export function isPlanetInterfaceKind(kind) {
    return kind === PLANET_KIND_IFACE_ON || kind === PLANET_KIND_IFACE_OFF || kind === PLANET_KIND_DISCOVERED;
}

/**
 * @param {number} planetCount
 * @param {number} [maxPlanetRadius]
 */
export function orbitDistFloor(planetCount, maxPlanetRadius) {
    const hub = hubRadiusForPlanetCount(planetCount, maxPlanetRadius);
    const r = maxPlanetRadius > 0 ? maxPlanetRadius : PLANET_RADIUS_MIN;
    return Math.max(PLANET_DIST_MIN, hub + r + 1.15);
}

/**
 * @param {number} planetCount
 * @param {number} [maxPlanetRadius]
 */
export function orbitDistCeiling(planetCount, maxPlanetRadius) {
    const floor = orbitDistFloor(planetCount, maxPlanetRadius);
    return Math.max(PLANET_DIST_MAX, floor + 8);
}

export function clampOrbit(yaw, pitch, dist, planetCount, maxPlanetRadius) {
    let y = Number.isFinite(yaw) ? yaw : DEFAULT_ORBIT_YAW;
    let p = Number.isFinite(pitch) ? pitch : DEFAULT_ORBIT_PITCH;
    if (p < -PLANET_PITCH_LIMIT) p = -PLANET_PITCH_LIMIT;
    if (p > PLANET_PITCH_LIMIT) p = PLANET_PITCH_LIMIT;
    let d = Number.isFinite(dist) && dist > 0 ? dist : DEFAULT_ORBIT_DIST;
    const minD = planetCount != null ? orbitDistFloor(planetCount, maxPlanetRadius) : PLANET_DIST_MIN;
    const maxD = planetCount != null ? orbitDistCeiling(planetCount, maxPlanetRadius) : PLANET_DIST_MAX;
    if (d < minD) d = minD;
    if (d > maxD) d = maxD;
    return { yaw: y, pitch: p, dist: d };
}

/**
 * Max layout radius used to wrap a cluster onto a sphere.
 * @param {Float32Array|number[]|null|undefined} nodes
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

export function orbitEye(yaw, pitch, dist) {
    const cp = Math.cos(pitch);
    return {
        x: dist * cp * Math.sin(yaw),
        y: dist * Math.sin(pitch),
        z: dist * cp * Math.cos(yaw),
    };
}

export function cameraBasis(eye) {
    const fl = Math.hypot(eye.x, eye.y, eye.z) || 1;
    const forward: any = { x: -eye.x / fl, y: -eye.y / fl, z: -eye.z / fl };
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
    const right: any = { x: cx / rl, y: cy / rl, z: cz / rl };
    const up: any = {
        x: right.y * forward.z - right.z * forward.y,
        y: right.z * forward.x - right.x * forward.z,
        z: right.x * forward.y - right.y * forward.x,
    };
    return { forward, right, up };
}

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

export function transformPoint(m, x, y, z, out) {
    const dest = out || { x: 0, y: 0, z: 0, w: 0 };
    dest.x = m[0] * x + m[4] * y + m[8] * z + m[12];
    dest.y = m[1] * x + m[5] * y + m[9] * z + m[13];
    dest.z = m[2] * x + m[6] * y + m[10] * z + m[14];
    dest.w = m[3] * x + m[7] * y + m[11] * z + m[15];
    return dest;
}

/**
 * Front of a unit sphere at the origin when dot(p, eye) > 1.
 */
export function sphereFacing(px, py, pz, eye) {
    return px * eye.x + py * eye.y + pz * eye.z - 1;
}

/**
 * Front of a sphere at C with radius R. n is the unit local point.
 */
export function sphereFacingAt(nx, ny, nz, eye, cx, cy, cz, radius) {
    const r = radius > 1e-6 ? radius : 1;
    return nx * (eye.x - cx) + ny * (eye.y - cy) + nz * (eye.z - cz) - r;
}

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
 * Clip a clip-space segment so both ends have w >= wMin.
 * Drops segments entirely behind the camera.
 */
export function clipLineToPositiveW(c1, c2, wMin = CLIP_W_MIN) {
    if (!c1 || !c2) return null;
    const minW = wMin > 0 ? wMin : CLIP_W_MIN;
    const aIn = c1.w >= minW;
    const bIn = c2.w >= minW;
    if (aIn && bIn) {
        return { x1: c1.x, y1: c1.y, w1: c1.w, x2: c2.x, y2: c2.y, w2: c2.w };
    }
    if (!aIn && !bIn) return null;
    const dw = c2.w - c1.w;
    if (!(Math.abs(dw) > 1e-12)) return null;
    const t = (minW - c1.w) / dw;
    if (!Number.isFinite(t) || t < 0 || t > 1) return null;
    const mx = c1.x + (c2.x - c1.x) * t;
    const my = c1.y + (c2.y - c1.y) * t;
    if (!aIn) {
        return { x1: mx, y1: my, w1: minW, x2: c2.x, y2: c2.y, w2: c2.w };
    }
    return { x1: c1.x, y1: c1.y, w1: c1.w, x2: mx, y2: my, w2: minW };
}

export function stabilizeLayoutScale(computed, prev) {
    const next = computed > 1e-6 ? computed : PLANET_CLUSTER_SCALE_FLOOR;
    if (!(prev > 1e-6)) return next;
    const ratio = next / prev;
    if (ratio >= SCALE_HOLD_LO && ratio <= SCALE_HOLD_HI) return prev;
    return prev * 0.55 + next * 0.45;
}

export function screenToDrawWorld(sx, sy, width, height) {
    return { x: sx - width * 0.5, y: sy - height * 0.5 };
}

export function projectedSphereRadiusPx(dist, fovY, height) {
    const d = Math.max(dist, 1.001);
    const ang = Math.asin(Math.min(0.999, 1 / d));
    const half = Math.tan(fovY * 0.5);
    if (!(half > 0)) return height * 0.25;
    return (Math.tan(ang) / half) * (height * 0.5);
}

export function planetLodZoom(dist) {
    const d = dist > 0.2 ? dist : DEFAULT_ORBIT_DIST;
    return DEFAULT_ORBIT_DIST / d;
}

function sph(lon, lat) {
    const cl = Math.cos(lat);
    return { x: cl * Math.cos(lon), y: Math.sin(lat), z: cl * Math.sin(lon) };
}

export function buildGlobeGrid(meridianCount = 12, parallelCount = 5, segs = 12) {
    const m = Math.max(4, meridianCount | 0);
    const p = Math.max(2, parallelCount | 0);
    const g = Math.max(6, segs | 0);
    const key = `${m}:${p}:${g}`;
    const cached = globeGridCache.get(key);
    if (cached) return cached;
    const lines = [];
    for (let i = 0; i < m; i++) {
        const lon = (i / m) * Math.PI * 2;
        let prev = null;
        for (let s = 0; s <= g; s++) {
            const lat = Math.PI / 2 - (s / g) * Math.PI;
            const pt = sph(lon, lat);
            if (prev) {
                lines.push({ x1: prev.x, y1: prev.y, z1: prev.z, x2: pt.x, y2: pt.y, z2: pt.z });
            }
            prev = pt;
        }
    }
    for (let j = 1; j <= p; j++) {
        const lat = Math.PI / 2 - (j / (p + 1)) * Math.PI;
        let prev = null;
        const first = sph(0, lat);
        for (let s = 1; s <= g; s++) {
            const lon = (s / g) * Math.PI * 2;
            const pt = s === g ? first : sph(lon, lat);
            if (prev) {
                lines.push({ x1: prev.x, y1: prev.y, z1: prev.z, x2: pt.x, y2: pt.y, z2: pt.z });
            }
            prev = pt;
        }
    }
    globeGridCache.set(key, lines);
    return lines;
}

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
 * Ray vs sphere at C with radius R.
 */
export function raySphereAt(origin, dir, cx, cy, cz, radius) {
    const hit = raySphere({ x: origin.x - cx, y: origin.y - cy, z: origin.z - cz }, dir, radius);
    if (!hit) return null;
    return { x: hit.x + cx, y: hit.y + cy, z: hit.z + cz, t: hit.t };
}

export function hubRadiusForPlanetCount(n, maxPlanetRadius) {
    const c = Math.max(1, n | 0);
    const r = maxPlanetRadius > 0 ? maxPlanetRadius : PLANET_RADIUS_MIN;
    if (c <= 1) return 1.35 + r;
    const minCenterDist = 2 * r + PLANET_HUB_GAP;
    const ring = minCenterDist / (2 * Math.sin(Math.PI / c));
    return Math.max(1.35 + r, ring);
}

export function planetRadiusForPeers(n) {
    const c = Math.max(0, n | 0);
    return Math.min(PLANET_RADIUS_MAX, PLANET_RADIUS_MIN + 0.11 * Math.sqrt(c));
}

/**
 * Centers for n interface planets on a ring around the origin.
 * First planet sits on +X so the local node stays visible on camera +Z.
 */
export function placePlanetCenters(count, maxPlanetRadius) {
    const n = Math.max(0, count | 0);
    const R = hubRadiusForPlanetCount(n, maxPlanetRadius);
    const out = [];
    for (let i = 0; i < n; i++) {
        const ang = n === 1 ? 0 : (i / n) * Math.PI * 2;
        out.push({
            cx: R * Math.cos(ang),
            cy: n === 1 ? 0.12 : 0.16 * Math.sin(i * 2.15 + 0.35),
            cz: R * Math.sin(ang),
        });
    }
    return out;
}

function tangentBasis(nx, ny, nz) {
    let rx = 0;
    let ry = 1;
    let rz = 0;
    if (Math.abs(ny) > 0.92) {
        rx = 1;
        ry = 0;
    }
    let cx = ny * rz - nz * ry;
    let cy = nz * rx - nx * rz;
    let cz = nx * ry - ny * rx;
    let rl = Math.hypot(cx, cy, cz) || 1;
    cx /= rl;
    cy /= rl;
    cz /= rl;
    return {
        rx: cx,
        ry: cy,
        rz: cz,
        ux: cy * nz - cz * ny,
        uy: cz * nx - cx * nz,
        uz: cx * ny - cy * nx,
    };
}

function setUnit(p, x, y, z) {
    const len = Math.hypot(x, y, z) || 1;
    p.x = x / len;
    p.y = y / len;
    p.z = z / len;
}

/**
 * Minimum angular gap for n points on a unit sphere.
 * @param {number} n
 */
export function planetMinAngle(n) {
    const c = Math.max(1, n | 0);
    return Math.min(0.52, 1.38 / Math.sqrt(c));
}

/**
 * Unstick stacked unit-sphere points and push near neighbors apart.
 * Deterministic. Uses a golden-angle cap for coincident groups.
 *
 * @param {{x:number,y:number,z:number}[]} points
 * @param {number} minAngle
 */
export function spreadSphereLocals(points, minAngle) {
    const n = points && points.length ? points.length : 0;
    if (n < 2 || !(minAngle > 1e-4)) return points;
    const quant = 2500;
    const groups = new Map();
    for (let i = 0; i < n; i++) {
        const p = points[i];
        const key = `${Math.round(p.x * quant)}:${Math.round(p.y * quant)}:${Math.round(p.z * quant)}`;
        let g = groups.get(key);
        if (!g) {
            g = [];
            groups.set(key, g);
        }
        g.push(i);
    }
    for (const g of groups.values()) {
        if (g.length < 2) return;
        const mean = points[g[0]];
        const b = tangentBasis(mean.x, mean.y, mean.z);
        const cap = Math.min(0.78, minAngle * Math.sqrt(g.length));
        const m = g.length;
        for (let k = 0; k < m; k++) {
            const t = (k + 0.5) / m;
            const phiOff = cap * Math.sqrt(t);
            const th = k * GOLDEN_ANGLE;
            const sp = Math.sin(phiOff);
            const cp = Math.cos(phiOff);
            const ca = Math.cos(th);
            const sa = Math.sin(th);
            setUnit(
                points[g[k]],
                mean.x * cp + (b.rx * ca + b.ux * sa) * sp,
                mean.y * cp + (b.ry * ca + b.uy * sa) * sp,
                mean.z * cp + (b.rz * ca + b.uz * sa) * sp
            );
        }
    }

    const minDot = Math.cos(Math.min(minAngle, Math.PI * 0.45));
    const cell = Math.max(minAngle, 0.14);
    const iters = n > 220 ? 2 : 3;
    const push = 0.32;
    for (let iter = 0; iter < iters; iter++) {
        const buckets = new Map();
        for (let i = 0; i < n; i++) {
            const p = points[i];
            const theta = Math.atan2(p.y, p.x);
            const phi = Math.acos(Math.max(-1, Math.min(1, p.z)));
            const kx = Math.floor(theta / cell);
            const ky = Math.floor(phi / cell);
            const key = kx * 100003 + ky;
            let list = buckets.get(key);
            if (!list) {
                list = [];
                buckets.set(key, list);
            }
            list.push(i);
        }
        for (let i = 0; i < n; i++) {
            const a = points[i];
            const theta = Math.atan2(a.y, a.x);
            const phi = Math.acos(Math.max(-1, Math.min(1, a.z)));
            const kx = Math.floor(theta / cell);
            const ky = Math.floor(phi / cell);
            let fx = 0;
            let fy = 0;
            let fz = 0;
            for (let dx = -1; dx <= 1; dx++) {
                for (let dy = -1; dy <= 1; dy++) {
                    const list = buckets.get((kx + dx) * 100003 + (ky + dy));
                    if (!list) continue;
                    for (let li = 0; li < list.length; li++) {
                        const j = list[li];
                        if (j === i) continue;
                        const b = points[j];
                        const dot = a.x * b.x + a.y * b.y + a.z * b.z;
                        if (dot < minDot) continue;
                        const overlap = (dot - minDot) / (1 - minDot + 1e-6);
                        fx += (a.x - b.x) * overlap;
                        fy += (a.y - b.y) * overlap;
                        fz += (a.z - b.z) * overlap;
                    }
                }
            }
            if (fx === 0 && fy === 0 && fz === 0) continue;
            const tdot = fx * a.x + fy * a.y + fz * a.z;
            setUnit(a, a.x + (fx - tdot * a.x) * push, a.y + (fy - tdot * a.y) * push, a.z + (fz - tdot * a.z) * push);
        }
    }
    return points;
}

function kindOf(i, kindByIndex, idByIndex) {
    if (kindByIndex && kindByIndex[i] != null && kindByIndex[i] !== "") {
        return kindByIndex[i] | 0;
    }
    const id = idByIndex && idByIndex[i] != null ? String(idByIndex[i]) : "";
    if (id === "me") return PLANET_KIND_ME;
    return PLANET_KIND_PEER;
}

/**
 * Map each node to an interface planet. Me is the hub (home -1).
 * With no interfaces, leftover peers share one fallback planet.
 *
 * @returns {{
 *   ifaceIndices: number[],
 *   home: Int16Array,
 *   fallback: boolean,
 * }}
 */
export function assignPlanetHomes(srcCount, kindByIndex, idByIndex, nodes, prevHomeById) {
    const home = new Int16Array(srcCount);
    const ifaceIndices = [];
    for (let i = 0; i < srcCount; i++) {
        home[i] = -1;
        const k = kindOf(i, kindByIndex, idByIndex);
        if (isPlanetInterfaceKind(k)) {
            home[i] = ifaceIndices.length;
            ifaceIndices.push(i);
        }
    }
    const homeById = Object.create(null);
    if (ifaceIndices.length === 0) {
        for (let i = 0; i < srcCount; i++) {
            const k = kindOf(i, kindByIndex, idByIndex);
            if (k !== PLANET_KIND_ME) home[i] = 0;
        }
        return { ifaceIndices, home, fallback: true, homeById };
    }
    const ifaceIdOf = (planetIndex) => {
        const ii = ifaceIndices[planetIndex];
        return ii == null || idByIndex[ii] == null ? "" : String(idByIndex[ii]);
    };
    for (let i = 0; i < srcCount; i++) {
        const k = kindOf(i, kindByIndex, idByIndex);
        if (k === PLANET_KIND_ME || isPlanetInterfaceKind(k)) continue;
        const o = i * NODE_STRIDE;
        const x = nodes[o] || 0;
        const y = nodes[o + 1] || 0;
        let best = 0;
        let bestD = Infinity;
        for (let p = 0; p < ifaceIndices.length; p++) {
            const io = ifaceIndices[p] * NODE_STRIDE;
            const d = Math.hypot(x - (nodes[io] || 0), y - (nodes[io + 1] || 0));
            if (d < bestD) {
                bestD = d;
                best = p;
            }
        }
        const id = idByIndex[i] != null ? String(idByIndex[i]) : "";
        const prevIfaceId = id && prevHomeById ? prevHomeById[id] : "";
        if (prevIfaceId) {
            for (let p = 0; p < ifaceIndices.length; p++) {
                if (ifaceIdOf(p) !== String(prevIfaceId)) continue;
                const io = ifaceIndices[p] * NODE_STRIDE;
                const prevD = Math.hypot(x - (nodes[io] || 0), y - (nodes[io + 1] || 0));
                if (prevD <= bestD + PLANET_HOME_STICKY) {
                    best = p;
                }
                break;
            }
        }
        home[i] = best;
        if (id) homeById[id] = ifaceIdOf(best);
    }
    for (let p = 0; p < ifaceIndices.length; p++) {
        const ii = ifaceIndices[p];
        const id = idByIndex[ii] != null ? String(idByIndex[ii]) : "";
        if (id) homeById[id] = id;
    }
    return { ifaceIndices, home, fallback: false, homeById };
}

function paletteForId(id, offline, dark) {
    const s = String(id || "");
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    const base = PLANET_PALETTE[Math.abs(h) % PLANET_PALETTE.length];
    const dim = offline ? 0.48 : 1;
    const lift = dark ? 0.0 : 0.12;
    return [Math.min(1, base[0] * dim + lift), Math.min(1, base[1] * dim + lift), Math.min(1, base[2] * dim + lift)];
}

/**
 * Nearest planet hit, or null.
 * @param {{cx:number,cy:number,cz:number,radius:number}[]} planets
 */
export function raycastPlanets(cssX, cssY, width, height, eye, planets) {
    if (!Array.isArray(planets) || !planets.length) return null;
    const ray = screenRay(cssX, cssY, width, height, eye);
    let best = null;
    for (let i = 0; i < planets.length; i++) {
        const p = planets[i];
        const hit = raySphereAt(ray.origin, ray.dir, p.cx, p.cy, p.cz, p.radius);
        if (!hit) continue;
        if (!best || hit.t < best.t) {
            best = { ...hit, planetIndex: i };
        }
    }
    return best;
}

/**
 * 2D layout under a planet-mode pointer, or null if the ray misses.
 * With planets, the hit maps onto that interface cluster.
 */
export function pointerToLayout(cssX, cssY, width, height, eye, layoutScale, planets) {
    if (Array.isArray(planets) && planets.length) {
        const hit = raycastPlanets(cssX, cssY, width, height, eye, planets);
        if (!hit) return null;
        const p = planets[hit.planetIndex];
        const r = p.radius > 1e-6 ? p.radius : 1;
        const off = sphereToLayout((hit.x - p.cx) / r, (hit.y - p.cy) / r, (hit.z - p.cz) / r, p.layoutScale);
        return { x: (p.originX || 0) + off.x, y: (p.originY || 0) + off.y, planetIndex: hit.planetIndex };
    }
    const ray = screenRay(cssX, cssY, width, height, eye);
    const hit = raySphere(ray.origin, ray.dir, 1);
    if (!hit) return null;
    return sphereToLayout(hit.x, hit.y, hit.z, layoutScale);
}

export function layoutToWasmScreen(lx, ly, width, height, cam = null) {
    const zoom = cam?.zoom > 0 ? cam.zoom : 1;
    return {
        x: (lx - (cam?.x || 0)) * zoom + width * 0.5,
        y: (ly - (cam?.y || 0)) * zoom + height * 0.5,
    };
}

function localScaleForPlanet(nodes, srcCount, home, planetIndex, ifaceIndex, fallback) {
    let maxR = 0;
    const ox = fallback || ifaceIndex < 0 ? 0 : nodes[ifaceIndex * NODE_STRIDE] || 0;
    const oy = fallback || ifaceIndex < 0 ? 0 : nodes[ifaceIndex * NODE_STRIDE + 1] || 0;
    for (let i = 0; i < srcCount; i++) {
        if (home[i] !== planetIndex) continue;
        const kOff = i * NODE_STRIDE;
        const r = Math.hypot((nodes[kOff] || 0) - ox, (nodes[kOff + 1] || 0) - oy);
        if (r > maxR) maxR = r;
    }
    return Math.max(maxR * LAYOUT_SCALE_FIT, PLANET_CLUSTER_SCALE_FLOOR);
}

function posKey(x, y) {
    return (Math.round(x * 2) + 500000) * 1000003 + (Math.round(y * 2) + 500000);
}

function buildNodePosIndex(nodes, count) {
    const map = new Map();
    for (let n = 0; n < count; n++) {
        const o = n * NODE_STRIDE;
        const key = posKey(nodes[o] || 0, nodes[o + 1] || 0);
        let list = map.get(key);
        if (!list) {
            list = [];
            map.set(key, list);
        }
        list.push(n);
    }
    return map;
}

function nearestNodeAt(map, x, y, nodes, maxD) {
    const kx = Math.round(x * 2);
    const ky = Math.round(y * 2);
    let best = -1;
    let bestD = maxD;
    for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
            const list = map.get((kx + dx + 500000) * 1000003 + (ky + dy + 500000));
            if (!list) continue;
            for (let li = 0; li < list.length; li++) {
                const n = list[li];
                const o = n * NODE_STRIDE;
                const d = Math.hypot((nodes[o] || 0) - x, (nodes[o + 1] || 0) - y);
                if (d < bestD) {
                    bestD = d;
                    best = n;
                }
            }
        }
    }
    return best;
}

function takeWorld(i) {
    let w = worldScratch[i];
    if (!w) {
        w = { x: 0, y: 0, z: 0, nx: 0, ny: 0, nz: 1, planet: -1 };
        worldScratch[i] = w;
    }
    return w;
}

function setWorld(i, x, y, z, nx, ny, nz, planet) {
    const w = takeWorld(i);
    w.x = x;
    w.y = y;
    w.z = z;
    w.nx = nx;
    w.ny = ny;
    w.nz = nz;
    w.planet = planet;
    return w;
}

function takeSprite(i) {
    let s = spriteScratch[i];
    if (!s) {
        s = {
            x: 0,
            y: 0,
            z: 0,
            size: 0,
            r: 0,
            g: 0,
            b: 0,
            a: 0,
            useTex: 0,
            u: 0,
            v: 0,
            sx: 0,
            sy: 0,
            ok: true,
        };
        spriteScratch[i] = s;
    }
    return s;
}

/**
 * Project the 2D graph onto per-interface globes.
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
 *   kindByIndex?: (number|null|undefined)[],
 *   prevPlanets?: {id?:string,layoutScale?:number}[],
 *   prevHomeById?: Record<string, string>,
 * }} opts
 */
export function projectPlanetScene(opts) {
    const width = Math.max(1, opts?.width || 1);
    const height = Math.max(1, opts?.height || 1);
    const srcNodes = opts?.nodes;
    const srcCount = srcNodes && srcNodes.length ? Math.floor(srcNodes.length / NODE_STRIDE) : 0;
    const idByIndex = opts?.idByIndex || [];
    const kindByIndex = opts?.kindByIndex || [];
    const dark = opts?.dark === true;
    const srcEdges = opts?.edges;
    const srcEdgeCount = srcEdges && srcEdges.length ? Math.floor(srcEdges.length / EDGE_STRIDE) : 0;
    const prevPlanets = Array.isArray(opts?.prevPlanets) ? opts.prevPlanets : [];
    const prevScaleById = Object.create(null);
    for (let i = 0; i < prevPlanets.length; i++) {
        const pl = prevPlanets[i];
        if (pl?.id) prevScaleById[String(pl.id)] = pl.layoutScale;
    }

    const assigned = assignPlanetHomes(srcCount, kindByIndex, idByIndex, srcNodes, opts?.prevHomeById);
    const planetCount = assigned.fallback ? (srcCount > 1 ? 1 : 0) : assigned.ifaceIndices.length;
    const memberCounts = new Array(Math.max(planetCount, 1)).fill(0);
    for (let i = 0; i < srcCount; i++) {
        const h = assigned.home[i];
        if (h >= 0 && h < memberCounts.length) memberCounts[h] += 1;
    }
    let maxPlanetR = PLANET_RADIUS_MIN;
    const radii = new Array(planetCount);
    for (let p = 0; p < planetCount; p++) {
        radii[p] = planetRadiusForPeers(Math.max(0, memberCounts[p] - (assigned.fallback ? 0 : 1)));
        if (radii[p] > maxPlanetR) maxPlanetR = radii[p];
    }
    const orbit = clampOrbit(
        opts?.yaw ?? DEFAULT_ORBIT_YAW,
        opts?.pitch ?? DEFAULT_ORBIT_PITCH,
        opts?.dist ?? DEFAULT_ORBIT_DIST,
        planetCount,
        maxPlanetR
    );
    const hub = hubRadiusForPlanetCount(Math.max(planetCount, 1), maxPlanetR);
    const eye = orbitEye(orbit.yaw, orbit.pitch, orbit.dist);
    const view = lookAtOrigin(eye);
    const far = Math.max(PLANET_FAR, orbit.dist + hub + maxPlanetR + 8);
    const proj = perspective(PLANET_FOV_Y, width / height, PLANET_NEAR, far);
    const viewProj = mat4Multiply(proj, view);
    const centers = placePlanetCenters(planetCount, maxPlanetR);

    const planets = [];
    for (let p = 0; p < planetCount; p++) {
        const ifaceIndex = assigned.fallback ? -1 : assigned.ifaceIndices[p];
        const c = centers[p] || { cx: 1.7, cy: 0.1, cz: 0 };
        const radius = radii[p];
        const originX = ifaceIndex >= 0 ? srcNodes[ifaceIndex * NODE_STRIDE] || 0 : 0;
        const originY = ifaceIndex >= 0 ? srcNodes[ifaceIndex * NODE_STRIDE + 1] || 0 : 0;
        const id = ifaceIndex >= 0 && idByIndex[ifaceIndex] != null ? String(idByIndex[ifaceIndex]) : `planet-${p}`;
        const kind = ifaceIndex >= 0 ? kindOf(ifaceIndex, kindByIndex, idByIndex) : PLANET_KIND_IFACE_ON;
        const offline = kind === PLANET_KIND_IFACE_OFF || kind === PLANET_KIND_DISCOVERED;
        planets.push({
            cx: c.cx,
            cy: c.cy,
            cz: c.cz,
            radius,
            originX,
            originY,
            layoutScale: stabilizeLayoutScale(
                localScaleForPlanet(srcNodes, srcCount, assigned.home, p, ifaceIndex, assigned.fallback),
                prevScaleById[id]
            ),
            ifaceIndex,
            id,
            fill: paletteForId(id, offline, dark),
            offline,
        });
    }

    for (let i = 0; i < srcCount; i++) {
        const k = kindOf(i, kindByIndex, idByIndex);
        if (k === PLANET_KIND_ME) {
            setWorld(i, 0, 0, 0, 0, 0, 1, -1);
            continue;
        }
        const p = planets[assigned.home[i]];
        if (!p) {
            setWorld(i, 0, 0, 0, 0, 0, 1, -1);
            continue;
        }
        if (!assigned.fallback && i === p.ifaceIndex) {
            setWorld(i, p.cx, p.cy, p.cz, 0, 0, 1, assigned.home[i]);
            continue;
        }
        const o = i * NODE_STRIDE;
        const local = layoutToSphere((srcNodes[o] || 0) - p.originX, (srcNodes[o + 1] || 0) - p.originY, p.layoutScale);
        setWorld(
            i,
            p.cx + local.x * p.radius,
            p.cy + local.y * p.radius,
            p.cz + local.z * p.radius,
            local.x,
            local.y,
            local.z,
            assigned.home[i]
        );
    }

    for (let p = 0; p < planetCount; p++) {
        const idxs = [];
        const locals = [];
        const pl = planets[p];
        for (let i = 0; i < srcCount; i++) {
            if (assigned.home[i] !== p) continue;
            if (!assigned.fallback && i === pl.ifaceIndex) continue;
            if (kindOf(i, kindByIndex, idByIndex) === PLANET_KIND_ME) continue;
            idxs.push(i);
            const w = worldScratch[i];
            locals.push({ x: w.nx, y: w.ny, z: w.nz });
        }
        if (locals.length < 2) continue;
        spreadSphereLocals(locals, planetMinAngle(locals.length));
        for (let k = 0; k < idxs.length; k++) {
            const loc = locals[k];
            setWorld(
                idxs[k],
                pl.cx + loc.x * pl.radius,
                pl.cy + loc.y * pl.radius,
                pl.cz + loc.z * pl.radius,
                loc.x,
                loc.y,
                loc.z,
                p
            );
        }
    }

    let spriteCount = 0;
    const addSprite = (wx, wy, wz, size, r, g, b, a, useTex, u, v) => {
        const clip = transformPoint(viewProj, wx, wy, wz, clipA);
        const screen = clipToScreen(clip.x, clip.y, clip.w, width, height);
        if (!screen.ok && clip.w <= 0) return null;
        const draw = screenToDrawWorld(screen.x, screen.y, width, height);
        const viewZ = Math.hypot(wx - eye.x, wy - eye.y, wz - eye.z);
        const spr = takeSprite(spriteCount);
        spriteCount += 1;
        spr.x = draw.x;
        spr.y = draw.y;
        spr.z = viewZ;
        spr.size = size;
        spr.r = r;
        spr.g = g;
        spr.b = b;
        spr.a = a;
        spr.useTex = useTex;
        spr.u = u;
        spr.v = v;
        spr.sx = screen.x;
        spr.sy = screen.y;
        spr.ok = screen.ok;
        return spr;
    };

    for (let p = 0; p < planets.length; p++) {
        const pl = planets[p];
        const dist = Math.hypot(pl.cx - eye.x, pl.cy - eye.y, pl.cz - eye.z);
        const pxR = Math.max(18, projectedSphereRadiusPx(Math.max(dist, 1.05), PLANET_FOV_Y, height) * pl.radius);
        const fill = pl.fill;
        const bodyA = dark ? 0.9 : 0.92;
        addSprite(pl.cx, pl.cy, pl.cz, pxR * 1.08, fill[0], fill[1], fill[2], 0.14, 0, 0, 0);
        addSprite(
            pl.cx,
            pl.cy,
            pl.cz,
            pxR,
            fill[0] * 0.35 + (dark ? 0.04 : 0.55),
            fill[1] * 0.4 + (dark ? 0.08 : 0.62),
            fill[2] * 0.5 + (dark ? 0.14 : 0.7),
            bodyA,
            0,
            0,
            0
        );
    }

    addSprite(0, 0, 0, 22, dark ? 0.95 : 0.9, dark ? 0.78 : 0.62, dark ? 0.28 : 0.16, 0.22, 0, 0, 0);

    const projected = new Array(srcCount);
    const pick = [];
    for (let i = 0; i < srcCount; i++) {
        const w = worldScratch[i];
        const o = i * NODE_STRIDE;
        const k = kindOf(i, kindByIndex, idByIndex);
        const pl = w.planet >= 0 ? planets[w.planet] : null;
        let facing = 1;
        if (pl && k !== PLANET_KIND_ME && i !== pl.ifaceIndex) {
            facing = sphereFacingAt(w.nx, w.ny, w.nz, eye, pl.cx, pl.cy, pl.cz, pl.radius);
        }
        const viewZ = Math.hypot(w.x - eye.x, w.y - eye.y, w.z - eye.z);
        const persp = Math.max(0.4, Math.min(2.2, 3.2 / Math.max(viewZ, 0.25)));
        let size = Math.max(7, (srcNodes[o + 2] || 18) * persp);
        if (k === PLANET_KIND_ME) size = Math.max(size, 20);
        if (isPlanetInterfaceKind(k)) size = Math.max(size, 16);
        else if (pl) {
            const crowd = Math.max(1, memberCounts[w.planet] - (assigned.fallback ? 0 : 1));
            if (crowd > 12) size *= Math.max(0.5, Math.sqrt(12 / crowd));
        }
        const front = facing > 0;
        const a = front ? srcNodes[o + 6] || 1 : Math.max(0.1, (srcNodes[o + 6] || 1) * 0.2);
        const spr = addSprite(
            w.x,
            w.y,
            w.z,
            front ? size : size * 0.55,
            srcNodes[o + 3],
            srcNodes[o + 4],
            srcNodes[o + 5],
            a,
            front ? srcNodes[o + 7] : 0,
            srcNodes[o + 8],
            srcNodes[o + 9]
        );
        const rec: any = {
            sx: spr ? spr.sx : 0,
            sy: spr ? spr.sy : 0,
            size,
            facing,
            front: front && (!spr || spr.ok),
            kind: k,
        };
        projected[i] = rec;
        const id = idByIndex[i];
        if (rec.front && id) {
            pick.push({ id: String(id), sx: rec.sx, sy: rec.sy, size: rec.size });
        }
    }

    const drawnSprites = spriteScratch.slice(0, spriteCount);
    drawnSprites.sort((a, b) => b.z - a.z);
    const nodeNeed = spriteCount * NODE_STRIDE;
    if (nodeScratch.length < nodeNeed) {
        nodeScratch = new Float32Array(nodeNeed);
    }
    for (let s = 0; s < spriteCount; s++) {
        const d = s * NODE_STRIDE;
        const n = drawnSprites[s];
        nodeScratch[d] = n.x;
        nodeScratch[d + 1] = n.y;
        nodeScratch[d + 2] = n.size;
        nodeScratch[d + 3] = n.r;
        nodeScratch[d + 4] = n.g;
        nodeScratch[d + 5] = n.b;
        nodeScratch[d + 6] = n.a;
        nodeScratch[d + 7] = n.useTex;
        nodeScratch[d + 8] = n.u;
        nodeScratch[d + 9] = n.v;
    }

    const denseGrid = srcCount < 90 && planetCount < 6 && orbit.dist < 8.5;
    const grid = denseGrid ? buildGlobeGrid(12, 5, 12) : buildGlobeGrid(8, 3, 8);
    const edgeNeed = (planets.length * (grid.length + 8) + srcEdgeCount + ringSegs + planetCount) * EDGE_STRIDE;
    if (edgeScratch.length < edgeNeed) {
        edgeScratch = new Float32Array(Math.max(edgeNeed, 64));
    }
    let w = 0;
    const maxSeg = 1.5 * Math.hypot(width, height);
    const writeWorldSeg = (x1, y1, z1, x2, y2, z2, r, g, b, a, requireFront, cx, cy, cz, radius) => {
        if (requireFront) {
            const n1x = radius > 1e-6 ? (x1 - cx) / radius : x1;
            const n1y = radius > 1e-6 ? (y1 - cy) / radius : y1;
            const n1z = radius > 1e-6 ? (z1 - cz) / radius : z1;
            const n2x = radius > 1e-6 ? (x2 - cx) / radius : x2;
            const n2y = radius > 1e-6 ? (y2 - cy) / radius : y2;
            const n2z = radius > 1e-6 ? (z2 - cz) / radius : z2;
            const f1 = sphereFacingAt(n1x, n1y, n1z, eye, cx, cy, cz, radius);
            const f2 = sphereFacingAt(n2x, n2y, n2z, eye, cx, cy, cz, radius);
            if (f1 <= 0 || f2 <= 0) return;
        }
        transformPoint(viewProj, x1, y1, z1, clipA);
        transformPoint(viewProj, x2, y2, z2, clipB);
        const clipped = clipLineToPositiveW(clipA, clipB);
        if (!clipped) return;
        const s1 = clipToScreen(clipped.x1, clipped.y1, clipped.w1, width, height);
        const s2 = clipToScreen(clipped.x2, clipped.y2, clipped.w2, width, height);
        if (!s1.ok || !s2.ok) return;
        if (!Number.isFinite(s1.x) || !Number.isFinite(s1.y) || !Number.isFinite(s2.x) || !Number.isFinite(s2.y)) {
            return;
        }
        if (Math.hypot(s1.x - s2.x, s1.y - s2.y) > maxSeg) return;
        const d1 = screenToDrawWorld(s1.x, s1.y, width, height);
        const d2 = screenToDrawWorld(s2.x, s2.y, width, height);
        const o = w * EDGE_STRIDE;
        edgeScratch[o] = d1.x;
        edgeScratch[o + 1] = d1.y;
        edgeScratch[o + 2] = d2.x;
        edgeScratch[o + 3] = d2.y;
        edgeScratch[o + 4] = r;
        edgeScratch[o + 5] = g;
        edgeScratch[o + 6] = b;
        edgeScratch[o + 7] = a;
        w += 1;
    };

    const ringR = hub;
    const ringCol = dark ? [0.28, 0.4, 0.55, 0.22] : [0.45, 0.55, 0.7, 0.28];
    let prevRing = null;
    for (let s = 0; s <= ringSegs; s++) {
        const ang = (s / ringSegs) * Math.PI * 2;
        const pt: any = { x: ringR * Math.cos(ang), y: 0, z: ringR * Math.sin(ang) };
        if (prevRing) {
            writeWorldSeg(
                prevRing.x,
                prevRing.y,
                prevRing.z,
                pt.x,
                pt.y,
                pt.z,
                ringCol[0],
                ringCol[1],
                ringCol[2],
                ringCol[3],
                false,
                0,
                0,
                0,
                1
            );
        }
        prevRing = pt;
    }

    for (let p = 0; p < planets.length; p++) {
        const pl = planets[p];
        const gc = [pl.fill[0] * 0.7 + 0.15, pl.fill[1] * 0.7 + 0.18, pl.fill[2] * 0.75 + 0.22, dark ? 0.42 : 0.48];
        for (let i = 0; i < grid.length; i++) {
            const ln = grid[i];
            writeWorldSeg(
                pl.cx + ln.x1 * pl.radius,
                pl.cy + ln.y1 * pl.radius,
                pl.cz + ln.z1 * pl.radius,
                pl.cx + ln.x2 * pl.radius,
                pl.cy + ln.y2 * pl.radius,
                pl.cz + ln.z2 * pl.radius,
                gc[0],
                gc[1],
                gc[2],
                gc[3],
                true,
                pl.cx,
                pl.cy,
                pl.cz,
                pl.radius
            );
        }
        writeWorldSeg(
            0,
            0,
            0,
            pl.cx,
            pl.cy,
            pl.cz,
            pl.fill[0],
            pl.fill[1],
            pl.fill[2],
            dark ? 0.38 : 0.42,
            false,
            0,
            0,
            0,
            1
        );
    }

    const EDGE_MATCH = 0.75;
    const nodeIndex = srcEdgeCount > 0 ? buildNodePosIndex(srcNodes, srcCount) : null;
    for (let i = 0; i < srcEdgeCount; i++) {
        const o = i * EDGE_STRIDE;
        const x1 = srcEdges[o];
        const y1 = srcEdges[o + 1];
        const x2 = srcEdges[o + 2];
        const y2 = srcEdges[o + 3];
        const ia = nearestNodeAt(nodeIndex, x1, y1, srcNodes, EDGE_MATCH);
        const ib = nearestNodeAt(nodeIndex, x2, y2, srcNodes, EDGE_MATCH);
        if (ia < 0 || ib < 0 || ia === ib) continue;
        const wa = worldScratch[ia];
        const wb = worldScratch[ib];
        if (!wa || !wb) continue;
        if (wa.planet !== wb.planet || wa.planet < 0) continue;
        const pa = projected[ia];
        const pb = projected[ib];
        if (pa && pb && pa.facing <= 0 && pb.facing <= 0) continue;
        writeWorldSeg(
            wa.x,
            wa.y,
            wa.z,
            wb.x,
            wb.y,
            wb.z,
            srcEdges[o + 4],
            srcEdges[o + 5],
            srcEdges[o + 6],
            srcEdges[o + 7] || 0.45,
            false,
            0,
            0,
            0,
            1
        );
    }

    const layoutScale = planets[0] ? planets[0].layoutScale : LAYOUT_SCALE_FLOOR;
    return {
        nodes: nodeScratch.subarray(0, Math.max(nodeNeed, 0)),
        edges: edgeScratch.subarray(0, w * EDGE_STRIDE),
        pick,
        projected,
        planets,
        layoutScale,
        homeById: assigned.homeById,
        orbit,
        camera: { x: 0, y: 0, zoom: 1 },
    };
}

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
