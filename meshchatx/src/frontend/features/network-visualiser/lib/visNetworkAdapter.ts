// SPDX-License-Identifier: 0BSD

import { Network } from "vis-network";
import type { DataSet } from "vis-data";
import { VIZ_EDGE_SMOOTH } from "./constants.js";
import { pickAdaptiveChunkSize, yieldToMain } from "./visualiserIconUtils.js";

export interface CreateVisNetworkOptions {
    enablePhysics: boolean;
    isDarkMode: boolean;
    onZoom?: () => void;
    onDragStart?: () => void;
    onDragEnd?: () => void;
    onDoubleClickNode?: (nodeId: string, node: Record<string, unknown> | null) => void;
}

export function createVisNetworkInstance(
    container: HTMLElement,
    nodes: DataSet<any>,
    edges: DataSet<any>,
    options: CreateVisNetworkOptions
): Network {
    const fontColor = options.isDarkMode ? "#ffffff" : "#000000";

    const networkOptions = {
        nodes: {
            shape: "circularImage",
            size: 25,
            font: {
                color: fontColor,
                size: 11,
                face: "Inter, system-ui, sans-serif",
            },
            borderWidth: 2,
            shadow: true,
        },
        edges: {
            width: 2,
            smooth: VIZ_EDGE_SMOOTH as any,
            shadow: false,
        },
        physics: {
            enabled: options.enablePhysics,
            solver: "forceAtlas2Based",
            forceAtlas2Based: {
                gravitationalConstant: -50,
                centralGravity: 0.01,
                springLength: 100,
                springConstant: 0.08,
                damping: 0.4,
                avoidOverlap: 0.5,
            },
            stabilization: {
                enabled: false,
            },
        },
        interaction: {
            hover: true,
            tooltipDelay: 200,
            hideEdgesOnDrag: true,
            hideEdgesOnZoom: true,
        },
    };

    const network = new Network(container, { nodes, edges }, networkOptions as any);

    if (options.onZoom) {
        network.on("zoom", options.onZoom);
    }
    if (options.onDragStart) {
        network.on("dragStart", options.onDragStart);
    }
    if (options.onDragEnd) {
        network.on("dragEnd", options.onDragEnd);
    }
    if (options.onDoubleClickNode) {
        network.on("doubleClick", (params: { nodes?: string[] }) => {
            const clickedNodeId = params?.nodes?.[0];
            if (!clickedNodeId) {
                return;
            }
            const node = nodes.get(clickedNodeId) as Record<string, unknown> | null;
            options.onDoubleClickNode?.(clickedNodeId, node);
        });
    }

    return network;
}

export function syncVisNetworkDataFast(
    nodes: DataSet<any>,
    edges: DataSet<any>,
    nodeList: any[],
    edgeList: any[]
): void {
    const nextNodeIds = new Set(nodeList.map((n) => n.id));
    const nextEdgeIds = new Set(edgeList.map((e) => e.id));

    const staleNodes = (nodes.getIds() as string[]).filter((id) => !nextNodeIds.has(id));
    const staleEdges = (edges.getIds() as string[]).filter((id) => !nextEdgeIds.has(id));

    if (staleNodes.length > 0) nodes.remove(staleNodes);
    if (staleEdges.length > 0) edges.remove(staleEdges);

    if (nodeList.length > 0) nodes.update(nodeList);
    if (edgeList.length > 0) edges.update(edgeList);
}

export async function updateVisNetworkDataInChunks(options: {
    nodes: DataSet<any>;
    edges: DataSet<any>;
    nodeList: any[];
    edgeList: any[];
    isCurrentRun: () => boolean;
    onChunkNodes?: (count: number) => void;
}): Promise<void> {
    const { nodes, edges, nodeList, edgeList, isCurrentRun, onChunkNodes } = options;
    const chunkSize = pickAdaptiveChunkSize();

    syncVisNetworkDataFast(nodes, edges, [], []);

    for (let i = 0; i < nodeList.length; i += chunkSize) {
        if (!isCurrentRun()) return;
        const chunk = nodeList.slice(i, i + chunkSize);
        nodes.update(chunk);
        onChunkNodes?.(Math.min(nodeList.length, i + chunkSize));
        await yieldToMain();
    }

    for (let i = 0; i < edgeList.length; i += chunkSize) {
        if (!isCurrentRun()) return;
        const chunk = edgeList.slice(i, i + chunkSize);
        edges.update(chunk);
        await yieldToMain();
    }
}
