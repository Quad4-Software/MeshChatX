// SPDX-License-Identifier: 0BSD

/**
 * WebGL2 canvas renderer for MeshChatX network visualiser.
 * Draws instanced circular sprites (textured when available) and line edges.
 */

/** WASM / scene pack: x y size r g b a kind */
export const SCENE_NODE_STRIDE = 8;
/** Draw instance: x y size r g b a useTex u v */
export const NODE_STRIDE = 10;
export const EDGE_STRIDE = 8;

export type NodeTexMeta = { useTex: number; u: number; v: number };
export type AtlasUv = { u: number; v: number };
export type IconPixelMode = "opaque" | "glyph";
export type IconPixelStats = { painted: number; glyphPixels: number };
export type VisualiserCamera = { x: number; y: number; zoom: number };
export type VisualiserLabel = { x: number; y: number; size: number; text: string; fontSize?: number };
export type VisualiserCssSize = { width: number; height: number };
export type NetworkVisualiserWebGL = {
    draw: (
        nodes: Float32Array | null | undefined,
        edges: Float32Array | null | undefined,
        camera: VisualiserCamera | null | undefined,
        dark: boolean,
        labels?: VisualiserLabel[] | null
    ) => VisualiserCssSize;
    resize: () => VisualiserCssSize;
    destroy: () => void;
    clearBackground: (dark: boolean) => void;
    ensureIcon: (url: string) => Promise<number | null>;
    iconUv: (slot: number) => AtlasUv;
    getIconSlot: (url: string) => number | null;
    getCssSize: () => VisualiserCssSize;
};

const ATLAS_CELL = 128;
const ATLAS_COLS = 16;
const ATLAS_ROWS = 16;
const ATLAS_CAPACITY = ATLAS_COLS * ATLAS_ROWS;

/** Soft-edge AA width in UV radius units (1.0 = disc edge). Keep tight to avoid fuzzy blobs. */
export const NODE_EDGE_INNER = 0.97;
/** Border ring starts inside the disc (untextured and under glyphs). */
export const NODE_BORDER_INNER = 0.82;
export const NODE_BORDER_OUTER = 0.97;

const NODE_VS = `#version 300 es
layout(location=0) in vec2 a_corner;
layout(location=1) in vec2 a_center;
layout(location=2) in float a_size;
layout(location=3) in vec4 a_color;
layout(location=4) in float a_useTex;
layout(location=5) in vec2 a_uvOrigin;
uniform vec2 u_resolution;
uniform vec2 u_camera;
uniform float u_zoom;
out vec4 v_color;
out vec2 v_uv;
out float v_useTex;
out vec2 v_uvOrigin;
void main() {
  v_uv = a_corner;
  v_color = a_color;
  v_useTex = a_useTex;
  v_uvOrigin = a_uvOrigin;
  float r = max(a_size, 2.0);
  vec2 world = a_center + a_corner * r;
  vec2 screen = (world - u_camera) * u_zoom + u_resolution * 0.5;
  vec2 clip = (screen / u_resolution) * 2.0 - 1.0;
  clip.y = -clip.y;
  gl_Position = vec4(clip, 0.0, 1.0);
}
`;

const NODE_FS = `#version 300 es
precision mediump float;
in vec4 v_color;
in vec2 v_uv;
in float v_useTex;
in vec2 v_uvOrigin;
uniform sampler2D u_atlas;
uniform vec2 u_cellUv;
out vec4 outColor;
void main() {
  float d = length(v_uv);
  if (d > 1.0) discard;
  // Tight AA so nodes read as crisp discs, not soft fuzzy blobs.
  float edge = smoothstep(1.0, ${NODE_EDGE_INNER.toFixed(2)}, d);
  float border = smoothstep(${NODE_BORDER_INNER.toFixed(2)}, ${NODE_BORDER_OUTER.toFixed(2)}, d);
  vec3 fill = v_color.rgb;
  vec3 rim = fill * 0.55;
  if (v_useTex > 0.5) {
    vec2 local = v_uv * 0.5 + 0.5;
    vec2 texUV = v_uvOrigin + local * u_cellUv;
    vec4 tex = texture(u_atlas, texUV);
    float texA = clamp(tex.a, 0.0, 1.0);
    // Colored disc from node color, optional glyph/logo from atlas on top.
    vec3 rgb = mix(fill, tex.rgb, texA);
    rgb = mix(rgb, rim, border * (1.0 - texA));
    float a = edge * v_color.a;
    if (a < 0.02) discard;
    outColor = vec4(rgb, a);
  } else {
    vec3 rgb = mix(fill, rim, border);
    outColor = vec4(rgb, v_color.a * edge);
  }
}
`;

const EDGE_VS = `#version 300 es
layout(location=0) in vec2 a_pos;
layout(location=1) in vec4 a_color;
uniform vec2 u_resolution;
uniform vec2 u_camera;
uniform float u_zoom;
out vec4 v_color;
void main() {
  v_color = a_color;
  vec2 screen = (a_pos - u_camera) * u_zoom + u_resolution * 0.5;
  vec2 clip = (screen / u_resolution) * 2.0 - 1.0;
  clip.y = -clip.y;
  gl_Position = vec4(clip, 0.0, 1.0);
}
`;

const EDGE_FS = `#version 300 es
precision mediump float;
in vec4 v_color;
out vec4 outColor;
void main() {
  outColor = v_color;
}
`;

function compile(gl: WebGL2RenderingContext, type: number, src: string): WebGLShader {
    const sh = gl.createShader(type);
    if (!sh) throw new Error("WebGL shader create failed");
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        const info = gl.getShaderInfoLog(sh);
        gl.deleteShader(sh);
        throw new Error(`WebGL shader: ${info}`);
    }
    return sh;
}

function link(gl: WebGL2RenderingContext, vsSrc: string, fsSrc: string): WebGLProgram {
    const vs = compile(gl, gl.VERTEX_SHADER, vsSrc);
    const fs = compile(gl, gl.FRAGMENT_SHADER, fsSrc);
    const prog = gl.createProgram();
    if (!prog) throw new Error("WebGL program create failed");
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
        const info = gl.getProgramInfoLog(prog);
        gl.deleteProgram(prog);
        throw new Error(`WebGL program: ${info}`);
    }
    return prog;
}

/**
 * Merge WASM scene node packs with atlas UVs into draw instances.
 */
export function mergeSceneNodesWithTextures(
    sceneNodes: Float32Array | null | undefined,
    texMeta: NodeTexMeta[] | null | undefined,
    dst?: Float32Array | null
): Float32Array {
    if (!sceneNodes?.length) {
        return new Float32Array(0);
    }
    const count = Math.floor(sceneNodes.length / SCENE_NODE_STRIDE);
    const need = count * NODE_STRIDE;
    const out = dst && dst.length >= need ? dst : new Float32Array(need);
    for (let i = 0; i < count; i++) {
        const s = i * SCENE_NODE_STRIDE;
        const d = i * NODE_STRIDE;
        out[d] = sceneNodes[s];
        out[d + 1] = sceneNodes[s + 1];
        out[d + 2] = sceneNodes[s + 2];
        out[d + 3] = sceneNodes[s + 3];
        out[d + 4] = sceneNodes[s + 4];
        out[d + 5] = sceneNodes[s + 5];
        out[d + 6] = sceneNodes[s + 6];
        const meta = texMeta?.[i];
        out[d + 7] = meta?.useTex ? 1 : 0;
        out[d + 8] = meta?.u ?? 0;
        out[d + 9] = meta?.v ?? 0;
    }
    return need === out.length ? out : out.subarray(0, need);
}

/**
 * Atlas UV origin for a slot index.
 */
export function atlasUvForSlot(slot: number): AtlasUv {
    const col = slot % ATLAS_COLS;
    const row = Math.floor(slot / ATLAS_COLS);
    return {
        u: col / ATLAS_COLS,
        v: row / ATLAS_ROWS,
    };
}

export function tryCreateWebGL2Context(canvas: HTMLCanvasElement | null | undefined): WebGL2RenderingContext | null {
    if (!canvas || typeof canvas.getContext !== "function") return null;
    try {
        return canvas.getContext("webgl2", {
            alpha: false,
            antialias: true,
            depth: false,
            stencil: false,
            powerPreference: "high-performance",
        });
    } catch {
        return null;
    }
}

/**
 * Resolve a same-origin asset path against the Vite/app base URL.
 * Absolute http(s)/blob/data URLs are returned unchanged.
 */
export function resolveVisualiserAssetUrl(url: string | null | undefined): string {
    if (!url || typeof url !== "string") return "";
    const trimmed = url.trim();
    if (!trimmed) return "";
    // Reject file: and other non-web schemes. Icons are same-origin paths or http(s)/blob/data.
    if (/^(?:file:|javascript:|vbscript:)/i.test(trimmed)) return "";
    if (/^(?:blob:|data:|https?:)/i.test(trimmed)) return trimmed;
    if (typeof window !== "undefined" && window.location?.origin && trimmed.startsWith("/")) {
        const base = typeof import.meta !== "undefined" && import.meta.env?.BASE_URL ? import.meta.env.BASE_URL : "/";
        const root = String(base || "/").replace(/\/?$/, "/");
        if (root !== "/" && !trimmed.startsWith(root)) {
            return `${window.location.origin}${root.replace(/\/$/, "")}${trimmed}`;
        }
        return `${window.location.origin}${trimmed}`;
    }
    return trimmed;
}

/**
 * True when the asset is a solid-fill network-visualiser badge (colored disc + light glyph).
 * Those should be converted to white-on-transparent glyphs so the shader can paint node color.
 */
export function isGlyphStyleVisualiserIcon(url: string | null | undefined): boolean {
    if (!url || typeof url !== "string") return false;
    return /\/network-visualiser\//i.test(url);
}

/**
 * Prepare atlas RGBA pixels for upload.
 *
 * - opaque: keep soft alpha (logo AA). Only promote RGB-with-a=0 PNG quirks.
 * - glyph: keep bright glyph coverage as soft alpha (preserves AA), clear fill
 *
 */
export function prepareVisualiserIconPixels(
    data: Uint8ClampedArray | Uint8Array,
    mode: IconPixelMode = "opaque"
): IconPixelStats {
    let painted = 0;
    let glyphPixels = 0;
    if (!data || data.length < 4) return { painted: 0, glyphPixels: 0 };
    const glyphMode = mode === "glyph";
    for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        const a = data[i + 3];
        if (!(r | g | b | a)) continue;
        painted += 1;
        if (glyphMode) {
            // Soft coverage from luma so badge AA edges stay smooth when scaled.
            const luma = 0.299 * r + 0.587 * g + 0.114 * b;
            const maxc = Math.max(r, g, b);
            const minc = Math.min(r, g, b);
            const sat = maxc - minc;
            let cover = 0;
            if (luma >= 210) {
                cover = 1;
            } else if (luma >= 150) {
                cover = (luma - 150) / 60;
                if (sat > 50) {
                    cover *= Math.max(0, 1 - (sat - 50) / 120);
                }
            } else if (luma >= 130 && sat < 35) {
                cover = ((luma - 130) / 20) * 0.45;
            }
            if (cover <= 0.02) {
                data[i] = 0;
                data[i + 1] = 0;
                data[i + 2] = 0;
                data[i + 3] = 0;
            } else {
                const alpha = Math.round(Math.min(1, cover) * 255);
                data[i] = 255;
                data[i + 1] = 255;
                data[i + 2] = 255;
                data[i + 3] = alpha;
                if (alpha >= 24) glyphPixels += 1;
            }
        } else if (a === 0 && (r !== 0 || g !== 0 || b !== 0)) {
            // Some RGB PNGs store color with a=0. Promote those only.
            // Never crush existing soft alpha (RNS logo fringe looked jagged).
            data[i + 3] = 255;
        }
    }
    return { painted, glyphPixels };
}

/**
 * Downscale large bitmaps in steps before the final atlas blit.
 * A single 512→116 drawImage looks soft/jagged on HiDPI discs.
 */
export function drawImageToAtlasCell(
    ctx: CanvasRenderingContext2D | null | undefined,
    source: CanvasImageSource | null | undefined,
    sw: number,
    sh: number,
    dx: number,
    dy: number,
    dw: number,
    dh: number
): void {
    if (!ctx || !source || !(dw > 0 && dh > 0 && sw > 0 && sh > 0)) return;
    ctx.imageSmoothingEnabled = true;
    if ("imageSmoothingQuality" in ctx) {
        ctx.imageSmoothingQuality = "high";
    }
    if (typeof document === "undefined" || (sw <= dw * 2 && sh <= dh * 2)) {
        ctx.drawImage(source, dx, dy, dw, dh);
        return;
    }
    let curW = sw;
    let curH = sh;
    let cur = source;
    const temps: HTMLCanvasElement[] = [];
    try {
        while (curW > dw * 2 || curH > dh * 2) {
            const nextW = Math.max(dw, Math.ceil(curW / 2));
            const nextH = Math.max(dh, Math.ceil(curH / 2));
            const tmp = document.createElement("canvas");
            tmp.width = nextW;
            tmp.height = nextH;
            const tctx = tmp.getContext("2d", { alpha: true });
            if (!tctx) break;
            tctx.imageSmoothingEnabled = true;
            if ("imageSmoothingQuality" in tctx) {
                tctx.imageSmoothingQuality = "high";
            }
            tctx.drawImage(cur, 0, 0, nextW, nextH);
            temps.push(tmp);
            cur = tmp;
            curW = nextW;
            curH = nextH;
        }
        ctx.drawImage(cur, dx, dy, dw, dh);
    } finally {
        // Drop temp canvases promptly (no explicit dispose API).
        temps.length = 0;
    }
}

function createIconAtlas(gl: WebGL2RenderingContext) {
    const width = ATLAS_COLS * ATLAS_CELL;
    const height = ATLAS_ROWS * ATLAS_CELL;
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    // Cap mip depth so neighbouring atlas cells do not bleed into logos.
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_BASE_LEVEL, 0);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAX_LEVEL, 2);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    gl.generateMipmap(gl.TEXTURE_2D);

    const urlToSlot = new Map<string, number>();
    const pending = new Map<string, Promise<number | null>>();
    const freeSlots: number[] = [];
    let nextSlot = 0;
    const scratch = typeof document !== "undefined" ? document.createElement("canvas") : null;
    if (scratch) {
        scratch.width = ATLAS_CELL;
        scratch.height = ATLAS_CELL;
    }
    const scratchCtx = scratch?.getContext?.("2d", { willReadFrequently: true, alpha: true }) || null;
    if (scratchCtx) {
        scratchCtx.imageSmoothingEnabled = true;
        if ("imageSmoothingQuality" in scratchCtx) {
            scratchCtx.imageSmoothingQuality = "high";
        }
    }

    function allocSlot(): number | null {
        if (freeSlots.length > 0) {
            const slot = freeSlots.pop();
            return slot == null ? null : slot;
        }
        if (nextSlot >= ATLAS_CAPACITY) return null;
        return nextSlot++;
    }

    function paintSlot(
        slot: number,
        source: CanvasImageSource & {
            width?: number;
            height?: number;
            videoWidth?: number;
            videoHeight?: number;
            close?: () => void;
        },
        url: string
    ): boolean {
        if (!scratchCtx || !scratch) return false;
        scratchCtx.save();
        scratchCtx.setTransform(1, 0, 0, 1, 0, 0);
        scratchCtx.globalCompositeOperation = "source-over";
        scratchCtx.imageSmoothingEnabled = true;
        if ("imageSmoothingQuality" in scratchCtx) {
            scratchCtx.imageSmoothingQuality = "high";
        }
        scratchCtx.clearRect(0, 0, ATLAS_CELL, ATLAS_CELL);
        const sw = source.width || source.videoWidth || ATLAS_CELL;
        const sh = source.height || source.videoHeight || ATLAS_CELL;
        if (!(sw > 0 && sh > 0)) {
            scratchCtx.restore();
            return false;
        }
        // Pad so circular clip and mip filtering do not chew logo AA.
        const pad = isGlyphStyleVisualiserIcon(url) ? 2 : 6;
        const fit = ATLAS_CELL - pad * 2;
        const scale = Math.min(fit / sw, fit / sh);
        const dw = Math.max(1, Math.round(sw * scale));
        const dh = Math.max(1, Math.round(sh * scale));
        const dx = Math.floor((ATLAS_CELL - dw) / 2);
        const dy = Math.floor((ATLAS_CELL - dh) / 2);
        drawImageToAtlasCell(scratchCtx, source, sw, sh, dx, dy, dw, dh);
        const pixels = scratchCtx.getImageData(0, 0, ATLAS_CELL, ATLAS_CELL);
        const data = pixels.data;
        const mode = isGlyphStyleVisualiserIcon(url) ? "glyph" : "opaque";
        if (mode === "glyph") {
            const backup = new Uint8ClampedArray(data);
            const { painted, glyphPixels } = prepareVisualiserIconPixels(data, "glyph");
            if (painted < 8) {
                scratchCtx.restore();
                return false;
            }
            if (glyphPixels < 8) {
                data.set(backup);
                prepareVisualiserIconPixels(data, "opaque");
            }
        } else {
            const { painted } = prepareVisualiserIconPixels(data, "opaque");
            if (painted < 8) {
                scratchCtx.restore();
                return false;
            }
        }
        scratchCtx.putImageData(pixels, 0, 0);
        scratchCtx.restore();
        const col = slot % ATLAS_COLS;
        const row = Math.floor(slot / ATLAS_COLS);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
        gl.texSubImage2D(gl.TEXTURE_2D, 0, col * ATLAS_CELL, row * ATLAS_CELL, gl.RGBA, gl.UNSIGNED_BYTE, scratch);
        gl.generateMipmap(gl.TEXTURE_2D);
        return true;
    }

    async function loadImageSource(url: string): Promise<CanvasImageSource> {
        const resolved = resolveVisualiserAssetUrl(url);
        if (typeof createImageBitmap === "function") {
            try {
                const res = await fetch(resolved);
                if (!res.ok) throw new Error(`icon fetch ${res.status}`);
                const blob = await res.blob();
                return await createImageBitmap(blob);
            } catch {
                // Fall through to HTMLImageElement.
            }
        }
        const img = await new Promise<HTMLImageElement>((resolve, reject) => {
            const el = new Image();
            el.decoding = "sync";
            el.onload = () => resolve(el);
            el.onerror = () => reject(new Error(`icon load failed: ${resolved}`));
            el.src = resolved;
        });
        if (typeof img.decode === "function") {
            try {
                await img.decode();
            } catch {
                // decode() can reject for already-decoded bitmaps
            }
        }
        return img;
    }

    async function ensure(url: string): Promise<number | null> {
        if (!url || typeof url !== "string") return null;
        if (urlToSlot.has(url)) return urlToSlot.get(url) ?? null;
        if (pending.has(url)) return (await pending.get(url)) ?? null;
        const slot = allocSlot();
        if (slot == null) return null;
        const work = loadImageSource(url)
            .then((img) => {
                const ok = paintSlot(
                    slot,
                    img as CanvasImageSource & { width?: number; height?: number; close?: () => void },
                    url
                );
                if (img && typeof (img as { close?: () => void }).close === "function") {
                    try {
                        (img as { close: () => void }).close();
                    } catch {
                        /* ignore */
                    }
                }
                if (!ok) {
                    freeSlots.push(slot);
                    pending.delete(url);
                    return null;
                }
                urlToSlot.set(url, slot);
                pending.delete(url);
                return slot;
            })
            .catch(() => {
                pending.delete(url);
                freeSlots.push(slot);
                return null;
            });
        pending.set(url, work);
        return work;
    }

    function destroy() {
        gl.deleteTexture(texture);
        urlToSlot.clear();
        pending.clear();
    }

    return {
        texture,
        ensure,
        uvForSlot: atlasUvForSlot,
        cellUv: { x: 1 / ATLAS_COLS, y: 1 / ATLAS_ROWS },
        destroy,
        getSlot: (url: string): number | null => urlToSlot.get(url) ?? null,
    };
}

export function createNetworkVisualiserWebGL(
    canvas: HTMLCanvasElement,
    gl: WebGL2RenderingContext
): NetworkVisualiserWebGL {
    const nodeProg = link(gl, NODE_VS, NODE_FS);
    const edgeProg = link(gl, EDGE_VS, EDGE_FS);
    const atlas = createIconAtlas(gl);

    const nodeCornerBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, nodeCornerBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);

    const nodeInstanceBuf = gl.createBuffer();
    const edgeBuf = gl.createBuffer();

    const nodeVao = gl.createVertexArray();
    gl.bindVertexArray(nodeVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, nodeCornerBuf);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

    gl.bindBuffer(gl.ARRAY_BUFFER, nodeInstanceBuf);
    const strideBytes = NODE_STRIDE * 4;
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 2, gl.FLOAT, false, strideBytes, 0);
    gl.vertexAttribDivisor(1, 1);
    gl.enableVertexAttribArray(2);
    gl.vertexAttribPointer(2, 1, gl.FLOAT, false, strideBytes, 8);
    gl.vertexAttribDivisor(2, 1);
    gl.enableVertexAttribArray(3);
    gl.vertexAttribPointer(3, 4, gl.FLOAT, false, strideBytes, 12);
    gl.vertexAttribDivisor(3, 1);
    gl.enableVertexAttribArray(4);
    gl.vertexAttribPointer(4, 1, gl.FLOAT, false, strideBytes, 28);
    gl.vertexAttribDivisor(4, 1);
    gl.enableVertexAttribArray(5);
    gl.vertexAttribPointer(5, 2, gl.FLOAT, false, strideBytes, 32);
    gl.vertexAttribDivisor(5, 1);
    gl.bindVertexArray(null);

    const edgeVao = gl.createVertexArray();
    gl.bindVertexArray(edgeVao);
    gl.bindBuffer(gl.ARRAY_BUFFER, edgeBuf);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 6 * 4, 0);
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 4, gl.FLOAT, false, 6 * 4, 8);
    gl.bindVertexArray(null);

    const uNodeRes = gl.getUniformLocation(nodeProg, "u_resolution");
    const uNodeCam = gl.getUniformLocation(nodeProg, "u_camera");
    const uNodeZoom = gl.getUniformLocation(nodeProg, "u_zoom");
    const uNodeAtlas = gl.getUniformLocation(nodeProg, "u_atlas");
    const uNodeCellUv = gl.getUniformLocation(nodeProg, "u_cellUv");
    const uEdgeRes = gl.getUniformLocation(edgeProg, "u_resolution");
    const uEdgeCam = gl.getUniformLocation(edgeProg, "u_camera");
    const uEdgeZoom = gl.getUniformLocation(edgeProg, "u_zoom");

    let cssW = 1;
    let cssH = 1;
    let nodeCount = 0;
    let edgeVertexCount = 0;
    let edgeScratch = new Float32Array(0);

    let labelCanvas: HTMLCanvasElement | null = null;
    let labelCtx: CanvasRenderingContext2D | null = null;
    if (typeof document !== "undefined" && canvas?.parentElement) {
        labelCanvas = document.createElement("canvas");
        labelCanvas.className = "network-webgl-labels";
        labelCanvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1;";
        canvas.parentElement.appendChild(labelCanvas);
        labelCtx = labelCanvas.getContext("2d", { alpha: true });
        if (labelCtx) {
            labelCtx.imageSmoothingEnabled = true;
            if ("imageSmoothingQuality" in labelCtx) {
                labelCtx.imageSmoothingQuality = "high";
            }
        }
    }

    function resize(): VisualiserCssSize {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const rect = canvas.getBoundingClientRect();
        cssW = Math.max(1, rect.width || canvas.clientWidth || 1);
        cssH = Math.max(1, rect.height || canvas.clientHeight || 1);
        const bw = Math.max(1, Math.floor(cssW * dpr));
        const bh = Math.max(1, Math.floor(cssH * dpr));
        if (canvas.width !== bw || canvas.height !== bh) {
            canvas.width = bw;
            canvas.height = bh;
        }
        if (labelCanvas && (labelCanvas.width !== bw || labelCanvas.height !== bh)) {
            labelCanvas.width = bw;
            labelCanvas.height = bh;
        }
        gl.viewport(0, 0, canvas.width, canvas.height);
        return { width: cssW, height: cssH };
    }

    function clearBackground(dark: boolean): void {
        resize();
        if (dark) {
            gl.clearColor(0.035, 0.035, 0.04, 1);
        } else {
            gl.clearColor(0.973, 0.98, 0.988, 1);
        }
        gl.clear(gl.COLOR_BUFFER_BIT);
        if (labelCtx && labelCanvas) {
            labelCtx.clearRect(0, 0, labelCanvas.width, labelCanvas.height);
        }
    }

    function draw(
        nodes: Float32Array | null | undefined,
        edges: Float32Array | null | undefined,
        camera: VisualiserCamera | null | undefined,
        dark: boolean,
        labels?: VisualiserLabel[] | null
    ): VisualiserCssSize {
        const size = resize();
        const camX = camera?.x ?? 0;
        const camY = camera?.y ?? 0;
        const zoomRaw = camera?.zoom;
        const zoom = zoomRaw != null && zoomRaw > 0 ? zoomRaw : 1;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);

        if (dark) {
            gl.clearColor(0.035, 0.035, 0.04, 1);
        } else {
            gl.clearColor(0.973, 0.98, 0.988, 1);
        }
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        nodeCount = nodes && nodes.length ? Math.floor(nodes.length / NODE_STRIDE) : 0;
        const edgeData = edges && edges.length ? edges : null;
        const edgeCount = edgeData ? Math.floor(edgeData.length / EDGE_STRIDE) : 0;

        const need = edgeCount * 12;
        if (edgeScratch.length < need) {
            edgeScratch = new Float32Array(Math.max(need, 64));
        }
        for (let i = 0; i < edgeCount; i++) {
            const o = i * EDGE_STRIDE;
            const d = i * 12;
            const x1 = edgeData![o];
            const y1 = edgeData![o + 1];
            const x2 = edgeData![o + 2];
            const y2 = edgeData![o + 3];
            const r = edgeData![o + 4];
            const g = edgeData![o + 5];
            const b = edgeData![o + 6];
            const a = edgeData![o + 7];
            edgeScratch[d] = x1;
            edgeScratch[d + 1] = y1;
            edgeScratch[d + 2] = r;
            edgeScratch[d + 3] = g;
            edgeScratch[d + 4] = b;
            edgeScratch[d + 5] = a;
            edgeScratch[d + 6] = x2;
            edgeScratch[d + 7] = y2;
            edgeScratch[d + 8] = r;
            edgeScratch[d + 9] = g;
            edgeScratch[d + 10] = b;
            edgeScratch[d + 11] = a;
        }
        edgeVertexCount = edgeCount * 2;

        if (edgeVertexCount > 0) {
            gl.useProgram(edgeProg);
            gl.uniform2f(uEdgeRes, size.width, size.height);
            gl.uniform2f(uEdgeCam, camX, camY);
            gl.uniform1f(uEdgeZoom, zoom);
            gl.bindVertexArray(edgeVao);
            gl.bindBuffer(gl.ARRAY_BUFFER, edgeBuf);
            gl.bufferData(gl.ARRAY_BUFFER, edgeScratch.subarray(0, need), gl.DYNAMIC_DRAW);
            gl.lineWidth(1);
            gl.drawArrays(gl.LINES, 0, edgeVertexCount);
            gl.bindVertexArray(null);
        }

        if (nodeCount > 0) {
            gl.useProgram(nodeProg);
            gl.uniform2f(uNodeRes, size.width, size.height);
            gl.uniform2f(uNodeCam, camX, camY);
            gl.uniform1f(uNodeZoom, zoom);
            gl.uniform1i(uNodeAtlas, 0);
            gl.uniform2f(uNodeCellUv, atlas.cellUv.x, atlas.cellUv.y);
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, atlas.texture);
            gl.bindVertexArray(nodeVao);
            gl.bindBuffer(gl.ARRAY_BUFFER, nodeInstanceBuf);
            if (nodes) {
                gl.bufferData(gl.ARRAY_BUFFER, nodes, gl.DYNAMIC_DRAW);
            }
            gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, nodeCount);
            gl.bindVertexArray(null);
        }

        if (labelCtx && labelCanvas) {
            labelCtx.setTransform(1, 0, 0, 1, 0, 0);
            labelCtx.clearRect(0, 0, labelCanvas.width, labelCanvas.height);
            // LOD (when labels appear) is decided by the engine via collectWebGLLabels.
            if (Array.isArray(labels) && labels.length > 0) {
                labelCtx.textAlign = "center";
                labelCtx.textBaseline = "top";
                labelCtx.imageSmoothingEnabled = true;
                const fill = dark ? "#f4f4f5" : "#18181b";
                const stroke = dark ? "rgba(9,9,11,0.75)" : "rgba(255,255,255,0.88)";
                labelCtx.lineJoin = "round";
                labelCtx.miterLimit = 2;
                labelCtx.lineWidth = Math.max(2, Math.round(2.25 * dpr));
                let lastFontKey = "";
                for (const lab of labels) {
                    if (!lab?.text) continue;
                    const sx = (lab.x - camX) * zoom + cssW * 0.5;
                    const sy = (lab.y - camY) * zoom + cssH * 0.5;
                    if (sx < -40 || sy < -20 || sx > cssW + 40 || sy > cssH + 20) continue;
                    const r = Math.max(lab.size || 10, 6) * zoom;
                    // Snap to device pixels to avoid blurry half-pixel text.
                    const tx = Math.round(sx * dpr);
                    const ty = Math.round((sy + r + 4) * dpr);
                    const cssFont = Math.max(11, Number(lab.fontSize) || 11);
                    const fontPx = Math.max(11, Math.round(cssFont * dpr));
                    const fontKey = String(fontPx);
                    if (fontKey !== lastFontKey) {
                        labelCtx.font = `500 ${fontPx}px Inter, system-ui, -apple-system, "Segoe UI", sans-serif`;
                        lastFontKey = fontKey;
                    }
                    labelCtx.strokeStyle = stroke;
                    labelCtx.fillStyle = fill;
                    labelCtx.strokeText(lab.text, tx, ty);
                    labelCtx.fillText(lab.text, tx, ty);
                }
            }
        }

        return size;
    }

    function destroy() {
        atlas.destroy();
        gl.deleteBuffer(nodeCornerBuf);
        gl.deleteBuffer(nodeInstanceBuf);
        gl.deleteBuffer(edgeBuf);
        gl.deleteVertexArray(nodeVao);
        gl.deleteVertexArray(edgeVao);
        gl.deleteProgram(nodeProg);
        gl.deleteProgram(edgeProg);
        if (labelCanvas?.parentElement) {
            labelCanvas.parentElement.removeChild(labelCanvas);
        }
        labelCanvas = null;
        labelCtx = null;
    }

    return {
        draw,
        resize,
        destroy,
        clearBackground,
        ensureIcon: (url: string) => atlas.ensure(url),
        iconUv: (slot: number) => atlas.uvForSlot(slot),
        getIconSlot: (url: string) => atlas.getSlot(url),
        getCssSize: (): VisualiserCssSize => ({ width: cssW, height: cssH }),
    };
}

export { ATLAS_CELL, ATLAS_COLS, ATLAS_ROWS };
