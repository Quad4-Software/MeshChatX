import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
    graphToSceneRequest,
    isVisualiserWebGLSceneReady,
    KIND_ME,
    KIND_IFACE_ON,
    KIND_IFACE_OFF,
    KIND_PEER,
    KIND_DISCOVERED,
    pointerDistance,
    pointerMidpoint,
    canUseVisualiserWebGL,
    createVisualiserWebGLEngine,
    collectWebGLLabels,
    truncateWebGLLabel,
    WEBGL_LABEL_MAX_CHARS,
} from "@/js/networkVisualiserWebGLEngine.js";
import {
    atlasUvForSlot,
    mergeSceneNodesWithTextures,
    resolveVisualiserAssetUrl,
    SCENE_NODE_STRIDE,
    NODE_STRIDE,
    ATLAS_COLS,
    ATLAS_ROWS,
    tryCreateWebGL2Context,
} from "@/js/networkVisualiserWebGL.js";

const SCENE_READY_FNS = [
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

function clearSceneGlobals() {
    for (const name of SCENE_READY_FNS) {
        delete globalThis[name];
    }
    delete globalThis.meshchatxVisualiserScenePanBy;
    delete globalThis.meshchatxVisualiserSceneZoomAt;
    delete globalThis.meshchatxVisualiserSceneDragStart;
    delete globalThis.meshchatxVisualiserSceneDragTo;
    delete globalThis.meshchatxVisualiserSceneDragEnd;
    delete globalThis.meshchatxVisualiserSceneResize;
    delete globalThis.meshchatxVisualiserSceneGetPositions;
}

function installSceneReadyStubs(overrides = {}) {
    for (const name of SCENE_READY_FNS) {
        globalThis[name] = overrides[name] || (() => null);
    }
}

function stubGl() {
    return {
        createShader: () => ({}),
        shaderSource: vi.fn(),
        compileShader: vi.fn(),
        getShaderParameter: () => true,
        getShaderInfoLog: () => "",
        deleteShader: vi.fn(),
        createProgram: () => ({}),
        attachShader: vi.fn(),
        linkProgram: vi.fn(),
        getProgramParameter: () => true,
        getProgramInfoLog: () => "",
        deleteProgram: vi.fn(),
        createBuffer: () => ({}),
        bindBuffer: vi.fn(),
        bufferData: vi.fn(),
        createVertexArray: () => ({}),
        bindVertexArray: vi.fn(),
        enableVertexAttribArray: vi.fn(),
        vertexAttribPointer: vi.fn(),
        vertexAttribDivisor: vi.fn(),
        getUniformLocation: () => ({}),
        createTexture: () => ({}),
        bindTexture: vi.fn(),
        texParameteri: vi.fn(),
        texImage2D: vi.fn(),
        texSubImage2D: vi.fn(),
        generateMipmap: vi.fn(),
        pixelStorei: vi.fn(),
        deleteTexture: vi.fn(),
        deleteBuffer: vi.fn(),
        deleteVertexArray: vi.fn(),
        viewport: vi.fn(),
        clearColor: vi.fn(),
        clear: vi.fn(),
        enable: vi.fn(),
        blendFunc: vi.fn(),
        useProgram: vi.fn(),
        uniform2f: vi.fn(),
        uniform1f: vi.fn(),
        uniform1i: vi.fn(),
        activeTexture: vi.fn(),
        drawArrays: vi.fn(),
        drawArraysInstanced: vi.fn(),
        lineWidth: vi.fn(),
        TEXTURE_2D: 0x0de1,
        TEXTURE0: 0x84c0,
        RGBA: 0x1908,
        UNSIGNED_BYTE: 0x1401,
        LINEAR: 0x2601,
        LINEAR_MIPMAP_LINEAR: 0x2703,
        CLAMP_TO_EDGE: 0x812f,
        TEXTURE_MIN_FILTER: 0x2801,
        TEXTURE_MAG_FILTER: 0x2800,
        TEXTURE_WRAP_S: 0x2802,
        TEXTURE_WRAP_T: 0x2803,
        UNPACK_FLIP_Y_WEBGL: 0x9240,
        UNPACK_PREMULTIPLY_ALPHA_WEBGL: 0x9241,
        COLOR_BUFFER_BIT: 0x4000,
        BLEND: 0x0be2,
        SRC_ALPHA: 0x0302,
        ONE_MINUS_SRC_ALPHA: 0x0303,
        ARRAY_BUFFER: 0x8892,
        STATIC_DRAW: 0x88e4,
        DYNAMIC_DRAW: 0x88e8,
        FLOAT: 0x1406,
        TRIANGLES: 0x0004,
        LINES: 0x0001,
        VERTEX_SHADER: 0x8b31,
        FRAGMENT_SHADER: 0x8b30,
        COMPILE_STATUS: 0x8b81,
        LINK_STATUS: 0x8b82,
    };
}

function makeCanvas(gl) {
    const host = document.createElement("div");
    host.style.cssText = "position:relative;width:400px;height:300px;";
    const canvas = document.createElement("canvas");
    host.appendChild(canvas);
    document.body.appendChild(host);
    Object.defineProperty(canvas, "clientWidth", { value: 400 });
    Object.defineProperty(canvas, "clientHeight", { value: 300 });
    canvas.getBoundingClientRect = () => ({ left: 10, top: 20, width: 400, height: 300 });
    canvas.setPointerCapture = vi.fn();
    canvas.releasePointerCapture = vi.fn();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(function (type, opts) {
        if (this === canvas && type === "webgl2") return gl;
        if (type === "2d") {
            return {
                clearRect: vi.fn(),
                drawImage: vi.fn(),
                getImageData: () => ({
                    data: new Uint8ClampedArray(128 * 128 * 4).fill(255),
                    width: 128,
                    height: 128,
                }),
                putImageData: vi.fn(),
                save: vi.fn(),
                restore: vi.fn(),
                setTransform: vi.fn(),
                strokeText: vi.fn(),
                fillText: vi.fn(),
            };
        }
        return null;
    });
    return canvas;
}

describe("networkVisualiserWebGLEngine", () => {
    beforeEach(() => {
        clearSceneGlobals();
    });

    afterEach(() => {
        clearSceneGlobals();
        vi.restoreAllMocks();
    });

    it("isVisualiserWebGLSceneReady requires scene exports", () => {
        expect(isVisualiserWebGLSceneReady()).toBe(false);
        installSceneReadyStubs();
        expect(isVisualiserWebGLSceneReady()).toBe(true);
    });

    it("canUseVisualiserWebGL is false without scene readiness", () => {
        expect(canUseVisualiserWebGL()).toBe(false);
    });

    it("truncateWebGLLabel caps long names", () => {
        expect(truncateWebGLLabel("")).toBeNull();
        expect(truncateWebGLLabel(null)).toBeNull();
        expect(truncateWebGLLabel("short")).toBe("short");
        const long = "a".repeat(WEBGL_LABEL_MAX_CHARS + 10);
        const out = truncateWebGLLabel(long);
        expect(out.length).toBe(WEBGL_LABEL_MAX_CHARS);
        expect(out.endsWith("...")).toBe(true);
    });

    it("collectWebGLLabels follows canvas LOD bands", () => {
        const nodes = new Float32Array([
            0, 0, 50, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            10, 20, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            30, 40, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ]);
        const labelByIndex = ["Local", "eth0", "Alice"];
        const idByIndex = ["me", "eth0", "peer1"];
        const base = { sceneCount: 3, nodes, labelByIndex, idByIndex };

        expect(collectWebGLLabels({ ...base, zoom: 0.1 })).toEqual([]);
        expect(collectWebGLLabels({ ...base, zoom: 0.3 }).map((l) => l.text)).toEqual(["Local"]);
        expect(
            collectWebGLLabels({ ...base, zoom: 0.3, hoverId: "peer1" }).map((l) => l.text).sort()
        ).toEqual(["Alice", "Local"]);
        const high = collectWebGLLabels({ ...base, zoom: 0.8 });
        expect(high.map((l) => l.text)).toEqual(["Local", "eth0", "Alice"]);
        expect(high[0].fontSize).toBe(16);
        expect(high[1].fontSize).toBe(11);
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

    it("graphToSceneRequest keeps zoom 0 so Scene.Set can preserve camera", () => {
        const req = graphToSceneRequest([], [], { width: 100, height: 100, zoom: 0, camX: 12, camY: -4 });
        expect(req.zoom).toBe(0);
        expect(req.cam_x).toBe(12);
        expect(req.cam_y).toBe(-4);
        const def = graphToSceneRequest([], [], { width: 100, height: 100 });
        expect(def.zoom).toBe(1);
    });

    it("graphToSceneRequest marks disconnected interfaces and discovered peers", () => {
        const req = graphToSceneRequest(
            [
                {
                    id: "down",
                    group: "interface",
                    image: "/assets/images/network-visualiser/interface_disconnected.png",
                    color: { border: "#ef4444" },
                },
                { id: "disc", group: "discovered", color: "#a855f7" },
            ],
            [],
            { width: 100, height: 100, zoom: 1 }
        );
        expect(req.nodes[0].kind).toBe(KIND_IFACE_OFF);
        expect(req.nodes[1].kind).toBe(KIND_DISCOVERED);
        expect(req.nodes[1].r).toBeCloseTo(168 / 255);
    });

    it("graphToSceneRequest skips incomplete edges and nodes", () => {
        const req = graphToSceneRequest(
            [{ id: "" }, { group: "me" }, { id: "ok", x: 1, y: 2 }],
            [{ from: "a" }, { to: "b" }, { from: "ok", to: "ok" }],
            { width: 10, height: 10 }
        );
        expect(req.nodes).toHaveLength(1);
        expect(req.nodes[0].id).toBe("ok");
        expect(req.edges).toHaveLength(1);
        expect(req.zoom).toBe(1);
    });

    it("pointerDistance and midpoint support pinch zoom math", () => {
        const a = { x: 0, y: 0 };
        const b = { x: 30, y: 40 };
        expect(pointerDistance(a, b)).toBe(50);
        expect(pointerMidpoint(a, b)).toEqual({ x: 15, y: 20 });
    });

    it("pinch zoom factor is distance ratio around midpoint", () => {
        const startA = { x: 100, y: 100 };
        const startB = { x: 200, y: 100 };
        const endA = { x: 80, y: 100 };
        const endB = { x: 220, y: 100 };
        const startDist = pointerDistance(startA, startB);
        const endDist = pointerDistance(endA, endB);
        expect(startDist).toBe(100);
        expect(endDist).toBe(140);
        expect(endDist / startDist).toBeCloseTo(1.4);
        expect(pointerMidpoint(endA, endB)).toEqual({ x: 150, y: 100 });
    });
});

describe("networkVisualiserWebGL textures", () => {
    it("atlasUvForSlot maps grid cells", () => {
        expect(atlasUvForSlot(0)).toEqual({ u: 0, v: 0 });
        expect(atlasUvForSlot(1).u).toBeCloseTo(1 / ATLAS_COLS);
        expect(atlasUvForSlot(ATLAS_COLS).v).toBeCloseTo(1 / ATLAS_ROWS);
        const last = atlasUvForSlot(ATLAS_COLS * ATLAS_ROWS - 1);
        expect(last.u).toBeCloseTo((ATLAS_COLS - 1) / ATLAS_COLS);
        expect(last.v).toBeCloseTo((ATLAS_ROWS - 1) / ATLAS_ROWS);
    });

    it("resolveVisualiserAssetUrl keeps blob/data/http URLs", () => {
        expect(resolveVisualiserAssetUrl("blob:http://localhost/x")).toBe("blob:http://localhost/x");
        expect(resolveVisualiserAssetUrl("data:image/png;base64,xx")).toBe("data:image/png;base64,xx");
        expect(resolveVisualiserAssetUrl("https://example.com/a.png")).toBe("https://example.com/a.png");
    });

    it("resolveVisualiserAssetUrl absolutizes root paths", () => {
        const origin = window.location.origin;
        expect(resolveVisualiserAssetUrl("/assets/images/reticulum_logo_512.png")).toBe(
            `${origin}/assets/images/reticulum_logo_512.png`
        );
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

    it("mergeSceneNodesWithTextures handles multiple nodes and reuses scratch", () => {
        const scene = new Float32Array(SCENE_NODE_STRIDE * 2);
        scene[0] = 1;
        scene[SCENE_NODE_STRIDE] = 5;
        const scratch = new Float32Array(NODE_STRIDE * 4);
        const meta = [
            { useTex: 1, u: 0.1, v: 0.2 },
            { useTex: 0, u: 0, v: 0 },
        ];
        const out = mergeSceneNodesWithTextures(scene, meta, scratch);
        expect(out.length).toBe(NODE_STRIDE * 2);
        expect(out.buffer).toBe(scratch.buffer);
        expect(out[0]).toBe(1);
        expect(out[7]).toBe(1);
        expect(out[NODE_STRIDE]).toBe(5);
        expect(out[NODE_STRIDE + 7]).toBe(0);
    });

    it("mergeSceneNodesWithTextures tolerates empty input", () => {
        expect(mergeSceneNodesWithTextures(null, []).length).toBe(0);
        expect(mergeSceneNodesWithTextures(new Float32Array(0), []).length).toBe(0);
    });

    it("tryCreateWebGL2Context returns null for invalid canvas", () => {
        expect(tryCreateWebGL2Context(null)).toBeNull();
        expect(tryCreateWebGL2Context({})).toBeNull();
    });
});

describe("createVisualiserWebGLEngine interactions", () => {
    let engine;
    let canvas;
    let gl;
    let zoomAt;

    beforeEach(() => {
        clearSceneGlobals();
        zoomAt = vi.fn();
        gl = stubGl();
        installSceneReadyStubs({
            meshchatxVisualiserSceneSet: () => JSON.stringify({ ok: true, nodes: 2, edges: 0 }),
            meshchatxVisualiserSceneGetDrawBuffers: () => ({
                ok: true,
                nodes: new Float32Array(SCENE_NODE_STRIDE * 2),
                edges: new Float32Array(0),
                camX: 0,
                camY: 0,
                zoom: 1,
                nodeCount: 2,
                edgeCount: 0,
            }),
            meshchatxVisualiserScenePick: () => null,
        });
        globalThis.meshchatxVisualiserSceneZoomAt = (...args) => zoomAt(...args);
        globalThis.meshchatxVisualiserScenePanBy = vi.fn();
        globalThis.meshchatxVisualiserSceneGetPositions = () => JSON.stringify({ positions: { me: { x: 0, y: 0 } } });
        globalThis.meshchatxVisualiserSceneResize = vi.fn();
        canvas = makeCanvas(gl);
        engine = createVisualiserWebGLEngine(canvas, {
            getLiveLayout: () => false,
            isDark: () => false,
        });
    });

    afterEach(() => {
        if (engine) {
            engine.destroy();
            engine = null;
        }
        canvas?.parentElement?.remove();
        clearSceneGlobals();
        vi.restoreAllMocks();
    });

    it("throws without WASM scene readiness", () => {
        engine.destroy();
        engine = null;
        clearSceneGlobals();
        const c = makeCanvas(stubGl());
        expect(() => createVisualiserWebGLEngine(c)).toThrow(/WASM scene unavailable/);
        c.parentElement?.remove();
    });

    it("pinch gesture calls SceneZoomAt with distance ratio", () => {
        const fire = (type, props) => {
            const ev = new Event(type, { bubbles: true });
            Object.assign(ev, props);
            canvas.dispatchEvent(ev);
        };

        // css = client - rect.left/top  => 110-10=100, 120-20=100
        fire("pointerdown", { pointerId: 1, pointerType: "touch", button: 0, clientX: 110, clientY: 120 });
        fire("pointerdown", { pointerId: 2, pointerType: "touch", button: 0, clientX: 210, clientY: 120 });
        // dist 100 -> 140 (css x 100 and 240), mid css (170, 100)
        fire("pointermove", { pointerId: 2, pointerType: "touch", button: 0, clientX: 250, clientY: 120 });

        expect(zoomAt).toHaveBeenCalled();
        const [sx, sy, factor] = zoomAt.mock.calls.at(-1);
        expect(factor).toBeCloseTo(1.4, 5);
        expect(sx).toBeCloseTo(170);
        expect(sy).toBeCloseTo(100);
        expect(globalThis.meshchatxVisualiserScenePanBy).not.toHaveBeenCalled();
    });

    it("wheel zoom calls SceneZoomAt", () => {
        const ev = new Event("wheel", { bubbles: true, cancelable: true });
        Object.assign(ev, { clientX: 60, clientY: 80, deltaY: -100 });
        canvas.dispatchEvent(ev);
        // css: 60-10=50, 80-20=60
        expect(zoomAt).toHaveBeenCalledWith(50, 60, 1.12);
    });

    it("setGraph and updateNodeImages upload icon textures", async () => {
        const bitmap = { width: 32, height: 32, close: vi.fn() };
        vi.stubGlobal(
            "fetch",
            vi.fn(async () => ({
                ok: true,
                blob: async () => new Blob([new Uint8Array([1, 2, 3])], { type: "image/png" }),
            }))
        );
        vi.stubGlobal(
            "createImageBitmap",
            vi.fn(async () => bitmap)
        );

        engine.setGraph(
            [
                {
                    id: "me",
                    group: "me",
                    label: "Local",
                    image: "/assets/images/reticulum_logo_512.png",
                    x: 0,
                    y: 0,
                },
                {
                    id: "peer",
                    group: "announce",
                    label: "Peer",
                    image: "/assets/images/network-visualiser/user.png",
                    x: 10,
                    y: 10,
                },
            ],
            [],
            { preserveCamera: false, zoom: 1 }
        );
        expect(engine.getCounts()).toEqual({ nodes: 2, edges: 0 });
        expect(engine.getPositions()).toEqual({ me: { x: 0, y: 0 } });

        await vi.waitFor(() => {
            expect(gl.texSubImage2D).toHaveBeenCalled();
        });

        const uploadsBefore = gl.texSubImage2D.mock.calls.length;
        engine.updateNodeImages([{ id: "peer", image: "blob:custom-icon" }]);
        await vi.waitFor(() => {
            expect(gl.texSubImage2D.mock.calls.length).toBeGreaterThan(uploadsBefore);
        });
    });

    it("setGraph applies kind default icons when image missing", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn(async () => ({
                ok: true,
                blob: async () => new Blob([new Uint8Array([9])], { type: "image/png" }),
            }))
        );
        vi.stubGlobal(
            "createImageBitmap",
            vi.fn(async () => ({ width: 16, height: 16, close: vi.fn() }))
        );

        engine.setGraph([{ id: "me", group: "me", label: "Me", x: 0, y: 0 }], [], {
            preserveCamera: false,
            zoom: 1,
        });
        await vi.waitFor(() => {
            expect(globalThis.fetch).toHaveBeenCalled();
            expect(String(globalThis.fetch.mock.calls[0][0])).toContain("reticulum_logo_512.png");
        });
    });

    it("sets touch-action none for mobile gestures", () => {
        expect(canvas.style.touchAction).toBe("none");
    });
});
