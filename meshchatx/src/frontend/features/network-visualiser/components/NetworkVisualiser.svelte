<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import "vis-network/styles/vis-network.css";
    import type { Network } from "vis-network";
    import { DataSet } from "vis-data";
    import NetworkVisualiserViewport from "./NetworkVisualiserViewport.svelte";
    import NetworkVisualiserLoadingOverlay from "./NetworkVisualiserLoadingOverlay.svelte";
    import NetworkVisualiserToolbar from "./NetworkVisualiserToolbar.svelte";
    import NetworkVisualiserLegend from "./NetworkVisualiserLegend.svelte";
    import { pickAdaptiveFetchConcurrency } from "../../../js/networkVisualiserPerf.js";
    import { effectiveVisualiserReloadMs, loadBatterySaverPrefs } from "../../../js/settings/batterySaverPrefs.js";
    import {
        loadVisualiserDisplayPrefs,
        normalizeVisualiserViewMode,
        readStoredHopMaxFilter,
        writeStoredHopMaxFilter,
        persistVisualiserRenderer,
        persistVisualiserViewMode,
    } from "../lib/visualiserPrefs.js";
    import { createVisualiserIconQueueManager } from "../lib/visualiserIconQueue.js";
    import { handleVisualiserLODUpdate } from "../lib/visualiserLOD.js";
    import { setupVisualiserRenderer, destroyActiveRenderer } from "../lib/visualiserRendererSetup.js";
    import {
        executeVisualiserUpdate,
        executeVisualiserRender,
        createInitialVisualiserDataState,
        type VisualiserDataState,
    } from "../lib/visualiserPipeline.js";
    import { bindVisualiserEvents } from "../lib/visualiserEvents.js";
    import { VIZ_EDGE_SMOOTH } from "../lib/constants.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import { t } from "../../../js/i18n.js";
    import type { RendererMode, EngineMode, ViewMode, PreferredRenderer } from "../lib/types.js";

    let networkContainer = $state<HTMLDivElement | null>(null);
    let webglCanvas = $state<HTMLCanvasElement | null>(null);

    let rendererMode = $state<RendererMode>("vis");
    let engineMode = $state<EngineMode>("checking");
    let viewMode = $state<ViewMode>("flat");
    let preferredRenderer = $state<PreferredRenderer>("auto");

    let isShowingControls = $state(true);
    let isUpdating = $state(false);
    let isLoading = $state(false);
    let loadingStatus = $state("");
    let totalNodesToLoad = $state(0);
    let loadedNodesCount = $state(0);
    let currentBatch = $state(0);
    let totalBatches = $state(0);
    let autoReload = $state(false);
    let enablePhysics = $state(true);
    let showDisabledInterfaces = $state(true);
    let showDiscoveredInterfaces = $state(true);
    let hopMaxFilter = $state<number | null>(4);
    let searchQuery = $state("");
    let displayNodeCount = $state(0);
    let displayEdgeCount = $state(0);
    let fps = $state(0);

    let hoverTooltip = $state<{ text: string; x: number; y: number } | null>(null);
    let data = $state<VisualiserDataState>(createInitialVisualiserDataState());

    let onlineInterfaces = $derived(data.interfaces.filter((i) => i.status));
    let offlineInterfaces = $derived(data.interfaces.filter((i) => !i.status));

    let network: Network | null = null;
    let webglEngine: any = null;
    let nodes = new DataSet<any>([]);
    let edges = new DataSet<any>([]);
    let iconCache: Record<string, string> = {};
    let vizRunGeneration = 0;
    let autoReloadInterval: ReturnType<typeof setInterval> | null = null;
    let lodRafId: number | null = null;
    let currentLOD = "high";
    let batterySaverPrefs = loadBatterySaverPrefs();
    let abortController = new AbortController();
    let didDisableStabilization = false;
    let physicsPausedForDrag = false;
    let unbindEvents: (() => void) | null = null;
    let didInitRenderer = false;
    let resetCameraOnNextGraph = false;
    // Set while a flat rebuild follows radial: the live position snapshot is
    // still the ring layout and must not overwrite the cached force positions.
    let leavingRadialLayout = false;

    let pathFetchConcurrency = $derived(pickAdaptiveFetchConcurrency());

    const iconManager = createVisualiserIconQueueManager({
        nodes,
        iconCache,
        getAbortSignal: () => abortController.signal,
        getLOD: () => currentLOD,
    });

    function loadDisplayPrefs() {
        const p = loadVisualiserDisplayPrefs();
        showDisabledInterfaces = p.showDisabledInterfaces;
        showDiscoveredInterfaces = p.showDiscoveredInterfaces;
        enablePhysics = p.enablePhysics;
        autoReload = p.autoReload;
        preferredRenderer = p.renderer || "auto";
        viewMode = normalizeVisualiserViewMode(p.viewMode);
        hopMaxFilter = readStoredHopMaxFilter();
    }

    function onPrefsChanged() {
        const prevRenderer = preferredRenderer;
        const prevDisabled = showDisabledInterfaces;
        const prevDiscovered = showDiscoveredInterfaces;
        const prevViewMode = viewMode;
        loadDisplayPrefs();
        webglEngine?.setViewMode?.(viewMode);
        const hasRenderer = webglEngine != null || network != null;
        if (preferredRenderer !== prevRenderer) {
            void reinitRenderer();
            return;
        }
        if (viewMode !== prevViewMode && hasRenderer) {
            // Same transition rules as onViewModeChange: preserve the force
            // layout when entering radial, keep ring positions out of the
            // cache when leaving it, then rebuild.
            const wasRadial = prevViewMode === "radial";
            if (viewMode === "radial") {
                snapshotLivePositions();
            }
            leavingRadialLayout = wasRadial;
            resetCameraOnNextGraph = true;
            void processVisualization();
            return;
        }
        const filtersChanged = showDisabledInterfaces !== prevDisabled || showDiscoveredInterfaces !== prevDiscovered;
        if (filtersChanged && hasRenderer) {
            void processVisualization();
        }
    }

    function onUserHopMaxFilterChange(val: number | null) {
        if (val === hopMaxFilter) return;
        hopMaxFilter = val;
        writeStoredHopMaxFilter(val);
        manualUpdate();
    }

    async function onPreferredRendererChange(next: PreferredRenderer) {
        const normalized = next === "webgl" || next === "vis" || next === "auto" ? next : "auto";
        if (normalized === preferredRenderer) return;
        preferredRenderer = normalized;
        persistVisualiserRenderer(normalized, { emit: false });
        await reinitRenderer();
    }

    function onViewModeChange(next: ViewMode) {
        const normalized = normalizeVisualiserViewMode(next);
        if (normalized === viewMode) return;
        const hasRenderer = webglEngine != null || network != null;
        const wasRadial = viewMode === "radial";
        viewMode = normalized;
        persistVisualiserViewMode(normalized, { emit: false });
        webglEngine?.setViewMode?.(normalized);
        // Radial swaps force layout for pinned hop rings, so switching to
        // or from it needs a rebuild plus a camera reset.
        if (normalized === "radial" || wasRadial) {
            if (normalized === "radial" && hasRenderer) {
                // Preserve the live force layout so flat can restore it on
                // the way back instead of reopening on ring coordinates.
                snapshotLivePositions();
            }
            leavingRadialLayout = wasRadial;
            resetCameraOnNextGraph = true;
            void processVisualization();
        }
    }

    function snapshotLivePositions() {
        if (webglEngine) {
            const snap = webglEngine.getPositions() || {};
            for (const [id, p] of Object.entries(snap)) {
                const pos = p as { x?: unknown; y?: unknown } | null;
                if (pos && Number.isFinite(pos.x) && Number.isFinite(pos.y)) {
                    data.cachedPositions[id] = { x: pos.x as number, y: pos.y as number };
                }
            }
            return;
        }
        if (!network || typeof network.getPositions !== "function") return;
        const ids = nodes.getIds() as string[];
        const snap = network.getPositions(ids);
        if (snap) {
            for (const id of ids) {
                const p = snap[id];
                if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                    data.cachedPositions[id] = { x: p.x, y: p.y };
                }
            }
        }
    }

    function teardownActiveRenderer() {
        hoverTooltip = null;
        const res = destroyActiveRenderer({ webglEngine, network, nodes, edges });
        webglEngine = res.webglEngine;
        network = res.network;
        rendererMode = res.rendererMode;
    }

    async function reinitRenderer() {
        teardownActiveRenderer();
        await init({ skipWarm: true });
    }

    async function init({ skipWarm = false, forceVis = false } = {}) {
        const res = await setupVisualiserRenderer({
            skipWarm,
            preferredRenderer: forceVis ? "vis" : preferredRenderer,
            webglCanvas,
            networkContainer,
            nodes,
            edges,
            enablePhysics,
            getEnablePhysics: () => enablePhysics === true && viewMode !== "radial",
            viewMode,
            currentWebglEngine: webglEngine,
            onHover: (t) => {
                hoverTooltip = t;
            },
            onZoom: scheduleUpdateLOD,
            onDragStart: () => {
                physicsPausedForDrag = true;
            },
            onDragEnd: () => {
                physicsPausedForDrag = false;
            },
            onSceneFailure: onWebGLSceneFailure,
        });
        webglEngine = res.webglEngine;
        network = res.network;
        rendererMode = res.rendererMode;
        engineMode = res.engineMode;

        await manualUpdate();
        restartAutoReloadInterval();
    }

    $effect(() => {
        if (didInitRenderer || networkContainer == null) return;
        didInitRenderer = true;
        void init();
    });

    let didInitPhysicsWatcher = false;
    $effect(() => {
        const enabled = enablePhysics;
        const mode = viewMode;
        if (!didInitPhysicsWatcher) {
            didInitPhysicsWatcher = true;
            return;
        }
        // Ring coordinates must never enter the force-position cache: not
        // while radial is active, and not during the radial-to-flat
        // transition where the live snapshot is still the ring layout.
        const skipSnapshot = mode === "radial" || leavingRadialLayout;
        if (webglEngine) {
            webglEngine.setLiveLayout?.(enabled);
            if (!enabled && !skipSnapshot) {
                snapshotLivePositions();
            }
            return;
        }
        if (!network || physicsPausedForDrag) return;
        // Freeze current coordinates before stopping the solver so peers
        // stay where the live layout left them.
        if (!enabled && !skipSnapshot) {
            snapshotLivePositions();
        }
        network.setOptions({
            physics: { enabled: enabled && mode !== "radial" },
            edges: { smooth: VIZ_EDGE_SMOOTH as any },
        });
    });

    function scheduleUpdateLOD() {
        if (lodRafId != null) cancelAnimationFrame(lodRafId);
        lodRafId = requestAnimationFrame(() => {
            lodRafId = null;
            currentLOD = handleVisualiserLODUpdate({
                network,
                nodes,
                currentLOD,
                pathTable: data.pathTable,
                onHighLOD: () => iconManager.schedule(),
            });
        });
    }

    async function manualUpdate() {
        if (isLoading || isUpdating) return;
        isLoading = true;
        isUpdating = true;
        try {
            await update({ silent: false });
        } finally {
            isLoading = false;
            isUpdating = false;
        }
    }

    async function onAutoReloadTick() {
        if (!autoReload || isUpdating || isLoading) return;
        isUpdating = true;
        try {
            await update({ silent: true });
        } finally {
            isUpdating = false;
        }
    }

    function restartAutoReloadInterval() {
        if (autoReloadInterval) {
            clearInterval(autoReloadInterval);
            autoReloadInterval = null;
        }
        const ms = effectiveVisualiserReloadMs(15000, batterySaverPrefs);
        if (ms === null) return;
        autoReloadInterval = setInterval(() => {
            if (autoReload) onAutoReloadTick();
        }, ms);
    }

    function onIdentitySwitched() {
        vizRunGeneration += 1;
        data.pathTable = [];
        data.announces = {};
        iconManager.reset();
        abortController.abort();
        abortController = new AbortController();
        data = createInitialVisualiserDataState();
        displayNodeCount = 0;
        displayEdgeCount = 0;
        if (webglEngine) {
            try {
                webglEngine.setGraph([], []);
            } catch {
                /* ignore */
            }
        }
        try {
            nodes.clear();
            edges.clear();
        } catch {
            /* ignore */
        }
        manualUpdate();
    }

    async function update(options: { silent?: boolean } = {}) {
        const silent = options.silent === true;
        await executeVisualiserUpdate({
            silent,
            abortController,
            hopMaxFilter,
            pathFetchConcurrency,
            alreadyPainted: displayNodeCount > 0,
            state: data,
            onStatusChange: (status) => {
                loadingStatus = status;
            },
            onBatchProgress: (batch, total) => {
                currentBatch = batch;
                totalBatches = total;
            },
            onStateUpdate: (updated) => {
                Object.assign(data, updated);
            },
            processVisualization,
        });
    }

    async function processVisualization(options: { silent?: boolean } = {}) {
        const silent = options.silent === true;
        const runId = ++vizRunGeneration;
        iconManager.reset();
        const radial = viewMode === "radial";
        const resetCamera = resetCameraOnNextGraph;
        resetCameraOnNextGraph = false;
        // Leaving radial: the live snapshot is still the ring layout.
        // Skip it so the cached force positions win the rebuild.
        const skipLivePositionOverlay = leavingRadialLayout === true;
        leavingRadialLayout = false;

        didDisableStabilization = await executeVisualiserRender({
            silent,
            runId,
            getCurrentRunId: () => vizRunGeneration,
            abortController,
            state: data,
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
            enablePhysics: enablePhysics && !radial,
            physicsPausedForDrag,
            didDisableStabilization,
            iconCache,
            iconGeneration: iconManager.generation,
            skipLivePositionOverlay,
            radial,
            resetCamera,
            onStatusChange: (status) => {
                loadingStatus = status;
            },
            onChunkNodes: (count) => {
                loadedNodesCount = Math.min(totalNodesToLoad, count);
            },
            onDisplayCounts: (n, e, f) => {
                displayNodeCount = n;
                displayEdgeCount = e;
                fps = f;
            },
            onNewIcons: (q) => iconManager.push(q),
        });
    }

    function onWebGLSceneFailure(err: unknown) {
        if (rendererMode !== "webgl") return;
        console.warn("WebGL scene failed, falling back to vis-network:", err);
        teardownActiveRenderer();
        if (preferredRenderer === "webgl") {
            ToastUtils.warning(t("visualiser.renderer_webgl_unavailable"));
        }
        void init({ skipWarm: true, forceVis: true }).catch((e) => console.warn("vis-network fallback failed:", e));
    }

    onMount(() => {
        loadDisplayPrefs();
        unbindEvents = bindVisualiserEvents({
            onConfigUpdated: manualUpdate,
            onPrefsChanged: () => void onPrefsChanged(),
            onBatterySaverChanged: () => {
                batterySaverPrefs = loadBatterySaverPrefs();
                restartAutoReloadInterval();
            },
            onIdentitySwitched,
            onThemeChanged: () => {
                if (webglEngine) {
                    webglEngine.requestRedraw();
                } else if (network) {
                    scheduleUpdateLOD();
                }
            },
        });
    });

    onDestroy(() => {
        abortController.abort();
        if (autoReloadInterval) clearInterval(autoReloadInterval);
        iconManager.destroy();
        if (lodRafId != null) cancelAnimationFrame(lodRafId);
        if (unbindEvents) unbindEvents();
        teardownActiveRenderer();
    });
</script>

<div class="flex-1 h-full min-h-0 min-w-0 relative dark:bg-zinc-950 overflow-hidden">
    <NetworkVisualiserViewport bind:networkContainer bind:webglCanvas {rendererMode} {hoverTooltip} />

    <NetworkVisualiserLoadingOverlay
        {isLoading}
        {loadingStatus}
        {totalNodesToLoad}
        {loadedNodesCount}
        {currentBatch}
        {totalBatches}
    />

    <NetworkVisualiserToolbar
        bind:isShowingControls
        {isUpdating}
        {isLoading}
        bind:autoReload
        bind:enablePhysics
        {hopMaxFilter}
        nodeCount={displayNodeCount}
        edgeCount={displayEdgeCount}
        onlineInterfaceCount={onlineInterfaces.length}
        offlineInterfaceCount={offlineInterfaces.length}
        bind:searchQuery
        {preferredRenderer}
        {engineMode}
        {viewMode}
        {fps}
        onmanualupdate={manualUpdate}
        onupdatehopmaxfilter={onUserHopMaxFilterChange}
        onupdatepreferredrenderer={onPreferredRendererChange}
        onupdateviewmode={onViewModeChange}
    />

    <NetworkVisualiserLegend {showDiscoveredInterfaces} discoveredCount={data.discoveredInterfaces.length} />
</div>
