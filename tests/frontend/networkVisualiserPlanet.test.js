import { describe, it, expect } from "vitest";
import {
    FLAT_VIEW,
    PLANET_VIEW,
    DEFAULT_ORBIT_DIST,
    LAYOUT_SCALE_FLOOR,
    clampOrbit,
    computeLayoutScale,
    layoutToSphere,
    sphereToLayout,
    orbitEye,
    planetLodZoom,
    pickPlanetNode,
    pointerToLayout,
    projectPlanetScene,
    raySphere,
    normalizeVisualiserViewMode,
} from "@/js/networkVisualiserPlanet.js";
import { NODE_STRIDE as DRAW_STRIDE } from "@/js/networkVisualiserWebGL.js";

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
        expect(c.dist).toBeGreaterThan(1.5);
        const far = clampOrbit(0, 0, 99);
        expect(far.dist).toBeLessThan(9);
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

    it("projects me onto the globe disc and keeps a pick target", () => {
        const nodes = new Float32Array(DRAW_STRIDE);
        nodes[0] = 0;
        nodes[1] = 0;
        nodes[2] = 32;
        nodes[3] = 0.2;
        nodes[4] = 0.5;
        nodes[6] = 1;
        const edges = new Float32Array(0);
        const out = projectPlanetScene({
            nodes,
            edges,
            width: 800,
            height: 600,
            yaw: 0,
            pitch: 0,
            dist: DEFAULT_ORBIT_DIST,
            dark: true,
            idByIndex: ["me"],
        });
        expect(out.nodes.length).toBe(DRAW_STRIDE * 2);
        expect(out.edges.length).toBeGreaterThan(0);
        expect(out.pick.some((p) => p.id === "me")).toBe(true);
        expect(pickPlanetNode(out.pick, out.pick[0].sx, out.pick[0].sy, 20)).toBe("me");
        expect(pickPlanetNode(out.pick, -400, -400, 8)).toBeNull();
    });

    it("draws back-facing nodes before front-facing nodes", () => {
        const nodes = new Float32Array(DRAW_STRIDE * 2);
        nodes[0] = 0;
        nodes[1] = 0;
        nodes[2] = 24;
        nodes[6] = 1;
        nodes[DRAW_STRIDE] = 400;
        nodes[DRAW_STRIDE + 1] = 0;
        nodes[DRAW_STRIDE + 2] = 24;
        nodes[DRAW_STRIDE + 6] = 1;
        const out = projectPlanetScene({
            nodes,
            edges: new Float32Array(0),
            width: 800,
            height: 600,
            yaw: 0,
            pitch: 0,
            dist: DEFAULT_ORBIT_DIST,
            dark: true,
            idByIndex: ["me", "peer"],
        });
        const frontAlpha = out.nodes[DRAW_STRIDE * 2 + 6];
        const backAlpha = out.nodes[DRAW_STRIDE + 6];
        expect(backAlpha).toBeLessThan(frontAlpha);
        expect(out.pick.some((p) => p.id === "me")).toBe(true);
        expect(out.pick.some((p) => p.id === "peer")).toBe(false);
    });

    it("maps closer orbit to a higher LOD zoom", () => {
        expect(planetLodZoom(DEFAULT_ORBIT_DIST)).toBeCloseTo(1, 5);
        expect(planetLodZoom(DEFAULT_ORBIT_DIST * 2)).toBeCloseTo(0.5, 5);
    });
});
