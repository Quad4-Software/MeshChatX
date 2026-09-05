// SPDX-License-Identifier: 0BSD

import type { Network } from "vis-network";
import type { DataSet } from "vis-data";
import { canUseVisualiserWebGL, createVisualiserWebGLEngine } from "../../../js/networkVisualiserWebGLEngine.js";
import { VIZ_EDGE_SMOOTH } from "./constants.js";
import type { ViewMode } from "./types.js";

export function tryStartVisualiserWebGL(
    canvas: HTMLCanvasElement | null,
    options: {
        getEnablePhysics: () => boolean;
        getIsDark: () => boolean;
        onNodeActivate: (id: string, meta: any) => void;
        onHover: (id: string | null, meta: any, x: number, y: number) => void;
        viewMode: ViewMode;
    }
): { engine: any; success: boolean } {
    if (!canvas || !canUseVisualiserWebGL()) {
        return { engine: null, success: false };
    }
    try {
        const engine = createVisualiserWebGLEngine(canvas, {
            getLiveLayout: () => options.getEnablePhysics(),
            isDark: () => options.getIsDark(),
            onNodeActivate: options.onNodeActivate,
            onHover: options.onHover,
        });
        engine.setViewMode(options.viewMode);
        return { engine, success: true };
    } catch (e) {
        console.warn("WebGL visualiser failed:", e);
        return { engine: null, success: false };
    }
}

export function destroyVisualiserRenderer(
    webglEngine: any,
    network: Network | null,
    nodes: DataSet<any>,
    edges: DataSet<any>
): void {
    if (webglEngine) {
        webglEngine.destroy();
    }
    if (network) {
        network.destroy();
    }
    try {
        nodes.clear();
        edges.clear();
    } catch {
        /* ignore */
    }
}

export function pauseVisPhysicsForProcessing(
    network: Network | null,
    silent: boolean,
    enablePhysics: boolean
): { physicsWasOn: boolean; pausePhysics: boolean } {
    const physicsWasOn = Boolean(network && enablePhysics);
    const pausePhysics = Boolean(network && !silent);
    if (pausePhysics && network) {
        network.setOptions({
            physics: { enabled: false },
            edges: { smooth: VIZ_EDGE_SMOOTH as any },
        });
    }
    return { physicsWasOn, pausePhysics };
}

export function resumeVisPhysicsAfterProcessing(options: {
    network: Network | null;
    webglEngine: any;
    enablePhysics: boolean;
    physicsWasOn: boolean;
    pausePhysics: boolean;
    physicsPausedForDrag: boolean;
    didDisableStabilization: boolean;
}): boolean {
    const {
        network,
        webglEngine,
        enablePhysics,
        physicsWasOn,
        pausePhysics,
        physicsPausedForDrag,
        didDisableStabilization,
    } = options;

    let updatedDidDisableStabilization = didDisableStabilization;

    if (webglEngine) {
        webglEngine.setLiveLayout(enablePhysics);
        webglEngine.requestRedraw();
    }
    if (network && !didDisableStabilization) {
        updatedDidDisableStabilization = true;
        network.setOptions({
            physics: { stabilization: { enabled: false } },
            edges: { smooth: VIZ_EDGE_SMOOTH as any },
        });
    }
    if (pausePhysics && network && !physicsPausedForDrag) {
        network.setOptions({
            physics: { enabled: Boolean(physicsWasOn || enablePhysics) },
            edges: { smooth: VIZ_EDGE_SMOOTH as any },
        });
    }
    if (network && typeof network.redraw === "function") {
        network.redraw();
    }

    return updatedDidDisableStabilization;
}
