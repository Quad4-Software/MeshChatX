import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    graphToSceneRequest,
    isVisualiserWebGLSceneReady,
    KIND_ME,
    KIND_IFACE_ON,
    KIND_PEER,
    pointerDistance,
    pointerMidpoint,
} from "@/js/networkVisualiserWebGLEngine.js";
import {
    atlasUvForSlot,
    mergeSceneNodesWithTextures,
    SCENE_NODE_STRIDE,
    NODE_STRIDE,
} from "@/js/networkVisualiserWebGL.js";

describe("networkVisualiserWebGLEngine", () => {
    const sceneFns = [
        "meshchatxVisualiserSceneSet",
        "meshchatxVisualiserSceneGetDrawBuffers",
        "meshchatxVisualiserSceneTick",
        "meshchatxVisualiserScenePick",
        "meshchatxVisualiserBuildPathGraph",
        "meshchatxVisualiserBuildFullGraph",
        "meshchatxVisualiserLayout",
        "meshchatxVisualiserPathHashes",
        "meshchatxVisualiserDedupeIcons",
    ];

    beforeEach(() => {
        for (const name of sceneFns) {
            delete globalThis[name];
        }
    });

    afterEach(() => {
        for (const name of sceneFns) {
            delete globalThis[name];
        }
    });

    it("isVisualiserWebGLSceneReady requires scene exports", () => {
        expect(isVisualiserWebGLSceneReady()).toBe(false);
        for (const name of sceneFns) {
            globalThis[name] = () => null;
        }
        expect(isVisualiserWebGLSceneReady()).toBe(true);
    });

    it("graphToSceneRequest maps me/iface/peer colors and kinds", () => {
        const req = graphToSceneRequest(
            [
                { id: "me", group: "me", x: 0, y: 0, size: 50, color: { border: "#3b82f6" } },
                {
                    id: "Radio",
                    group: "interface",
                    x: 10,
                    y: 20,
                    size: 35,
                    image: "/assets/images/network-visualiser/interface_connected.png",
                    color: { border: "#10b981" },
                },
                { id: "abcd", group: "announce", x: 30, y: 40, size: 25, color: { border: "#8b5cf6" } },
            ],
            [{ from: "me", to: "Radio", width: 3, color: { color: "#10b981", opacity: 1 } }],
            { width: 640, height: 480, zoom: 1 }
        );
        expect(req.nodes).toHaveLength(3);
        expect(req.nodes[0].kind).toBe(KIND_ME);
        expect(req.nodes[0].fixed).toBe(true);
        expect(req.nodes[1].kind).toBe(KIND_IFACE_ON);
        expect(req.nodes[2].kind).toBe(KIND_PEER);
        expect(req.edges).toHaveLength(1);
        expect(req.edges[0].from).toBe("me");
        expect(req.width).toBe(640);
    });

    it("pointerDistance and midpoint support pinch zoom math", () => {
        const a = { x: 0, y: 0 };
        const b = { x: 30, y: 40 };
        expect(pointerDistance(a, b)).toBe(50);
        expect(pointerMidpoint(a, b)).toEqual({ x: 15, y: 20 });
    });
});

describe("networkVisualiserWebGL textures", () => {
    it("atlasUvForSlot maps grid cells", () => {
        expect(atlasUvForSlot(0)).toEqual({ u: 0, v: 0 });
        expect(atlasUvForSlot(1).u).toBeCloseTo(1 / 16);
        expect(atlasUvForSlot(16).v).toBeCloseTo(1 / 16);
    });

    it("mergeSceneNodesWithTextures attaches atlas UVs", () => {
        const scene = new Float32Array(SCENE_NODE_STRIDE);
        scene[0] = 1;
        scene[1] = 2;
        scene[2] = 10;
        scene[3] = 0.1;
        scene[4] = 0.2;
        scene[5] = 0.3;
        scene[6] = 1;
        scene[7] = 3;
        const out = mergeSceneNodesWithTextures(scene, [{ useTex: 1, u: 0.25, v: 0.5 }]);
        expect(out.length).toBe(NODE_STRIDE);
        expect(out[0]).toBe(1);
        expect(out[2]).toBe(10);
        expect(out[7]).toBe(1);
        expect(out[8]).toBe(0.25);
        expect(out[9]).toBe(0.5);
    });

    it("mergeSceneNodesWithTextures falls back to untextured discs", () => {
        const scene = new Float32Array(SCENE_NODE_STRIDE);
        const out = mergeSceneNodesWithTextures(scene, [{ useTex: 0, u: 0, v: 0 }]);
        expect(out[7]).toBe(0);
    });
});
