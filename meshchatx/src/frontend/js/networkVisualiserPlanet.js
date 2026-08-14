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
export const LAYOUT_SCALE_FIT = 1.08;

export const PLANET_KIND_ME = 0;
export const PLANET_KIND_IFACE_ON = 1;
export const PLANET_KIND_IFACE_OFF = 2;
export const PLANET_KIND_PEER = 3;
export const PLANET_KIND_DISCOVERED = 4;

const meridians = 14;
const parallels = 6;
const gridSegs = 18;
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

/** @type {{x1:number,y1:number,z1:number,x2:number,y2:number,z2:number}[]|null} */
let globeGridCache = null;

let nodeScratch = new Float32Array(0);
let edgeScratch = new Float32Array(0);

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

export function transformPoint(m, x, y, z) {
    return {
        x: m[0] * x + m[4] * y + m[8] * z + m[12],
        y: m[1] * x + m[5] * y + m[9] * z + m[13],
        z: m[2] * x + m[6] * y + m[10] * z + m[14],
        w: m[3] * x + m[7] * y + m[11] * z + m[15],
    };
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

export function hubRadiusForPlanetCount(n) {
    const c = Math.max(1, n | 0);
    if (c <= 1) return 1.72;
    return 1.5 + 0.28 * Math.min(c, 8);
}

export function planetRadiusForPeers(n) {
    const c = Math.max(0, n | 0);
    return Math.min(0.78, 0.4 + 0.075 * Math.sqrt(c));
}

/**
 * Centers for n interface planets on a ring around the origin.
 * First planet sits on +X so the local node stays visible on camera +Z.
 */
export function placePlanetCenters(count) {
    const n = Math.max(0, count | 0);
    const R = hubRadiusForPlanetCount(n);
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
export function assignPlanetHomes(srcCount, kindByIndex, idByIndex, nodes) {
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
    if (ifaceIndices.length === 0) {
        for (let i = 0; i < srcCount; i++) {
            const k = kindOf(i, kindByIndex, idByIndex);
            if (k !== PLANET_KIND_ME) home[i] = 0;
        }
        return { ifaceIndices, home, fallback: true };
    }
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
        home[i] = best;
    }
    return { ifaceIndices, home, fallback: false };
}

function paletteForId(id, offline, dark) {
    const s = String(id || "");
    let h = 0;
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    const base = PLANET_PALETTE[Math.abs(h) % PLANET_PALETTE.length];
    const dim = offline ? 0.48 : 1;
    const lift = dark ? 0.0 : 0.12;
    return [
        Math.min(1, base[0] * dim + lift),
        Math.min(1, base[1] * dim + lift),
        Math.min(1, base[2] * dim + lift),
    ];
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
    return Math.max(maxR * LAYOUT_SCALE_FIT, 90);
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
 * }} opts
 */
export function projectPlanetScene(opts) {
    const width = Math.max(1, opts?.width || 1);
    const height = Math.max(1, opts?.height || 1);
    const orbit = clampOrbit(
        opts?.yaw ?? DEFAULT_ORBIT_YAW,
        opts?.pitch ?? DEFAULT_ORBIT_PITCH,
        opts?.dist ?? DEFAULT_ORBIT_DIST
    );
    const eye = orbitEye(orbit.yaw, orbit.pitch, orbit.dist);
    const view = lookAtOrigin(eye);
    const proj = perspective(PLANET_FOV_Y, width / height, PLANET_NEAR, PLANET_FAR);
    const viewProj = mat4Multiply(proj, view);
    const srcNodes = opts?.nodes;
    const srcCount = srcNodes && srcNodes.length ? Math.floor(srcNodes.length / NODE_STRIDE) : 0;
    const idByIndex = opts?.idByIndex || [];
    const kindByIndex = opts?.kindByIndex || [];
    const dark = opts?.dark === true;
    const srcEdges = opts?.edges;
    const srcEdgeCount = srcEdges && srcEdges.length ? Math.floor(srcEdges.length / EDGE_STRIDE) : 0;

    const assigned = assignPlanetHomes(srcCount, kindByIndex, idByIndex, srcNodes);
    const planetCount = assigned.fallback ? (srcCount > 1 ? 1 : 0) : assigned.ifaceIndices.length;
    const centers = placePlanetCenters(planetCount);
    const memberCounts = new Array(Math.max(planetCount, 1)).fill(0);
    for (let i = 0; i < srcCount; i++) {
        const h = assigned.home[i];
        if (h >= 0 && h < memberCounts.length) memberCounts[h] += 1;
    }

    const planets = [];
    for (let p = 0; p < planetCount; p++) {
        const ifaceIndex = assigned.fallback ? -1 : assigned.ifaceIndices[p];
        const c = centers[p] || { cx: 1.7, cy: 0.1, cz: 0 };
        const radius = planetRadiusForPeers(Math.max(0, memberCounts[p] - (assigned.fallback ? 0 : 1)));
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
            layoutScale: localScaleForPlanet(srcNodes, srcCount, assigned.home, p, ifaceIndex, assigned.fallback),
            ifaceIndex,
            id,
            fill: paletteForId(id, offline, dark),
            offline,
        });
    }

    const world = new Array(srcCount);
    for (let i = 0; i < srcCount; i++) {
        const k = kindOf(i, kindByIndex, idByIndex);
        if (k === PLANET_KIND_ME) {
            world[i] = { x: 0, y: 0, z: 0, nx: 0, ny: 0, nz: 1, planet: -1 };
            continue;
        }
        const p = planets[assigned.home[i]];
        if (!p) {
            world[i] = { x: 0, y: 0, z: 0, nx: 0, ny: 0, nz: 1, planet: -1 };
            continue;
        }
        if (!assigned.fallback && i === p.ifaceIndex) {
            world[i] = { x: p.cx, y: p.cy, z: p.cz, nx: 0, ny: 0, nz: 1, planet: assigned.home[i] };
            continue;
        }
        const o = i * NODE_STRIDE;
        const local = layoutToSphere(
            (srcNodes[o] || 0) - p.originX,
            (srcNodes[o + 1] || 0) - p.originY,
            p.layoutScale
        );
        world[i] = {
            x: p.cx + local.x * p.radius,
            y: p.cy + local.y * p.radius,
            z: p.cz + local.z * p.radius,
            nx: local.x,
            ny: local.y,
            nz: local.z,
            planet: assigned.home[i],
        };
    }

    const sprites = [];
    const addSprite = (wx, wy, wz, size, r, g, b, a, useTex, u, v) => {
        const clip = transformPoint(viewProj, wx, wy, wz);
        const screen = clipToScreen(clip.x, clip.y, clip.w, width, height);
        if (!screen.ok && clip.w <= 0) return null;
        const draw = screenToDrawWorld(screen.x, screen.y, width, height);
        const viewZ = Math.hypot(wx - eye.x, wy - eye.y, wz - eye.z);
        sprites.push({
            x: draw.x,
            y: draw.y,
            z: viewZ,
            size,
            r,
            g,
            b,
            a,
            useTex,
            u,
            v,
            sx: screen.x,
            sy: screen.y,
            ok: screen.ok,
        });
        return sprites[sprites.length - 1];
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

    addSprite(
        0,
        0,
        0,
        22,
        dark ? 0.95 : 0.9,
        dark ? 0.78 : 0.62,
        dark ? 0.28 : 0.16,
        0.22,
        0,
        0,
        0
    );

    const projected = new Array(srcCount);
    const pick = [];
    for (let i = 0; i < srcCount; i++) {
        const w = world[i];
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
        const rec = {
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

    sprites.sort((a, b) => b.z - a.z);
    const nodeNeed = sprites.length * NODE_STRIDE;
    if (nodeScratch.length < nodeNeed) {
        nodeScratch = new Float32Array(nodeNeed);
    }
    for (let s = 0; s < sprites.length; s++) {
        const d = s * NODE_STRIDE;
        const n = sprites[s];
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

    const grid = buildGlobeGrid();
    const edgeNeed = (planets.length * (grid.length + 8) + srcEdgeCount + ringSegs + planetCount) * EDGE_STRIDE;
    if (edgeScratch.length < edgeNeed) {
        edgeScratch = new Float32Array(Math.max(edgeNeed, 64));
    }
    let w = 0;
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
            if (f1 <= 0 && f2 <= 0) return;
        }
        const c1 = transformPoint(viewProj, x1, y1, z1);
        const c2 = transformPoint(viewProj, x2, y2, z2);
        const s1 = clipToScreen(c1.x, c1.y, c1.w, width, height);
        const s2 = clipToScreen(c2.x, c2.y, c2.w, width, height);
        if (!s1.ok && !s2.ok) return;
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

    const ringR = hubRadiusForPlanetCount(Math.max(planetCount, 1));
    const ringCol = dark ? [0.28, 0.4, 0.55, 0.22] : [0.45, 0.55, 0.7, 0.28];
    let prevRing = null;
    for (let s = 0; s <= ringSegs; s++) {
        const ang = (s / ringSegs) * Math.PI * 2;
        const pt = { x: ringR * Math.cos(ang), y: 0, z: ringR * Math.sin(ang) };
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
        const gc = [
            pl.fill[0] * 0.7 + 0.15,
            pl.fill[1] * 0.7 + 0.18,
            pl.fill[2] * 0.75 + 0.22,
            dark ? 0.42 : 0.48,
        ];
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
        writeWorldSeg(0, 0, 0, pl.cx, pl.cy, pl.cz, pl.fill[0], pl.fill[1], pl.fill[2], dark ? 0.38 : 0.42, false, 0, 0, 0, 1);
    }

    for (let i = 0; i < srcEdgeCount; i++) {
        const o = i * EDGE_STRIDE;
        let ia = -1;
        let ib = -1;
        let da = Infinity;
        let db = Infinity;
        const x1 = srcEdges[o];
        const y1 = srcEdges[o + 1];
        const x2 = srcEdges[o + 2];
        const y2 = srcEdges[o + 3];
        for (let n = 0; n < srcCount; n++) {
            const no = n * NODE_STRIDE;
            const a = Math.hypot((srcNodes[no] || 0) - x1, (srcNodes[no + 1] || 0) - y1);
            const b = Math.hypot((srcNodes[no] || 0) - x2, (srcNodes[no + 1] || 0) - y2);
            if (a < da) {
                da = a;
                ia = n;
            }
            if (b < db) {
                db = b;
                ib = n;
            }
        }
        if (ia < 0 || ib < 0 || ia === ib) continue;
        const wa = world[ia];
        const wb = world[ib];
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
