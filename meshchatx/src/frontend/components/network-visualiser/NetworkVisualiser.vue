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
            :hop-filter-slider="hopFilterSlider"
            :hop-slider-max="hopSliderMax"
            :node-count="nodes.length"
            :edge-count="edges.length"
            :online-interface-count="onlineInterfaces.length"
            :offline-interface-count="offlineInterfaces.length"
            :search-query="searchQuery"
            @update:is-showing-controls="isShowingControls = $event"
            @update:auto-reload="autoReload = $event"
            @update:enable-physics="enablePhysics = $event"
            @update:hop-filter-slider="hopFilterSlider = $event"
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
import * as mdi from "@mdi/js";
import Utils from "../../js/Utils";
import GlobalEmitter from "../../js/GlobalEmitter";
import ToastUtils from "../../js/ToastUtils";
import { PONG_NODE_IDS } from "./internal/visualiserConstants.js";
import NetworkVisualiserLoadingOverlay from "./internal/NetworkVisualiserLoadingOverlay.vue";
import NetworkVisualiserToolbar from "./internal/NetworkVisualiserToolbar.vue";
import NetworkVisualiserLegend from "./internal/NetworkVisualiserLegend.vue";

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
            enableOrbit: false,
            enableBouncingBalls: false,
            enableFallingSkies: false,
            enableSnake: false,
            enablePong: false,
            orbitAnimationFrame: null,
            bouncingBallsAnimationFrame: null,
            fallingSkiesAnimationFrame: null,
            snakeAnimationFrame: null,
            pongAnimationFrame: null,
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
            hopFilterSlider: 0,
            hopFilterDebounceTimer: null,
            abortController: new AbortController(),
            currentLOD: "high",
            lastVizKeys: [],
            vizHadOneLayout: false,
            didDisableStabilization: false,
            vizChunkSize: pickAdaptiveChunkSize(),
            iconQueue: [],
            iconQueueRunning: false,
            iconQueueGeneration: 0,
        };
    },
    computed: {
        onlineInterfaces() {
            return this.interfaces.filter((i) => i.status);
        },
        offlineInterfaces() {
            return this.interfaces.filter((i) => !i.status);
        },
        hopSliderMax() {
            let m = 0;
            for (const e of this.pathTable) {
                if (e.hops != null && e.hops > m) m = e.hops;
            }
            return Math.min(256, Math.max(1, m));
        },
        hopFilterMax() {
            if (this.hopFilterSlider === 0) return null;
            return this.hopFilterSlider;
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
        enableOrbit(val) {
            if (val) {
                this.enableBouncingBalls = false;
                this.enableFallingSkies = false;
                this.enableSnake = false;
                this.enablePong = false;
                this.stopFallingSkies();
                this.stopSnake();
                this.stopPong();
                this.startOrbit();
            } else {
                this.stopOrbit();
            }
        },
        enableBouncingBalls(val) {
            if (val) {
                this.enableOrbit = false;
                this.enableFallingSkies = false;
                this.enableSnake = false;
                this.enablePong = false;
                this.stopFallingSkies();
                this.stopSnake();
                this.stopPong();
                this.startBouncingBalls();
            } else {
                this.stopBouncingBalls();
            }
        },
        enableFallingSkies(val) {
            if (val) {
                this.enableOrbit = false;
                this.enableBouncingBalls = false;
                this.enableSnake = false;
                this.enablePong = false;
                this.stopOrbit();
                this.stopBouncingBalls();
                this.stopSnake();
                this.stopPong();
                this.startFallingSkies();
            } else {
                this.stopFallingSkies();
            }
        },
        enableSnake(val) {
            if (val) {
                this.enableOrbit = false;
                this.enableBouncingBalls = false;
                this.enableFallingSkies = false;
                this.enablePong = false;
                this.stopOrbit();
                this.stopBouncingBalls();
                this.stopFallingSkies();
                this.stopPong();
                this.startSnake();
            } else {
                this.stopSnake();
            }
        },
        enablePong(val) {
            if (val) {
                this.enableOrbit = false;
                this.enableBouncingBalls = false;
                this.enableFallingSkies = false;
                this.enableSnake = false;
                this.stopOrbit();
                this.stopBouncingBalls();
                this.stopFallingSkies();
                this.stopSnake();
                this.startPong();
            } else {
                this.stopPong();
            }
        },
        searchQuery() {
            // we don't want to trigger a full update from server, just re-run the filtering on existing data
            this.processVisualization();
        },
        hopSliderMax() {
            if (this.hopFilterSlider > this.hopSliderMax) {
                this.hopFilterSlider = this.hopSliderMax;
            }
        },
        hopFilterSlider() {
            if (this.hopFilterDebounceTimer) clearTimeout(this.hopFilterDebounceTimer);
            this.hopFilterDebounceTimer = setTimeout(() => {
                this.hopFilterDebounceTimer = null;
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
        if (this._toggleOrbitHandler) {
            GlobalEmitter.off("toggle-orbit", this._toggleOrbitHandler);
        }
        if (this._toggleBouncingBallsHandler) {
            GlobalEmitter.off("toggle-bouncing-balls", this._toggleBouncingBallsHandler);
        }
        if (this._toggleFallingSkiesHandler) {
            GlobalEmitter.off("toggle-falling-skies", this._toggleFallingSkiesHandler);
        }
        if (this._visualiserPrefsHandler) {
            GlobalEmitter.off("visualiser-display-prefs-changed", this._visualiserPrefsHandler);
        }
        if (this._toggleSnakeHandler) {
            GlobalEmitter.off("toggle-snake", this._toggleSnakeHandler);
        }
        if (this._togglePongHandler) {
            GlobalEmitter.off("toggle-pong", this._togglePongHandler);
        }
        this.detachGameKeyListeners();
        this.stopOrbit();
        this.stopBouncingBalls();
        this.stopFallingSkies();
        this.stopSnake(false);
        this.stopPong(false);
        clearInterval(this.reloadInterval);
        if (this.hopFilterDebounceTimer) {
            clearTimeout(this.hopFilterDebounceTimer);
            this.hopFilterDebounceTimer = null;
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

        this._toggleOrbitHandler = () => {
            this.enableOrbit = !this.enableOrbit;
        };
        GlobalEmitter.on("toggle-orbit", this._toggleOrbitHandler);

        this._toggleBouncingBallsHandler = () => {
            this.enableBouncingBalls = !this.enableBouncingBalls;
        };
        GlobalEmitter.on("toggle-bouncing-balls", this._toggleBouncingBallsHandler);

        this._toggleFallingSkiesHandler = () => {
            this.enableFallingSkies = !this.enableFallingSkies;
        };
        GlobalEmitter.on("toggle-falling-skies", this._toggleFallingSkiesHandler);

        this._visualiserPrefsHandler = () => {
            this.loadVisualiserDisplayPrefs();
            if (this.network) {
                this.processVisualization();
            }
        };
        GlobalEmitter.on("visualiser-display-prefs-changed", this._visualiserPrefsHandler);

        this._toggleSnakeHandler = () => {
            this.enableSnake = !this.enableSnake;
        };
        GlobalEmitter.on("toggle-snake", this._toggleSnakeHandler);

        this._togglePongHandler = () => {
            this.enablePong = !this.enablePong;
        };
        GlobalEmitter.on("toggle-pong", this._togglePongHandler);

        this.loadVisualiserDisplayPrefs();
        this.init();
    },
    methods: {
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
                        const concurrency = 3;
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
        async getAnnouncesBatch() {
            this.announces = {};
            const aspectsToFetch = ["lxmf.delivery", "nomadnetwork.node"];
            try {
                for (const aspect of aspectsToFetch) {
                    if (this.abortController.signal.aborted) return;
                    this.loadingStatus = `Loading ${aspect}...`;
                    let offset = 0;
                    let hasMore = true;
                    while (hasMore) {
                        const resp = await window.api.get(`/api/v1/announces`, {
                            params: { aspect, limit: this.pageSize, offset },
                            signal: this.abortController.signal,
                        });
                        for (const announce of resp.data.announces) {
                            this.announces[announce.destination_hash] = announce;
                        }
                        const loaded = Object.keys(this.announces).length;
                        const total = resp.data.total_count;
                        this.loadingStatus = `Loading announces (${loaded})`;
                        offset += resp.data.announces.length;
                        hasMore = resp.data.announces.length === this.pageSize && offset < total;
                    }
                }
            } catch (e) {
                if (window.api.isCancel(e)) return;
                console.error("Failed to fetch announces batch", e);
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
            const mdiIconName =
                "mdi" +
                iconName
                    .split("-")
                    .map((word) => {
                        return word.charAt(0).toUpperCase() + word.slice(1);
                    })
                    .join("");

            const iconPath = mdi[mdiIconName] || mdi["mdiAccountOutline"];

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
            const on =
                this.enablePhysics &&
                !this.enableOrbit &&
                !this.enableBouncingBalls &&
                !this.enableFallingSkies &&
                !this.enableSnake &&
                !this.enablePong;
            this.network.setOptions({ physics: { enabled: on } });
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
        edgeHiddenForMode(peerNodeId) {
            if (this.enableBouncingBalls || this.enableSnake || this.enablePong) {
                return true;
            }
            if (
                peerNodeId != null &&
                this.enableFallingSkies &&
                this._fallingPendingIds &&
                this._fallingPendingIds.has(peerNodeId)
            ) {
                return true;
            }
            return false;
        },
        edgesHiddenForOverlayGames() {
            return this.enableBouncingBalls || this.enableSnake || this.enablePong;
        },
        startOrbit() {
            if (!this.network) return;
            this.stopOrbit();
            this.stopBouncingBalls();
            this.stopSnake(false);
            this.stopPong(false);

            this.refreshPhysicsEnabled();

            const nodeIds = this.nodes.getIds();
            const positions = this.network.getPositions(nodeIds) || {};
            const mePos = positions["me"] || { x: 0, y: 0 };

            this._orbitAroundMe = [];
            this._orbitAroundIface = [];

            for (const id of nodeIds) {
                if (id === "me") continue;
                const n = this.nodes.get(id);
                if (!n || !n.group) continue;
                const pos = positions[id] || { x: mePos.x, y: mePos.y };
                if (n.group === "interface" || n.group === "discovered") {
                    const dx = pos.x - mePos.x;
                    const dy = pos.y - mePos.y;
                    const r = Math.hypot(dx, dy) || 400;
                    this._orbitAroundMe.push({
                        id,
                        radius: r,
                        angle: Math.atan2(dy, dx),
                        speed: (0.0012 + Math.random() * 0.0024) * (Math.random() > 0.5 ? 1 : -1),
                    });
                } else if (n.group === "announce" && n._parentInterface) {
                    const parentId = n._parentInterface;
                    const pPos = positions[parentId] || mePos;
                    const dx = pos.x - pPos.x;
                    const dy = pos.y - pPos.y;
                    const r = Math.hypot(dx, dy) || 140;
                    this._orbitAroundIface.push({
                        id,
                        parentId,
                        radius: r,
                        angle: Math.atan2(dy, dx),
                        speed: (0.002 + Math.random() * 0.004) * (Math.random() > 0.5 ? 1 : -1),
                    });
                }
            }

            const animate = () => {
                if (!this.enableOrbit) return;

                const meP = this.network.getPositions(["me"])["me"] || { x: 0, y: 0 };

                const ifacePos = { me: meP };
                const batch = [];

                for (const data of this._orbitAroundMe) {
                    if (data.id === this._draggingNodeId) {
                        const p = this.network.getPositions([data.id])[data.id];
                        if (p) {
                            const dx = p.x - meP.x;
                            const dy = p.y - meP.y;
                            data.radius = Math.hypot(dx, dy) || data.radius;
                            data.angle = Math.atan2(dy, dx);
                            ifacePos[data.id] = p;
                        }
                        continue;
                    }
                    data.angle += data.speed;
                    const x = meP.x + Math.cos(data.angle) * data.radius;
                    const y = meP.y + Math.sin(data.angle) * data.radius;
                    batch.push({ id: data.id, x, y });
                    ifacePos[data.id] = { x, y };
                }

                if (batch.length > 0) {
                    this.nodes.update(batch);
                }

                const annBatch = [];
                for (const data of this._orbitAroundIface) {
                    if (data.id === this._draggingNodeId) {
                        const p = this.network.getPositions([data.id])[data.id];
                        const parent =
                            ifacePos[data.parentId] || this.network.getPositions([data.parentId])[data.parentId];
                        if (p && parent) {
                            const dx = p.x - parent.x;
                            const dy = p.y - parent.y;
                            data.radius = Math.hypot(dx, dy) || data.radius;
                            data.angle = Math.atan2(dy, dx);
                        }
                        continue;
                    }
                    const parent =
                        ifacePos[data.parentId] || this.network.getPositions([data.parentId])[data.parentId] || meP;
                    data.angle += data.speed;
                    annBatch.push({
                        id: data.id,
                        x: parent.x + Math.cos(data.angle) * data.radius,
                        y: parent.y + Math.sin(data.angle) * data.radius,
                    });
                }

                if (annBatch.length > 0) {
                    this.nodes.update(annBatch);
                }

                this.orbitAnimationFrame = requestAnimationFrame(animate);
            };

            this.orbitAnimationFrame = requestAnimationFrame(animate);
        },
        stopOrbit() {
            if (this.orbitAnimationFrame) {
                cancelAnimationFrame(this.orbitAnimationFrame);
                this.orbitAnimationFrame = null;
            }
            this._orbitAroundMe = [];
            this._orbitAroundIface = [];
            this.refreshPhysicsEnabled();
        },
        startFallingSkies() {
            if (!this.network) return;
            this.stopSnake(false);
            this.stopPong(false);
            this.refreshPhysicsEnabled();
            if (this._fallingById && this._fallingById.size > 0) {
                this.scheduleFallingTick();
            }
        },
        stopFallingSkies() {
            if (this.fallingSkiesAnimationFrame) {
                cancelAnimationFrame(this.fallingSkiesAnimationFrame);
                this.fallingSkiesAnimationFrame = null;
            }
            this._fallingById = new Map();
            this._fallingPendingIds = new Set();
            this.refreshPhysicsEnabled();
            if (this.network) {
                this.processVisualization();
            }
        },
        scheduleFallingTick() {
            if (!this.enableFallingSkies || !this.network) return;
            if (this.fallingSkiesAnimationFrame != null) return;
            const tick = () => {
                this.fallingSkiesAnimationFrame = null;
                if (!this.enableFallingSkies || !this._fallingById || this._fallingById.size === 0) {
                    return;
                }
                const gravity = 0.55;
                const updates = [];
                const done = [];

                for (const [id, st] of this._fallingById) {
                    st.vy += gravity;
                    st.y += st.vy;
                    if (st.y >= st.ty - 2) {
                        updates.push({ id, x: st.tx, y: st.ty });
                        done.push({ id, edgeIds: st.edgeIds || [] });
                    } else {
                        updates.push({ id, x: st.tx, y: st.y });
                    }
                }

                if (updates.length > 0) {
                    this.nodes.update(updates);
                }
                const edgeUnhide = [];
                for (const { id, edgeIds } of done) {
                    this._fallingById.delete(id);
                    this._fallingPendingIds.delete(id);
                    edgeUnhide.push(...edgeIds);
                }
                if (edgeUnhide.length > 0) {
                    this.edges.update(edgeUnhide.map((eid) => ({ id: eid, hidden: this.enableBouncingBalls })));
                }
                if (this._fallingById.size > 0) {
                    this.fallingSkiesAnimationFrame = requestAnimationFrame(tick);
                }
            };
            this.fallingSkiesAnimationFrame = requestAnimationFrame(tick);
        },
        startBouncingBalls() {
            if (!this.network) return;
            this.stopBouncingBalls();
            this.stopOrbit();
            this.stopSnake(false);
            this.stopPong(false);

            // Disable physics
            this.network.setOptions({ physics: { enabled: false } });

            // Hide edges
            const edges = this.edges.get();
            const updatedEdges = edges.map((edge) => ({ id: edge.id, hidden: true }));
            this.edges.update(updatedEdges);

            const container = document.getElementById("network");
            if (!container) return;
            const width = container.clientWidth;
            const height = container.clientHeight;

            const scale = this.network.getScale();
            const viewPosition = this.network.getViewPosition();

            const halfWidth = width / scale / 2;
            const halfHeight = height / scale / 2;
            const topBound = viewPosition.y - halfHeight;
            const leftBound = viewPosition.x - halfWidth;
            const rightBound = viewPosition.x + halfWidth;

            const nodeIds = this.nodes.getIds();
            this._bouncingNodes = nodeIds.map((id) => {
                const node = this.nodes.get(id);
                // Get current canvas position if available, otherwise randomize
                const currentPos = this.network.getPositions([id])[id] || {
                    x: leftBound + Math.random() * (rightBound - leftBound),
                    y: topBound - Math.random() * 800 - 100,
                };
                return {
                    id: id,
                    x: currentPos.x,
                    y: currentPos.y < topBound ? currentPos.y : topBound - Math.random() * 800 - 100, // ensure they start above or at their current high pos
                    vx: (Math.random() - 0.5) * 15,
                    vy: Math.random() * 10,
                    radius: (node.size || 25) * 1.5, // approximate collision radius
                };
            });

            const gravity = 0.45;
            const friction = 0.99;
            const bounce = 0.75;

            const animate = () => {
                if (!this.enableBouncingBalls) return;

                // Re-calculate boundaries in case of zoom/pan
                const scale = this.network.getScale();
                const viewPosition = this.network.getViewPosition();
                const halfWidth = width / scale / 2;
                const halfHeight = height / scale / 2;
                const bottomBound = viewPosition.y + halfHeight;
                const leftBound = viewPosition.x - halfWidth;
                const rightBound = viewPosition.x + halfWidth;

                const updates = this._bouncingNodes.map((node) => {
                    if (node.id === this._draggingNodeId) {
                        return {
                            id: node.id,
                            x: node.x,
                            y: node.y,
                        };
                    }

                    node.vy += gravity;
                    node.vx *= friction;
                    node.vy *= friction;
                    node.x += node.vx;
                    node.y += node.vy;

                    // Bounce off bottom
                    if (node.y + node.radius > bottomBound) {
                        node.y = bottomBound - node.radius;
                        node.vy *= -bounce;
                        node.vx += (Math.random() - 0.5) * 4;
                    }

                    // Bounce off sides
                    if (node.x - node.radius < leftBound) {
                        node.x = leftBound + node.radius;
                        node.vx *= -bounce;
                    } else if (node.x + node.radius > rightBound) {
                        node.x = rightBound - node.radius;
                        node.vx *= -bounce;
                    }

                    return {
                        id: node.id,
                        x: node.x,
                        y: node.y,
                    };
                });

                this.nodes.update(updates);
                this.bouncingBallsAnimationFrame = requestAnimationFrame(animate);
            };

            this.bouncingBallsAnimationFrame = requestAnimationFrame(animate);
        },
        stopBouncingBalls() {
            if (this.bouncingBallsAnimationFrame) {
                cancelAnimationFrame(this.bouncingBallsAnimationFrame);
                this.bouncingBallsAnimationFrame = null;
            }

            const edges = this.edges.get();
            const updatedEdges = edges.map((edge) => ({ id: edge.id, hidden: false }));
            this.edges.update(updatedEdges);

            this.refreshPhysicsEnabled();
        },
        getViewCanvasBounds() {
            const container = document.getElementById("network");
            if (!container || !this.network) return null;
            const scale = this.network.getScale();
            const vp = this.network.getViewPosition();
            const w = container.clientWidth;
            const h = container.clientHeight;
            const halfW = w / (2 * scale);
            const halfH = h / (2 * scale);
            return {
                left: vp.x - halfW,
                right: vp.x + halfW,
                top: vp.y - halfH,
                bottom: vp.y + halfH,
                scale,
            };
        },
        attachGameKeyListeners(mode) {
            this.detachGameKeyListeners();
            this._gameKeyMode = mode;
            this._snakeKeys = { u: 0, d: 0, l: 0, r: 0, w: 0, s: 0 };
            this._onGameKeyDown = (e) => {
                const tag = (e.target && e.target.tagName) || "";
                if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
                if (mode === "snake") {
                    if (["ArrowUp", "w", "W"].includes(e.key)) {
                        e.preventDefault();
                        this._snakeKeys.u = 1;
                    }
                    if (["ArrowDown", "s", "S"].includes(e.key)) {
                        e.preventDefault();
                        this._snakeKeys.d = 1;
                    }
                    if (["ArrowLeft", "a", "A"].includes(e.key)) {
                        e.preventDefault();
                        this._snakeKeys.l = 1;
                    }
                    if (["ArrowRight", "d", "D"].includes(e.key)) {
                        e.preventDefault();
                        this._snakeKeys.r = 1;
                    }
                } else if (mode === "pong") {
                    if (e.key === "w" || e.key === "W") {
                        e.preventDefault();
                        this._snakeKeys.w = 1;
                    }
                    if (e.key === "s" || e.key === "S") {
                        e.preventDefault();
                        this._snakeKeys.s = 1;
                    }
                }
            };
            this._onGameKeyUp =
                mode === "snake"
                    ? (e) => {
                          if (["ArrowUp", "w", "W"].includes(e.key)) this._snakeKeys.u = 0;
                          if (["ArrowDown", "s", "S"].includes(e.key)) this._snakeKeys.d = 0;
                          if (["ArrowLeft", "a", "A"].includes(e.key)) this._snakeKeys.l = 0;
                          if (["ArrowRight", "d", "D"].includes(e.key)) this._snakeKeys.r = 0;
                      }
                    : (e) => {
                          if (e.key === "w" || e.key === "W") this._snakeKeys.w = 0;
                          if (e.key === "s" || e.key === "S") this._snakeKeys.s = 0;
                      };
            window.addEventListener("keydown", this._onGameKeyDown, true);
            window.addEventListener("keyup", this._onGameKeyUp, true);
        },
        detachGameKeyListeners() {
            if (this._onGameKeyDown) {
                window.removeEventListener("keydown", this._onGameKeyDown, true);
                this._onGameKeyDown = null;
            }
            if (this._onGameKeyUp) {
                window.removeEventListener("keyup", this._onGameKeyUp, true);
                this._onGameKeyUp = null;
            }
            this._gameKeyMode = null;
        },
        getPositionAlongTrail(trail, distBehind) {
            if (!trail || trail.length === 0) return { x: 0, y: 0 };
            if (trail.length === 1) return { ...trail[0] };
            let d = 0;
            for (let i = trail.length - 1; i > 0; i--) {
                const p = trail[i];
                const q = trail[i - 1];
                const seg = Math.hypot(p.x - q.x, p.y - q.y);
                if (d + seg >= distBehind) {
                    const t = seg > 0 ? (distBehind - d) / seg : 0;
                    return { x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t };
                }
                d += seg;
            }
            return { ...trail[0] };
        },
        startSnake() {
            if (!this.network) return;
            this.stopSnake(false);
            this.stopPong(false);
            this.stopOrbit();
            this.stopBouncingBalls();
            this.stopFallingSkies();
            this.network.setOptions({ physics: { enabled: false } });
            const edges = this.edges.get();
            this.edges.update(edges.map((edge) => ({ id: edge.id, hidden: true })));

            const me = this.network.getPositions(["me"]).me || { x: 0, y: 0 };
            this._snakeVx = 7;
            this._snakeVy = 0;
            this._snakeHeadX = me.x;
            this._snakeHeadY = me.y;
            this._snakeTrail = [{ x: me.x, y: me.y }];
            this._snakeEatenIds = [];
            this._snakeFoodIds = new Set();
            for (const id of this.nodes.getIds()) {
                if (id !== "me") this._snakeFoodIds.add(id);
            }
            this.attachGameKeyListeners("snake");
            ToastUtils.info(this.$t("visualiser.snake_hint"));

            const speed = 8;
            const margin = 40;
            const headR = 28;
            const tailGap = 42;

            const tick = () => {
                if (!this.enableSnake || !this.network) return;
                const b = this.getViewCanvasBounds();
                if (!b) return;

                let vx = 0;
                let vy = 0;
                const k = this._snakeKeys || {};
                if (k.u) vy -= 1;
                if (k.d) vy += 1;
                if (k.l) vx -= 1;
                if (k.r) vx += 1;
                if (vx !== 0 || vy !== 0) {
                    const len = Math.hypot(vx, vy) || 1;
                    this._snakeVx = (vx / len) * speed;
                    this._snakeVy = (vy / len) * speed;
                }

                let hx = this._snakeHeadX + this._snakeVx;
                let hy = this._snakeHeadY + this._snakeVy;
                hx = Math.max(b.left + margin, Math.min(b.right - margin, hx));
                hy = Math.max(b.top + margin, Math.min(b.bottom - margin, hy));
                this._snakeHeadX = hx;
                this._snakeHeadY = hy;

                this.nodes.update([{ id: "me", x: hx, y: hy }]);

                const last = this._snakeTrail[this._snakeTrail.length - 1];
                if (!last || Math.hypot(hx - last.x, hy - last.y) > 3) {
                    this._snakeTrail.push({ x: hx, y: hy });
                    if (this._snakeTrail.length > 8000) {
                        this._snakeTrail.splice(0, 1500);
                    }
                }

                const updates = [];
                for (let i = 0; i < this._snakeEatenIds.length; i++) {
                    const id = this._snakeEatenIds[i];
                    const pos = this.getPositionAlongTrail(this._snakeTrail, (i + 1) * tailGap);
                    updates.push({ id, x: pos.x, y: pos.y });
                }
                if (updates.length > 0) this.nodes.update(updates);

                const foodArr = [...this._snakeFoodIds];
                const posMap = foodArr.length > 0 ? this.network.getPositions(foodArr) : {};
                for (const fid of foodArr) {
                    const fp = posMap[fid];
                    if (!fp) {
                        this._snakeFoodIds.delete(fid);
                        continue;
                    }
                    const n = this.nodes.get(fid);
                    const nr = n && n.size ? n.size * 0.45 : 14;
                    if (Math.hypot(hx - fp.x, hy - fp.y) < headR + nr) {
                        this._snakeFoodIds.delete(fid);
                        this._snakeEatenIds.push(fid);
                    }
                }

                for (let i = 0; i < this._snakeEatenIds.length; i++) {
                    const pos = this.getPositionAlongTrail(this._snakeTrail, (i + 1) * tailGap);
                    if (Math.hypot(hx - pos.x, hy - pos.y) < headR * 0.55) {
                        if (this.snakeAnimationFrame) {
                            cancelAnimationFrame(this.snakeAnimationFrame);
                            this.snakeAnimationFrame = null;
                        }
                        ToastUtils.info(this.$t("visualiser.snake_hit_self"));
                        this.enableSnake = false;
                        return;
                    }
                }

                if (this._snakeFoodIds.size === 0 && this._snakeEatenIds.length > 0) {
                    if (this.snakeAnimationFrame) {
                        cancelAnimationFrame(this.snakeAnimationFrame);
                        this.snakeAnimationFrame = null;
                    }
                    ToastUtils.success(this.$t("visualiser.snake_win"));
                    this.enableSnake = false;
                    return;
                }

                this.snakeAnimationFrame = requestAnimationFrame(tick);
            };

            this.snakeAnimationFrame = requestAnimationFrame(tick);
        },
        stopSnake(runProcessViz = true) {
            if (this.snakeAnimationFrame) {
                cancelAnimationFrame(this.snakeAnimationFrame);
                this.snakeAnimationFrame = null;
            }
            this.detachGameKeyListeners();
            this._snakeTrail = [];
            this._snakeFoodIds = null;
            this._snakeEatenIds = [];
            const edges = this.edges.get();
            this.edges.update(edges.map((edge) => ({ id: edge.id, hidden: false })));
            this.refreshPhysicsEnabled();
            if (runProcessViz && this.network) {
                this.processVisualization();
            }
        },
        startPong() {
            if (!this.network) return;
            this.stopPong(false);
            this.stopSnake(false);
            this.stopOrbit();
            this.stopBouncingBalls();
            this.stopFallingSkies();
            this.network.setOptions({ physics: { enabled: false } });
            const edges = this.edges.get();
            this.edges.update(edges.map((edge) => ({ id: edge.id, hidden: true })));

            const b = this.getViewCanvasBounds();
            if (!b) return;
            const midX = (b.left + b.right) / 2;
            const midY = (b.top + b.bottom) / 2;
            const padH = 100;
            const padW = 14;
            const ballR = 10;

            this._pongBall = { x: midX, y: midY, vx: 9, vy: 6, r: ballR };
            this._pongPadL = { x: b.left + 36, y: midY, w: padW, h: padH };
            this._pongPadR = { x: b.right - 36, y: midY, w: padW, h: padH };
            this._pongScoreYou = 0;
            this._pongScoreAi = 0;
            this._pongWinPoints = 7;

            const isDark = document.documentElement.classList.contains("dark");
            const padBg = isDark ? "#1e40af" : "#60a5fa";
            const padBr = isDark ? "#3b82f6" : "#2563eb";
            const hudFg = isDark ? "#fafafa" : "#18181b";
            const hudBg = isDark ? "#27272a" : "#f4f4f5";

            this.nodes.update([
                {
                    id: "__pong_ball",
                    group: "pong",
                    shape: "dot",
                    size: ballR * 2,
                    color: this.nodeColor("#e2e8f0", isDark ? "#f8fafc" : "#0f172a"),
                    label: "",
                    font: { size: 0 },
                    x: this._pongBall.x,
                    y: this._pongBall.y,
                    physics: false,
                },
                {
                    id: "__pong_hud",
                    group: "pong",
                    shape: "box",
                    label: `0 - 0`,
                    font: { size: 16, color: hudFg, bold: true },
                    margin: 10,
                    color: {
                        background: hudBg,
                        border: padBr,
                        highlight: { background: hudBg, border: padBr },
                        hover: { background: hudBg, border: padBr },
                    },
                    x: midX,
                    y: b.top + 44,
                    physics: false,
                },
                {
                    id: "__pong_pad_l",
                    group: "pong",
                    shape: "box",
                    label: "",
                    font: { size: 0 },
                    margin: 6,
                    widthConstraint: { minimum: padW * 2, maximum: padW * 2 },
                    heightConstraint: { minimum: padH, maximum: padH },
                    color: { background: padBg, border: padBr, highlight: { background: padBg, border: padBr } },
                    x: this._pongPadL.x,
                    y: this._pongPadL.y,
                    physics: false,
                },
                {
                    id: "__pong_pad_r",
                    group: "pong",
                    shape: "box",
                    label: "",
                    font: { size: 0 },
                    margin: 6,
                    widthConstraint: { minimum: padW * 2, maximum: padW * 2 },
                    heightConstraint: { minimum: padH, maximum: padH },
                    color: {
                        background: isDark ? "#4c1d95" : "#a78bfa",
                        border: padBr,
                        highlight: { background: padBg, border: padBr },
                    },
                    x: this._pongPadR.x,
                    y: this._pongPadR.y,
                    physics: false,
                },
            ]);

            this.attachGameKeyListeners("pong");
            ToastUtils.info(this.$t("visualiser.pong_hint"));

            const paddleSpeed = 11;
            const aiMaxStep = paddleSpeed * 0.92;

            const resetBall = (bounds, towardSign) => {
                const bb = this._pongBall;
                bb.x = (bounds.left + bounds.right) / 2;
                bb.y = (bounds.top + bounds.bottom) / 2;
                const ramp = Math.min(5, this._pongScoreYou + this._pongScoreAi);
                const base = 8.5 + ramp * 0.35;
                bb.vx = towardSign * base * (0.95 + Math.random() * 0.1);
                bb.vy = (Math.random() * 8 + 3) * (Math.random() > 0.5 ? 1 : -1);
            };

            const loop = () => {
                if (!this.enablePong || !this.network || !this._pongBall) return;
                const bounds = this.getViewCanvasBounds();
                if (!bounds) return;
                const ball = this._pongBall;
                const pl = this._pongPadL;
                const pr = this._pongPadR;

                if (this._snakeKeys.w) pl.y -= paddleSpeed;
                if (this._snakeKeys.s) pl.y += paddleSpeed;

                const ph = padH / 2;
                const dy = ball.y - pr.y;
                const step = Math.min(aiMaxStep, Math.abs(dy) * 0.22);
                if (dy < -1.5) pr.y -= step;
                else if (dy > 1.5) pr.y += step;

                pl.y = Math.max(bounds.top + ph + 8, Math.min(bounds.bottom - ph - 8, pl.y));
                pr.y = Math.max(bounds.top + ph + 8, Math.min(bounds.bottom - ph - 8, pr.y));

                ball.x += ball.vx;
                ball.y += ball.vy;

                if (ball.y - ball.r < bounds.top) {
                    ball.y = bounds.top + ball.r;
                    ball.vy *= -1;
                } else if (ball.y + ball.r > bounds.bottom) {
                    ball.y = bounds.bottom - ball.r;
                    ball.vy *= -1;
                }

                if (ball.vx < 0 && ball.x - ball.r <= pl.x + padW && ball.y >= pl.y - ph && ball.y <= pl.y + ph) {
                    ball.x = pl.x + padW + ball.r;
                    ball.vx *= -1.025;
                    ball.vy += (Math.random() - 0.5) * 2.2;
                } else if (
                    ball.vx > 0 &&
                    ball.x + ball.r >= pr.x - padW &&
                    ball.y >= pr.y - ph &&
                    ball.y <= pr.y + ph
                ) {
                    ball.x = pr.x - padW - ball.r;
                    ball.vx *= -1.025;
                    ball.vy += (Math.random() - 0.5) * 2.2;
                }

                const edgeMargin = 18;
                if (ball.x - ball.r < bounds.left - edgeMargin) {
                    this._pongScoreAi++;
                    if (this._pongScoreAi >= this._pongWinPoints) {
                        if (this.pongAnimationFrame) {
                            cancelAnimationFrame(this.pongAnimationFrame);
                            this.pongAnimationFrame = null;
                        }
                        ToastUtils.info(this.$t("visualiser.pong_win_ai"));
                        this.enablePong = false;
                        return;
                    }
                    resetBall(bounds, -1);
                } else if (ball.x + ball.r > bounds.right + edgeMargin) {
                    this._pongScoreYou++;
                    if (this._pongScoreYou >= this._pongWinPoints) {
                        if (this.pongAnimationFrame) {
                            cancelAnimationFrame(this.pongAnimationFrame);
                            this.pongAnimationFrame = null;
                        }
                        ToastUtils.success(this.$t("visualiser.pong_win_you"));
                        this.enablePong = false;
                        return;
                    }
                    resetBall(bounds, 1);
                }

                const hudLabel = `${this._pongScoreYou} - ${this._pongScoreAi}`;

                this.nodes.update([
                    { id: "__pong_ball", x: ball.x, y: ball.y },
                    { id: "__pong_pad_l", x: pl.x, y: pl.y },
                    { id: "__pong_pad_r", x: pr.x, y: pr.y },
                    { id: "__pong_hud", label: hudLabel, x: (bounds.left + bounds.right) / 2, y: bounds.top + 44 },
                ]);

                this.pongAnimationFrame = requestAnimationFrame(loop);
            };
            this.pongAnimationFrame = requestAnimationFrame(loop);
        },
        stopPong(runProcessViz = true) {
            if (this.pongAnimationFrame) {
                cancelAnimationFrame(this.pongAnimationFrame);
                this.pongAnimationFrame = null;
            }
            this.detachGameKeyListeners();
            this._pongBall = null;
            for (const id of PONG_NODE_IDS) {
                try {
                    this.nodes.remove(id);
                } catch {
                    /* node may already be removed */
                }
            }
            const edges = this.edges.get();
            this.edges.update(edges.map((edge) => ({ id: edge.id, hidden: false })));
            this.refreshPhysicsEnabled();
            if (runProcessViz && this.network) {
                this.processVisualization();
            }
        },
        reconcileSnakeFoodAfterViz() {
            if (!this._snakeFoodIds || !this._snakeEatenIds) return;
            const ids = new Set(this.nodes.getIds());
            this._snakeEatenIds = this._snakeEatenIds.filter((id) => ids.has(id));
            const eaten = new Set(this._snakeEatenIds);
            for (const id of [...this._snakeFoodIds]) {
                if (!ids.has(id)) this._snakeFoodIds.delete(id);
            }
            for (const id of ids) {
                if (id === "me" || eaten.has(id) || PONG_NODE_IDS.includes(id)) continue;
                this._snakeFoodIds.add(id);
            }
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
                        // "continuous" computes bezier curves on every frame and
                        // is noticeably heavier than straight edges on slow ARM
                        // CPUs once you have a few hundred edges. Straight edges
                        // still look clean against the dotted background.
                        smooth: false,
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

            this.network.on("dragStart", (params) => {
                if (
                    (this.enableBouncingBalls ||
                        this.enableOrbit ||
                        this.enableFallingSkies ||
                        this.enableSnake ||
                        this.enablePong) &&
                    params.nodes.length > 0
                ) {
                    this._draggingNodeId = params.nodes[0];
                    this.network.setOptions({ physics: { enabled: false } });
                }
            });

            this.network.on("dragging", (params) => {
                if (this._draggingNodeId) {
                    const canvasPos = params.pointer.canvas;
                    if (this.enableBouncingBalls) {
                        const node = this._bouncingNodes.find((n) => n.id === this._draggingNodeId);
                        if (node) {
                            node.vx = (canvasPos.x - node.x) * 0.5;
                            node.vy = (canvasPos.y - node.y) * 0.5;
                            node.x = canvasPos.x;
                            node.y = canvasPos.y;
                        }
                    } else if (this.enableOrbit || this.enableFallingSkies || this.enableSnake || this.enablePong) {
                        this.nodes.update({ id: this._draggingNodeId, x: canvasPos.x, y: canvasPos.y });
                    }
                }
            });

            this.network.on("dragEnd", () => {
                this._draggingNodeId = null;
                this.refreshPhysicsEnabled();
            });

            this.network.on("zoom", () => {
                this.updateLOD();
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
            if (this.enableSnake || this.enablePong) return;
            if (!this.autoReload || this.isUpdating || this.isLoading) return;
            this.isUpdating = true;
            try {
                await this.update();
            } finally {
                this.isUpdating = false;
            }
        },
        updateLOD() {
            if (!this.network || this.enableSnake || this.enablePong) return;
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
        },
        nodeColor(border, background) {
            return {
                border,
                background,
                highlight: { border, background },
                hover: { border, background },
            };
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
            await this.getAnnouncesBatch();
            if (this.abortController.signal.aborted) return;
            await this.getPathTableBatch(Object.keys(this.announces));
            if (this.abortController.signal.aborted) return;

            await this.processVisualization();
        },
        async processVisualization() {
            await new Promise((r) => {
                requestAnimationFrame(r);
            });
            if (this.abortController.signal.aborted) return;

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
                this.network.setOptions({ physics: { enabled: false } });
            }

            const processedNodeIds = new Set();
            const processedEdgeIds = new Set();

            const posById = {};
            const prevIds = new Set(this.lastVizKeys);

            if (!this.enableFallingSkies) {
                this._fallingById = new Map();
                if (!this._fallingPendingIds) {
                    this._fallingPendingIds = new Set();
                } else {
                    this._fallingPendingIds.clear();
                }
            } else {
                if (!this._fallingById) {
                    this._fallingById = new Map();
                }
                if (!this._fallingPendingIds) {
                    this._fallingPendingIds = new Set();
                }
            }

            const allowAnnounceFall = this.enableFallingSkies && this.vizHadOneLayout;

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
                    color: entry.status ? (isDarkMode ? "#065f46" : "#10b981") : isDarkMode ? "#7f1d1d" : "#ef4444",
                    width: 3,
                    length: 200,
                    arrows: { to: { enabled: true, scaleFactor: 0.5 } },
                    hidden: this.edgesHiddenForOverlayGames(),
                });
                processedEdgeIds.add(edgeId);
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
                        hidden: this.edgesHiddenForOverlayGames(),
                    });
                    processedEdgeIds.add(edgeId);
                }
            }
            if (discoveredNodes.length > 0) this.nodes.update(discoveredNodes);
            if (discoveredEdges.length > 0) this.edges.update(discoveredEdges);

            await this.$nextTick();
            if (this.abortController.signal.aborted) return;

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
                if (this.abortController.signal.aborted) return;
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
                    const shouldFall = allowAnnounceFall && !prevIds.has(entry.hash);

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

                    if (shouldFall) {
                        this._fallingPendingIds.add(entry.hash);
                        let topY = targetXY.y - 1100;
                        const container = document.getElementById("network");
                        if (container && this.network) {
                            const scale = this.network.getScale();
                            const vp = this.network.getViewPosition();
                            const halfH = container.clientHeight / (2 * scale);
                            topY = vp.y - halfH - 60;
                        }
                        node.x = targetXY.x;
                        node.y = topY;
                        posById[entry.hash] = { x: targetXY.x, y: targetXY.y };
                        this._fallingById.set(entry.hash, {
                            tx: targetXY.x,
                            ty: targetXY.y,
                            x: targetXY.x,
                            y: topY,
                            vy: 0,
                            edgeIds: [edgeId],
                        });
                    }

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
                                node.image =
                                    entry.hops === 1
                                        ? "/assets/images/network-visualiser/user_1hop.png"
                                        : "/assets/images/network-visualiser/user.png";
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
                            node.size = 30;
                            node._originalSize = 30;
                        } else {
                            node.shape = "circularImage";
                            node._originalShape = "circularImage";
                            node.image =
                                entry.hops === 1
                                    ? "/assets/images/network-visualiser/user_1hop.png"
                                    : "/assets/images/network-visualiser/user.png";
                        }
                        node.color = this.nodeColor(
                            entry.hops === 1 ? "#10b981" : "#3b82f6",
                            entry.hops === 1 ? (isDarkMode ? "#064e3b" : "#ecfdf5") : isDarkMode ? "#1e40af" : "#eff6ff"
                        );
                    } else if (announce.aspect === "nomadnetwork.node") {
                        node.shape = "circularImage";
                        node._originalShape = "circularImage";
                        node.image =
                            entry.hops === 1
                                ? "/assets/images/network-visualiser/server_1hop.png"
                                : "/assets/images/network-visualiser/server.png";
                        node.color = this.nodeColor(
                            entry.hops === 1 ? "#10b981" : "#8b5cf6",
                            entry.hops === 1 ? (isDarkMode ? "#064e3b" : "#ecfdf5") : isDarkMode ? "#4c1d95" : "#f5f3ff"
                        );
                    }

                    node = { ...node, ...this.getNodeLODProps(node, this.currentLOD) };
                    batchNodes.push(node);
                    processedNodeIds.add(node.id);

                    batchEdges.push({
                        id: edgeId,
                        from: entry.interface,
                        to: entry.hash,
                        color: {
                            color:
                                entry.hops === 1
                                    ? isDarkMode
                                        ? "#065f46"
                                        : "#10b981"
                                    : isDarkMode
                                      ? "#1e3a8a"
                                      : "#3b82f6",
                            opacity: entry.hops === 1 ? 1 : 0.5,
                        },
                        width: entry.hops === 1 ? 2 : 1,
                        dashes: entry.hops > 1,
                        hidden: this.edgeHiddenForMode(entry.hash),
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

                if (this.abortController.signal.aborted) return;
            }

            if (this.enablePong) {
                for (const id of PONG_NODE_IDS) {
                    processedNodeIds.add(id);
                }
            }

            // Cleanup: remove nodes/edges that are no longer in the network
            const nodesToRemove = this.nodes.getIds().filter((id) => !processedNodeIds.has(id));
            if (nodesToRemove.length > 0) this.nodes.remove(nodesToRemove);

            const edgesToRemove = this.edges.getIds().filter((id) => !processedEdgeIds.has(id));
            if (edgesToRemove.length > 0) this.edges.remove(edgesToRemove);

            this.totalNodesToLoad = 0;
            this.loadedNodesCount = 0;
            this.currentBatch = 0;
            this.totalBatches = 0;

            this.lastVizKeys = [...processedNodeIds];
            this.vizHadOneLayout = true;

            if (this.network && !this.didDisableStabilization) {
                this.didDisableStabilization = true;
                this.network.setOptions({ physics: { stabilization: { enabled: false } } });
            }

            if (this.enableFallingSkies && this._fallingById && this._fallingById.size > 0) {
                this.scheduleFallingTick();
            }

            if (this.enableSnake && this._snakeFoodIds) {
                this.reconcileSnakeFoodAfterViz();
            }

            if (this.enableOrbit) {
                this.startOrbit();
            }

            /*
             * Re-enable physics now that all nodes/edges are in place. The
             * solver runs once on the final graph instead of repeatedly on
             * partial states, which is dramatically cheaper.
             */
            if (physicsWasOn && this.network) {
                this.network.setOptions({ physics: { enabled: this.enablePhysics } });
            }

            this.runIconQueue();
        },
        /*
         * Drains the deferred lxmf custom-icon queue. Runs sequentially with
         * a yield between each icon so painting many icons cannot pin the
         * main thread the way the old inline-await version did. Items tagged
         * with a stale generation (a newer processVisualization started while
         * we were running) are skipped, as are nodes that no longer exist.
         */
        async runIconQueue() {
            if (this.iconQueueRunning) return;
            this.iconQueueRunning = true;
            try {
                while (this.iconQueue.length > 0) {
                    if (this.abortController.signal.aborted) return;
                    const item = this.iconQueue.shift();
                    if (item.generation !== this.iconQueueGeneration) {
                        continue;
                    }
                    if (!this.nodes.get(item.nodeId)) {
                        continue;
                    }
                    /*
                     * Queue items can collapse onto a single cached icon: if
                     * a previous iteration already painted this cacheKey we
                     * can short-circuit instead of re-invoking createIconImage
                     * (which would also redo the canvas+SVG decode work).
                     */
                    let url = this.iconCache[item.cacheKey];
                    if (!url) {
                        url = await this.createIconImage(item.iconName, item.fg, item.bg, item.size);
                        if (this.abortController.signal.aborted) return;
                    }
                    if (url && this.nodes.get(item.nodeId)) {
                        this.nodes.update({ id: item.nodeId, image: url });
                    }
                    await yieldToMain();
                }
            } finally {
                this.iconQueueRunning = false;
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
