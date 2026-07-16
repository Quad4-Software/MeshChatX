/**
 * WebGL2 canvas renderer for MeshChatX network visualiser.
 * Draws instanced node discs and line edges from WASM float buffers.
 */

const NODE_STRIDE = 8;
const EDGE_STRIDE = 8;

const NODE_VS = `#version 300 es
layout(location=0) in vec2 a_corner;
layout(location=1) in vec2 a_center;
layout(location=2) in float a_size;
layout(location=3) in vec4 a_color;
uniform vec2 u_resolution;
uniform vec2 u_camera;
uniform float u_zoom;
out vec4 v_color;
out vec2 v_uv;
void main() {
  v_uv = a_corner;
  v_color = a_color;
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
out vec4 outColor;
void main() {
  float d = length(v_uv);
  if (d > 1.0) discard;
  float edge = smoothstep(1.0, 0.72, d);
  outColor = vec4(v_color.rgb, v_color.a * edge);
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

function compile(gl, type, src) {
    const sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        const info = gl.getShaderInfoLog(sh);
        gl.deleteShader(sh);
        throw new Error(`WebGL shader: ${info}`);
    }
    return sh;
}

function link(gl, vsSrc, fsSrc) {
    const vs = compile(gl, gl.VERTEX_SHADER, vsSrc);
    const fs = compile(gl, gl.FRAGMENT_SHADER, fsSrc);
    const prog = gl.createProgram();
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
 * @param {HTMLCanvasElement} canvas
 * @returns {WebGL2RenderingContext|null}
 */
export function tryCreateWebGL2Context(canvas) {
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
 * @param {HTMLCanvasElement} canvas
 * @param {WebGL2RenderingContext} gl
 */
export function createNetworkVisualiserWebGL(canvas, gl) {
    const nodeProg = link(gl, NODE_VS, NODE_FS);
    const edgeProg = link(gl, EDGE_VS, EDGE_FS);

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
    // center xy
    gl.enableVertexAttribArray(1);
    gl.vertexAttribPointer(1, 2, gl.FLOAT, false, NODE_STRIDE * 4, 0);
    gl.vertexAttribDivisor(1, 1);
    // size
    gl.enableVertexAttribArray(2);
    gl.vertexAttribPointer(2, 1, gl.FLOAT, false, NODE_STRIDE * 4, 8);
    gl.vertexAttribDivisor(2, 1);
    // rgba
    gl.enableVertexAttribArray(3);
    gl.vertexAttribPointer(3, 4, gl.FLOAT, false, NODE_STRIDE * 4, 12);
    gl.vertexAttribDivisor(3, 1);
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
    const uEdgeRes = gl.getUniformLocation(edgeProg, "u_resolution");
    const uEdgeCam = gl.getUniformLocation(edgeProg, "u_camera");
    const uEdgeZoom = gl.getUniformLocation(edgeProg, "u_zoom");

    let cssW = 1;
    let cssH = 1;
    let nodeCount = 0;
    let edgeVertexCount = 0;
    let edgeScratch = new Float32Array(0);

    function resize() {
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
        gl.viewport(0, 0, canvas.width, canvas.height);
        return { width: cssW, height: cssH };
    }

    /**
     * @param {Float32Array} nodes packed NODE_STRIDE
     * @param {Float32Array} edges packed EDGE_STRIDE
     * @param {{x:number,y:number,zoom:number}} camera
     * @param {boolean} dark
     */
    function draw(nodes, edges, camera, dark) {
        const size = resize();
        const camX = camera?.x ?? 0;
        const camY = camera?.y ?? 0;
        const zoom = camera?.zoom > 0 ? camera.zoom : 1;

        if (dark) {
            gl.clearColor(0.035, 0.035, 0.04, 1);
        } else {
            gl.clearColor(0.973, 0.98, 0.988, 1);
        }
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        nodeCount = nodes && nodes.length ? Math.floor(nodes.length / NODE_STRIDE) : 0;
        const edgeCount = edges && edges.length ? Math.floor(edges.length / EDGE_STRIDE) : 0;

        // Expand edges to 2 verts * (xy + rgba) = 12 floats per edge -> 6 floats per vertex
        const need = edgeCount * 12;
        if (edgeScratch.length < need) {
            edgeScratch = new Float32Array(Math.max(need, 64));
        }
        for (let i = 0; i < edgeCount; i++) {
            const o = i * EDGE_STRIDE;
            const d = i * 12;
            const x1 = edges[o];
            const y1 = edges[o + 1];
            const x2 = edges[o + 2];
            const y2 = edges[o + 3];
            const r = edges[o + 4];
            const g = edges[o + 5];
            const b = edges[o + 6];
            const a = edges[o + 7];
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
            gl.bindVertexArray(nodeVao);
            gl.bindBuffer(gl.ARRAY_BUFFER, nodeInstanceBuf);
            gl.bufferData(gl.ARRAY_BUFFER, nodes, gl.DYNAMIC_DRAW);
            gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, nodeCount);
            gl.bindVertexArray(null);
        }

        return size;
    }

    function destroy() {
        gl.deleteBuffer(nodeCornerBuf);
        gl.deleteBuffer(nodeInstanceBuf);
        gl.deleteBuffer(edgeBuf);
        gl.deleteVertexArray(nodeVao);
        gl.deleteVertexArray(edgeVao);
        gl.deleteProgram(nodeProg);
        gl.deleteProgram(edgeProg);
    }

    return { draw, resize, destroy, getCssSize: () => ({ width: cssW, height: cssH }) };
}

export { NODE_STRIDE, EDGE_STRIDE };
