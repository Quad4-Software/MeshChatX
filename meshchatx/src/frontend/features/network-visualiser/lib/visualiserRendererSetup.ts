// SPDX-License-Identifier: 0BSD

import { tick } from "svelte";
import type { Network } from "vis-network";
import type { DataSet } from "vis-data";
import { warmVisualiserWasm } from "../../../js/networkVisualiserPerf.js";
import { isVisualiserWasmReady } from "../../../js/VisualiserWasmLoader.js";
import { resolveVisualiserIsDark } from "./visualiserPrefs.js";
import { createVisNetworkInstance } from "./visNetworkAdapter.js";
import { tryStartVisualiserWebGL, destroyVisualiserRenderer } from "./visualiserEngineManager.js";
import type { PreferredRenderer, RendererMode, EngineMode, ViewMode } from "./types.js";

export function destroyActiveRenderer(params: {
    webglEngine: any;
    network: Network | null;
    nodes: DataSet<any>;
    edges: DataSet<any>;
}): { webglEngine: null; network: null; rendererMode: RendererMode } {
    destroyVisualiserRenderer(params.webglEngine, params.network, params.nodes, params.edges);
    return { webglEngine: null, network: null, rendererMode: "vis" };
}

export async function tryStartWebGL(params: {
    webglCanvas: HTMLCanvasElement | null;
    enablePhysics: boolean;
    viewMode: ViewMode;
    onHover: (tooltip: { text: string; x: number; y: number } | null) => void;
    currentWebglEngine: any;
}): Promise<{ engine: any; rendererMode: RendererMode; engineMode: EngineMode; success: boolean }> {
    const result = tryStartVisualiserWebGL(params.webglCanvas, {
        getEnablePhysics: () => params.enablePhysics === true,
        getIsDark: () => resolveVisualiserIsDark(),
        onNodeActivate: (_id, meta) => {
            if (meta?.hash && typeof window !== "undefined" && window.location) {
                window.location.hash = `#/messages/${meta.hash}`;
            }
        },
        onHover: (id, meta, x, y) => {
            if (!id || !meta?.title) {
                params.onHover(null);
            } else {
                params.onHover({ text: meta.title, x, y });
            }
        },
        viewMode: params.viewMode,
    });

    if (result.success && result.engine) {
        return {
            engine: result.engine,
            rendererMode: "webgl",
            engineMode: "webgl",
            success: true,
        };
    }

    if (params.currentWebglEngine) {
        params.currentWebglEngine.destroy();
    }
    return {
        engine: null,
        rendererMode: "vis",
        engineMode: "fallback",
        success: false,
    };
}

export async function setupVisualiserRenderer(params: {
    skipWarm?: boolean;
    preferredRenderer: PreferredRenderer;
    webglCanvas: HTMLCanvasElement | null;
    networkContainer: HTMLElement | null;
    nodes: DataSet<any>;
    edges: DataSet<any>;
    enablePhysics: boolean;
    viewMode: ViewMode;
    currentWebglEngine: any;
    onHover: (tooltip: { text: string; x: number; y: number } | null) => void;
    onZoom: () => void;
    onDragStart: () => void;
    onDragEnd: () => void;
}): Promise<{
    webglEngine: any;
    network: Network | null;
    rendererMode: RendererMode;
    engineMode: EngineMode;
}> {
    if (!params.skipWarm) {
        warmVisualiserWasm();
    }

    let webglEngine: any = null;
    let network: Network | null = null;
    let rendererMode: RendererMode = "vis";
    let engineMode: EngineMode = isVisualiserWasmReady() ? "wasm" : "fallback";

    const wantWebGL = params.preferredRenderer === "webgl" || params.preferredRenderer === "auto";
    let webglStarted = false;

    if (wantWebGL) {
        const res = await tryStartWebGL({
            webglCanvas: params.webglCanvas,
            enablePhysics: params.enablePhysics,
            viewMode: params.viewMode,
            onHover: params.onHover,
            currentWebglEngine: params.currentWebglEngine,
        });
        if (res.success) {
            webglEngine = res.engine;
            rendererMode = res.rendererMode;
            engineMode = res.engineMode;
            webglStarted = true;
        }
    }

    if (!webglStarted) {
        engineMode = isVisualiserWasmReady() ? "wasm" : "fallback";
        rendererMode = "vis";
        await tick();
        if (params.networkContainer) {
            network = createVisNetworkInstance(params.networkContainer, params.nodes, params.edges, {
                enablePhysics: params.enablePhysics,
                isDarkMode: resolveVisualiserIsDark(),
                onZoom: params.onZoom,
                onDragStart: params.onDragStart,
                onDragEnd: params.onDragEnd,
            });
        }
    }

    return { webglEngine, network, rendererMode, engineMode };
}
