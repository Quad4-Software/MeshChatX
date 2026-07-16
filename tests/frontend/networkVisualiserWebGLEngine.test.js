import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
    graphToSceneRequest,
    isVisualiserWebGLSceneReady,
    KIND_ME,
    KIND_IFACE_ON,
    KIND_PEER,
} from "@/js/networkVisualiserWebGLEngine.js";

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
});
