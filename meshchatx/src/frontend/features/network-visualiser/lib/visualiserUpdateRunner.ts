// SPDX-License-Identifier: 0BSD

import type { DataSet } from "vis-data";
import { VIZ_SYNC_PATH_THRESHOLD } from "./constants.js";
import {
    fetchBasicVisualiserData,
    fetchPathTableBatches,
    ensureAnnouncesForPathHashes,
    loadCachedVisualiserGraph,
} from "./visualiserDataService.js";
import { collectVisualiserPositions, buildVisualiserGraph } from "./visualiserGraphBuilder.js";
import { syncVisNetworkDataFast, updateVisNetworkDataInChunks } from "./visNetworkAdapter.js";
import type {
    PathTableEntry,
    AnnounceEntry,
    InterfaceEntry,
    DiscoveredInterfaceEntry,
    ConversationEntry,
    VisualiserConfig,
} from "./types.js";

export interface LoadVisualiserDataParams {
    signal: AbortSignal;
    hopMaxFilter: number | null;
    pathFetchConcurrency: number;
    alreadyPainted: boolean;
    currentPathTable: PathTableEntry[];
    currentAnnounces: Record<string, AnnounceEntry>;
    currentCachedPositions: Record<string, { x: number; y: number }>;
    onBatchProgress: (loaded: number, total: number, batch: number, totalBatches: number) => void;
    onAnnounceProgress: (count: number) => void;
}

export interface LoadVisualiserDataResult {
    config: VisualiserConfig | null;
    interfaces: InterfaceEntry[];
    discoveredInterfaces: DiscoveredInterfaceEntry[];
    conversations: Record<string, ConversationEntry>;
    pathTable: PathTableEntry[];
    announces: Record<string, AnnounceEntry>;
    cachedPositions: Record<string, { x: number; y: number }>;
    paintedFromCache: boolean;
}

export async function loadInitialVisualiserData(
    params: LoadVisualiserDataParams
): Promise<LoadVisualiserDataResult | null> {
    const { signal, alreadyPainted, currentPathTable, currentAnnounces, currentCachedPositions } = params;

    const basic = await fetchBasicVisualiserData(signal);
    if (signal.aborted) return null;

    let pathTable = currentPathTable;
    let announces = currentAnnounces;
    let cachedPositions = currentCachedPositions;
    let paintedFromCache = false;

    const identityHash = basic.config?.identity_hash;
    if (identityHash && !alreadyPainted) {
        const cached = await loadCachedVisualiserGraph(identityHash);
        if (cached?.pathTable?.length) {
            pathTable = cached.pathTable as PathTableEntry[];
            announces = { ...((cached.announces as Record<string, AnnounceEntry>) || {}) };
            cachedPositions = { ...((cached.positions as Record<string, { x: number; y: number }>) || {}) };
            paintedFromCache = true;
        }
    }

    return {
        config: basic.config,
        interfaces: basic.interfaces,
        discoveredInterfaces: basic.discoveredInterfaces,
        conversations: basic.conversations,
        pathTable,
        announces,
        cachedPositions,
        paintedFromCache,
    };
}

export async function fetchVisualiserNetworkData(params: {
    signal: AbortSignal;
    hopMaxFilter: number | null;
    pathFetchConcurrency: number;
    currentAnnounces: Record<string, AnnounceEntry>;
    onBatchProgress: (loaded: number, total: number, batch: number, totalBatches: number) => void;
    onAnnounceProgress: (count: number) => void;
}): Promise<{ pathTable: PathTableEntry[]; announces: Record<string, AnnounceEntry> } | null> {
    const { signal, hopMaxFilter, pathFetchConcurrency, currentAnnounces, onBatchProgress, onAnnounceProgress } =
        params;

    const pathResult = await fetchPathTableBatches({
        signal,
        hopMaxFilter,
        onProgress: onBatchProgress,
    });
    if (signal.aborted) return null;

    const announces = await ensureAnnouncesForPathHashes({
        pathTable: pathResult.pathTable,
        hopMaxFilter,
        announces: currentAnnounces,
        signal,
        concurrency: pathFetchConcurrency,
        reset: false,
        onProgress: onAnnounceProgress,
    });
    if (signal.aborted) return null;

    return { pathTable: pathResult.pathTable, announces };
}

export interface RenderGraphOptions {
    runId: number;
    isCurrentRun: () => boolean;
    config: VisualiserConfig | null;
    interfaces: InterfaceEntry[];
    discoveredInterfaces: DiscoveredInterfaceEntry[];
    pathTable: PathTableEntry[];
    announces: Record<string, AnnounceEntry>;
    conversations: Record<string, ConversationEntry>;
    showDisabledInterfaces: boolean;
    showDiscoveredInterfaces: boolean;
    searchQuery: string;
    hopMaxFilter: number | null;
    cachedPositions: Record<string, { x: number; y: number }>;
    isDarkMode: boolean;
    currentLOD: string;
    batterySaverPrefs?: { enabled?: boolean; maxVisualiserInterfaces?: number };
    webglEngine?: any;
    network?: any;
    nodes: DataSet<any>;
    edges: DataSet<any>;
    onChunkNodes?: (count: number) => void;
    onDisplayCounts?: (nodes: number, edges: number, fps: number) => void;
    onIconQueue?: (queue: any[]) => void;
}

export async function renderVisualiserGraph(options: RenderGraphOptions): Promise<void> {
    const {
        isCurrentRun,
        config,
        interfaces,
        discoveredInterfaces,
        pathTable,
        announces,
        conversations,
        showDisabledInterfaces,
        showDiscoveredInterfaces,
        searchQuery,
        hopMaxFilter,
        cachedPositions,
        isDarkMode,
        currentLOD,
        batterySaverPrefs,
        webglEngine,
        network,
        nodes,
        edges,
        onChunkNodes,
        onDisplayCounts,
        onIconQueue,
    } = options;

    const posById = collectVisualiserPositions({
        cachedPositions,
        webglEngine,
        network,
        existingNodeIds: nodes.getIds() as string[],
    });

    const graph = buildVisualiserGraph({
        config,
        interfaces,
        discoveredInterfaces,
        pathTable,
        announces,
        conversations,
        showDisabledInterfaces,
        showDiscoveredInterfaces,
        searchQuery,
        hopMaxFilter,
        positions: posById,
        isDarkMode,
        currentLOD,
        batterySaverPrefs,
    });

    if (!isCurrentRun()) return;

    if (webglEngine) {
        webglEngine.setGraph(graph.nodes, graph.edges);
        const fps = typeof webglEngine.getFps === "function" ? webglEngine.getFps() : 0;
        onDisplayCounts?.(graph.nodes.length, graph.edges.length, fps);
        return;
    }

    const totalItems = graph.nodes.length + graph.edges.length;
    if (totalItems <= VIZ_SYNC_PATH_THRESHOLD) {
        syncVisNetworkDataFast(nodes, edges, graph.nodes, graph.edges);
    } else {
        await updateVisNetworkDataInChunks({
            nodes,
            edges,
            nodeList: graph.nodes,
            edgeList: graph.edges,
            isCurrentRun,
            onChunkNodes,
        });
    }

    if (!isCurrentRun()) return;
    onDisplayCounts?.(nodes.length, edges.length, 0);

    if (graph.icon_queue && graph.icon_queue.length > 0) {
        onIconQueue?.(graph.icon_queue);
    }
}
