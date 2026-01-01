<template>
    <div class="flex flex-col h-full w-full bg-white dark:bg-zinc-950 overflow-hidden">
        <!-- header -->
        <div
            class="flex items-center px-4 py-2 border-b border-gray-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur z-10 relative"
        >
            <div class="flex items-center space-x-2">
                <MaterialDesignIcon icon-name="map" class="size-6 text-blue-500" />
                <h1 class="text-lg font-semibold text-gray-900 dark:text-zinc-100">{{ $t("map.title") }}</h1>
            </div>

            <div class="ml-auto flex items-center space-x-2">
                <!-- export tool toggle -->
                <button
                    v-if="!offlineEnabled"
                    ref="exportButton"
                    class="p-2 rounded-lg transition-colors"
                    :class="
                        isExportMode
                            ? 'bg-blue-500 text-white shadow-sm'
                            : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800'
                    "
                    :title="$t('map.export_area')"
                    @click="toggleExportMode"
                >
                    <MaterialDesignIcon icon-name="crop-free" class="size-5" />
                </button>

                <!-- offline/online toggle -->
                <div class="flex items-center bg-gray-100 dark:bg-zinc-800 rounded-lg p-1">
                    <button
                        :class="
                            !offlineEnabled
                                ? 'bg-white dark:bg-zinc-700 shadow-sm text-blue-600 dark:text-blue-400'
                                : 'text-gray-500 dark:text-zinc-400'
                        "
                        class="px-3 py-1 text-sm font-medium rounded-md transition-all"
                        @click="toggleOffline(false)"
                    >
                        {{ $t("map.online_mode") }}
                    </button>
                    <button
                        :class="
                            offlineEnabled
                                ? 'bg-white dark:bg-zinc-700 shadow-sm text-blue-600 dark:text-blue-400'
                                : 'text-gray-500 dark:text-zinc-400'
                        "
                        class="px-3 py-1 text-sm font-medium rounded-md transition-all"
                        :disabled="!hasOfflineMap"
                        @click="toggleOffline(true)"
                    >
                        {{ $t("map.offline_mode") }}
                    </button>
                </div>

                <!-- upload button (desktop only) -->
                <button
                    class="hidden sm:flex items-center space-x-1 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg shadow-sm transition-colors text-sm font-medium"
                    @click="$refs.fileInput.click()"
                >
                    <MaterialDesignIcon icon-name="upload" class="size-4" />
                    <span>{{ $t("map.upload_mbtiles") }}</span>
                </button>
                <input ref="fileInput" type="file" accept=".mbtiles" class="hidden" @change="onFileSelected" />

                <!-- settings button -->
                <button
                    class="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-full transition-colors"
                    @click="isSettingsOpen = !isSettingsOpen"
                >
                    <MaterialDesignIcon icon-name="cog" class="size-5" />
                </button>
            </div>
        </div>

        <!-- map container -->
        <div class="relative flex-1 min-h-0">
            <!-- search bar -->
            <div
                v-if="!offlineEnabled"
                ref="searchContainer"
                class="absolute top-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 z-30"
            >
                <div class="relative">
                    <div
                        class="flex items-center bg-white dark:bg-zinc-900 rounded-lg shadow-lg border border-gray-200 dark:border-zinc-800"
                    >
                        <input
                            v-model="searchQuery"
                            type="text"
                            class="flex-1 px-3 py-2 bg-transparent text-gray-900 dark:text-zinc-100 placeholder-gray-400 focus:outline-none text-sm"
                            :placeholder="$t('map.search_placeholder')"
                            @input="onSearchInput"
                            @keydown.enter="performSearch"
                            @focus="isSearchFocused = true"
                        />
                        <button
                            v-if="searchQuery"
                            class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                            @click="clearSearch"
                        >
                            <MaterialDesignIcon icon-name="close" class="size-4" />
                        </button>
                        <button
                            class="p-2 text-blue-500 hover:text-blue-600 disabled:text-gray-300"
                            :disabled="!searchQuery || isSearching"
                            @click="performSearch"
                        >
                            <MaterialDesignIcon
                                :icon-name="isSearching ? 'loading' : 'magnify'"
                                :class="['size-5', { 'animate-spin': isSearching }]"
                            />
                        </button>
                    </div>

                    <!-- search results dropdown -->
                    <div
                        v-if="isSearchFocused && (searchResults.length > 0 || searchError)"
                        class="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-zinc-900 rounded-lg shadow-xl border border-gray-200 dark:border-zinc-800 max-h-64 overflow-y-auto z-40"
                    >
                        <div v-if="searchError" class="p-4 text-sm text-red-500">
                            {{ searchError }}
                        </div>
                        <button
                            v-for="(result, index) in searchResults"
                            :key="index"
                            class="w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-zinc-800 border-b border-gray-100 dark:border-zinc-800 last:border-b-0 transition-colors"
                            @click="selectSearchResult(result)"
                        >
                            <div class="font-medium text-gray-900 dark:text-zinc-100 text-sm">
                                {{ result.display_name }}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-zinc-400 mt-1">
                                {{ result.type }}
                            </div>
                        </button>
                    </div>
                </div>
            </div>

            <div ref="mapContainer" class="absolute inset-0" :class="{ 'cursor-crosshair': isExportMode }"></div>

            <!-- export instructions overlay -->
            <div
                v-if="isExportMode && !selectedBbox"
                class="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-4 py-2 bg-blue-600 text-white rounded-full shadow-lg font-medium text-sm animate-bounce"
            >
                {{ $t("map.export_instructions") }}
            </div>

            <!-- export configuration overlay -->
            <div
                v-if="isExportMode && selectedBbox"
                class="absolute top-4 left-1/2 -translate-x-1/2 z-20 w-80 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden"
            >
                <div class="p-4 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="font-semibold text-gray-900 dark:text-zinc-100">{{ $t("map.export_area") }}</h3>
                    <button class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300" @click="cancelExport">
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-4 space-y-4">
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{
                                $t("map.min_zoom")
                            }}</label>
                            <input
                                v-model.number="exportMinZoom"
                                type="number"
                                min="0"
                                max="20"
                                class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm dark:text-zinc-100"
                            />
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{
                                $t("map.max_zoom")
                            }}</label>
                            <input
                                v-model.number="exportMaxZoom"
                                type="number"
                                min="0"
                                max="20"
                                class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm dark:text-zinc-100"
                            />
                        </div>
                    </div>
                    <div class="flex justify-between items-center text-sm">
                        <span class="text-gray-600 dark:text-zinc-400">{{ $t("map.tile_count") }}:</span>
                        <span class="font-bold text-blue-600">{{ estimatedTiles }}</span>
                    </div>
                    <div class="flex gap-2">
                        <button
                            :disabled="isExporting"
                            class="flex-1 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-zinc-700 dark:hover:bg-zinc-600 disabled:bg-gray-100 dark:disabled:bg-zinc-800 text-gray-900 dark:text-zinc-100 rounded-lg font-bold transition-colors"
                            @click="cancelExport"
                        >
                            {{ $t("common.cancel") }}
                        </button>
                        <button
                            :disabled="isExporting"
                            class="flex-1 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg font-bold transition-colors shadow-md"
                            @click="startExport"
                        >
                            {{ $t("map.start_export") }}
                        </button>
                    </div>
                </div>
            </div>

            <!-- export progress overlay -->
            <div
                v-if="exportStatus"
                class="absolute bottom-4 right-4 z-20 w-72 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 p-4 space-y-3 animate-in slide-in-from-bottom-4"
            >
                <div class="flex justify-between items-center">
                    <span class="font-bold text-sm text-gray-900 dark:text-zinc-100">{{
                        exportStatus.status === "completed" ? $t("map.download_ready") : $t("map.exporting")
                    }}</span>
                    <button
                        v-if="exportStatus.status === 'completed' || exportStatus.status === 'failed'"
                        class="text-gray-400"
                        @click="exportStatus = null"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-4" />
                    </button>
                </div>

                <div v-if="exportStatus.status !== 'completed' && exportStatus.status !== 'failed'">
                    <div class="w-full h-2 bg-gray-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                        <div
                            class="h-full bg-blue-500 transition-all duration-300"
                            :style="{ width: exportStatus.progress + '%' }"
                        ></div>
                    </div>
                    <div class="flex justify-between text-[10px] text-gray-500 mt-1 uppercase font-bold tracking-wider">
                        <span>{{ exportStatus.current }} / {{ exportStatus.total }} tiles</span>
                        <span>{{ exportStatus.progress }}%</span>
                    </div>
                </div>

                <div v-if="exportStatus.status === 'completed'">
                    <a
                        :href="`/api/v1/map/export/${exportId}/download`"
                        class="flex items-center justify-center space-x-2 w-full py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-bold transition-colors shadow-md"
                    >
                        <MaterialDesignIcon icon-name="download" class="size-4" />
                        <span>{{ $t("map.download_now") }}</span>
                    </a>
                </div>

                <div
                    v-if="exportStatus.status === 'failed'"
                    class="text-xs text-red-500 bg-red-50 dark:bg-red-950/20 p-2 rounded-lg"
                >
                    {{ exportStatus.error }}
                </div>
            </div>

            <!-- loading overlay -->
            <div
                v-if="isUploading"
                class="absolute inset-0 z-20 flex items-center justify-center bg-white/50 dark:bg-black/50 backdrop-blur-sm"
            >
                <div class="bg-white dark:bg-zinc-900 p-6 rounded-xl shadow-xl flex flex-col items-center space-y-4">
                    <div
                        class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"
                    ></div>
                    <p class="text-gray-900 dark:text-zinc-100 font-medium">{{ $t("map.uploading") }}</p>
                </div>
            </div>

            <!-- no map warning -->
            <div
                v-if="offlineEnabled && !hasOfflineMap"
                class="absolute inset-0 z-20 flex items-center justify-center p-4"
            >
                <div
                    class="max-w-md bg-white dark:bg-zinc-900 p-6 rounded-xl shadow-xl border border-amber-200 dark:border-amber-900/50 flex flex-col items-center text-center space-y-4"
                >
                    <MaterialDesignIcon icon-name="alert-circle" class="size-12 text-amber-500" />
                    <p class="text-gray-900 dark:text-zinc-100 font-medium">{{ $t("map.no_map_loaded") }}</p>
                    <button
                        class="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-colors font-medium"
                        @click="$refs.fileInput.click()"
                    >
                        {{ $t("map.upload_mbtiles") }}
                    </button>
                </div>
            </div>

            <!-- map info overlay -->
            <div class="absolute bottom-4 left-4 z-10 space-y-2 pointer-events-none">
                <div
                    v-if="metadata && metadata.name && !metadata.name.startsWith('Map Export')"
                    class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 p-2 rounded-lg text-xs text-gray-600 dark:text-zinc-400 pointer-events-auto shadow-sm"
                >
                    <div class="font-semibold text-gray-900 dark:text-zinc-100 mb-1">
                        {{ metadata.name }}
                    </div>
                    <div
                        v-if="metadata.attribution"
                        class="max-w-xs overflow-hidden text-ellipsis whitespace-nowrap"
                        :title="metadata.attribution"
                    >
                        {{ metadata.attribution }}
                    </div>
                </div>

                <!-- Lat/Lon Box -->
                <div
                    class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur border border-gray-200 dark:border-zinc-800 p-2 rounded-lg text-[10px] font-mono text-gray-600 dark:text-zinc-400 pointer-events-auto shadow-sm flex flex-col space-y-0.5"
                >
                    <div class="flex justify-between space-x-4">
                        <span class="opacity-50 uppercase tracking-tighter">Lat</span>
                        <span class="text-gray-900 dark:text-zinc-100">{{ currentCenter[1].toFixed(6) }}</span>
                    </div>
                    <div class="flex justify-between space-x-4">
                        <span class="opacity-50 uppercase tracking-tighter">Lon</span>
                        <span class="text-gray-900 dark:text-zinc-100">{{ currentCenter[0].toFixed(6) }}</span>
                    </div>
                </div>
            </div>

            <!-- controls overlay -->
            <div
                v-if="isSettingsOpen"
                class="absolute top-4 right-4 z-20 w-64 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden"
            >
                <div class="p-4 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="font-semibold text-gray-900 dark:text-zinc-100">{{ $t("app.settings") }}</h3>
                    <button
                        class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300"
                        @click="isSettingsOpen = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-4 space-y-4">
                    <div>
                        <button
                            class="w-full flex items-center justify-center space-x-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-gray-900 dark:text-zinc-100 rounded-lg transition-colors text-sm font-medium"
                            @click="setAsDefaultView"
                        >
                            <MaterialDesignIcon icon-name="pin" class="size-4" />
                            <span>{{ $t("map.set_as_default") }}</span>
                        </button>
                    </div>

                    <div v-if="!offlineEnabled" class="border-t border-gray-100 dark:border-zinc-800 pt-4 space-y-4">
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{
                                $t("map.tile_server_url")
                            }}</label>
                            <input
                                v-model="tileServerUrl"
                                type="text"
                                class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm dark:text-zinc-100"
                                :placeholder="$t('map.tile_server_url_placeholder')"
                                @blur="saveTileServerUrl"
                            />
                            <p class="text-xs text-gray-500 dark:text-zinc-500 mt-1">
                                {{ $t("map.tile_server_url_hint") }}
                            </p>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">{{
                                $t("map.nominatim_api_url")
                            }}</label>
                            <input
                                v-model="nominatimApiUrl"
                                type="text"
                                class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm dark:text-zinc-100"
                                :placeholder="$t('map.nominatim_api_url_placeholder')"
                                @blur="saveNominatimApiUrl"
                            />
                            <p class="text-xs text-gray-500 dark:text-zinc-500 mt-1">
                                {{ $t("map.nominatim_api_url_hint") }}
                            </p>
                        </div>
                    </div>

                    <div class="flex items-center justify-between py-2 border-t border-gray-100 dark:border-zinc-800">
                        <span class="text-sm text-gray-700 dark:text-zinc-300">{{ $t("map.caching_enabled") }}</span>
                        <Toggle :model-value="cachingEnabled" @update:model-value="toggleCaching" />
                    </div>

                    <div class="border-t border-gray-100 dark:border-zinc-800 pt-4 space-y-4">
                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">MBTiles Storage Directory</label>
                            <input
                                v-model="mbtilesDir"
                                type="text"
                                class="w-full bg-gray-50 dark:bg-zinc-800 border border-gray-300 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm dark:text-zinc-100"
                                placeholder="Default storage directory"
                                @blur="saveMBTilesDir"
                            />
                        </div>

                        <div v-if="mbtilesList.length > 0" class="space-y-2">
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Available Maps</label>
                            <div class="max-h-48 overflow-y-auto space-y-1">
                                <div
                                    v-for="file in mbtilesList"
                                    :key="file.name"
                                    class="flex items-center justify-between p-2 rounded-lg bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-800"
                                >
                                    <div class="flex flex-col min-w-0 flex-1 mr-2">
                                        <span class="text-xs font-medium text-gray-900 dark:text-zinc-100 truncate" :title="file.name">{{ file.name }}</span>
                                        <span class="text-[10px] text-gray-500">{{ (file.size / 1024 / 1024).toFixed(1) }} MB</span>
                                    </div>
                                    <div class="flex items-center space-x-1">
                                        <button
                                            v-if="!file.is_active"
                                            class="p-1 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                                            title="Set as active"
                                            @click="setActiveMBTiles(file.name)"
                                        >
                                            <MaterialDesignIcon icon-name="check" class="size-4" />
                                        </button>
                                        <div v-else class="p-1 text-emerald-500" title="Active">
                                            <MaterialDesignIcon icon-name="check-circle" class="size-4" />
                                        </div>
                                        <button
                                            class="p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                                            title="Delete"
                                            @click="deleteMBTiles(file.name)"
                                        >
                                            <MaterialDesignIcon icon-name="delete" class="size-4" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <button
                        class="w-full px-3 py-2 bg-red-50 hover:bg-red-100 dark:bg-red-950/20 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg transition-colors text-xs font-bold uppercase tracking-wider"
                        @click="clearCache"
                    >
                        {{ $t("map.clear_cache") }}
                    </button>

                    <div
                        class="text-xs text-gray-500 dark:text-zinc-500 space-y-1 pt-2 border-t border-gray-100 dark:border-zinc-800"
                    >
                        <div class="flex justify-between">
                            <span>{{ $t("map.zoom") }}:</span>
                            <span class="font-mono">{{ currentZoom.toFixed(1) }}</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Lat:</span>
                            <span class="font-mono">{{ currentCenter[1].toFixed(5) }}</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Lon:</span>
                            <span class="font-mono">{{ currentCenter[0].toFixed(5) }}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- onboarding tooltip -->
            <div
                v-if="showOnboardingTooltip"
                class="fixed inset-0 z-[100] pointer-events-none"
                @click="dismissOnboardingTooltip"
            >
                <div class="absolute inset-0 bg-black/50 pointer-events-auto"></div>
                <div
                    ref="tooltipElement"
                    class="absolute bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 p-4 pointer-events-auto max-w-xs sm:max-w-sm"
                    :style="tooltipStyle"
                >
                    <div class="flex items-start justify-between mb-2">
                        <h3 class="font-semibold text-gray-900 dark:text-zinc-100 text-sm">
                            {{ $t("map.onboarding_title") }}
                        </h3>
                        <button
                            class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                            @click="dismissOnboardingTooltip"
                        >
                            <MaterialDesignIcon icon-name="close" class="size-4" />
                        </button>
                    </div>
                    <p class="text-sm text-gray-600 dark:text-zinc-400 mb-3">
                        {{ $t("map.onboarding_text") }}
                    </p>
                    <button
                        class="w-full px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors text-sm font-medium"
                        @click="dismissOnboardingTooltip"
                    >
                        {{ $t("map.onboarding_got_it") }}
                    </button>
                </div>
                <svg
                    v-if="arrowPath && !isMobileScreen"
                    ref="arrowElement"
                    class="absolute pointer-events-none"
                    :style="arrowStyle"
                    :width="arrowSvgWidth"
                    :height="arrowSvgHeight"
                    :viewBox="`0 0 ${arrowSvgWidth} ${arrowSvgHeight}`"
                >
                    <path :d="arrowPath" stroke="#3b82f6" stroke-width="3" fill="none" marker-end="url(#arrowhead)" />
                    <defs>
                        <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                            <polygon points="0 0, 10 3, 0 6" fill="#3b82f6" />
                        </marker>
                    </defs>
                </svg>
            </div>

            <!-- floating upload button (mobile only) -->
            <button
                class="sm:hidden fixed bottom-4 right-4 z-30 p-4 bg-blue-500 hover:bg-blue-600 text-white rounded-full shadow-lg transition-colors"
                :title="$t('map.upload_mbtiles')"
                @click="$refs.fileInput.click()"
            >
                <MaterialDesignIcon icon-name="upload" class="size-6" />
            </button>
        </div>
    </div>
</template>

<script>
import "ol/ol.css";
import Map from "ol/Map";
import View from "ol/View";
import TileLayer from "ol/layer/Tile";
import XYZ from "ol/source/XYZ";
import { fromLonLat, toLonLat } from "ol/proj";
import { defaults as defaultControls } from "ol/control";
import DragBox from "ol/interaction/DragBox";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import TileCache from "../../js/TileCache";
import Toggle from "../forms/Toggle.vue";

export default {
    name: "MapPage",
    components: {
        MaterialDesignIcon,
        Toggle,
    },
    data() {
        return {
            map: null,
            offlineEnabled: false,
            hasOfflineMap: false,
            metadata: null,
            isUploading: false,
            isSettingsOpen: false,
            currentCenter: [0, 0],
            currentZoom: 2,
            config: null,

            // caching
            cachingEnabled: true,

            // tile server
            tileServerUrl: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",

            // search
            searchQuery: "",
            searchResults: [],
            isSearching: false,
            isSearchFocused: false,
            searchError: null,
            nominatimApiUrl: "https://nominatim.openstreetmap.org",
            searchTimeout: null,

            // export mode
            isExportMode: false,
            dragBox: null,
            selectedBbox: null,
            exportMinZoom: 0,
            exportMaxZoom: 10,
            isExporting: false,
            exportId: null,
            exportStatus: null,
            exportInterval: null,

            // onboarding
            showOnboardingTooltip: false,
            tooltipStyle: {},
            arrowStyle: {},
            arrowPath: null,
            arrowSvgWidth: 200,
            arrowSvgHeight: 200,
            isMobileScreen: false,

            // MBTiles management
            mbtilesList: [],
            mbtilesDir: "",
        };
    },
    computed: {
        estimatedTiles() {
            if (!this.selectedBbox) return 0;
            const [minLon, minLat, maxLon, maxLat] = this.selectedBbox;
            let total = 0;
            for (let z = this.exportMinZoom; z <= this.exportMaxZoom; z++) {
                const x1 = this.lonToTile(minLon, z);
                const x2 = this.lonToTile(maxLon, z);
                const y1 = this.latToTile(maxLat, z);
                const y2 = this.latToTile(minLat, z);
                total += (Math.abs(x2 - x1) + 1) * (Math.abs(y2 - y1) + 1);
            }
            return total;
        },
    },
    async mounted() {
        await this.getConfig();
        this.initMap();
        await this.checkOfflineMap();
        await this.loadMBTilesList();

        // Listen for moveend to update coordinates in UI
        if (this.map) {
            this.map.on("moveend", () => {
                const view = this.map.getView();
                this.currentCenter = toLonLat(view.getCenter());
                this.currentZoom = view.getZoom();
            });
        }

        // Check if onboarding tooltip should be shown
        this.checkOnboardingTooltip();

        // Add click outside handler for search
        document.addEventListener("click", this.handleClickOutside);

        // Check screen size for mobile
        this.checkScreenSize();
        window.addEventListener("resize", this.checkScreenSize);
    },
    beforeUnmount() {
        if (this.exportInterval) clearInterval(this.exportInterval);
        if (this.searchTimeout) clearTimeout(this.searchTimeout);
        document.removeEventListener("click", this.handleClickOutside);
        window.removeEventListener("resize", this.checkScreenSize);
    },
    methods: {
        async getConfig() {
            try {
                const response = await window.axios.get("/api/v1/config");
                this.config = response.data.config;
                this.offlineEnabled = this.config.map_offline_enabled;
                this.cachingEnabled = this.config.map_tile_cache_enabled !== undefined ? this.config.map_tile_cache_enabled : true;
                this.mbtilesDir = this.config.map_mbtiles_dir || "";
                if (this.config.map_tile_server_url) {
                    this.tileServerUrl = this.config.map_tile_server_url;
                }
                if (this.config.map_nominatim_api_url) {
                    this.nominatimApiUrl = this.config.map_nominatim_api_url;
                }
            } catch (e) {
                console.error("Failed to load config", e);
            }
        },
        async loadMBTilesList() {
            try {
                const response = await window.axios.get("/api/v1/map/mbtiles");
                this.mbtilesList = response.data;
            } catch (e) {
                console.error("Failed to load MBTiles list", e);
            }
        },
        async setActiveMBTiles(filename) {
            try {
                await window.axios.post("/api/v1/map/mbtiles/active", { filename });
                await this.checkOfflineMap();
                await this.loadMBTilesList();
                ToastUtils.success("Map source updated");
            } catch (e) {
                ToastUtils.error("Failed to set active map");
            }
        },
        async deleteMBTiles(filename) {
            if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
            try {
                await window.axios.delete(`/api/v1/map/mbtiles/${filename}`);
                await this.loadMBTilesList();
                if (this.metadata && this.metadata.path && this.metadata.path.endsWith(filename)) {
                    await this.checkOfflineMap();
                }
                ToastUtils.success("File deleted");
            } catch (e) {
                ToastUtils.error("Failed to delete file");
            }
        },
        async saveMBTilesDir() {
            try {
                await window.axios.patch("/api/v1/config", {
                    map_mbtiles_dir: this.mbtilesDir,
                });
                ToastUtils.success("Storage directory saved");
                this.loadMBTilesList();
            } catch (e) {
                ToastUtils.error("Failed to save directory");
            }
        },
        initMap() {
            const defaultLat = parseFloat(this.config?.map_default_lat || 0);
            const defaultLon = parseFloat(this.config?.map_default_lon || 0);
            const defaultZoom = parseInt(this.config?.map_default_zoom || 2);

            this.map = new Map({
                target: this.$refs.mapContainer,
                layers: [
                    new TileLayer({
                        source: this.getTileSource(),
                    }),
                ],
                view: new View({
                    center: fromLonLat([defaultLon, defaultLat]),
                    zoom: defaultZoom,
                }),
                controls: defaultControls({
                    attribution: false,
                    rotate: false,
                }),
            });

            this.currentCenter = [defaultLon, defaultLat];
            this.currentZoom = defaultZoom;

            // Setup dragBox for export
            this.dragBox = new DragBox({
                condition: () => this.isExportMode,
            });

            this.dragBox.on("boxend", () => {
                const extent = this.dragBox.getGeometry().getExtent();
                const min = toLonLat([extent[0], extent[1]]);
                const max = toLonLat([extent[2], extent[3]]);
                this.selectedBbox = [min[0], min[1], max[0], max[1]];
                this.exportMinZoom = Math.floor(this.map.getView().getZoom());
                this.exportMaxZoom = Math.min(this.exportMinZoom + 3, 18);
            });

            this.map.addInteraction(this.dragBox);
        },
        isLocalUrl(url) {
            if (!url) return false;
            try {
                const urlObj = new URL(url, window.location.origin);
                return (
                    urlObj.hostname === "localhost" ||
                    urlObj.hostname === "127.0.0.1" ||
                    urlObj.hostname === "::1" ||
                    urlObj.hostname.startsWith("192.168.") ||
                    urlObj.hostname.startsWith("10.") ||
                    urlObj.hostname.startsWith("172.") ||
                    urlObj.hostname.endsWith(".local") ||
                    url.startsWith("/")
                );
            } catch {
                return url.startsWith("/") || url.startsWith("./") || !url.startsWith("http");
            }
        },
        isDefaultOnlineUrl(url, type) {
            if (!url) return false;
            if (type === "tile") {
                return url.includes("tile.openstreetmap.org") || url.includes("openstreetmap.org");
            } else if (type === "nominatim") {
                return url.includes("nominatim.openstreetmap.org") || url.includes("openstreetmap.org");
            }
            return false;
        },
        async checkApiConnection(url) {
            if (!url || this.isLocalUrl(url)) {
                return true;
            }
            try {
                let testUrl = url.endsWith("/") ? url.slice(0, -1) : url;
                if (testUrl.includes("{z}") || testUrl.includes("{x}") || testUrl.includes("{y}")) {
                    testUrl = testUrl.replace("{z}", "0").replace("{x}", "0").replace("{y}", "0");
                }
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 3000);
                const response = await fetch(testUrl, {
                    method: "HEAD",
                    signal: controller.signal,
                    headers: {
                        "User-Agent": "ReticulumMeshChatX/1.0",
                    },
                });
                clearTimeout(timeoutId);
                return response.ok || response.status === 405 || response.status === 404;
            } catch {
                return false;
            }
        },
        getTileSource() {
            const isOffline = this.offlineEnabled;
            const defaultTileUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
            const customTileUrl = this.tileServerUrl || defaultTileUrl;
            const isCustomLocal = this.isLocalUrl(customTileUrl);
            const isDefaultOnline = this.isDefaultOnlineUrl(customTileUrl, "tile");
            
            let tileUrl;
            if (isOffline) {
                if (isCustomLocal || (!isDefaultOnline && customTileUrl !== defaultTileUrl)) {
                    tileUrl = customTileUrl;
                } else {
                    tileUrl = "/api/v1/map/tiles/{z}/{x}/{y}.png";
                }
            } else {
                tileUrl = customTileUrl;
            }
            
            const source = new XYZ({
                url: tileUrl,
                crossOrigin: "anonymous",
            });

            const originalTileLoadFunction = source.getTileLoadFunction();
            
            if (isOffline) {
                source.setTileLoadFunction(async (tile, src) => {
                    try {
                        const response = await fetch(src);
                        if (!response.ok) {
                            if (response.status === 404) {
                                tile.setState(3);
                                return;
                            }
                            throw new Error(`HTTP ${response.status}`);
                        }
                        const blob = await response.blob();
                        tile.getImage().src = URL.createObjectURL(blob);
                    } catch (error) {
                        tile.setState(3);
                    }
                });
            } else {
                source.setTileLoadFunction(async (tile, src) => {
                    if (!this.cachingEnabled) {
                        originalTileLoadFunction(tile, src);
                        return;
                    }

                    try {
                        const cached = await TileCache.getTile(src);
                        if (cached) {
                            tile.getImage().src = URL.createObjectURL(cached);
                            return;
                        }

                        const response = await fetch(src);
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}`);
                        }
                        const blob = await response.blob();
                        await TileCache.setTile(src, blob);
                        tile.getImage().src = URL.createObjectURL(blob);
                    } catch {
                        originalTileLoadFunction(tile, src);
                    }
                });
            }

            return source;
        },
        async checkOfflineMap() {
            try {
                const response = await window.axios.get("/api/v1/map/offline");
                this.metadata = response.data;
                this.hasOfflineMap = true;

                if (this.offlineEnabled) {
                    this.updateMapSource();
                }
            } catch {
                this.hasOfflineMap = false;
                this.metadata = null;
                if (this.offlineEnabled) {
                    this.offlineEnabled = false;
                    this.updateMapSource();
                }
            }
        },
        updateMapSource() {
            if (!this.map) return;
            const layers = this.map.getLayers();
            layers.clear();
            layers.push(
                new TileLayer({
                    source: this.getTileSource(),
                })
            );
        },
        async toggleOffline(enabled) {
            if (enabled && !this.hasOfflineMap) {
                ToastUtils.error(this.$t("map.no_map_loaded"));
                return;
            }

            if (enabled) {
                const defaultTileUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
                const defaultNominatimUrl = "https://nominatim.openstreetmap.org";
                
                const isCustomTileLocal = this.isLocalUrl(this.tileServerUrl);
                const isDefaultTileOnline = this.isDefaultOnlineUrl(this.tileServerUrl, "tile");
                const hasCustomTile = this.tileServerUrl && this.tileServerUrl !== defaultTileUrl;
                
                const isCustomNominatimLocal = this.isLocalUrl(this.nominatimApiUrl);
                const isDefaultNominatimOnline = this.isDefaultOnlineUrl(this.nominatimApiUrl, "nominatim");
                const hasCustomNominatim = this.nominatimApiUrl && this.nominatimApiUrl !== defaultNominatimUrl;
                
                if (hasCustomTile && !isCustomTileLocal && !isDefaultTileOnline) {
                    const isAccessible = await this.checkApiConnection(this.tileServerUrl);
                    if (!isAccessible) {
                        ToastUtils.error(this.$t("map.custom_tile_server_unavailable"));
                        return;
                    }
                }
                
                if (hasCustomNominatim && !isCustomNominatimLocal && !isDefaultNominatimOnline) {
                    const isAccessible = await this.checkApiConnection(this.nominatimApiUrl);
                    if (!isAccessible) {
                        ToastUtils.error(this.$t("map.custom_nominatim_unavailable"));
                        return;
                    }
                }
            }

            this.offlineEnabled = enabled;
            if (enabled) {
                this.isExportMode = false;
                this.clearSearch();
            }
            this.updateMapSource();

            // Persist setting
            try {
                await window.axios.patch("/api/v1/config", {
                    map_offline_enabled: enabled,
                });
            } catch (e) {
                console.error("Failed to save offline setting", e);
            }
        },
        async toggleCaching(enabled) {
            this.cachingEnabled = enabled;
            try {
                await window.axios.patch("/api/v1/config", {
                    map_tile_cache_enabled: enabled,
                });
            } catch (e) {
                console.error("Failed to save caching setting", e);
            }
        },
        toggleExportMode() {
            this.isExportMode = !this.isExportMode;
            if (!this.isExportMode) {
                this.selectedBbox = null;
            }
        },
        cancelExport() {
            this.selectedBbox = null;
            this.isExportMode = false;
        },
        async startExport() {
            if (!this.selectedBbox) return;
            this.isExporting = true;
            try {
                const response = await window.axios.post("/api/v1/map/export", {
                    bbox: this.selectedBbox,
                    min_zoom: this.exportMinZoom,
                    max_zoom: this.exportMaxZoom,
                    name: `Map Export ${new Date().toLocaleString()}`,
                });
                this.exportId = response.data.export_id;
                this.isExportMode = false;
                this.selectedBbox = null;
                this.pollExportStatus();
            } catch {
                ToastUtils.error("Failed to start export");
                this.isExporting = false;
            }
        },
        pollExportStatus() {
            if (this.exportInterval) clearInterval(this.exportInterval);
            this.exportInterval = setInterval(async () => {
                try {
                    const response = await window.axios.get(`/api/v1/map/export/${this.exportId}`);
                    this.exportStatus = response.data;
                    if (this.exportStatus.status === "completed" || this.exportStatus.status === "failed") {
                        clearInterval(this.exportInterval);
                        this.isExporting = false;
                    }
                } catch {
                    clearInterval(this.exportInterval);
                    this.isExporting = false;
                }
            }, 2000);
        },
        lonToTile(lon, zoom) {
            return Math.floor(((lon + 180) / 360) * Math.pow(2, zoom));
        },
        latToTile(lat, zoom) {
            return Math.floor(
                ((1 - Math.log(Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)) / Math.PI) / 2) *
                    Math.pow(2, zoom)
            );
        },
        async onFileSelected(event) {
            const file = event.target.files[0];
            if (!file) return;

            if (!file.name.endsWith(".mbtiles")) {
                ToastUtils.error("Please select an .mbtiles file");
                return;
            }

            this.isUploading = true;
            const formData = new FormData();
            formData.append("file", file);

            try {
                const response = await window.axios.post("/api/v1/map/offline", formData, {
                    headers: {
                        "Content-Type": "multipart/form-data",
                    },
                });

                this.metadata = response.data.metadata;
                this.hasOfflineMap = true;
                this.offlineEnabled = true;
                this.updateMapSource();
                this.loadMBTilesList();
                ToastUtils.success(this.$t("map.upload_success"));

                // If the map has bounds, we might want to fit to them
                if (this.metadata.bounds) {
                    const bounds = this.metadata.bounds.split(",").map(parseFloat);
                    if (bounds.length === 4) {
                        const extent = [...fromLonLat([bounds[0], bounds[1]]), ...fromLonLat([bounds[2], bounds[3]])];
                        this.map.getView().fit(extent, { padding: [20, 20, 20, 20] });
                    }
                }
            } catch (e) {
                const error = e.response?.data?.error || e.message;
                ToastUtils.error(this.$t("map.upload_failed") + ": " + error);
            } finally {
                this.isUploading = false;
                event.target.value = ""; // Reset input
            }
        },
        async setAsDefaultView() {
            if (!this.map) return;
            const view = this.map.getView();
            const center = toLonLat(view.getCenter());
            const zoom = Math.round(view.getZoom());

            try {
                await window.axios.patch("/api/v1/config", {
                    map_default_lat: center[1],
                    map_default_lon: center[0],
                    map_default_zoom: zoom,
                });
                ToastUtils.success("Default view saved");
            } catch {
                ToastUtils.error("Failed to save default view");
            }
        },
        async clearCache() {
            try {
                await TileCache.clear();
                ToastUtils.success(this.$t("map.cache_cleared"));
            } catch {
                ToastUtils.error("Failed to clear cache");
            }
        },
        async saveTileServerUrl() {
            try {
                await window.axios.patch("/api/v1/config", {
                    map_tile_server_url: this.tileServerUrl,
                });
                this.updateMapSource();
                ToastUtils.success(this.$t("map.tile_server_saved"));
            } catch {
                ToastUtils.error("Failed to save tile server URL");
            }
        },
        async saveNominatimApiUrl() {
            try {
                await window.axios.patch("/api/v1/config", {
                    map_nominatim_api_url: this.nominatimApiUrl,
                });
                ToastUtils.success(this.$t("map.nominatim_api_saved"));
            } catch {
                ToastUtils.error("Failed to save Nominatim API URL");
            }
        },
        checkOnboardingTooltip() {
            const hasSeenOnboarding = localStorage.getItem("map_onboarding_seen");
            if (!hasSeenOnboarding && !this.offlineEnabled) {
                this.$nextTick(() => {
                    this.showOnboardingTooltip = true;
                    this.positionOnboardingTooltip();
                });
            }
        },
        positionOnboardingTooltip() {
            this.$nextTick(() => {
                if (!this.$refs.exportButton || !this.$refs.tooltipElement) return;

                const exportButton = this.$refs.exportButton;
                const tooltip = this.$refs.tooltipElement;
                const buttonRect = exportButton.getBoundingClientRect();
                const tooltipRect = tooltip.getBoundingClientRect();

                const isMobile = window.innerWidth < 640;
                let tooltipLeft, tooltipTop;
                let tooltipAboveButton = false;

                if (isMobile) {
                    tooltipLeft = window.innerWidth / 2 - tooltipRect.width / 2;
                    tooltipTop = buttonRect.top - tooltipRect.height - 20;
                    tooltipAboveButton = true;
                    if (tooltipTop < 10) {
                        tooltipTop = buttonRect.bottom + 20;
                        tooltipAboveButton = false;
                    }
                } else {
                    tooltipLeft = buttonRect.left - tooltipRect.width - 20;
                    tooltipTop = buttonRect.top + buttonRect.height / 2 - tooltipRect.height / 2;
                }

                if (tooltipTop < 10) tooltipTop = 10;
                if (tooltipLeft < 10) tooltipLeft = 10;
                if (tooltipLeft + tooltipRect.width > window.innerWidth - 10) {
                    tooltipLeft = window.innerWidth - tooltipRect.width - 10;
                }

                this.tooltipStyle = {
                    left: `${tooltipLeft}px`,
                    top: `${tooltipTop}px`,
                };

                const buttonCenterY = buttonRect.top + buttonRect.height / 2;
                const tooltipCenterX = tooltipLeft + tooltipRect.width / 2;
                const tooltipCenterY = tooltipTop + tooltipRect.height / 2;

                const arrowStartX = isMobile ? tooltipCenterX : tooltipLeft + tooltipRect.width;
                const arrowStartY = isMobile
                    ? tooltipAboveButton
                        ? tooltipTop + tooltipRect.height
                        : tooltipTop
                    : tooltipCenterY;

                const arrowEndX = buttonRect.left + buttonRect.width * 0.25;
                const arrowEndY = buttonCenterY;

                const minX = Math.min(arrowStartX, arrowEndX) - 20;
                const maxX = Math.max(arrowStartX, arrowEndX) + 20;
                const minY = Math.min(arrowStartY, arrowEndY) - 20;
                const maxY = Math.max(arrowStartY, arrowEndY) + 20;

                this.arrowSvgWidth = maxX - minX;
                this.arrowSvgHeight = maxY - minY;

                const adjustedStartX = arrowStartX - minX;
                const adjustedStartY = arrowStartY - minY;
                const adjustedEndX = arrowEndX - minX;
                const adjustedEndY = arrowEndY - minY;

                const controlX1 = adjustedStartX + (adjustedEndX - adjustedStartX) * 0.5;
                const controlY1 = adjustedStartY + (adjustedEndY - adjustedStartY) * 0.3;
                const controlX2 = adjustedStartX + (adjustedEndX - adjustedStartX) * 0.7;
                const controlY2 = adjustedStartY + (adjustedEndY - adjustedStartY) * 0.7;

                this.arrowPath = `M ${adjustedStartX} ${adjustedStartY} C ${controlX1} ${controlY1}, ${controlX2} ${controlY2}, ${adjustedEndX} ${adjustedEndY}`;

                this.arrowStyle = {
                    left: `${minX}px`,
                    top: `${minY}px`,
                };
            });
        },
        dismissOnboardingTooltip() {
            this.showOnboardingTooltip = false;
            localStorage.setItem("map_onboarding_seen", "true");
        },
        onSearchInput() {
            this.searchError = null;
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }
        },
        async performSearch() {
            if (!this.searchQuery || this.isSearching) return;

            const defaultNominatimUrl = "https://nominatim.openstreetmap.org";
            const isCustomLocal = this.isLocalUrl(this.nominatimApiUrl);
            const isDefaultOnline = this.isDefaultOnlineUrl(this.nominatimApiUrl, "nominatim");
            
            if (this.offlineEnabled) {
                if (isCustomLocal || (!isDefaultOnline && this.nominatimApiUrl !== defaultNominatimUrl)) {
                    const isAccessible = await this.checkApiConnection(this.nominatimApiUrl);
                    if (!isAccessible) {
                        this.searchError = this.$t("map.search_offline_error");
                        return;
                    }
                } else {
                    this.searchError = this.$t("map.search_offline_error");
                    return;
                }
            }

            this.isSearching = true;
            this.searchError = null;
            this.searchResults = [];

            try {
                const apiUrl = this.nominatimApiUrl.endsWith("/")
                    ? this.nominatimApiUrl.slice(0, -1)
                    : this.nominatimApiUrl;
                const url = `${apiUrl}/search?format=json&q=${encodeURIComponent(this.searchQuery)}&limit=10&addressdetails=1`;

                const response = await fetch(url, {
                    headers: {
                        "User-Agent": "ReticulumMeshChatX/1.0",
                    },
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();

                if (Array.isArray(data) && data.length > 0) {
                    this.searchResults = data.map((item) => ({
                        display_name: item.display_name,
                        lat: parseFloat(item.lat),
                        lon: parseFloat(item.lon),
                        type: item.type || item.class || "",
                        boundingbox: item.boundingbox,
                    }));
                } else {
                    this.searchError = this.$t("map.search_no_results");
                }
            } catch (e) {
                console.error("Search error:", e);
                if (e.message.includes("Failed to fetch") || e.message.includes("NetworkError")) {
                    this.searchError = this.$t("map.search_connection_error");
                } else {
                    this.searchError = this.$t("map.search_error") + ": " + e.message;
                }
            } finally {
                this.isSearching = false;
            }
        },
        selectSearchResult(result) {
            if (!this.map) return;

            const view = this.map.getView();
            const center = fromLonLat([result.lon, result.lat]);

            if (result.boundingbox && result.boundingbox.length === 4) {
                const [minLat, maxLat, minLon, maxLon] = result.boundingbox.map(parseFloat);
                const extent = [...fromLonLat([minLon, minLat]), ...fromLonLat([maxLon, maxLat])];
                view.fit(extent, {
                    padding: [50, 50, 50, 50],
                    duration: 500,
                });
            } else {
                view.animate({
                    center: center,
                    zoom: Math.max(view.getZoom(), 15),
                    duration: 500,
                });
            }

            this.clearSearch();
        },
        clearSearch() {
            this.searchQuery = "";
            this.searchResults = [];
            this.searchError = null;
            this.isSearchFocused = false;
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = null;
            }
        },
        handleClickOutside(event) {
            if (this.$refs.searchContainer && !this.$refs.searchContainer.contains(event.target)) {
                this.isSearchFocused = false;
            }
        },
        checkScreenSize() {
            this.isMobileScreen = window.innerWidth < 640;
        },
    },
};
</script>

<style scoped>
/* Ensure map takes full space */
:deep(.ol-viewport) {
    border-radius: inherit;
}

.cursor-crosshair {
    cursor: crosshair !important;
}
</style>
