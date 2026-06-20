<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex-1 h-full min-w-0 relative dark:bg-zinc-950 overflow-hidden">
        <!-- network -->
        <div id="network" class="w-full h-full"></div>

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
            :node-count="nodes.length"
            :edge-count="edges.length"
            :online-interface-count="onlineInterfaces.length"
            :offline-interface-count="offlineInterfaces.length"
            :search-query="searchQuery"
            @update:is-showing-controls="isShowingControls = $event"
            @update:auto-reload="autoReload = $event"
            @update:enable-physics="enablePhysics = $event"
            @update:hop-max-filter="onUserHopMaxFilterChange"
            @update:search-query="searchQuery = $event"
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
    dedupeIconQueueEntries,
    pathHashesWithinHopFilter,
    pickAdaptiveFetchConcurrency,
} from "../../js/networkVisualiserPerf.js";

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
 * commonly report 4 logical cores; phones/SoCs frequently report 2. We keep
 * desktop throughput (larger chunks => fewer yields) but drop hard for low
 * core-count devices so the main thread is not pinned for tens of ms per chunk.
 */
function pickAdaptiveChunkSize() {
    const cores = (typeof navigator !== "undefined" && navigator.hardwareConcurrency) || 4;
    if (cores <= 2) return 40;
    if (cores <= 4) return 80;
    if (cores <= 6) return 150;
    return 250;
}

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
        return {
            reticulumLogoPath: "/assets/images/reticulum_logo_512.png",
            config: null,
            autoReload: false,
            reloadInterval: null,
            isShowingControls: true,
            isUpdating: false,
            isLoading: false,
            enablePhysics: true,
            showDisabledInterfaces: false,
            showDiscoveredInterfaces: false,
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
            nodes: new DataSet(),
            edges: new DataSet(),
            iconCache: {},

            pageSize: 1000,
            searchQuery: "",
            hopMaxFilter: readStoredHopMaxFilter(),
            hopFilterDebounceTimer: null,
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
    },
    watch: {
        autoReload(val) {
            if (val) {
                this.manualUpdate();
            }
        },
        enablePhysics() {
            this.refreshPhysicsEnabled();
        },
        searchQuery() {
            // we don't want to trigger a full update from server, just re-run the filtering on existing data
            this.processVisualization();
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
            GlobalEmitter.off("visualiser-display-prefs-changed", this._visualiserPrefsHandler);
        }
        clearInterval(this.reloadInterval);
        if (this.hopFilterDebounceTimer) {
            clearTimeout(this.hopFilterDebounceTimer);
            this.hopFilterDebounceTimer = null;
        }
        if (this.lodRafId != null) {
            cancelAnimationFrame(this.lodRafId);
            this.lodRafId = null;
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
    },
    mounted() {
        const isMobile = window.innerWidth < 640;
        if (isMobile) {
            this.isShowingControls = false;
        }

        this._visualiserPrefsHandler = () => {
            this.loadVisualiserDisplayPrefs();
            if (this.network) {
                this.processVisualization();
            }
        };
        GlobalEmitter.on("visualiser-display-prefs-changed", this._visualiserPrefsHandler);

        this.loadVisualiserDisplayPrefs();
        this.init();
    },
    methods: {
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
                if (window.api.isCancel(e)) return;
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
                if (window.api.isCancel(e)) return;
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
                    if (totalCount > this.pageSize) {
                        const concurrency = this.pathFetchConcurrency;
                        for (let offset = this.pageSize; offset < totalCount; offset += this.pageSize * concurrency) {
                            if (this.abortController.signal.aborted) return;
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
                                this.pathTable.push(...r.data.path_table);
                            }
                            this.loadingStatus = `Loading paths (${this.pathTable.length} / ${totalCount})`;
                        }
                    }
                }
            } catch (e) {
                if (window.api.isCancel(e)) return;
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
            if (reset && needed.length > 0) {
                const neededSet = new Set(needed);
                for (const hash of Object.keys(this.announces)) {
                    if (!neededSet.has(hash)) {
                        delete this.announces[hash];
                    }
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
                if (window.api.isCancel(e)) return;
                console.error("Failed to fetch config", e);
            }
        },
        async getConversations() {
            try {
                const response = await window.api.get(`/api/v1/lxmf/conversations`, {
                    signal: this.abortController.signal,
                });
                this.conversations = {};
                for (const conversation of response.data.conversations) {
                    this.conversations[conversation.destination_hash] = conversation;
                }
            } catch (e) {
                if (window.api.isCancel(e)) return;
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
            try {
                if (typeof localStorage !== "undefined") {
                    if (localStorage.getItem("meshchatx.visualiser.showDisabledInterfaces") === "true") {
                        this.showDisabledInterfaces = true;
                    }
                    if (localStorage.getItem("meshchatx.visualiser.showDiscoveredInterfaces") === "true") {
                        this.showDiscoveredInterfaces = true;
                    }
                }
            } catch {
                /* localStorage unavailable */
            }
        },
        refreshPhysicsEnabled() {
            if (!this.network) return;
            if (this.physicsPausedForDrag) return;
            this.network.setOptions({
                physics: { enabled: this.enablePhysics },
                edges: { smooth: VIZ_EDGE_SMOOTH },
            });
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
        async init() {
            const container = document.getElementById("network");
            const isDarkMode = document.documentElement.classList.contains("dark");

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
                        hideEdgesOnDrag: true,
                        hideEdgesOnZoom: false,
                    },
                    layout: {
                        randomSeed: 42,
                        improvedLayout: false, // faster for large networks
                    },
                    physics: {
                        enabled: this.enablePhysics,
                        solver: "barnesHut",
                        barnesHut: {
                            gravitationalConstant: -10000,
                            springConstant: 0.02,
                            springLength: 200,
                            damping: 0.4,
                            avoidOverlap: 1,
                        },
                        stabilization: {
                            enabled: true,
                            iterations: 150,
                            updateInterval: 25,
                        },
                    },
                    nodes: {
                        borderWidth: 3,
                        borderWidthSelected: 6,
                        color: {
                            border: "#3b82f6",
                            background: isDarkMode ? "#1e40af" : "#eff6ff",
                            highlight: { border: "#3b82f6", background: isDarkMode ? "#2563eb" : "#dbeafe" },
                            hover: { border: "#3b82f6", background: isDarkMode ? "#2563eb" : "#dbeafe" },
                        },
                        font: {
                            face: "Inter, system-ui, sans-serif",
                            strokeWidth: 4,
                            strokeColor: isDarkMode ? "rgba(9, 9, 11, 0.95)" : "rgba(255, 255, 255, 0.95)",
                        },
                        // Canvas shadows are by far the most expensive per-node
                        // operation in vis-network. Disable globally; the borders
                        // and circular-image rendering remain visually distinct.
                        shadow: false,
                    },
                    edges: {
                        smooth: VIZ_EDGE_SMOOTH,
                        selectionWidth: 3,
                        hoverWidth: 2,
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

                const announce = node._announce;
                if (announce.aspect === "lxmf.delivery") {
                    this.$router.push({
                        name: "messages",
                        params: { destinationHash: announce.destination_hash },
                    });
                } else if (announce.aspect === "nomadnetwork.node") {
                    this.$router.push({
                        name: "nomadnetwork",
                        params: { destinationHash: announce.destination_hash },
                    });
                }
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

            // auto reload
            this.reloadInterval = setInterval(this.onAutoReload, 15000);
        },
        async manualUpdate() {
            if (this.isLoading) return;
            this.isLoading = true;
            this.isUpdating = true;
            try {
                await this.update();
            } finally {
                this.isLoading = false;
                this.isUpdating = false;
            }
        },
        async onAutoReload() {
            if (!this.autoReload || this.isUpdating || this.isLoading) return;
            this.isUpdating = true;
            try {
                await this.update();
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
            let newLOD = "high";
            if (scale < 0.2) {
                newLOD = "low";
            } else if (scale < 0.5) {
                newLOD = "medium";
            }

            if (this.currentLOD === newLOD) return;
            this.currentLOD = newLOD;

            const allNodes = this.nodes.get();
            const updates = allNodes.map((node) => {
                return this.getNodeLODProps(node, newLOD);
            });
            this.nodes.update(updates);

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
        directEdgeArrows() {
            return { to: { enabled: true, scaleFactor: 0.5 } };
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
        async update() {
            this.loadingStatus = "Fetching basic info...";
            this.currentBatch = 0;
            this.totalBatches = 0;

            await Promise.all([
                this.getConfig(),
                this.getInterfaceStats(),
                this.getConversations(),
                this.getDiscoveredInterfaces(),
            ]);
            if (this.abortController.signal.aborted) return;

            this.loadingStatus = "Fetching network data...";
            await this.getPathTableBatch();
            if (this.abortController.signal.aborted) return;
            await this.ensureAnnouncesForPathHashes({ reset: true });
            if (this.abortController.signal.aborted) return;

            await this.processVisualization();
        },
        async processVisualization() {
            await new Promise((r) => {
                requestAnimationFrame(r);
            });
            if (this.abortController.signal.aborted) return;

            const runId = ++this.vizRunGeneration;

            this.loadingStatus = "Processing visualization...";

            /*
             * Invalidate any in-flight icon-generation work. Each call to
             * processVisualization gets a new generation token; queued items
             * carrying an older token are dropped when consumed so we do not
             * paint canvases for nodes that no longer exist.
             */
            this.iconQueueGeneration += 1;
            this.iconQueue = [];

            /*
             * Pause physics for the duration of the bulk update. Running the
             * force-directed solver between chunks just churns the layout for
             * a partial graph and pegs the main thread on slow CPUs. We
             * restore the user's physics preference at the end so the final
             * layout still settles naturally.
             */
            const physicsWasOn = this.network && this.enablePhysics;
            if (physicsWasOn) {
                this.network.setOptions({
                    physics: { enabled: false },
                    edges: { smooth: VIZ_EDGE_SMOOTH },
                });
            }

            try {
                await this._processVisualizationGraph(runId);
            } finally {
                if (runId === this.vizRunGeneration) {
                    if (this.network && !this.didDisableStabilization) {
                        this.didDisableStabilization = true;
                        this.network.setOptions({
                            physics: { stabilization: { enabled: false } },
                            edges: { smooth: VIZ_EDGE_SMOOTH },
                        });
                    }
                    if (physicsWasOn && this.network && !this.physicsPausedForDrag) {
                        this.network.setOptions({
                            physics: { enabled: this.enablePhysics },
                            edges: { smooth: VIZ_EDGE_SMOOTH },
                        });
                    }
                    if (this.network && typeof this.network.redraw === "function") {
                        this.network.redraw();
                    }
                }
            }
        },
        async _processVisualizationGraph(runId) {
            const isCurrentRun = () => runId === this.vizRunGeneration && !this.abortController.signal.aborted;
            const processedNodeIds = new Set();
            const processedEdgeIds = new Set();

            const posById = {};

            const existingNodeIds = this.nodes.getIds();
            if (this.network) {
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
            const fontColor = isDarkMode ? "#ffffff" : "#000000";

            const searchLower = this.searchQuery.toLowerCase();
            const matchesSearch = (text) => !this.searchQuery || (text && text.toLowerCase().includes(searchLower));

            const meLabel = this.config?.display_name ?? "Local Node";
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
                    title: `Local Node: ${meLabel}\nIdentity: ${this.config?.identity_hash ?? "Unknown"}`,
                    color: this.nodeColor("#3b82f6", isDarkMode ? "#1e40af" : "#eff6ff"),
                    font: { color: fontColor, size: 16, bold: true },
                    x: mp.x,
                    y: mp.y,
                };
                meNode = { ...meNode, ...this.getNodeLODProps(meNode, this.currentLOD) };
                this.nodes.update([meNode]);
                processedNodeIds.add("me");
            }

            const interfaceNodes = [];
            const interfaceEdges = [];
            const ifaceEntries = [];
            const radius = 400;

            for (let idx = 0; idx < this.interfaces.length; idx++) {
                const entry = this.interfaces[idx];
                if (!this.showDisabledInterfaces && !entry.status) {
                    continue;
                }
                let label = entry.interface_name ?? entry.name;
                if (entry.type === "LocalServerInterface" || entry.parent_interface_name != null) {
                    label = entry.name;
                }
                if (matchesSearch(label) || matchesSearch(entry.name)) {
                    ifaceEntries.push({ entry, label });
                }
            }

            const nIface = ifaceEntries.length;
            for (let j = 0; j < nIface; j++) {
                const { entry, label } = ifaceEntries[j];
                const angle = nIface > 0 ? (j / nIface) * 2 * Math.PI : 0;
                const initialX = Math.cos(angle) * radius;
                const initialY = Math.sin(angle) * radius;
                const pos = this.pickStablePosition(entry.name, posById, () => ({ x: initialX, y: initialY }));

                let interfaceNode = {
                    id: entry.name,
                    group: "interface",
                    label: label,
                    title: `${entry.name}\nState: ${entry.status ? "Online" : "Offline"}\nBitrate: ${Utils.formatBitsPerSecond(entry.bitrate)}\nTX: ${Utils.formatBytes(entry.txb)}\nRX: ${Utils.formatBytes(entry.rxb)}`,
                    size: 35,
                    _originalSize: 35,
                    shape: "circularImage",
                    _originalShape: "circularImage",
                    image: entry.status
                        ? "/assets/images/network-visualiser/interface_connected.png"
                        : "/assets/images/network-visualiser/interface_disconnected.png",
                    color: this.nodeColor(entry.status ? "#10b981" : "#ef4444", isDarkMode ? "#064e3b" : "#ecfdf5"),
                    font: { color: fontColor, size: 12, bold: true },
                    x: pos.x,
                    y: pos.y,
                };
                interfaceNode = { ...interfaceNode, ...this.getNodeLODProps(interfaceNode, this.currentLOD) };
                interfaceNodes.push(interfaceNode);
                processedNodeIds.add(entry.name);

                const edgeId = `me~${entry.name}`;
                interfaceEdges.push({
                    id: edgeId,
                    from: "me",
                    to: entry.name,
                    color: entry.status
                        ? this.directEdgeColor(isDarkMode)
                        : {
                              color: isDarkMode ? "#f87171" : "#ef4444",
                              opacity: 1,
                          },
                    width: 3,
                    length: 200,
                    arrows: this.directEdgeArrows(),
                    hidden: false,
                });
                processedEdgeIds.add(edgeId);
            }

            /*
             * interface-stats can be empty while the path table still names
             * interfaces on every hop. vis-network drops any edge whose from/to
             * node does not exist, so synthesize interface nodes from the path
             * table whenever stats did not already create them.
             */
            const pathOnlyInterfaces = [...this.pathTableInterfaceNames()].filter(
                (name) => !processedNodeIds.has(name)
            );
            const nPathIface = pathOnlyInterfaces.length;
            for (let j = 0; j < nPathIface; j++) {
                const ifaceName = pathOnlyInterfaces[j];
                if (!matchesSearch(ifaceName) && !matchesSearch(this.interfaceDisplayLabel(ifaceName))) {
                    continue;
                }
                const angle = nPathIface > 0 ? (j / nPathIface) * 2 * Math.PI : 0;
                const initialX = Math.cos(angle) * radius;
                const initialY = Math.sin(angle) * radius;
                const pos = this.pickStablePosition(ifaceName, posById, () => ({ x: initialX, y: initialY }));
                const label = this.interfaceDisplayLabel(ifaceName);
                let pathIfaceNode = {
                    id: ifaceName,
                    group: "interface",
                    label,
                    title: `${ifaceName}\nState: Active (path table)\nUsed as next-hop for known routes`,
                    size: 35,
                    _originalSize: 35,
                    shape: "circularImage",
                    _originalShape: "circularImage",
                    image: "/assets/images/network-visualiser/interface_connected.png",
                    color: this.nodeColor("#10b981", isDarkMode ? "#064e3b" : "#ecfdf5"),
                    font: { color: fontColor, size: 12, bold: true },
                    x: pos.x,
                    y: pos.y,
                };
                pathIfaceNode = { ...pathIfaceNode, ...this.getNodeLODProps(pathIfaceNode, this.currentLOD) };
                interfaceNodes.push(pathIfaceNode);
                processedNodeIds.add(ifaceName);

                if (processedNodeIds.has("me")) {
                    const edgeId = `me~${ifaceName}`;
                    interfaceEdges.push({
                        id: edgeId,
                        from: "me",
                        to: ifaceName,
                        color: this.directEdgeColor(isDarkMode),
                        width: 3,
                        length: 200,
                        arrows: this.directEdgeArrows(),
                        hidden: false,
                    });
                    processedEdgeIds.add(edgeId);
                }
            }

            if (interfaceNodes.length > 0) this.nodes.update(interfaceNodes);
            if (interfaceEdges.length > 0) this.edges.update(interfaceEdges);

            const discoveredNodes = [];
            const discoveredEdges = [];
            if (this.showDiscoveredInterfaces) {
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

                    if (this.hopFilterMax != null && disc.hops != null && disc.hops > this.hopFilterMax) {
                        continue;
                    }

                    const isConnected = this.discoveredActive.some((a) => {
                        const aHost = a.target_host || a.remote || a.listen_ip;
                        const aPort = a.target_port || a.listen_port;
                        return aHost && aPort && disc.reachable_on === aHost && String(disc.port) === String(aPort);
                    });

                    const angle = Math.random() * 2 * Math.PI;
                    const dist = 800 + Math.random() * 200;
                    const dp = this.pickStablePosition(discId, posById, () => ({
                        x: Math.cos(angle) * dist,
                        y: Math.sin(angle) * dist,
                    }));
                    let discNode = {
                        id: discId,
                        group: "discovered",
                        label: discLabel,
                        title: `Discovered: ${discLabel}\nType: ${disc.type || "Unknown"}\nHops: ${disc.hops ?? "?"}\nStatus: ${isConnected ? "Connected" : disc.status || "Available"}${disc.reachable_on ? `\nAddress: ${disc.reachable_on}:${disc.port}` : ""}`,
                        size: 25,
                        _originalSize: 25,
                        shape: "circularImage",
                        _originalShape: "circularImage",
                        image: isConnected
                            ? "/assets/images/network-visualiser/interface_connected.png"
                            : "/assets/images/network-visualiser/interface_disconnected.png",
                        color: this.nodeColor(
                            isConnected ? "#06b6d4" : "#64748b",
                            isDarkMode ? (isConnected ? "#164e63" : "#1e293b") : isConnected ? "#ecfeff" : "#f1f5f9"
                        ),
                        font: { color: fontColor, size: 10 },
                        x: dp.x,
                        y: dp.y,
                    };
                    discNode = { ...discNode, ...this.getNodeLODProps(discNode, this.currentLOD) };
                    discoveredNodes.push(discNode);
                    processedNodeIds.add(discId);

                    const edgeId = `me~${discId}`;
                    discoveredEdges.push({
                        id: edgeId,
                        from: "me",
                        to: discId,
                        color: {
                            color: isDarkMode ? "#155e75" : "#06b6d4",
                            opacity: 0.4,
                        },
                        width: 1,
                        dashes: true,
                        hidden: false,
                    });
                    processedEdgeIds.add(edgeId);
                }
            }
            if (discoveredNodes.length > 0) this.nodes.update(discoveredNodes);
            if (discoveredEdges.length > 0) this.edges.update(discoveredEdges);

            if (!isCurrentRun()) return;

            // Process path table in batches to prevent UI block
            this.totalNodesToLoad = this.pathTable.length;
            this.loadedNodesCount = 0;

            const aspectsToShow = ["lxmf.delivery", "nomadnetwork.node"];

            /*
             * Chunk size is adaptive to hardwareConcurrency. Smaller chunks
             * on weak hardware mean more frequent yields, which keeps the
             * loading overlay animating and keeps input responsive at the
             * cost of slightly higher total work due to extra event-loop
             * round-trips. The trade-off massively favours smoothness on
             * ARM SBCs.
             */
            const chunkSize = this.vizChunkSize;
            this.totalBatches = Math.ceil(this.pathTable.length / chunkSize);
            this.currentBatch = 0;

            for (let i = 0; i < this.pathTable.length; i += chunkSize) {
                if (!isCurrentRun()) return;
                this.currentBatch++;
                const chunk = this.pathTable.slice(i, i + chunkSize);
                const batchNodes = [];
                const batchEdges = [];

                for (const entry of chunk) {
                    this.loadedNodesCount++;
                    if (entry.hops == null) continue;
                    if (this.hopFilterMax != null && entry.hops > this.hopFilterMax) continue;

                    const announce = this.announces[entry.hash];
                    if (!announce || !aspectsToShow.includes(announce.aspect)) continue;

                    const displayName = announce.custom_display_name ?? announce.display_name;
                    if (
                        !matchesSearch(displayName) &&
                        !matchesSearch(announce.destination_hash) &&
                        !matchesSearch(announce.identity_hash)
                    ) {
                        continue;
                    }

                    const conversation = this.conversations[announce.destination_hash];
                    const ip = posById[entry.interface];
                    let initX = 0;
                    let initY = 0;

                    if (ip && Number.isFinite(ip.x) && Number.isFinite(ip.y)) {
                        const angle = Math.random() * 2 * Math.PI;
                        const dist = 150 + Math.random() * 150;
                        initX = ip.x + Math.cos(angle) * dist;
                        initY = ip.y + Math.sin(angle) * dist;
                    } else {
                        const angle = Math.random() * 2 * Math.PI;
                        const dist = 600 + Math.random() * 200;
                        initX = Math.cos(angle) * dist;
                        initY = Math.sin(angle) * dist;
                    }

                    const targetXY = this.pickStablePosition(entry.hash, posById, () => ({ x: initX, y: initY }));
                    const edgeId = `${entry.interface}~${entry.hash}`;

                    let node = {
                        id: entry.hash,
                        group: "announce",
                        size: 25,
                        _originalSize: 25,
                        _announce: announce,
                        _parentInterface: entry.interface,
                        font: { color: fontColor, size: 11 },
                        x: targetXY.x,
                        y: targetXY.y,
                    };

                    node.label = displayName;
                    node.title = `${displayName}\nAspect: ${announce.aspect}\nHops: ${entry.hops}\nVia: ${entry.interface}\nLast Seen: ${Utils.convertDateTimeToLocalDateTimeString(new Date(announce.updated_at))}`;

                    if (announce.aspect === "lxmf.delivery") {
                        if (conversation?.lxmf_user_icon) {
                            node.shape = "circularImage";
                            node._originalShape = "circularImage";
                            const cacheKey = `${conversation.lxmf_user_icon.icon_name}-${conversation.lxmf_user_icon.foreground_colour}-${conversation.lxmf_user_icon.background_colour}-64`;
                            if (this.iconCache[cacheKey]) {
                                node.image = this.iconCache[cacheKey];
                            } else {
                                /*
                                 * Defer custom-icon generation. Painting the
                                 * canvas + decoding the SVG inline used to
                                 * serialise every chunk and was the dominant
                                 * cause of the visualiser freezing on slow ARM
                                 * CPUs. Use a sensible placeholder (the same
                                 * default user image we use for icon-less lxmf
                                 * nodes) and queue the real icon for async
                                 * generation once all chunks are processed.
                                 */
                                node.image = this.isDirectPathHop(entry.hops)
                                    ? "/assets/images/network-visualiser/user_1hop.png"
                                    : "/assets/images/network-visualiser/user.png";
                                if (this.currentLOD !== "low") {
                                    this.iconQueue.push({
                                        nodeId: node.id,
                                        cacheKey,
                                        iconName: conversation.lxmf_user_icon.icon_name,
                                        fg: conversation.lxmf_user_icon.foreground_colour,
                                        bg: conversation.lxmf_user_icon.background_colour,
                                        size: 64,
                                        generation: this.iconQueueGeneration,
                                    });
                                }
                            }
                            node.size = 30;
                            node._originalSize = 30;
                        } else {
                            node.shape = "circularImage";
                            node._originalShape = "circularImage";
                            node.image = this.isDirectPathHop(entry.hops)
                                ? "/assets/images/network-visualiser/user_1hop.png"
                                : "/assets/images/network-visualiser/user.png";
                        }
                        node.color = this.nodeColor(
                            this.isDirectPathHop(entry.hops) ? "#10b981" : "#3b82f6",
                            this.isDirectPathHop(entry.hops)
                                ? isDarkMode
                                    ? "#064e3b"
                                    : "#ecfdf5"
                                : isDarkMode
                                  ? "#1e40af"
                                  : "#eff6ff"
                        );
                    } else if (announce.aspect === "nomadnetwork.node") {
                        node.shape = "circularImage";
                        node._originalShape = "circularImage";
                        node.image = this.isDirectPathHop(entry.hops)
                            ? "/assets/images/network-visualiser/server_1hop.png"
                            : "/assets/images/network-visualiser/server.png";
                        node.color = this.nodeColor(
                            this.isDirectPathHop(entry.hops) ? "#10b981" : "#8b5cf6",
                            this.isDirectPathHop(entry.hops)
                                ? isDarkMode
                                    ? "#064e3b"
                                    : "#ecfdf5"
                                : isDarkMode
                                  ? "#4c1d95"
                                  : "#f5f3ff"
                        );
                    }

                    node = { ...node, ...this.getNodeLODProps(node, this.currentLOD) };
                    batchNodes.push(node);
                    processedNodeIds.add(node.id);

                    const directHop = this.isDirectPathHop(entry.hops);
                    batchEdges.push({
                        id: edgeId,
                        from: entry.interface,
                        to: entry.hash,
                        color: directHop ? this.directEdgeColor(isDarkMode) : this.multiHopEdgeColor(isDarkMode),
                        width: directHop ? 2 : 1,
                        dashes: !directHop,
                        arrows: directHop ? this.directEdgeArrows() : undefined,
                        hidden: false,
                    });
                    processedEdgeIds.add(edgeId);
                }

                if (batchNodes.length > 0) this.nodes.update(batchNodes);
                if (batchEdges.length > 0) this.edges.update(batchEdges);

                this.loadingStatus = `Processing Batch ${this.currentBatch} / ${this.totalBatches}...`;

                /*
                 * Yield to the event loop using the prioritized scheduler
                 * (or setTimeout fallback). $nextTick is a microtask and does
                 * not let the renderer paint or process input between chunks,
                 * which is what was making the app feel frozen.
                 */
                await yieldToMain();

                if (!isCurrentRun()) return;
            }

            if (!isCurrentRun()) return;

            // Cleanup: remove nodes/edges that are no longer in the network
            const nodesToRemove = this.nodes.getIds().filter((id) => !processedNodeIds.has(id));
            if (nodesToRemove.length > 0) this.nodes.remove(nodesToRemove);

            const edgesToRemove = this.edges.getIds().filter((id) => !processedEdgeIds.has(id));
            if (edgesToRemove.length > 0) this.edges.remove(edgesToRemove);

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
                        if (this.nodes.get(nodeId)) {
                            updates.push({ id: nodeId, image: url });
                        }
                    }
                    if (updates.length > 0) {
                        this.nodes.update(updates);
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
    background: rgba(9, 9, 11, 0.9) !important;
    border: 1px solid rgba(63, 63, 70, 0.5) !important;
    border-radius: 12px !important;
    padding: 12px 16px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    font-style: normal !important;
    font-family: Inter, system-ui, sans-serif !important;
    line-height: 1.5 !important;
    backdrop-filter: blur(8px) !important;
    pointer-events: none !important;
}

#network {
    background-color: #f8fafc;
    background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
    background-size: 32px 32px;
}

.dark #network {
    background-color: #09090b;
    background-image: radial-gradient(#18181b 1px, transparent 1px);
    background-size: 32px 32px;
}
</style>
