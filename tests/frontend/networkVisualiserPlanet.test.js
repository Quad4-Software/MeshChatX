import { describe, it, expect } from "vitest";
import {
    FLAT_VIEW,
    PLANET_VIEW,
    DEFAULT_ORBIT_DIST,
    LAYOUT_SCALE_FLOOR,
    PLANET_KIND_ME,
    PLANET_KIND_IFACE_ON,
    PLANET_KIND_PEER,
    assignPlanetHomes,
    clampOrbit,
    computeLayoutScale,
    layoutToSphere,
    sphereToLayout,
    orbitEye,
    planetLodZoom,
    pickPlanetNode,
    pointerToLayout,
    placePlanetCenters,
    projectPlanetScene,
    raySphere,
    normalizeVisualiserViewMode,
} from "@/js/networkVisualiserPlanet.js";
import { NODE_STRIDE as DRAW_STRIDE } from "@/js/networkVisualiserWebGL.js";

function packNode(arr, i, x, y, size = 24, a = 1) {
    const o = i * DRAW_STRIDE;
    arr[o] = x;
    arr[o + 1] = y;
    arr[o + 2] = size;
    arr[o + 6] = a;
}

describe("networkVisualiserPlanet", () => {
    it("normalizes view mode to flat or planet", () => {
        expect(normalizeVisualiserViewMode("planet")).toBe(PLANET_VIEW);
        expect(normalizeVisualiserViewMode("flat")).toBe(FLAT_VIEW);
        expect(normalizeVisualiserViewMode("nope")).toBe(FLAT_VIEW);
        expect(normalizeVisualiserViewMode(null)).toBe(FLAT_VIEW);
    });

    it("maps the origin to the front of the globe and inverts", () => {
        const p = layoutToSphere(0, 0, 400);
        expect(p.x).toBeCloseTo(0, 5);
        expect(p.y).toBeCloseTo(0, 5);
        expect(p.z).toBeCloseTo(1, 5);
        const back = layoutToSphere(400, 0, 400);
        expect(back.z).toBeCloseTo(-1, 5);
        const round = sphereToLayout(p.x, p.y, p.z, 400);
        expect(round.x).toBeCloseTo(0, 5);
        expect(round.y).toBeCloseTo(0, 5);
        const q = layoutToSphere(120, -40, 400);
        const inv = sphereToLayout(q.x, q.y, q.z, 400);
        expect(inv.x).toBeCloseTo(120, 4);
        expect(inv.y).toBeCloseTo(-40, 4);
    });

    it("keeps layout scale at least the floor and grows with spread", () => {
        expect(computeLayoutScale(new Float32Array(DRAW_STRIDE), DRAW_STRIDE)).toBe(LAYOUT_SCALE_FLOOR);
        const nodes = new Float32Array(DRAW_STRIDE * 2);
        nodes[0] = 0;
        nodes[1] = 0;
        nodes[DRAW_STRIDE] = 1000;
        nodes[DRAW_STRIDE + 1] = 0;
        expect(computeLayoutScale(nodes, DRAW_STRIDE)).toBeGreaterThan(LAYOUT_SCALE_FLOOR);
        expect(1000 / computeLayoutScale(nodes, DRAW_STRIDE)).toBeLessThan(1);
    });

    it("keeps layout points on the front-to-back hemisphere", () => {
        const scale = 400;
        const overshoot = layoutToSphere(scale * 2.5, 0, scale);
        expect(overshoot.phi).toBeLessThanOrEqual(Math.PI);
        expect(overshoot.z).toBeCloseTo(-1, 5);
        const atRim = layoutToSphere(scale, 0, scale);
        expect(atRim.z).toBeCloseTo(-1, 5);
        const mid = layoutToSphere(scale * 0.5, 0, scale);
        expect(mid.phi).toBeCloseTo(Math.PI * 0.5, 5);
        expect(mid.z).toBeCloseTo(0, 5);
    });

    it("clamps orbit pitch and distance", () => {
        const c = clampOrbit(1, 9, 0.2);
        expect(c.pitch).toBeLessThan(1.2);
        expect(c.dist).toBeGreaterThan(2.5);
        const far = clampOrbit(0, 0, 99);
        expect(far.dist).toBeLessThan(17);
        const bad = clampOrbit(Number.NaN, Number.NaN, Number.NaN);
        expect(Number.isFinite(bad.yaw)).toBe(true);
        expect(Number.isFinite(bad.pitch)).toBe(true);
        expect(Number.isFinite(bad.dist)).toBe(true);
    });

    it("places the default eye in front of the origin", () => {
        const eye = orbitEye(0, 0, DEFAULT_ORBIT_DIST);
        expect(eye.x).toBeCloseTo(0, 5);
        expect(eye.y).toBeCloseTo(0, 5);
        expect(eye.z).toBeCloseTo(DEFAULT_ORBIT_DIST, 5);
    });

    it("hits the unit sphere from the default camera", () => {
        const eye = orbitEye(0, 0, DEFAULT_ORBIT_DIST);
        const hit = raySphere(eye, { x: 0, y: 0, z: -1 }, 1);
        expect(hit).not.toBeNull();
        expect(hit.z).toBeCloseTo(1, 4);
    });

    it("maps a center click back to the layout origin", () => {
        const eye = orbitEye(0, 0, DEFAULT_ORBIT_DIST);
        const got = pointerToLayout(400, 300, 800, 600, eye, 400);
        expect(got).not.toBeNull();
        expect(Math.hypot(got.x, got.y)).toBeLessThan(8);
    });

    it("places interface planets on a ring with the first on +X", () => {
        const one = placePlanetCenters(1);
        expect(one).toHaveLength(1);
        expect(one[0].cx).toBeGreaterThan(1);
        expect(Math.abs(one[0].cz)).toBeLessThan(0.2);
        const two = placePlanetCenters(2);
        expect(two).toHaveLength(2);
        expect(Math.hypot(two[0].cx - two[1].cx, two[0].cz - two[1].cz)).toBeGreaterThan(1);
    });

    it("homes peers on the nearest interface planet", () => {
        const nodes = new Float32Array(DRAW_STRIDE * 4);
        packNode(nodes, 0, 0, 0, 32);
        packNode(nodes, 1, 200, 0, 24);
        packNode(nodes, 2, -200, 0, 24);
        packNode(nodes, 3, 230, 20, 22);
        const kinds = [PLANET_KIND_ME, PLANET_KIND_IFACE_ON, PLANET_KIND_IFACE_ON, PLANET_KIND_PEER];
        const got = assignPlanetHomes(4, kinds, ["me", "eth0", "wifi", "peer"], nodes);
        expect(got.fallback).toBe(false);
        expect(got.ifaceIndices).toEqual([1, 2]);
        expect(got.home[0]).toBe(-1);
        expect(got.home[1]).toBe(0);
        expect(got.home[2]).toBe(1);
        expect(got.home[3]).toBe(0);
    });

    it("projects me as a hub and each interface as its own globe", () => {
        const nodes = new Float32Array(DRAW_STRIDE * 3);
        packNode(nodes, 0, 0, 0, 32);
        packNode(nodes, 1, 200, 0, 24);
        packNode(nodes, 2, 240, 30, 22);
        const out = projectPlanetScene({
            nodes,
            edges: new Float32Array(0),
            width: 800,
            height: 600,
            yaw: 0,
            pitch: 0,
            dist: DEFAULT_ORBIT_DIST,
            dark: true,
            idByIndex: ["me", "eth0", "peer"],
            kindByIndex: [PLANET_KIND_ME, PLANET_KIND_IFACE_ON, PLANET_KIND_PEER],
        });
        expect(out.planets).toHaveLength(1);
        expect(out.nodes.length).toBeGreaterThanOrEqual(DRAW_STRIDE * 3);
        expect(out.pick.some((p) => p.id === "me")).toBe(true);
        expect(out.pick.some((p) => p.id === "eth0")).toBe(true);
        expect(out.projected[1].kind).toBe(PLANET_KIND_IFACE_ON);
        expect(pickPlanetNode(out.pick, out.pick.find((p) => p.id === "me").sx, out.pick.find((p) => p.id === "me").sy, 24)).toBe(
            "me"
        );
        expect(pickPlanetNode(out.pick, -400, -400, 8)).toBeNull();
    });

    it("builds one globe per interface", () => {
        const nodes = new Float32Array(DRAW_STRIDE * 3);
        packNode(nodes, 0, 0, 0, 32);
        packNode(nodes, 1, 200, 0, 24);
        packNode(nodes, 2, -180, 40, 24);
        const out = projectPlanetScene({
            nodes,
            edges: new Float32Array(0),
            width: 800,
            height: 600,
            yaw: 0.4,
            pitch: 0.2,
            dist: DEFAULT_ORBIT_DIST,
            dark: true,
            idByIndex: ["me", "eth0", "wifi"],
            kindByIndex: [PLANET_KIND_ME, PLANET_KIND_IFACE_ON, PLANET_KIND_IFACE_ON],
        });
        expect(out.planets).toHaveLength(2);
        expect(out.planets[0].id).toBe("eth0");
        expect(out.planets[1].id).toBe("wifi");
        expect(Math.hypot(out.planets[0].cx - out.planets[1].cx, out.planets[0].cz - out.planets[1].cz)).toBeGreaterThan(1);
    });

    it("marks a far-side peer as back-facing on its interface globe", () => {
        const nodes = new Float32Array(DRAW_STRIDE * 3);
        packNode(nodes, 0, 0, 0, 32);
        packNode(nodes, 1, 200, 0, 24);
        packNode(nodes, 2, 200 + 400, 0, 22);
        const out = projectPlanetScene({
            nodes,
            edges: new Float32Array(0),
            width: 800,
            height: 600,
            yaw: 0,
            pitch: 0,
            dist: DEFAULT_ORBIT_DIST,
            dark: true,
            idByIndex: ["me", "eth0", "peer"],
            kindByIndex: [PLANET_KIND_ME, PLANET_KIND_IFACE_ON, PLANET_KIND_PEER],
        });
        expect(out.projected[2].front).toBe(false);
        expect(out.pick.some((p) => p.id === "peer")).toBe(false);
        expect(out.pick.some((p) => p.id === "eth0")).toBe(true);
    });

    it("maps a click on an interface globe back near that interface layout", () => {
        const nodes = new Float32Array(DRAW_STRIDE * 2);
        packNode(nodes, 0, 0, 0, 32);
        packNode(nodes, 1, 200, 0, 24);
        const out = projectPlanetScene({
            nodes,
            edges: new Float32Array(0),
            width: 800,
            height: 600,
            yaw: 0,
            pitch: 0,
            dist: DEFAULT_ORBIT_DIST,
            dark: true,
            idByIndex: ["me", "eth0"],
            kindByIndex: [PLANET_KIND_ME, PLANET_KIND_IFACE_ON],
        });
        const eye = orbitEye(0, 0, DEFAULT_ORBIT_DIST);
        const pl = out.planets[0];
        const eth = out.pick.find((p) => p.id === "eth0");
        expect(eth).toBeTruthy();
        const got = pointerToLayout(eth.sx, eth.sy, 800, 600, eye, 400, out.planets);
        expect(got).not.toBeNull();
        expect(got.planetIndex).toBe(0);
        expect(Math.hypot(got.x - pl.originX, got.y - pl.originY)).toBeLessThan(pl.layoutScale);
    });

    it("maps closer orbit to a higher LOD zoom", () => {
        expect(planetLodZoom(DEFAULT_ORBIT_DIST)).toBeCloseTo(1, 5);
        expect(planetLodZoom(DEFAULT_ORBIT_DIST * 2)).toBeCloseTo(0.5, 5);
    });
});
