// SPDX-License-Identifier: 0BSD

import type { Network } from "vis-network";
import type { DataSet } from "vis-data";
import type {
    VisualiserConfig,
    InterfaceEntry,
    DiscoveredInterfaceEntry,
    ConversationEntry,
    PathTableEntry,
    AnnounceEntry,
    IconQueueEntry,
} from "./types.js";
import {
    loadInitialVisualiserData,
    fetchVisualiserNetworkData,
    renderVisualiserGraph,
} from "./visualiserUpdateRunner.js";
import { saveCachedVisualiserGraph } from "./visualiserDataService.js";
import { pauseVisPhysicsForProcessing, resumeVisPhysicsAfterProcessing } from "./visualiserEngineManager.js";
import { resolveVisualiserIsDark } from "./visualiserPrefs.js";

export interface VisualiserDataState {
    config: VisualiserConfig | null;
    interfaces: InterfaceEntry[];
    discoveredInterfaces: DiscoveredInterfaceEntry[];
    conversations: Record<string, ConversationEntry>;
    pathTable: PathTableEntry[];
    announces: Record<string, AnnounceEntry>;
    cachedPositions: Record<string, { x: number; y: number }>;
}

export function createInitialVisualiserDataState(): VisualiserDataState {
    return {
        config: null,
        interfaces: [],
        discoveredInterfaces: [],
        conversations: {},
        pathTable: [],
        announces: {},
        cachedPositions: {},
    };
}

export async function executeVisualiserUpdate(options: {
    silent: boolean;
    abortController: AbortController;
    hopMaxFilter: number | null;
    pathFetchConcurrency: number;
    alreadyPainted: boolean;
    state: VisualiserDataState;
    onStatusChange: (status: string) => void;
    onBatchProgress: (batch: number, total: number) => void;
    onStateUpdate: (updated: Partial<VisualiserDataState>) => void;
    processVisualization: (opts: { silent: boolean }) => Promise<void>;
}): Promise<void> {
    const {
        silent,
        abortController,
        hopMaxFilter,
        pathFetchConcurrency,
        alreadyPainted,
        state,
        onStatusChange,
        onBatchProgress,
        onStateUpdate,
        processVisualization,
    } = options;

    if (!silent) {
        onStatusChange("Fetching basic info...");
        onBatchProgress(0, 0);
    }

    const initial = await loadInitialVisualiserData({
        signal: abortController.signal,
        hopMaxFilter,
        pathFetchConcurrency,
        alreadyPainted,
        currentPathTable: state.pathTable,
        currentAnnounces: state.announces,
        currentCachedPositions: state.cachedPositions,
        onBatchProgress: (loaded, total, batch, totalB) => {
            onBatchProgress(batch, totalB);
            onStatusChange(`Loading paths (${loaded} / ${total})`);
        },
        onAnnounceProgress: (count) => {
            onStatusChange(`Loading announces (${count})`);
        },
    });

    if (!initial || abortController.signal.aborted) return;

    onStateUpdate({
        config: initial.config,
        interfaces: initial.interfaces,
        discoveredInterfaces: initial.discoveredInterfaces,
        conversations: initial.conversations,
        pathTable: initial.pathTable,
        announces: initial.announces,
        cachedPositions: initial.cachedPositions,
    });

    if (!silent && initial.paintedFromCache && initial.pathTable.length > 0) {
        onStatusChange("Restoring cached graph...");
        await processVisualization({ silent: false });
        if (abortController.signal.aborted) return;
    }

    if (!silent) {
        onStatusChange("Fetching network data...");
    }

    const networkData = await fetchVisualiserNetworkData({
        signal: abortController.signal,
        hopMaxFilter,
        pathFetchConcurrency,
        currentAnnounces: initial.announces,
        onBatchProgress: (loaded, total, batch, totalB) => {
            onBatchProgress(batch, totalB);
            onStatusChange(`Loading paths (${loaded} / ${total})`);
        },
        onAnnounceProgress: (count) => {
            onStatusChange(`Loading announces (${count})`);
        },
    });

    if (!networkData || abortController.signal.aborted) return;

    onStateUpdate({
        pathTable: networkData.pathTable,
        announces: networkData.announces,
    });

    await processVisualization({ silent });
    if (abortController.signal.aborted) return;

    const identityHash = initial.config?.identity_hash;
    if (identityHash) {
        saveCachedVisualiserGraph(
            identityHash,
            networkData.pathTable,
            networkData.announces,
            initial.cachedPositions
        ).catch(() => {});
    }
}

export async function executeVisualiserRender(options: {
    silent: boolean;
    runId: number;
    getCurrentRunId: () => number;
    abortController: AbortController;
    state: VisualiserDataState;
    showDisabledInterfaces: boolean;
    showDiscoveredInterfaces: boolean;
    searchQuery: string;
    hopMaxFilter: number | null;
    currentLOD: string;
    batterySaverPrefs: any;
    webglEngine: any;
    network: Network | null;
    nodes: DataSet<any>;
    edges: DataSet<any>;
    enablePhysics: boolean;
    physicsPausedForDrag: boolean;
    didDisableStabilization: boolean;
    onStatusChange: (status: string) => void;
    onChunkNodes: (count: number) => void;
    onDisplayCounts: (nodes: number, edges: number, fps: number) => void;
    onNewIcons: (icons: IconQueueEntry[]) => void;
}): Promise<boolean> {
    const {
        silent,
        runId,
        getCurrentRunId,
        abortController,
        state,
        showDisabledInterfaces,
        showDiscoveredInterfaces,
        searchQuery,
        hopMaxFilter,
        currentLOD,
        batterySaverPrefs,
        webglEngine,
        network,
        nodes,
        edges,
        enablePhysics,
        physicsPausedForDrag,
        didDisableStabilization,
        onStatusChange,
        onChunkNodes,
        onDisplayCounts,
        onNewIcons,
    } = options;

    await new Promise((r) => requestAnimationFrame(r));
    if (abortController.signal.aborted) return didDisableStabilization;

    if (!silent) {
        onStatusChange("Processing visualization...");
    }

    const { physicsWasOn, pausePhysics } = pauseVisPhysicsForProcessing(network, silent, enablePhysics);

    let updatedDidDisable = didDisableStabilization;

    try {
        await renderVisualiserGraph({
            runId,
            isCurrentRun: () => runId === getCurrentRunId() && !abortController.signal.aborted,
            config: state.config,
            interfaces: state.interfaces,
            discoveredInterfaces: state.discoveredInterfaces,
            pathTable: state.pathTable,
            announces: state.announces,
            conversations: state.conversations,
            showDisabledInterfaces,
            showDiscoveredInterfaces,
            searchQuery,
            hopMaxFilter,
            cachedPositions: state.cachedPositions,
            isDarkMode: resolveVisualiserIsDark(),
            currentLOD,
            batterySaverPrefs,
            webglEngine,
            network,
            nodes,
            edges,
            onChunkNodes,
            onDisplayCounts,
            onIconQueue: onNewIcons,
        });
    } finally {
        if (runId === getCurrentRunId()) {
            updatedDidDisable = resumeVisPhysicsAfterProcessing({
                network,
                webglEngine,
                enablePhysics,
                physicsWasOn,
                pausePhysics,
                physicsPausedForDrag,
                didDisableStabilization,
            });
        }
    }

    return updatedDidDisable;
}
