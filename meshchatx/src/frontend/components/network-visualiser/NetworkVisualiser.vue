<template>
    <div class="flex-1 h-full min-w-0 relative dark:bg-zinc-950 overflow-hidden">
        <!-- network -->
        <div id="network" class="w-full h-full"></div>

        <!-- loading overlay -->
        <div
            v-if="isLoading"
            class="absolute inset-0 z-20 flex items-center justify-center bg-zinc-950/10 backdrop-blur-[2px] transition-all duration-300"
        >
            <div
                class="bg-white/90 dark:bg-zinc-900/90 border border-gray-200 dark:border-zinc-800 rounded-2xl px-6 py-4 flex flex-col items-center gap-3"
            >
                <div class="relative">
                    <div
                        class="w-12 h-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"
                    ></div>
                    <div class="absolute inset-0 flex items-center justify-center">
                        <div
                            class="w-6 h-6 border-4 border-emerald-500/20 border-b-emerald-500 rounded-full animate-spin-reverse"
                        ></div>
                    </div>
                </div>
                <div class="text-sm font-medium text-gray-900 dark:text-zinc-100">{{ loadingStatus }}</div>
                <div v-if="totalNodesToLoad > 0" class="w-48 space-y-2">
                    <div class="h-1.5 bg-gray-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div
                            class="h-full bg-blue-500 transition-all duration-300 shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                            :style="{ width: `${(loadedNodesCount / totalNodesToLoad) * 100}%` }"
                        ></div>
                    </div>
                    <div
                        v-if="totalBatches > 0"
                        class="flex justify-between items-center text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider"
                    >
                        <span>{{ $t("visualiser.batch") }} {{ currentBatch }} / {{ totalBatches }}</span>
                        <span>{{ Math.round((loadedNodesCount / totalNodesToLoad) * 100) }}%</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- controls & search -->
        <div
            class="absolute top-2 left-2 right-2 sm:top-4 sm:left-4 sm:right-4 z-10 flex flex-col sm:flex-row gap-2 pointer-events-none"
        >
            <!-- header glass card -->
            <div
                class="pointer-events-auto border border-gray-200/50 dark:border-zinc-800/50 bg-white/70 dark:bg-zinc-900/70 backdrop-blur-xl rounded-2xl overflow-hidden w-full sm:min-w-[280px] sm:w-auto transition-all duration-300"
            >
                <div
                    class="flex items-center px-4 sm:px-5 py-3 sm:py-4 cursor-pointer hover:bg-gray-50/50 dark:hover:bg-zinc-800/50 transition-colors"
                    @click="isShowingControls = !isShowingControls"
                >
                    <div class="flex-1 flex flex-col min-w-0 mr-2">
                        <span class="font-bold text-gray-900 dark:text-zinc-100 tracking-tight truncate">{{
                            $t("visualiser.reticulum_mesh")
                        }}</span>
                        <span
                            class="text-[10px] uppercase font-bold text-gray-500 dark:text-zinc-500 tracking-widest truncate"
                            >{{ $t("visualiser.network_visualizer") }}</span
                        >
                    </div>
                    <div class="flex items-center gap-2">
                        <button
                            type="button"
                            class="inline-flex items-center justify-center w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-600 dark:hover:bg-blue-700 text-white transition-all active:scale-95"
                            :disabled="isUpdating || isLoading"
                            @click.stop="manualUpdate"
                        >
                            <svg
                                v-if="!isUpdating && !isLoading"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke-width="2"
                                stroke="currentColor"
                                class="w-4 h-4 sm:w-5 sm:h-5"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
                                />
                            </svg>
                            <svg
                                v-else
                                class="animate-spin h-4 w-4 sm:h-5 sm:w-5"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                            >
                                <circle
                                    class="opacity-25"
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    stroke-width="4"
                                ></circle>
                                <path
                                    class="opacity-75"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                ></path>
                            </svg>
                        </button>
                        <div class="w-5 sm:w-6 flex justify-center">
                            <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                                class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400 transition-transform duration-300"
                                :class="{ 'rotate-180': isShowingControls }"
                            >
                                <path
                                    fill-rule="evenodd"
                                    d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
                                    clip-rule="evenodd"
                                />
                            </svg>
                        </div>
                    </div>
                </div>

                <div
                    v-show="isShowingControls"
                    class="px-5 pb-5 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300"
                >
                    <!-- divider -->
                    <div
                        class="h-px bg-gradient-to-r from-transparent via-gray-200 dark:via-zinc-800 to-transparent"
                    ></div>

                    <!-- auto update toggle -->
                    <div class="flex items-center justify-between">
                        <label
                            for="auto-reload"
                            class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                            >Auto Update</label
                        >
                        <Toggle id="auto-reload" v-model="autoReload" />
                    </div>

                    <!-- physics toggle -->
                    <div class="flex items-center justify-between">
                        <label
                            for="enable-physics"
                            class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                            >Live Layout</label
                        >
                        <Toggle id="enable-physics" v-model="enablePhysics" />
                    </div>

                    <!-- max hops filter -->
                    <div class="space-y-2">
                        <div class="flex items-center justify-between gap-2">
                            <label
                                for="hop-filter-slider"
                                class="text-sm font-semibold text-gray-700 dark:text-zinc-300 cursor-pointer"
                                >{{ $t("visualiser.max_hops_filter") }}</label
                            >
                            <span
                                class="text-xs font-bold text-blue-600 dark:text-blue-400 tabular-nums min-w-[4rem] text-right"
                                >{{ hopFilterSlider === 0 ? $t("visualiser.all") : hopFilterSlider }}</span
                            >
                        </div>
                        <input
                            id="hop-filter-slider"
                            v-model.number="hopFilterSlider"
                            type="range"
                            min="0"
                            :max="hopSliderMax"
                            step="1"
                            class="w-full h-2 rounded-lg appearance-none cursor-pointer bg-gray-200 dark:bg-zinc-700 accent-blue-600 dark:accent-blue-500"
                        />
                    </div>

                    <!-- stats -->
                    <div class="grid grid-cols-2 gap-3 pt-2">
                        <div
                            class="bg-gray-50/50 dark:bg-zinc-800/50 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                        >
                            <div
                                class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-1"
                            >
                                Nodes
                            </div>
                            <div class="text-lg font-bold text-blue-600 dark:text-blue-400">{{ nodes.length }}</div>
                        </div>
                        <div
                            class="bg-gray-50/50 dark:bg-zinc-800/50 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                        >
                            <div
                                class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-1"
                            >
                                Links
                            </div>
                            <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                                {{ edges.length }}
                            </div>
                        </div>
                    </div>

                    <div
                        class="bg-zinc-950/5 dark:bg-white/5 rounded-xl p-3 border border-gray-100 dark:border-zinc-700/50"
                    >
                        <div
                            class="text-[10px] font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-2"
                        >
                            Interfaces
                        </div>
                        <div class="flex items-center gap-4">
                            <div class="flex items-center gap-1.5">
                                <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
                                <span class="text-xs font-bold text-gray-700 dark:text-zinc-300"
                                    >{{ onlineInterfaces.length }} Online</span
                                >
                            </div>
                            <div class="flex items-center gap-1.5">
                                <div class="w-2 h-2 rounded-full bg-red-500"></div>
                                <span class="text-xs font-bold text-gray-700 dark:text-zinc-300"
                                    >{{ offlineInterfaces.length }} Offline</span
                                >
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- search box -->
            <div class="sm:ml-auto w-full sm:w-auto pointer-events-auto">
                <div class="relative group">
                    <div
                        class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400 group-focus-within:text-blue-500 transition-colors"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                            <path
                                fill-rule="evenodd"
                                d="M9 3.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM2.25 10a7.75 7.75 0 1 1 14.03 4.5l3.47 3.47a.75.75 0 0 1-1.06 1.06l-3.47-3.47A7.75 7.75 0 0 1 2.25 10Z"
                                clip-rule="evenodd"
                            />
                        </svg>
                    </div>
                    <input
                        v-model="searchQuery"
                        type="text"
                        :placeholder="`Search nodes (${nodes.length})...`"
                        class="block w-full sm:w-64 pl-9 pr-10 py-2.5 sm:py-3 bg-white/70 dark:bg-zinc-900/70 backdrop-blur-xl border border-gray-200/50 dark:border-zinc-800/50 rounded-2xl text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/50 sm:focus:w-80 transition-all dark:text-zinc-100 shadow-sm"
                    />
                    <button
                        v-if="searchQuery"
                        class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 transition-colors"
                        @click="searchQuery = ''"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                            <path
                                d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
                            />
                        </svg>
                    </button>
                </div>
            </div>
        </div>

        <!-- navigation breadcrumb style legend -->
        <div
            class="absolute bottom-4 right-4 z-10 hidden sm:flex items-center gap-2 px-4 py-2 rounded-full border border-gray-200/50 dark:border-zinc-800/50 bg-white/70 dark:bg-zinc-900/70 backdrop-blur-xl"
        >
            <div class="flex items-center gap-1.5">
                <div class="w-3 h-3 rounded-full border-2 border-emerald-500 bg-emerald-500/20"></div>
                <span class="text-[10px] font-bold text-gray-600 dark:text-zinc-400 uppercase">Direct</span>
            </div>
            <div class="w-px h-3 bg-gray-200 dark:bg-zinc-800 mx-1"></div>
            <div class="flex items-center gap-1.5">
                <div class="w-3 h-3 rounded-full border-2 border-blue-500/50 bg-blue-500/10"></div>
                <span class="text-[10px] font-bold text-gray-600 dark:text-zinc-400 uppercase">Multi-Hop</span>
            </div>
            <div v-if="discoveredInterfaces.length > 0" class="w-px h-3 bg-gray-200 dark:bg-zinc-800 mx-1"></div>
            <div v-if="discoveredInterfaces.length > 0" class="flex items-center gap-1.5">
                <div class="w-3 h-3 rounded-full border-2 border-cyan-500/50 bg-cyan-500/10"></div>
                <span class="text-[10px] font-bold text-gray-600 dark:text-zinc-400 uppercase"
                    >Discovered ({{ discoveredInterfaces.length }})</span
                >
            </div>
        </div>
    </div>
</template>

<script>
import "vis-network/styles/vis-network.css";
import { Network } from "vis-network";
import { DataSet } from "vis-data";
import * as mdi from "@mdi/js";
import Utils from "../../js/Utils";
import GlobalEmitter from "../../js/GlobalEmitter";
import Toggle from "../forms/Toggle.vue";

export default {
    name: "NetworkVisualiser",
    components: {
        Toggle,
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
            orbitAnimationFrame: null,
            bouncingBallsAnimationFrame: null,
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
        enablePhysics(val) {
            if (this.network) {
                this.network.setOptions({ physics: { enabled: val && !this.enableOrbit } });
            }
        },
        enableOrbit(val) {
            if (val) {
                this.enableBouncingBalls = false;
                this.startOrbit();
            } else {
                this.stopOrbit();
            }
        },
        enableBouncingBalls(val) {
            if (val) {
                this.enableOrbit = false;
                this.startBouncingBalls();
            } else {
                this.stopBouncingBalls();
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
        if (this._toggleOrbitHandler) {
            GlobalEmitter.off("toggle-orbit", this._toggleOrbitHandler);
        }
        if (this._toggleBouncingBallsHandler) {
            GlobalEmitter.off("toggle-bouncing-balls", this._toggleBouncingBallsHandler);
        }
        this.stopOrbit();
        this.stopBouncingBalls();
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
        startOrbit() {
            if (!this.network) return;
            this.stopOrbit();
            this.stopBouncingBalls();

            // Disable physics while orbiting
            this.network.setOptions({ physics: { enabled: false } });

            // Hide edges
            const edges = this.edges.get();
            const updatedEdges = edges.map((edge) => ({ id: edge.id, hidden: true }));
            this.edges.update(updatedEdges);

            // Get current positions of nodes to start orbit from where they are
            const nodeIds = this.nodes.getIds();
            const positions = this.network.getPositions(nodeIds);
            const mePos = positions["me"] || { x: 0, y: 0 };

            this._orbitNodes = nodeIds
                .filter((id) => id !== "me")
                .map((id) => {
                    const pos = positions[id] || {
                        x: Math.random() * 1000 - 500,
                        y: Math.random() * 1000 - 500,
                    };
                    const dx = pos.x - mePos.x;
                    const dy = pos.y - mePos.y;
                    const radius = Math.sqrt(dx * dx + dy * dy) || Math.random() * 500 + 100;
                    return {
                        id: id,
                        radius: radius,
                        angle: Math.atan2(dy, dx),
                        // Random speed based on radius - further nodes move slower usually, but let's make it more dynamic
                        speed: (0.002 + Math.random() * 0.005) * (Math.random() > 0.5 ? 1 : -1),
                    };
                });

            const animate = () => {
                if (!this.enableOrbit) return;

                // Get current position of 'me' node in case it was dragged
                const positions = this.network.getPositions(["me"]);
                const mePos = positions["me"] || { x: 0, y: 0 };

                const updates = this._orbitNodes.map((data) => {
                    if (data.id === this._draggingNodeId) {
                        // If dragging, update our internal radius/angle to match new position
                        const nodePositions = this.network.getPositions([data.id]);
                        const pos = nodePositions[data.id];
                        if (pos) {
                            const dx = pos.x - mePos.x;
                            const dy = pos.y - mePos.y;
                            data.radius = Math.sqrt(dx * dx + dy * dy);
                            data.angle = Math.atan2(dy, dx);
                        }
                        return { id: data.id, x: pos.x, y: pos.y };
                    }

                    data.angle += data.speed;
                    return {
                        id: data.id,
                        x: mePos.x + Math.cos(data.angle) * data.radius,
                        y: mePos.y + Math.sin(data.angle) * data.radius,
                    };
                });

                this.nodes.update(updates);
                this.orbitAnimationFrame = requestAnimationFrame(animate);
            };

            this.orbitAnimationFrame = requestAnimationFrame(animate);
        },
        stopOrbit() {
            if (this.orbitAnimationFrame) {
                cancelAnimationFrame(this.orbitAnimationFrame);
                this.orbitAnimationFrame = null;
            }

            // Restore edges visibility
            const edges = this.edges.get();
            const updatedEdges = edges.map((edge) => ({ id: edge.id, hidden: false }));
            this.edges.update(updatedEdges);

            // Re-enable physics if it was enabled
            if (this.network) {
                this.network.setOptions({ physics: { enabled: this.enablePhysics } });
            }
        },
        startBouncingBalls() {
            if (!this.network) return;
            this.stopBouncingBalls();
            this.stopOrbit();

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

            // Restore edges visibility
            const edges = this.edges.get();
            const updatedEdges = edges.map((edge) => ({ id: edge.id, hidden: false }));
            this.edges.update(updatedEdges);

            // Re-enable physics if it was enabled
            if (this.network) {
                this.network.setOptions({ physics: { enabled: this.enablePhysics } });
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
                        shadow: {
                            enabled: true,
                            color: "rgba(0,0,0,0.24)",
                            size: 10,
                            x: 0,
                            y: 4,
                        },
                    },
                    edges: {
                        smooth: {
                            type: "continuous",
                            roundness: 0.5,
                        },
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

            this.network.on("dragStart", (params) => {
                if ((this.enableBouncingBalls || this.enableOrbit) && params.nodes.length > 0) {
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
                    } else if (this.enableOrbit) {
                        // For orbit mode, just update the node position in vis-network DataSet
                        // though it might be overwritten by orbit animation loop
                        this.nodes.update({ id: this._draggingNodeId, x: canvasPos.x, y: canvasPos.y });
                    }
                }
            });

            this.network.on("dragEnd", () => {
                this._draggingNodeId = null;
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
            if (!this.autoReload || this.isUpdating || this.isLoading) return;
            this.isUpdating = true;
            try {
                await this.update();
            } finally {
                this.isUpdating = false;
            }
        },
        updateLOD() {
            if (!this.network) return;
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

            const processedNodeIds = new Set();
            const processedEdgeIds = new Set();

            const isDarkMode = document.documentElement.classList.contains("dark");
            const fontColor = isDarkMode ? "#ffffff" : "#000000";

            // search filter helper
            const searchLower = this.searchQuery.toLowerCase();
            const matchesSearch = (text) => !this.searchQuery || (text && text.toLowerCase().includes(searchLower));

            // Add me
            const meLabel = this.config?.display_name ?? "Local Node";
            if (matchesSearch(meLabel) || matchesSearch(this.config?.identity_hash)) {
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
                    x: 0,
                    y: 0,
                };
                meNode = { ...meNode, ...this.getNodeLODProps(meNode, this.currentLOD) };
                this.nodes.update([meNode]);
                processedNodeIds.add("me");
            }

            // Add interfaces
            const interfaceNodes = [];
            const interfaceEdges = [];
            const interfaceCount = this.interfaces.length;
            const radius = 400; // Start interfaces at 400px from center

            for (let idx = 0; idx < interfaceCount; idx++) {
                const entry = this.interfaces[idx];
                let label = entry.interface_name ?? entry.name;
                if (entry.type === "LocalServerInterface" || entry.parent_interface_name != null) {
                    label = entry.name;
                }

                if (matchesSearch(label) || matchesSearch(entry.name)) {
                    // Distribute interfaces in a circle
                    const angle = (idx / interfaceCount) * 2 * Math.PI;
                    const initialX = Math.cos(angle) * radius;
                    const initialY = Math.sin(angle) * radius;

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
                        x: initialX,
                        y: initialY,
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
                        hidden: this.enableOrbit,
                    });
                    processedEdgeIds.add(edgeId);
                }
            }
            if (interfaceNodes.length > 0) this.nodes.update(interfaceNodes);
            if (interfaceEdges.length > 0) this.edges.update(interfaceEdges);

            const discoveredNodes = [];
            const discoveredEdges = [];
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
                    x: Math.cos(angle) * dist,
                    y: Math.sin(angle) * dist,
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
                    hidden: this.enableOrbit,
                });
                processedEdgeIds.add(edgeId);
            }
            if (discoveredNodes.length > 0) this.nodes.update(discoveredNodes);
            if (discoveredEdges.length > 0) this.edges.update(discoveredEdges);

            await this.$nextTick();
            if (this.abortController.signal.aborted) return;

            // Process path table in batches to prevent UI block
            this.totalNodesToLoad = this.pathTable.length;
            this.loadedNodesCount = 0;

            const aspectsToShow = ["lxmf.delivery", "nomadnetwork.node"];

            // Process in larger chunks for speed, but keep UI responsive
            const chunkSize = 250;
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
                    const interfaceNode = this.nodes.get(entry.interface);
                    let initX = 0,
                        initY = 0;

                    if (interfaceNode && interfaceNode.x !== undefined) {
                        // Place around their parent interface with some randomness to avoid stacking
                        const angle = Math.random() * 2 * Math.PI;
                        const dist = 150 + Math.random() * 150;
                        initX = interfaceNode.x + Math.cos(angle) * dist;
                        initY = interfaceNode.y + Math.sin(angle) * dist;
                    } else {
                        // Fallback far from center
                        const angle = Math.random() * 2 * Math.PI;
                        const dist = 600 + Math.random() * 200;
                        initX = Math.cos(angle) * dist;
                        initY = Math.sin(angle) * dist;
                    }

                    let node = {
                        id: entry.hash,
                        group: "announce",
                        size: 25,
                        _originalSize: 25,
                        _announce: announce,
                        font: { color: fontColor, size: 11 },
                        x: initX,
                        y: initY,
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
                                node.image = await this.createIconImage(
                                    conversation.lxmf_user_icon.icon_name,
                                    conversation.lxmf_user_icon.foreground_colour,
                                    conversation.lxmf_user_icon.background_colour,
                                    64
                                );
                            }
                            if (this.abortController.signal.aborted) return;
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

                    const edgeId = `${entry.interface}~${entry.hash}`;
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
                        hidden: this.enableOrbit,
                    });
                    processedEdgeIds.add(edgeId);
                }

                // Update DataSet incrementally
                if (batchNodes.length > 0) this.nodes.update(batchNodes);
                if (batchEdges.length > 0) this.edges.update(batchEdges);

                // Allow UI to breathe and show progress
                this.loadingStatus = `Processing Batch ${this.currentBatch} / ${this.totalBatches}...`;

                // Use nextTick for responsiveness
                await this.$nextTick();

                if (this.abortController.signal.aborted) return;
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

            if (this.enableOrbit) {
                this.startOrbit();
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
