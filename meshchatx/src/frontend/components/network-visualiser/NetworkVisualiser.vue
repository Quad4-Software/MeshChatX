<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex-1 h-full min-w-0 relative dark:bg-zinc-950 overflow-hidden">
        <!-- vis-network fallback canvas host -->
        <div id="network" class="w-full h-full" :class="{ hidden: rendererMode === 'webgl' }"></div>
        <!-- WebGL + WASM scene (preferred when available) -->
        <canvas
            id="network-webgl"
            ref="webglCanvas"
            class="w-full h-full absolute inset-0"
            :class="{ hidden: rendererMode !== 'webgl' }"
        ></canvas>
        <div
            v-if="rendererMode === 'webgl' && hoverTooltip"
            class="pointer-events-none absolute z-20 max-w-xs rounded-xl border border-zinc-600/50 bg-zinc-950/90 px-3 py-2 text-xs font-medium text-zinc-100 shadow-lg whitespace-pre-line"
            :style="{ left: `${hoverTooltip.x + 12}px`, top: `${hoverTooltip.y + 12}px` }"
        >
            {{ hoverTooltip.text }}
        </div>

        <NetworkVisualiserLoadingOverlay
            :is-loading="isLoading"
            :loading-status="loadingStatus"
            :total-nodes-to-load="totalNodesToLoad"
            :loaded-nodes-count="loadedNodesCount"
            :current-batch="currentBatch"
            :total-batches="totalBatches"
        />

        <NetworkVisualiserToolbar
            :is-showing-controls="isShowingControls"
            :is-updating="isUpdating"
            :is-loading="isLoading"
            :auto-reload="autoReload"
            :enable-physics="enablePhysics"
            :hop-max-filter="hopMaxFilter"
            :node-count="displayNodeCount"
            :edge-count="displayEdgeCount"
            :online-interface-count="onlineInterfaces.length"
            :offline-interface-count="offlineInterfaces.length"
            :search-query="searchQuery"
            :preferred-renderer="preferredRenderer"
            :engine-mode="engineMode"
            :fps="fps"
            @update:is-showing-controls="isShowingControls = $event"
            @update:auto-reload="autoReload = $event"
            @update:enable-physics="enablePhysics = $event"
            @update:hop-max-filter="onUserHopMaxFilterChange"
            @update:search-query="searchQuery = $event"
            @update:preferred-renderer="onPreferredRendererChange"
            @manual-update="manualUpdate"
        />
        <NetworkVisualiserLegend
            :show-discovered-interfaces="showDiscoveredInterfaces"
            :discovered-count="discoveredInterfaces.length"
        />
    </div>
</template>

<script>
import "vis-network/styles/vis-network.css";
import { Network } from "vis-network";
import { DataSet } from "vis-data";
import { getMdiIconPath } from "../../js/mdiIconNames.js";
import Utils from "../../js/Utils";
import GlobalEmitter from "../../js/GlobalEmitter";
import NetworkVisualiserLoadingOverlay from "./internal/NetworkVisualiserLoadingOverlay.vue";
import NetworkVisualiserToolbar from "./internal/NetworkVisualiserToolbar.vue";
import NetworkVisualiserLegend from "./internal/NetworkVisualiserLegend.vue";
import {
    ANNOUNCE_HASH_CHUNK_SIZE,
    VIZ_ANNOUNCE_ASPECTS,
    VIZ_ANNOUNCE_SOFT_CAP,
    VIZ_PATH_TABLE_SOFT_CAP,
    buildFullGraph,
    computeLodUpdates,
    dedupeIconQueueEntries,
    lodLevelFromScale,
    pathHashesWithinHopFilter,
    pickAdaptiveFetchConcurrency,
    settleLayout,
    warmVisualiserWasm,
} from "../../js/networkVisualiserPerf.js";
import { isVisualiserWasmReady } from "../../js/VisualiserWasmLoader.js";
import { canUseVisualiserWebGL, createVisualiserWebGLEngine } from "../../js/networkVisualiserWebGLEngine.js";
import { loadVisualiserCache, saveVisualiserCache } from "../../js/networkVisualiserCache.js";
import {
    BATTERY_SAVER_CHANGED_EVENT,
    effectiveVisualiserReloadMs,
    loadBatterySaverPrefs,
    saveBatterySaverPrefs,
} from "../../js/settings/batterySaverPrefs.js";
import {
    loadVisualiserDisplayPrefs,
    persistVisualiserAutoReload,
    persistVisualiserLiveLayout,
    persistVisualiserRenderer,
    VISUALISER_DISPLAY_PREFS_CHANGED,
} from "../../js/settings/settingsVisualiserPrefs.js";
import ToastUtils from "../../js/ToastUtils";

const HOP_MAX_FILTER_STORAGE_KEY = "meshchatx.visualiser.maxHops";

function readStoredHopMaxFilter() {
    if (typeof localStorage === "undefined") return 4;
    try {
        const raw = localStorage.getItem(HOP_MAX_FILTER_STORAGE_KEY);
        if (raw === null || raw === "") return 4;
        const v = JSON.parse(raw);
        if (v === null) return null;
        if (typeof v === "number" && Number.isFinite(v)) {
            return Math.max(0, Math.min(128, Math.round(v)));
        }
    } catch {
        return 4;
    }
    return 4;
}

function writeStoredHopMaxFilter(v) {
    if (typeof localStorage === "undefined") return;
    try {
        localStorage.setItem(HOP_MAX_FILTER_STORAGE_KEY, JSON.stringify(v));
    } catch {
        return;
    }
}

/*
 * Yields control back to the browser so it can paint, dispatch input events,
 * and run other tasks. Prefers the prioritized task scheduler when available
 * (Chromium 94+ / Electron) and falls back to a zero-delay timer everywhere
 * else. setTimeout(0) is intentionally used over Promise.resolve() because
 * microtasks do not give the renderer a chance to repaint.
 */
function yieldToMain() {
    if (typeof window !== "undefined" && window.scheduler) {
        if (typeof window.scheduler.yield === "function") {
            return window.scheduler.yield();
        }
        if (typeof window.scheduler.postTask === "function") {
            return new Promise((resolve) => {
                window.scheduler.postTask(resolve, { priority: "user-blocking" });
            });
        }
    }
    return new Promise((resolve) => setTimeout(resolve, 0));
}

/*
 * Pick a visualisation chunk size that scales down on weak hardware. ARM SBCs
 * commonly report 4 logical cores; phones/SoCs frequently report 2. Desktop
 * uses large chunks (fewer DataSet updates / yields) so wall-clock build time
 * stays competitive with upstream's single-pass update.
 */
function pickAdaptiveChunkSize() {
    const cores = (typeof navigator !== "undefined" && navigator.hardwareConcurrency) || 4;
    if (cores <= 2) return 60;
    if (cores <= 4) return 120;
    if (cores <= 6) return 250;
    return 500;
}

/* Skip event-loop yields when the path table is small enough for one paint. */
const VIZ_SYNC_PATH_THRESHOLD = 180;

/*
 * Straight edges ({ enabled: false } object, never the boolean `false`). Boolean
 * smooth breaks vis-network 9.x on later setOptions(); "continuous" curves
 * recompute every drag frame and are too heavy once the graph is large.
 */
const VIZ_EDGE_SMOOTH = { enabled: false };

export default {
    name: "NetworkVisualiser",
    components: {
        NetworkVisualiserLoadingOverlay,
        NetworkVisualiserToolbar,
        NetworkVisualiserLegend,
    },
    data() {
        const displayPrefs = loadVisualiserDisplayPrefs();
        return {
            reticulumLogoPath: "/assets/images/reticulum_logo_512.png",
            config: null,
            autoReload: displayPrefs.autoReload,
            reloadInterval: null,
            isShowingControls: true,
            isUpdating: false,
            isLoading: false,
            enablePhysics: displayPrefs.enablePhysics,
            preferredRenderer: displayPrefs.renderer || "auto",
            showDisabledInterfaces: displayPrefs.showDisabledInterfaces,
            showDiscoveredInterfaces: displayPrefs.showDiscoveredInterfaces,
            loadingStatus: "Initializing...",
            loadedNodesCount: 0,
            totalNodesToLoad: 0,
            currentBatch: 0,
            totalBatches: 0,

            interfaces: [],
            discoveredInterfaces: [],
            discoveredActive: [],
            pathTable: [],
            announces: {},
            conversations: {},

            network: null,
            webglEngine: null,
            rendererMode: "vis",
            graphNodeCount: 0,
            graphEdgeCount: 0,
            hoverTooltip: null,
            nodes: new DataSet(),
            edges: new DataSet(),
            iconCache: {},

            pageSize: 1000,
            searchQuery: "",
            hopMaxFilter: readStoredHopMaxFilter(),
            hopFilterDebounceTimer: null,
            searchDebounceTimer: null,
            abortController: new AbortController(),
            currentLOD: "high",
            didDisableStabilization: false,
            vizChunkSize: pickAdaptiveChunkSize(),
            pathFetchConcurrency: pickAdaptiveFetchConcurrency(),
            iconQueue: [],
            iconQueueRunning: false,
            iconQueueGeneration: 0,
            lodRafId: null,
            vizRunGeneration: 0,
            physicsPausedForDrag: false,
            engineMode: "checking",
            fps: 0,
            fpsRafId: null,
            fpsFrameCount: 0,
            fpsLastSampleMs: 0,
            cachedPositions: {},
            batterySaverPrefs: loadBatterySaverPrefs(),
            suppressLiveLayoutPersist: false,
            suppressAutoReloadPersist: false,
        };
    },
    computed: {
        onlineInterfaces() {
            return this.interfaces.filter((i) => i.status);
        },
        offlineInterfaces() {
            return this.interfaces.filter((i) => !i.status);
        },
        hopFilterMax() {
            return this.hopMaxFilter;
        },
        displayNodeCount() {
            if (this.rendererMode === "webgl") return this.graphNodeCount;
            return this.nodes.length;
        },
        displayEdgeCount() {
            if (this.rendererMode === "webgl") return this.graphEdgeCount;
            return this.edges.length;
        },
        hasRenderer() {
            return Boolean(this.network || this.webglEngine);
        },
    },
    watch: {
        autoReload(val) {
            if (!this.suppressAutoReloadPersist) {
                // Silent persist: do not rebuild the graph for toggle-only changes.
                persistVisualiserAutoReload(val === true, { emit: false });
            }
            if (val) {
                // Already painted: quiet refresh so enabling auto-update does not flash
                // the loading overlay or re-settle the whole graph.
                if (this.displayNodeCount > 0) {
                    this.onAutoReload();
                } else {
                    this.manualUpdate();
                }
            }
            this.restartAutoReloadInterval();
        },
        enablePhysics(val) {
            if (!this.suppressLiveLayoutPersist) {
                // Silent persist: emitting prefs-changed would reprocess the graph
                // and re-settle node positions (looks like a reset).
                persistVisualiserLiveLayout(val === true, { emit: false });
                // Explicit Live Layout on should win over battery-saver override.
                if (val === true) {
                    const prefs = loadBatterySaverPrefs();
                    if (prefs.enabled && prefs.disableVisualiserLiveLayout) {
                        this.batterySaverPrefs = saveBatterySaverPrefs({
                            disableVisualiserLiveLayout: false,
                        });
                    }
                }
            }
            this.refreshPhysicsEnabled();
        },
        searchQuery() {
            // Debounce full rebuilds while typing, as the filter still runs on existing data.
            if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
            this.searchDebounceTimer = setTimeout(() => {
                this.searchDebounceTimer = null;
                this.processVisualization();
            }, 120);
        },
        hopMaxFilter() {
            if (this.hopFilterDebounceTimer) clearTimeout(this.hopFilterDebounceTimer);
            this.hopFilterDebounceTimer = setTimeout(async () => {
                this.hopFilterDebounceTimer = null;
                await this.ensureAnnouncesForPathHashes();
                this.processVisualization();
            }, 80);
        },
    },
    beforeUnmount() {
        if (this.abortController) {
            this.abortController.abort();
        }
        this.iconQueue = [];
        this.iconQueueGeneration += 1;
        if (this._visualiserPrefsHandler) {
            GlobalEmitter.off(VISUALISER_DISPLAY_PREFS_CHANGED, this._visualiserPrefsHandler);
        }
        if (this._batterySaverPrefsHandler) {
            GlobalEmitter.off(BATTERY_SAVER_CHANGED_EVENT, this._batterySaverPrefsHandler);
        }
        clearInterval(this.reloadInterval);
        if (this.hopFilterDebounceTimer) {
            clearTimeout(this.hopFilterDebounceTimer);
            this.hopFilterDebounceTimer = null;
        }
        if (this.searchDebounceTimer) {
            clearTimeout(this.searchDebounceTimer);
            this.searchDebounceTimer = null;
        }
        if (this.lodRafId != null) {
            cancelAnimationFrame(this.lodRafId);
            this.lodRafId = null;
        }
        this.stopFpsMeter();
        if (this.webglEngine) {
            this.webglEngine.destroy();
            this.webglEngine = null;
        }
        if (this.network) {
            this.network.destroy();
        }
        // Clear icon cache to free memory
        const revokedUrls = new Set();
        const keys = Object.keys(this.iconCache);
        for (const key of keys) {
            const url = this.iconCache[key];
            if (url && url.startsWith("blob:") && !revokedUrls.has(url)) {
                URL.revokeObjectURL(url);
                revokedUrls.add(url);
            }
            delete this.iconCache[key];
        }
        this.iconCache = {};
        this.pathTable = [];
        this.announces = {};
        this.conversations = {};
        try {
            this.nodes.clear();
            this.edges.clear();
        } catch {
            /* DataSet may already be destroyed with the network */
        }
    },
    mounted() {
        const isMobile = window.innerWidth < 640;
        if (isMobile) {
            this.isShowingControls = false;
        }

        this._visualiserPrefsHandler = async () => {
            const prevRenderer = this.preferredRenderer;
            this.loadVisualiserDisplayPrefs();
            this.applyBatterySaverVisualiserPrefs();
            if (this.preferredRenderer !== prevRenderer) {
                await this.reinitRenderer();
                return;
            }
            if (this.hasRenderer) {
                this.processVisualization();
            }
        };
        GlobalEmitter.on(VISUALISER_DISPLAY_PREFS_CHANGED, this._visualiserPrefsHandler);

        this._batterySaverPrefsHandler = (prefs) => {
            this.batterySaverPrefs = prefs || loadBatterySaverPrefs();
            this.applyBatterySaverVisualiserPrefs();
            this.restartAutoReloadInterval();
            if (this.hasRenderer) {
                this.processVisualization();
            }
        };
        GlobalEmitter.on(BATTERY_SAVER_CHANGED_EVENT, this._batterySaverPrefsHandler);

        this.loadVisualiserDisplayPrefs();
        this.applyBatterySaverVisualiserPrefs();
        this.resolveEngineMode();
        this.startFpsMeter();
        this.init();
    },
    methods: {
        applyBatterySaverVisualiserPrefs() {
            const prefs = this.batterySaverPrefs || loadBatterySaverPrefs();
            if (!prefs.enabled) {
                return;
            }
            if (prefs.disableVisualiserDiscovery) {
                this.showDiscoveredInterfaces = false;
            }
            if (prefs.hideOfflineInterfaces) {
                this.showDisabledInterfaces = false;
            }
            if (prefs.disableVisualiserLiveLayout) {
                // Session override only. Do not overwrite the stored Live Layout pref.
                this.suppressLiveLayoutPersist = true;
                this.enablePhysics = false;
                this.suppressLiveLayoutPersist = false;
            }
            if (prefs.visualiserReloadSeconds === 0) {
                this.suppressAutoReloadPersist = true;
                this.autoReload = false;
                this.suppressAutoReloadPersist = false;
            }
        },
        restartAutoReloadInterval() {
            clearInterval(this.reloadInterval);
            this.reloadInterval = null;
            const ms = effectiveVisualiserReloadMs(15000, this.batterySaverPrefs || loadBatterySaverPrefs());
            if (ms == null) {
                return;
            }
            this.reloadInterval = setInterval(this.onAutoReload, ms);
        },
        resolveEngineMode() {
            warmVisualiserWasm()
                .then((ok) => {
                    if (this.rendererMode === "webgl") {
                        this.engineMode = "webgl";
                        return;
                    }
                    this.engineMode = ok && isVisualiserWasmReady() ? "wasm" : "fallback";
                })
                .catch(() => {
                    if (this.rendererMode === "webgl") {
                        this.engineMode = "webgl";
                        return;
                    }
                    this.engineMode = "fallback";
                });
        },
        startFpsMeter() {
            this.stopFpsMeter();
            this.fpsFrameCount = 0;
            this.fpsLastSampleMs = performance.now();
            const tick = (now) => {
                this.fpsFrameCount += 1;
                const elapsed = now - this.fpsLastSampleMs;
                if (elapsed >= 1000) {
                    this.fps = Math.round((this.fpsFrameCount * 1000) / elapsed);
                    this.fpsFrameCount = 0;
                    this.fpsLastSampleMs = now;
                    if (this.engineMode === "checking") {
                        if (this.rendererMode === "webgl") {
                            this.engineMode = "webgl";
                        } else if (isVisualiserWasmReady()) {
                            this.engineMode = "wasm";
                        }
                    }
                }
                this.fpsRafId = requestAnimationFrame(tick);
            };
            this.fpsRafId = requestAnimationFrame(tick);
        },
        stopFpsMeter() {
            if (this.fpsRafId != null) {
                cancelAnimationFrame(this.fpsRafId);
                this.fpsRafId = null;
            }
        },
        snapshotNodePositions() {
            if (this.webglEngine) {
                const snap = this.webglEngine.getPositions() || {};
                const out = {};
                for (const [id, p] of Object.entries(snap)) {
                    if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                        out[id] = { x: p.x, y: p.y };
                    }
                }
                return out;
            }
            const out = {};
            if (!this.network || typeof this.network.getPositions !== "function") {
                return out;
            }
            const ids = this.nodes.getIds();
            const snap = this.network.getPositions(ids);
            if (!snap) return out;
            for (const id of ids) {
                const p = snap[id];
                if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                    out[id] = { x: p.x, y: p.y };
                }
            }
            return out;
        },
        async persistVisualiserCache() {
            const identityHash = this.config?.identity_hash;
            if (!identityHash) return;
            const positions = this.snapshotNodePositions();
            this.cachedPositions = { ...this.cachedPositions, ...positions };
            await saveVisualiserCache({
                identityHash,
                pathTable: this.pathTable,
                announces: this.announces,
                positions: this.cachedPositions,
                pathSoftCap: VIZ_PATH_TABLE_SOFT_CAP,
                announceSoftCap: VIZ_ANNOUNCE_SOFT_CAP,
            });
        },
        onUserHopMaxFilterChange(v) {
            this.hopMaxFilter = v;
            writeStoredHopMaxFilter(v);
        },
        async getInterfaceStats() {
            try {
                const response = await window.api.get(`/api/v1/interface-stats`, {
                    signal: this.abortController.signal,
                });
                this.interfaces = response.data.interface_stats?.interfaces ?? [];
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
                console.error("Failed to fetch interface stats", e);
            }
        },
        async getDiscoveredInterfaces() {
            try {
                const response = await window.api.get(`/api/v1/reticulum/discovered-interfaces`, {
                    signal: this.abortController.signal,
                });
                this.discoveredInterfaces = response.data?.interfaces ?? [];
                this.discoveredActive = response.data?.active ?? [];
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
            }
        },
        async getPathTableBatch(destinationHashes = null) {
            this.pathTable = [];
            try {
                this.loadingStatus = "Loading paths...";
                if (destinationHashes && destinationHashes.length > 0) {
                    const resp = await window.api.post(
                        `/api/v1/path-table`,
                        { destination_hashes: destinationHashes },
                        {
                            signal: this.abortController.signal,
                        }
                    );
                    this.pathTable.push(...resp.data.path_table);
                } else {
                    const firstResp = await window.api.get(`/api/v1/path-table`, {
                        params: { limit: this.pageSize, offset: 0 },
                        signal: this.abortController.signal,
                    });
                    this.pathTable.push(...firstResp.data.path_table);
                    const totalCount = firstResp.data.total_count;
                    const softCap = VIZ_PATH_TABLE_SOFT_CAP;
                    if (totalCount > this.pageSize) {
                        const concurrency = this.pathFetchConcurrency;
                        for (let offset = this.pageSize; offset < totalCount; offset += this.pageSize * concurrency) {
                            if (this.abortController.signal.aborted) return;
                            if (this.pathTable.length >= softCap) {
                                this.loadingStatus = `Loading paths (capped at ${softCap} / ${totalCount})`;
                                break;
                            }
                            const chunk = [];
                            for (let i = 0; i < concurrency && offset + i * this.pageSize < totalCount; i++) {
                                chunk.push(offset + i * this.pageSize);
                            }
                            const promises = chunk.map((o) =>
                                window.api.get(`/api/v1/path-table`, {
                                    params: { limit: this.pageSize, offset: o },
                                    signal: this.abortController.signal,
                                })
                            );
                            const responses = await Promise.all(promises);
                            for (const r of responses) {
                                const rows = r.data.path_table || [];
                                const room = softCap - this.pathTable.length;
                                if (room <= 0) break;
                                this.pathTable.push(...rows.slice(0, room));
                            }
                            this.loadingStatus = `Loading paths (${this.pathTable.length} / ${totalCount})`;
                        }
                    }
                }
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
                console.error("Failed to fetch path table batch", e);
            }
        },
        async fetchAnnouncesForHashes(hashes) {
            if (!Array.isArray(hashes) || hashes.length === 0) {
                return;
            }
            const concurrency = this.pathFetchConcurrency;
            for (let i = 0; i < hashes.length; i += ANNOUNCE_HASH_CHUNK_SIZE * concurrency) {
                if (this.abortController.signal.aborted) return;
                const offsets = [];
                for (let j = 0; j < concurrency && i + j * ANNOUNCE_HASH_CHUNK_SIZE < hashes.length; j++) {
                    offsets.push(i + j * ANNOUNCE_HASH_CHUNK_SIZE);
                }
                const promises = offsets.map((start) => {
                    const chunk = hashes.slice(start, start + ANNOUNCE_HASH_CHUNK_SIZE);
                    return window.api.post(
                        "/api/v1/announces/query",
                        {
                            destination_hashes: chunk,
                            aspects: VIZ_ANNOUNCE_ASPECTS,
                        },
                        { signal: this.abortController.signal }
                    );
                });
                const responses = await Promise.all(promises);
                for (const resp of responses) {
                    for (const announce of resp.data?.announces || []) {
                        if (announce?.destination_hash) {
                            this.announces[announce.destination_hash] = announce;
                        }
                    }
                }
                this.loadingStatus = `Loading announces (${Object.keys(this.announces).length})`;
            }
        },
        async ensureAnnouncesForPathHashes({ reset = false } = {}) {
            const needed = pathHashesWithinHopFilter(this.pathTable, this.hopMaxFilter);
            if (reset) {
                this.announces = {};
            }
            const missing = needed.filter((hash) => !this.announces[hash]);
            if (missing.length > 0) {
                this.loadingStatus = "Loading announces...";
                await this.fetchAnnouncesForHashes(missing);
            }
            if (needed.length > 0) {
                const neededSet = new Set(needed);
                for (const hash of Object.keys(this.announces)) {
                    if (!neededSet.has(hash)) {
                        delete this.announces[hash];
                    }
                }
            }
            const announceKeys = Object.keys(this.announces);
            if (announceKeys.length > VIZ_ANNOUNCE_SOFT_CAP) {
                const neededSet = new Set(needed);
                const extras = announceKeys.filter((hash) => !neededSet.has(hash));
                const overflow = announceKeys.length - VIZ_ANNOUNCE_SOFT_CAP;
                for (const hash of extras.slice(0, overflow)) {
                    delete this.announces[hash];
                }
            }
        },
        async getConfig() {
            try {
                const response = await window.api.get("/api/v1/config", {
                    signal: this.abortController.signal,
                });
                this.config = response.data.config;
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
                console.error("Failed to fetch config", e);
            }
        },
        async getConversations() {
            try {
                const response = await window.api.get(`/api/v1/lxmf/conversations`, {
                    signal: this.abortController.signal,
                    params: { limit: 2000 },
                });
                this.conversations = {};
                for (const conversation of response.data.conversations) {
                    this.conversations[conversation.destination_hash] = conversation;
                }
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
                console.error("Failed to fetch conversations", e);
            }
        },
        async createIconImage(iconName, foregroundColor, backgroundColor, size = 64) {
            const cacheKey = `${iconName}-${foregroundColor}-${backgroundColor}-${size}`;
            if (this.iconCache[cacheKey]) {
                return this.iconCache[cacheKey];
            }

            // Limit cache size to 500 icons (approx 15-20MB max)
            const cacheKeys = Object.keys(this.iconCache);
            if (cacheKeys.length >= 500) {
                // simple FIFO eviction
                const oldKey = cacheKeys[0];
                const oldUrl = this.iconCache[oldKey];
                if (oldUrl && oldUrl.startsWith("blob:")) {
                    // Check if any other keys use this URL before revoking
                    const stillUsed = Object.values(this.iconCache).some(
                        (u, i) => u === oldUrl && Object.keys(this.iconCache)[i] !== oldKey
                    );
                    if (!stillUsed) {
                        URL.revokeObjectURL(oldUrl);
                    }
                }
                delete this.iconCache[oldKey];
            }

            return new Promise((resolve) => {
                const canvas = document.createElement("canvas");
                canvas.width = size;
                canvas.height = size;
                const ctx = canvas.getContext("2d", { alpha: true });

                // draw background circle with subtle gradient
                const gradient = ctx.createLinearGradient(0, 0, 0, size);
                gradient.addColorStop(0, backgroundColor);
                gradient.addColorStop(1, backgroundColor);

                ctx.fillStyle = gradient;
                ctx.beginPath();
                ctx.arc(size / 2, size / 2, size / 2 - 2, 0, 2 * Math.PI);
                ctx.fill();

                // Add subtle inner shadow for depth
                const innerShadow = ctx.createRadialGradient(
                    size / 2,
                    size / 2,
                    size / 2 - 10,
                    size / 2,
                    size / 2,
                    size / 2
                );
                innerShadow.addColorStop(0, "rgba(0,0,0,0)");
                innerShadow.addColorStop(1, "rgba(0,0,0,0.15)");
                ctx.fillStyle = innerShadow;
                ctx.fill();

                // Add a glass highlight on top
                const highlight = ctx.createLinearGradient(0, 0, 0, size);
                highlight.addColorStop(0, "rgba(255,255,255,0.25)");
                highlight.addColorStop(0.5, "rgba(255,255,255,0)");
                ctx.fillStyle = highlight;
                ctx.beginPath();
                ctx.arc(size / 2, size / 2, size / 2 - 4, 0, 2 * Math.PI);
                ctx.fill();

                // stroke
                ctx.strokeStyle = "rgba(255,255,255,0.2)";
                ctx.lineWidth = 2;
                ctx.stroke();

                // load MDI icon SVG
                const iconSvg = this.getMdiIconSvg(iconName, foregroundColor);
                const img = new Image();
                const svgBlob = new Blob([iconSvg], { type: "image/svg+xml" });
                const url = URL.createObjectURL(svgBlob);
                img.onload = () => {
                    if (this.abortController.signal.aborted) {
                        URL.revokeObjectURL(url);
                        resolve(null);
                        return;
                    }
                    // Draw a subtle shadow for the icon itself
                    ctx.shadowColor = "rgba(0,0,0,0.2)";
                    ctx.shadowBlur = 4;
                    ctx.shadowOffsetX = 0;
                    ctx.shadowOffsetY = 2;

                    ctx.drawImage(img, size * 0.22, size * 0.22, size * 0.56, size * 0.56);

                    // Reset shadow for next operations
                    ctx.shadowColor = "transparent";
                    ctx.shadowBlur = 0;
                    ctx.shadowOffsetX = 0;
                    ctx.shadowOffsetY = 0;

                    URL.revokeObjectURL(url);

                    canvas.toBlob((blob) => {
                        const blobUrl = URL.createObjectURL(blob);
                        this.iconCache[cacheKey] = blobUrl;
                        resolve(blobUrl);
                    }, "image/png");
                };
                img.onerror = () => {
                    if (this.abortController.signal.aborted) {
                        URL.revokeObjectURL(url);
                        resolve(null);
                        return;
                    }
                    URL.revokeObjectURL(url);
                    canvas.toBlob((blob) => {
                        const blobUrl = URL.createObjectURL(blob);
                        this.iconCache[cacheKey] = blobUrl;
                        resolve(blobUrl);
                    }, "image/png");
                };
                img.src = url;
            });
        },
        getMdiIconSvg(iconName, foregroundColor) {
            const iconPath = getMdiIconPath(iconName);

            return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="${foregroundColor}" d="${iconPath}"/></svg>`;
        },
        loadVisualiserDisplayPrefs() {
            const p = loadVisualiserDisplayPrefs();
            this.showDisabledInterfaces = p.showDisabledInterfaces;
            this.showDiscoveredInterfaces = p.showDiscoveredInterfaces;
            this.enablePhysics = p.enablePhysics;
            this.autoReload = p.autoReload;
            this.preferredRenderer = p.renderer || "auto";
        },
        async onPreferredRendererChange(next) {
            const normalized = next === "webgl" || next === "vis" || next === "auto" ? next : "auto";
            if (normalized === this.preferredRenderer) return;
            this.preferredRenderer = normalized;
            persistVisualiserRenderer(normalized, { emit: false });
            await this.reinitRenderer();
        },
        destroyActiveRenderer() {
            this.hoverTooltip = null;
            if (this.webglEngine) {
                this.webglEngine.destroy();
                this.webglEngine = null;
            }
            if (this.network) {
                this.network.destroy();
                this.network = null;
            }
            try {
                this.nodes.clear();
                this.edges.clear();
            } catch {
                /* ignore */
            }
            this.rendererMode = "vis";
        },
        async reinitRenderer() {
            this.destroyActiveRenderer();
            await this.init({ skipWarm: true });
        },
        async tryStartWebGL() {
            const canvas = this.$refs.webglCanvas;
            if (!canvas || !canUseVisualiserWebGL()) {
                return false;
            }
            try {
                this.webglEngine = createVisualiserWebGLEngine(canvas, {
                    getLiveLayout: () => this.enablePhysics === true,
                    isDark: () => document.documentElement.classList.contains("dark"),
                    onNodeActivate: (id, meta) => this.onWebGLNodeActivate(id, meta),
                    onHover: (id, meta, x, y) => this.onWebGLHover(id, meta, x, y),
                });
                this.rendererMode = "webgl";
                this.engineMode = "webgl";
                return true;
            } catch (e) {
                console.warn("WebGL visualiser failed:", e);
                if (this.webglEngine) {
                    this.webglEngine.destroy();
                    this.webglEngine = null;
                }
                this.rendererMode = "vis";
                return false;
            }
        },
        refreshPhysicsEnabled() {
            if (this.webglEngine) {
                this.webglEngine.setLiveLayout(this.enablePhysics);
                if (!this.enablePhysics) {
                    const snap = this.webglEngine.getPositions() || {};
                    this.cachedPositions = { ...this.cachedPositions, ...snap };
                }
                return;
            }
            if (!this.network) return;
            if (this.physicsPausedForDrag) return;
            // Freeze current coordinates before stopping the solver so peers
            // stay where the live layout left them.
            if (!this.enablePhysics) {
                this.snapshotNetworkPositions();
            }
            this.network.setOptions({
                physics: { enabled: this.enablePhysics },
                edges: { smooth: VIZ_EDGE_SMOOTH },
            });
        },
        snapshotNetworkPositions() {
            if (!this.network || typeof this.network.getPositions !== "function") return;
            const ids = this.nodes.getIds();
            if (!ids.length) return;
            const snap = this.network.getPositions(ids) || {};
            const updates = [];
            for (const id of ids) {
                const p = snap[id];
                if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                    this.cachedPositions[id] = { x: p.x, y: p.y };
                    updates.push({ id, x: p.x, y: p.y });
                }
            }
            if (updates.length > 0) {
                this.nodes.update(updates);
            }
        },
        resettleLayoutFromNetwork() {
            if (!this.network || typeof this.network.getPositions !== "function") return;
            const ids = this.nodes.getIds();
            if (!ids.length) return;
            const snap = this.network.getPositions(ids) || {};
            const layoutNodes = [];
            for (const id of ids) {
                const node = this.nodes.get(id);
                const p = snap[id] || {};
                layoutNodes.push({
                    id,
                    x: Number.isFinite(p.x) ? p.x : node?.x || 0,
                    y: Number.isFinite(p.y) ? p.y : node?.y || 0,
                    mass: id === "me" ? 4 : node?.group === "interface" ? 2.5 : 1,
                    fixed: id === "me",
                });
            }
            const layoutEdges = this.edges.get().map((e) => ({
                from: e.from,
                to: e.to,
                length: e.width >= 2.5 ? 260 : 300,
            }));
            const settled = settleLayout({ nodes: layoutNodes, edges: layoutEdges, iterations: 0 });
            const positions = settled?.positions || {};
            const updates = [];
            for (const id of ids) {
                const p = positions[id];
                if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                    updates.push({ id, x: p.x, y: p.y });
                    this.cachedPositions[id] = { x: p.x, y: p.y };
                }
            }
            if (updates.length > 0) {
                this.nodes.update(updates);
            }
            if (this.enablePhysics) {
                this.refreshPhysicsEnabled();
            }
        },
        pickStablePosition(id, posById, initialFn) {
            const prev = posById[id];
            if (prev && Number.isFinite(prev.x) && Number.isFinite(prev.y)) {
                return { x: prev.x, y: prev.y };
            }
            const v = initialFn();
            posById[id] = { x: v.x, y: v.y };
            return v;
        },
        async init(opts = {}) {
            if (!opts.skipWarm) {
                await warmVisualiserWasm();
            }
            const preferred = this.preferredRenderer || loadVisualiserDisplayPrefs().renderer || "auto";

            if (preferred === "vis") {
                await this.initVisNetwork();
                return;
            }

            const started = await this.tryStartWebGL();
            if (started) {
                await this.manualUpdate();
                this.restartAutoReloadInterval();
                return;
            }

            if (preferred === "webgl") {
                ToastUtils.warning(this.$t("visualiser.renderer_webgl_unavailable"));
            }
            await this.initVisNetwork();
        },
        onWebGLNodeActivate(id, meta) {
            const announce = meta?.announce;
            if (!announce) return;
            this.openAnnounceDestination(announce, id);
        },
        openAnnounceDestination(announce, fallbackHash = "") {
            if (!announce) return;
            const destinationHash = (announce.destination_hash || announce.destinationHash || fallbackHash || "")
                .toString()
                .trim();
            if (!destinationHash) return;

            if (announce.aspect === "lxmf.delivery") {
                this.$router.push({
                    name: "messages",
                    params: { destinationHash },
                });
                return;
            }
            if (announce.aspect === "nomadnetwork.node") {
                // Navigate directly. Do not rely on nomad-open-node: that listener
                // only exists while NomadNetworkBrowser is mounted (keep-alive).
                this.$router
                    .push({
                        name: "nomadnetwork",
                        params: { destinationHash },
                        query: { newTab: "1" },
                    })
                    .catch(() => {});
            }
        },
        onWebGLHover(id, meta, x, y) {
            if (!id || !meta) {
                this.hoverTooltip = null;
                return;
            }
            const text = meta.title || meta.label || id;
            this.hoverTooltip = { x, y, text };
        },
        async initVisNetwork() {
            const container = document.getElementById("network");
            const isDarkMode = document.documentElement.classList.contains("dark");
            this.rendererMode = "vis";

            this.network = new Network(
                container,
                {
                    nodes: this.nodes,
                    edges: this.edges,
                },
                {
                    interaction: {
                        tooltipDelay: 100,
                        hover: true,
                        // Hide edges while dragging/zooming, which is the biggest win vs upstream
                        // for large graphs (upstream redraws every edge every frame).
                        hideEdgesOnDrag: true,
                        hideEdgesOnZoom: true,
                    },
                    layout: {
                        randomSeed: 42,
                        improvedLayout: false, // faster for large networks
                    },
                    physics: {
                        enabled: this.enablePhysics,
                        solver: "barnesHut",
                        barnesHut: {
                            // Match upstream gravity, as avoidOverlap is O(n) per tick
                            // and is the main reason we felt slower than MeshChat.
                            gravitationalConstant: -3500,
                            springConstant: 0.03,
                            springLength: 200,
                            damping: 0.55,
                            avoidOverlap: 0,
                            theta: 0.6,
                        },
                        stabilization: {
                            enabled: true,
                            iterations: 80,
                            updateInterval: 50,
                        },
                        maxVelocity: 22,
                        minVelocity: 1.2,
                        timestep: 0.35,
                    },
                    nodes: {
                        borderWidth: 2,
                        borderWidthSelected: 4,
                        color: {
                            border: "#3b82f6",
                            background: isDarkMode ? "#1e40af" : "#eff6ff",
                            highlight: { border: "#3b82f6", background: isDarkMode ? "#2563eb" : "#dbeafe" },
                            hover: { border: "#3b82f6", background: isDarkMode ? "#2563eb" : "#dbeafe" },
                        },
                        font: {
                            face: "Inter, system-ui, sans-serif",
                            strokeWidth: 3,
                            strokeColor: isDarkMode ? "rgba(9, 9, 11, 0.95)" : "rgba(255, 255, 255, 0.95)",
                        },
                        // Canvas shadows are by far the most expensive per-node
                        // operation in vis-network. Disable globally, as the borders
                        // and circular-image rendering remain visually distinct.
                        shadow: false,
                    },
                    edges: {
                        smooth: VIZ_EDGE_SMOOTH,
                        selectionWidth: 2,
                        hoverWidth: 1.5,
                        color: {
                            opacity: 0.6,
                        },
                    },
                }
            );

            this.network.on("doubleClick", (params) => {
                const clickedNodeId = params.nodes[0];
                if (!clickedNodeId) return;

                const node = this.nodes.get(clickedNodeId);
                if (!node || !node._announce) return;

                this.openAnnounceDestination(node._announce, clickedNodeId);
            });

            this.refreshPhysicsEnabled();

            this.network.on("dragStart", () => {
                if (!this.enablePhysics || !this.network || this.physicsPausedForDrag) return;
                this.physicsPausedForDrag = true;
                this.network.setOptions({
                    physics: { enabled: false },
                    edges: { smooth: VIZ_EDGE_SMOOTH },
                });
            });
            this.network.on("dragEnd", () => {
                if (!this.physicsPausedForDrag || !this.network) return;
                this.physicsPausedForDrag = false;
                this.network.setOptions({
                    physics: { enabled: this.enablePhysics },
                    edges: { smooth: VIZ_EDGE_SMOOTH },
                });
            });

            this.network.on("zoom", () => {
                this.scheduleUpdateLOD();
            });

            await this.manualUpdate();

            // auto reload (interval respects battery saver)
            this.restartAutoReloadInterval();
        },
        async manualUpdate() {
            if (this.isLoading || this.isUpdating) return;
            this.isLoading = true;
            this.isUpdating = true;
            try {
                await this.update({ silent: false });
            } finally {
                this.isLoading = false;
                this.isUpdating = false;
            }
        },
        async onAutoReload() {
            if (!this.autoReload || this.isUpdating || this.isLoading) return;
            this.isUpdating = true;
            try {
                await this.update({ silent: true });
            } finally {
                this.isUpdating = false;
            }
        },
        scheduleUpdateLOD() {
            if (this.lodRafId != null) {
                cancelAnimationFrame(this.lodRafId);
            }
            this.lodRafId = requestAnimationFrame(() => {
                this.lodRafId = null;
                this.updateLOD();
            });
        },
        updateLOD() {
            if (!this.network) return;
            if (typeof this.network.getScale !== "function") return;
            const scale = this.network.getScale();
            const newLOD = lodLevelFromScale(scale);

            if (this.currentLOD === newLOD) return;
            this.currentLOD = newLOD;

            // Only mutate nodes whose LOD props actually change (avoids O(N)
            // DataSet churn + full redraw when zooming across thresholds).
            const isDarkMode = document.documentElement.classList.contains("dark");
            const updates = computeLodUpdates(this.nodes.get(), newLOD, isDarkMode);
            if (updates.length > 0) {
                this.nodes.update(updates);
            }

            if (newLOD === "high" && this.iconQueue.length > 0) {
                this.scheduleIconQueue();
            }
        },
        nodeColor(border, background) {
            return {
                border,
                background,
                highlight: { border, background },
                hover: { border, background },
            };
        },
        pathHopCount(hops) {
            const n = Number(hops);
            return Number.isFinite(n) ? n : null;
        },
        isDirectPathHop(hops) {
            return this.pathHopCount(hops) === 1;
        },
        directEdgeColor(isDarkMode) {
            return {
                color: isDarkMode ? "#34d399" : "#10b981",
                opacity: 1,
            };
        },
        multiHopEdgeColor(isDarkMode) {
            return {
                color: isDarkMode ? "#60a5fa" : "#3b82f6",
                opacity: 0.5,
            };
        },
        interfaceDisplayLabel(name) {
            if (!name) return "Interface";
            const bracket = name.match(/\[([^\]]+)\]/);
            if (bracket) return bracket[1];
            if (name.length > 28) return `${name.slice(0, 25)}...`;
            return name;
        },
        pathTableInterfaceNames() {
            const names = new Set();
            for (const entry of this.pathTable) {
                if (!entry?.interface || entry.hops == null) continue;
                if (this.hopFilterMax != null && entry.hops > this.hopFilterMax) continue;
                names.add(entry.interface);
            }
            return names;
        },
        getNodeLODProps(node, lod) {
            const isDarkMode = document.documentElement.classList.contains("dark");
            const fontColor = isDarkMode ? "#ffffff" : "#000000";
            const blueBorder = "#3b82f6";
            const blueBg = isDarkMode ? "#1e40af" : "#eff6ff";

            if (lod === "low") {
                const isInterface = node.group === "interface";
                const baseColor = isInterface && node.color ? node.color : this.nodeColor(blueBorder, blueBg);
                return {
                    id: node.id,
                    shape: "dot",
                    size: node.id === "me" ? 15 : 10,
                    font: { size: 0 },
                    color: baseColor,
                };
            } else if (lod === "medium") {
                return {
                    id: node.id,
                    shape: node._originalShape || "circularImage",
                    size: node._originalSize || (node.id === "me" ? 50 : 25),
                    font: { size: 0 },
                };
            } else {
                return {
                    id: node.id,
                    shape: node._originalShape || "circularImage",
                    size: node._originalSize || (node.id === "me" ? 50 : 25),
                    font: { size: node.id === "me" ? 16 : 11, color: fontColor },
                };
            }
        },
        async update(options = {}) {
            const silent = options.silent === true;
            const alreadyPainted = this.displayNodeCount > 0;

            if (!silent) {
                this.loadingStatus = "Fetching basic info...";
                this.currentBatch = 0;
                this.totalBatches = 0;
            }

            await this.getConfig();
            if (this.abortController.signal.aborted) return;

            const identityHash = this.config?.identity_hash;
            /*
             * Cold open only: restore IndexedDB cache for a fast first paint.
             * Auto-refresh must not reload cache (would overwrite live path data
             * and rebuild the graph twice, which looks like a UI reset).
             */
            let paintedFromCache = false;
            if (identityHash && !alreadyPainted) {
                const cached = await loadVisualiserCache(identityHash);
                if (cached?.pathTable?.length) {
                    this.pathTable = cached.pathTable;
                    this.announces = { ...(cached.announces || {}) };
                    this.cachedPositions = { ...(cached.positions || {}) };
                    paintedFromCache = true;
                }
            }

            await Promise.all([this.getInterfaceStats(), this.getConversations(), this.getDiscoveredInterfaces()]);
            if (this.abortController.signal.aborted) return;

            if (!silent && paintedFromCache && this.pathTable.length > 0) {
                this.loadingStatus = "Restoring cached graph...";
                await this.processVisualization({ silent: false });
                if (this.abortController.signal.aborted) return;
            }

            if (!silent) {
                this.loadingStatus = "Fetching network data...";
            }
            await this.getPathTableBatch();
            if (this.abortController.signal.aborted) return;
            /*
             * Keep cached announces for known hashes and only fetch missing ones
             * so reopen stays fast while still picking up newly seen nodes.
             */
            await this.ensureAnnouncesForPathHashes({ reset: false });
            if (this.abortController.signal.aborted) return;

            await this.processVisualization({ silent });
            if (this.abortController.signal.aborted) return;
            await this.persistVisualiserCache();
        },
        async processVisualization(options = {}) {
            const silent = options.silent === true;
            await new Promise((r) => {
                requestAnimationFrame(r);
            });
            if (this.abortController.signal.aborted) return;

            const runId = ++this.vizRunGeneration;

            if (!silent) {
                this.loadingStatus = "Processing visualization...";
            }

            /*
             * Invalidate any in-flight icon-generation work. Each call to
             * processVisualization gets a new generation token; queued items
             * carrying an older token are dropped when consumed so we do not
             * paint canvases for nodes that no longer exist.
             */
            this.iconQueueGeneration += 1;
            this.iconQueue = [];

            /*
             * Pause vis-network physics for the bulk update. WASM may settle
             * starting positions, then Live Layout re-enables JS physics so the
             * graph keeps moving without requiring a drag.
             * Silent auto-refresh keeps physics running so existing nodes do not jump.
             */
            const physicsWasOn = this.network && this.enablePhysics;
            const pausePhysics = Boolean(this.network && !silent);
            if (pausePhysics) {
                this.network.setOptions({
                    physics: { enabled: false },
                    edges: { smooth: VIZ_EDGE_SMOOTH },
                });
            }

            try {
                await this._processVisualizationGraph(runId, { silent });
            } finally {
                if (runId === this.vizRunGeneration) {
                    if (this.webglEngine) {
                        this.webglEngine.setLiveLayout(this.enablePhysics);
                        this.webglEngine.requestRedraw();
                    }
                    if (this.network && !this.didDisableStabilization) {
                        this.didDisableStabilization = true;
                        this.network.setOptions({
                            physics: { stabilization: { enabled: false } },
                            edges: { smooth: VIZ_EDGE_SMOOTH },
                        });
                    }
                    if (pausePhysics && this.network && !this.physicsPausedForDrag) {
                        this.network.setOptions({
                            physics: { enabled: Boolean(physicsWasOn || this.enablePhysics) },
                            edges: { smooth: VIZ_EDGE_SMOOTH },
                        });
                    }
                    if (this.network && typeof this.network.redraw === "function") {
                        this.network.redraw();
                    }
                }
            }
        },
        async _processVisualizationGraph(runId, options = {}) {
            const silent = options.silent === true;
            const isCurrentRun = () => runId === this.vizRunGeneration && !this.abortController.signal.aborted;
            const processedNodeIds = new Set();
            const processedEdgeIds = new Set();

            const posById = {};
            for (const [id, p] of Object.entries(this.cachedPositions || {})) {
                if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                    posById[id] = { x: p.x, y: p.y };
                }
            }
            const existingNodeIds = this.nodes.getIds();
            if (this.webglEngine) {
                const snap = this.webglEngine.getPositions() || {};
                for (const [id, p] of Object.entries(snap)) {
                    if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                        posById[id] = { x: p.x, y: p.y };
                    }
                }
            } else if (this.network) {
                const snap = this.network.getPositions(existingNodeIds);
                if (snap) {
                    for (const id of existingNodeIds) {
                        const p = snap[id];
                        if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                            posById[id] = { x: p.x, y: p.y };
                        }
                    }
                }
            }

            const isDarkMode = document.documentElement.classList.contains("dark");
            this.totalNodesToLoad = this.pathTable.length;
            this.loadedNodesCount = 0;
            if (!silent) {
                this.loadingStatus = "Building graph...";
            }

            const announcePayload = {};
            for (const [hash, announce] of Object.entries(this.announces || {})) {
                if (!announce) continue;
                announcePayload[hash] = {
                    destination_hash: announce.destination_hash,
                    aspect: announce.aspect,
                    display_name: announce.display_name,
                    custom_display_name: announce.custom_display_name,
                    identity_hash: announce.identity_hash,
                    last_seen: announce.updated_at
                        ? Utils.convertDateTimeToLocalDateTimeString(new Date(announce.updated_at))
                        : "",
                };
            }
            const conversationPayload = {};
            for (const [hash, conv] of Object.entries(this.conversations || {})) {
                if (!conv?.lxmf_user_icon) continue;
                conversationPayload[hash] = { lxmf_user_icon: conv.lxmf_user_icon };
            }

            const searchLower = this.searchQuery.toLowerCase();
            const matchesSearch = (text) => !this.searchQuery || (text && text.toLowerCase().includes(searchLower));

            const interfacesPayload = [];
            for (const entry of this.interfaces) {
                if (!this.showDisabledInterfaces && !entry.status) continue;
                let label = entry.interface_name ?? entry.name;
                if (entry.type === "LocalServerInterface" || entry.parent_interface_name != null) {
                    label = entry.name;
                }
                if (!matchesSearch(label) && !matchesSearch(entry.name)) continue;
                interfacesPayload.push({
                    name: entry.name,
                    label,
                    title: `${entry.name}\nState: ${entry.status ? "Online" : "Offline"}\nBitrate: ${Utils.formatBitsPerSecond(entry.bitrate)}\nTX: ${Utils.formatBytes(entry.txb)}\nRX: ${Utils.formatBytes(entry.rxb)}`,
                    online: !!entry.status,
                });
            }

            const saver = this.batterySaverPrefs || loadBatterySaverPrefs();
            if (
                saver.enabled &&
                saver.maxVisualiserInterfaces > 0 &&
                interfacesPayload.length > saver.maxVisualiserInterfaces
            ) {
                interfacesPayload.sort((a, b) => Number(b.online) - Number(a.online));
                interfacesPayload.length = saver.maxVisualiserInterfaces;
            }

            const seenIface = new Set(interfacesPayload.map((i) => i.name));
            const pathOnlyPayload = [];
            for (const name of this.pathTableInterfaceNames()) {
                if (seenIface.has(name)) continue;
                if (!matchesSearch(name) && !matchesSearch(this.interfaceDisplayLabel(name))) continue;
                pathOnlyPayload.push({
                    name,
                    label: this.interfaceDisplayLabel(name),
                    title: `${name}\nState: Active (path table)\nUsed as next-hop for known routes`,
                    online: true,
                });
            }

            const discoveredPayload = [];
            if (this.showDiscoveredInterfaces) {
                const activeEndpoints = new Set();
                for (const a of this.discoveredActive) {
                    const aHost = a.target_host || a.remote || a.listen_ip;
                    const aPort = a.target_port || a.listen_port;
                    if (aHost && aPort != null) activeEndpoints.add(`${aHost}:${aPort}`);
                }
                for (const disc of this.discoveredInterfaces) {
                    const discId = `discovered~${disc.discovery_hash || disc.name}`;
                    const discLabel = disc.name || disc.reachable_on || "Unknown";
                    if (
                        !matchesSearch(discLabel) &&
                        !matchesSearch(disc.reachable_on) &&
                        !matchesSearch(disc.transport_id)
                    ) {
                        continue;
                    }
                    const isConnected =
                        disc.reachable_on != null &&
                        disc.port != null &&
                        activeEndpoints.has(`${disc.reachable_on}:${disc.port}`);
                    discoveredPayload.push({
                        id: discId,
                        label: discLabel,
                        title: `Discovered: ${discLabel}\nType: ${disc.type || "Unknown"}\nHops: ${disc.hops ?? "?"}\nStatus: ${isConnected ? "Connected" : disc.status || "Available"}${disc.reachable_on ? `\nAddress: ${disc.reachable_on}:${disc.port}` : ""}`,
                        connected: isConnected,
                        hops: disc.hops ?? null,
                    });
                }
            }

            const meLabel = this.config?.display_name ?? "Local Node";
            const fullReq = {
                me_label: meLabel,
                me_title: `Local Node: ${meLabel}\nIdentity: ${this.config?.identity_hash ?? "Unknown"}`,
                me_image: this.reticulumLogoPath,
                identity_hash: this.config?.identity_hash ?? "",
                interfaces: interfacesPayload,
                path_only_interfaces: pathOnlyPayload,
                discovered: discoveredPayload,
                path_table: this.pathTable,
                announces: announcePayload,
                conversations: conversationPayload,
                icon_cache: this.iconCache,
                positions: posById,
                hop_max: this.hopFilterMax,
                search: this.searchQuery,
                dark_mode: isDarkMode,
                lod: this.currentLOD,
                aspects: VIZ_ANNOUNCE_ASPECTS,
                queue_icons: this.currentLOD !== "low",
                icon_generation: this.iconQueueGeneration,
                show_discovered: this.showDiscoveredInterfaces,
            };

            let graph;
            if (isVisualiserWasmReady()) {
                graph = buildFullGraph(fullReq);
            } else {
                // JS fallback keeps the previous path-only WASM/JS builder plus local shells.
                graph = buildFullGraph(fullReq);
                if (!graph.nodes?.some((n) => n.id === "me")) {
                    // buildFullGraph JS fallback only emits path nodes when WASM is down
                }
            }
            if (!isCurrentRun()) return;

            let graphNodes = Array.isArray(graph.nodes) ? graph.nodes : [];
            let graphEdges = Array.isArray(graph.edges) ? graph.edges : [];

            // When WASM full-graph is unavailable, synthesize me/ifaces/discovered in JS.
            if (!isVisualiserWasmReady()) {
                const localNodes = [];
                const localEdges = [];
                if (matchesSearch(meLabel) || matchesSearch(this.config?.identity_hash)) {
                    const mp = this.pickStablePosition("me", posById, () => ({ x: 0, y: 0 }));
                    let meNode = {
                        id: "me",
                        group: "me",
                        size: 50,
                        _originalSize: 50,
                        shape: "circularImage",
                        _originalShape: "circularImage",
                        image: this.reticulumLogoPath,
                        label: meLabel,
                        title: fullReq.me_title,
                        color: this.nodeColor("#3b82f6", isDarkMode ? "#1e40af" : "#eff6ff"),
                        font: { color: isDarkMode ? "#ffffff" : "#000000", size: 16, bold: true },
                        x: mp.x,
                        y: mp.y,
                    };
                    meNode = { ...meNode, ...this.getNodeLODProps(meNode, this.currentLOD) };
                    localNodes.push(meNode);
                }
                for (const entry of interfacesPayload) {
                    const pos = this.pickStablePosition(entry.name, posById, () => ({ x: 400, y: 0 }));
                    let n = {
                        id: entry.name,
                        group: "interface",
                        label: entry.label,
                        title: entry.title,
                        size: 35,
                        _originalSize: 35,
                        shape: "circularImage",
                        _originalShape: "circularImage",
                        image: entry.online
                            ? "/assets/images/network-visualiser/interface_connected.png"
                            : "/assets/images/network-visualiser/interface_disconnected.png",
                        color: this.nodeColor(entry.online ? "#10b981" : "#ef4444", isDarkMode ? "#064e3b" : "#ecfdf5"),
                        font: { color: isDarkMode ? "#ffffff" : "#000000", size: 12, bold: true },
                        x: pos.x,
                        y: pos.y,
                    };
                    n = { ...n, ...this.getNodeLODProps(n, this.currentLOD) };
                    localNodes.push(n);
                    localEdges.push({
                        id: `me~${entry.name}`,
                        from: "me",
                        to: entry.name,
                        color: entry.online
                            ? this.directEdgeColor(isDarkMode)
                            : { color: isDarkMode ? "#f87171" : "#ef4444", opacity: 1 },
                        width: 3,
                        hidden: false,
                    });
                }
                for (const entry of pathOnlyPayload) {
                    const pos = this.pickStablePosition(entry.name, posById, () => ({ x: 400, y: 0 }));
                    let n = {
                        id: entry.name,
                        group: "interface",
                        label: entry.label,
                        title: entry.title,
                        size: 35,
                        _originalSize: 35,
                        shape: "circularImage",
                        _originalShape: "circularImage",
                        image: "/assets/images/network-visualiser/interface_connected.png",
                        color: this.nodeColor("#10b981", isDarkMode ? "#064e3b" : "#ecfdf5"),
                        font: { color: isDarkMode ? "#ffffff" : "#000000", size: 12, bold: true },
                        x: pos.x,
                        y: pos.y,
                    };
                    n = { ...n, ...this.getNodeLODProps(n, this.currentLOD) };
                    localNodes.push(n);
                    localEdges.push({
                        id: `me~${entry.name}`,
                        from: "me",
                        to: entry.name,
                        color: this.directEdgeColor(isDarkMode),
                        width: 3,
                        hidden: false,
                    });
                }
                graphNodes = [...localNodes, ...graphNodes];
                graphEdges = [...localEdges, ...graphEdges];
                graph.layout_nodes = graphNodes.map((n) => ({
                    id: n.id,
                    x: n.x,
                    y: n.y,
                    mass: n.group === "me" ? 4 : n.group === "interface" ? 2.5 : 1,
                    fixed: n.id === "me",
                }));
                graph.layout_edges = graphEdges.map((e) => ({
                    from: e.from,
                    to: e.to,
                    length: e.width >= 2.5 ? 260 : 300,
                }));
            }

            if (!silent) {
                this.loadingStatus = "Settling layout...";
            }
            const layoutNodes = Array.isArray(graph.layout_nodes) ? graph.layout_nodes : [];
            const layoutEdges = Array.isArray(graph.layout_edges) ? graph.layout_edges : [];
            /*
             * Place only nodes that still lack coordinates. Existing nodes stay
             * fixed so auto-refresh spawns newcomers without resetting the map.
             */
            const missingIds = new Set();
            for (const n of layoutNodes) {
                const p = posById[n.id];
                if (!(p && Number.isFinite(p.x) && Number.isFinite(p.y))) {
                    missingIds.add(n.id);
                }
            }
            const shouldSettle = missingIds.size > 0 && isVisualiserWasmReady();
            if (shouldSettle) {
                const settleNodes = layoutNodes.map((n) => ({
                    ...n,
                    fixed: Boolean(n.fixed) || !missingIds.has(n.id),
                }));
                const settled = settleLayout({
                    nodes: settleNodes,
                    edges: layoutEdges,
                    iterations: 0,
                });
                const positions = settled?.positions || {};
                for (const node of graphNodes) {
                    if (!missingIds.has(node.id)) continue;
                    const p = positions[node.id];
                    if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
                        node.x = p.x;
                        node.y = p.y;
                        posById[node.id] = { x: p.x, y: p.y };
                    }
                }
                this.cachedPositions = { ...this.cachedPositions, ...posById };
            }
            if (!isCurrentRun()) return;

            for (const node of graphNodes) {
                const announce = this.announces[node.id];
                if (announce) node._announce = announce;
            }
            if (Array.isArray(graph.icon_queue) && graph.icon_queue.length > 0) {
                this.iconQueue.push(...graph.icon_queue);
            }
            for (const node of graphNodes) {
                if (node?.id) processedNodeIds.add(node.id);
            }
            for (const edge of graphEdges) {
                if (edge?.id) processedEdgeIds.add(edge.id);
            }

            const chunkSize = this.vizChunkSize;
            this.totalBatches = Math.max(1, Math.ceil(Math.max(graphNodes.length, graphEdges.length) / chunkSize));
            this.currentBatch = 0;

            if (this.webglEngine && this.rendererMode === "webgl") {
                if (!silent) {
                    this.loadingStatus = "Uploading scene...";
                }
                this.webglEngine.setGraph(graphNodes, graphEdges);
                const counts = this.webglEngine.getCounts();
                this.graphNodeCount = counts.nodes;
                this.graphEdgeCount = counts.edges;
                const snap = this.webglEngine.getPositions() || {};
                this.cachedPositions = { ...this.cachedPositions, ...snap };
                this.loadedNodesCount = this.pathTable.length;
                this.totalNodesToLoad = 0;
                this.loadedNodesCount = 0;
                this.currentBatch = 0;
                this.totalBatches = 0;
                this.scheduleIconQueue();
                return;
            }

            const applyLimit = Math.max(graphNodes.length, graphEdges.length);
            for (let i = 0; i < applyLimit; i += chunkSize) {
                if (!isCurrentRun()) return;
                this.currentBatch++;
                const batchNodes = graphNodes.slice(i, i + chunkSize);
                const batchEdges = graphEdges.slice(i, i + chunkSize);
                if (batchNodes.length > 0) this.nodes.update(batchNodes);
                if (batchEdges.length > 0) this.edges.update(batchEdges);
                this.loadedNodesCount = Math.min(this.pathTable.length, i + chunkSize);
                if (!silent) {
                    this.loadingStatus = `Processing Batch ${this.currentBatch} / ${this.totalBatches}...`;
                }
                if (this.pathTable.length > VIZ_SYNC_PATH_THRESHOLD) {
                    await yieldToMain();
                }
            }
            if (!isCurrentRun()) return;

            const nodesToRemove = this.nodes.getIds().filter((id) => !processedNodeIds.has(id));
            if (nodesToRemove.length > 0) this.nodes.remove(nodesToRemove);
            const edgesToRemove = this.edges.getIds().filter((id) => !processedEdgeIds.has(id));
            if (edgesToRemove.length > 0) this.edges.remove(edgesToRemove);

            this.graphNodeCount = this.nodes.length;
            this.graphEdgeCount = this.edges.length;
            this.totalNodesToLoad = 0;
            this.loadedNodesCount = 0;
            this.currentBatch = 0;
            this.totalBatches = 0;
            this.scheduleIconQueue();
        },
        scheduleIconQueue() {
            if (this.currentLOD === "low" || this.iconQueue.length === 0) {
                return;
            }
            if (this.iconQueueRunning) {
                return;
            }
            const run = () => {
                this.runIconQueue();
            };
            if (typeof requestIdleCallback === "function") {
                requestIdleCallback(run, { timeout: 1500 });
            } else {
                run();
            }
        },
        /*
         * Drains the deferred lxmf custom-icon queue. Runs sequentially with
         * a yield between each icon so painting many icons cannot pin the
         * main thread the way the old inline-await version did. Items tagged
         * with a stale generation (a newer processVisualization started while
         * we were running) are skipped, as are nodes that no longer exist.
         */
        async runIconQueue() {
            if (this.iconQueueRunning || this.currentLOD === "low") return;
            this.iconQueueRunning = true;
            try {
                const work = dedupeIconQueueEntries(this.iconQueue);
                this.iconQueue = [];
                for (const item of work) {
                    if (this.abortController.signal.aborted) return;
                    if (item.generation !== this.iconQueueGeneration) {
                        continue;
                    }
                    let url = this.iconCache[item.cacheKey];
                    if (!url) {
                        url = await this.createIconImage(item.iconName, item.fg, item.bg, item.size);
                        if (this.abortController.signal.aborted) return;
                    }
                    if (!url) {
                        continue;
                    }
                    const updates = [];
                    for (const nodeId of item.nodeIds) {
                        if (this.webglEngine) {
                            updates.push({ id: nodeId, image: url });
                        } else if (this.nodes.get(nodeId)) {
                            updates.push({ id: nodeId, image: url });
                        }
                    }
                    if (updates.length > 0) {
                        if (this.webglEngine) {
                            this.webglEngine.updateNodeImages(updates);
                        } else {
                            this.nodes.update(updates);
                        }
                    }
                    await yieldToMain();
                }
            } finally {
                this.iconQueueRunning = false;
                if (this.iconQueue.length > 0 && this.currentLOD !== "low") {
                    this.scheduleIconQueue();
                }
            }
        },
    },
};
</script>

<style>
.vis-network:focus {
    outline: none;
}

.vis-tooltip {
    color: #f4f4f5 !important;
    background: rgba(9, 9, 11, 0.92) !important;
    border: 1px solid rgba(63, 63, 70, 0.5) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    font-style: normal !important;
    font-family: Inter, system-ui, sans-serif !important;
    line-height: 1.5 !important;
    pointer-events: none !important;
}

#network,
#network-webgl {
    background-color: #f8fafc;
    background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
    background-size: 32px 32px;
}

.dark #network,
.dark #network-webgl {
    background-color: #09090b;
    background-image: radial-gradient(#18181b 1px, transparent 1px);
    background-size: 32px 32px;
}

#network-webgl,
.network-webgl-labels {
    image-rendering: auto;
}

.network-webgl-labels {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}
</style>
