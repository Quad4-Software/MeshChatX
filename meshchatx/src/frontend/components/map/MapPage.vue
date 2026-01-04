<template>
    <div class="flex flex-col h-full w-full bg-white dark:bg-zinc-950 overflow-hidden">
        <!-- header -->
        <div
            class="flex items-center px-4 py-2 border-b border-gray-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur z-10 relative"
        >
            <div class="flex items-center space-x-2">
                <v-icon icon="mdi-map" class="text-blue-500 dark:text-blue-400" size="24"></v-icon>
                <h1 class="text-xl font-black text-gray-900 dark:text-white">{{ $t("map.title") }}</h1>
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
            <!-- drawing toolbar -->
            <div
                class="absolute top-14 left-1/2 -translate-x-1/2 sm:top-2 z-20 flex flex-col gap-2 transform-gpu w-max max-w-[98vw]"
            >
                <div
                    class="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl overflow-hidden flex flex-row p-0.5 sm:p-1 gap-0 sm:gap-0.5 border-0"
                >
                    <button
                        v-for="tool in drawingTools"
                        :key="tool.type"
                        class="p-1.5 sm:p-2 rounded-xl transition-all hover:scale-110 active:scale-90"
                        :class="[
                            (drawType === tool.type && !isMeasuring) || (tool.type === 'Export' && isExportMode)
                                ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/30'
                                : 'hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-600 dark:text-gray-400',
                        ]"
                        :title="tool.type === 'Export' ? 'MBTiles exporter' : $t(`map.tool_${tool.type.toLowerCase()}`)"
                        @click="tool.type === 'Export' ? toggleExportMode() : toggleDraw(tool.type)"
                    >
                        <v-icon :icon="'mdi-' + tool.icon" size="18" class="sm:!size-5"></v-icon>
                    </button>
                    <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
                    <button
                        class="p-1.5 sm:p-2 rounded-xl transition-all hover:scale-110 active:scale-90"
                        :class="[
                            isMeasuring
                                ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/30'
                                : 'hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-600 dark:text-gray-400',
                        ]"
                        :title="$t('map.tool_measure')"
                        @click="toggleMeasure"
                    >
                        <v-icon icon="mdi-ruler" size="18" class="sm:!size-5"></v-icon>
                    </button>
                    <button
                        class="p-1.5 sm:p-2 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 transition-all hover:scale-110 active:scale-90"
                        :title="$t('map.tool_clear')"
                        @click="clearDrawings"
                    >
                        <v-icon icon="mdi-trash-can-outline" size="18" class="sm:!size-5"></v-icon>
                    </button>
                    <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
                    <button
                        class="p-1.5 sm:p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-600 dark:text-gray-400 transition-all hover:scale-110 active:scale-90"
                        :title="$t('map.save_drawing')"
                        @click="showSaveDrawingModal = true"
                    >
                        <v-icon icon="mdi-content-save-outline" size="18" class="sm:!size-5"></v-icon>
                    </button>
                    <button
                        class="p-1.5 sm:p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-600 dark:text-gray-400 transition-all hover:scale-110 active:scale-90"
                        :title="$t('map.load_drawing')"
                        @click="openLoadDrawingModal"
                    >
                        <v-icon icon="mdi-folder-open-outline" size="18" class="sm:!size-5"></v-icon>
                    </button>
                    <div class="w-px h-6 bg-gray-200 dark:bg-zinc-800 my-auto mx-0.5 sm:mx-1"></div>
                    <button
                        class="p-1.5 sm:p-2 rounded-xl hover:bg-blue-50 dark:hover:bg-blue-900/20 text-blue-500 transition-all hover:scale-110 active:scale-90"
                        :title="$t('map.go_to_my_location')"
                        @click="goToMyLocation"
                    >
                        <v-icon icon="mdi-crosshairs-gps" size="18" class="sm:!size-5"></v-icon>
                    </button>
                </div>
            </div>

            <!-- search bar -->
            <div
                v-if="!offlineEnabled"
                ref="searchContainer"
                class="absolute top-2 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 z-30"
            >
                <div class="relative">
                    <div class="flex items-center bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border-0 ring-0">
                        <input
                            v-model="searchQuery"
                            type="text"
                            class="flex-1 px-4 py-2.5 bg-transparent text-gray-900 dark:text-zinc-100 placeholder-gray-400 focus:outline-none focus:ring-0 border-0 text-sm"
                            :placeholder="$t('map.search_placeholder')"
                            @input="onSearchInput"
                            @keydown.enter="performSearch"
                            @focus="isSearchFocused = true"
                        />
                        <button
                            v-if="searchQuery"
                            class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300 transition-colors"
                            @click="clearSearch"
                        >
                            <v-icon icon="mdi-close" size="18"></v-icon>
                        </button>
                        <button
                            class="p-2 mr-1 text-blue-500 hover:text-blue-600 disabled:text-gray-300 transition-colors"
                            :disabled="!searchQuery || isSearching"
                            @click="performSearch"
                        >
                            <v-icon
                                :icon="isSearching ? 'mdi-loading' : 'mdi-magnify'"
                                :class="{ 'animate-spin': isSearching }"
                                size="20"
                            ></v-icon>
                        </button>
                    </div>

                    <!-- search results dropdown -->
                    <div
                        v-if="isSearchFocused && (searchResults.length > 0 || searchError)"
                        class="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border-0 overflow-y-auto z-40 max-h-64"
                    >
                        <div v-if="searchError" class="p-4 text-sm text-red-500 flex items-center gap-2">
                            <v-icon icon="mdi-alert-circle" size="16"></v-icon>
                            {{ searchError }}
                        </div>
                        <button
                            v-for="(result, index) in searchResults"
                            :key="index"
                            class="w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-zinc-800/50 border-b border-gray-100/50 dark:border-zinc-800/50 last:border-b-0 transition-all"
                            @click="selectSearchResult(result)"
                        >
                            <div class="font-bold text-gray-900 dark:text-zinc-100 text-sm">
                                {{ result.display_name }}
                            </div>
                            <div
                                class="text-[10px] text-gray-400 dark:text-zinc-500 mt-0.5 font-bold uppercase tracking-wider"
                            >
                                {{ result.type }}
                            </div>
                        </button>
                    </div>
                </div>
            </div>

            <div ref="mapContainer" class="absolute inset-0" :class="{ 'cursor-crosshair': isExportMode }"></div>

            <!-- note hover tooltip -->
            <div
                v-if="hoveredNote && !editingFeature"
                class="absolute pointer-events-none z-50 bg-white/90 dark:bg-zinc-900/90 backdrop-blur border border-gray-200 dark:border-zinc-700 rounded-lg shadow-xl p-2 text-sm text-gray-900 dark:text-zinc-100 max-w-xs transform -translate-x-1/2 -translate-y-full mb-4"
                :style="{
                    left: map.getPixelFromCoordinate(hoveredNote.getGeometry().getCoordinates())[0] + 'px',
                    top: map.getPixelFromCoordinate(hoveredNote.getGeometry().getCoordinates())[1] + 'px',
                }"
            >
                <div class="font-bold flex items-center gap-1 mb-1 text-amber-500">
                    <MaterialDesignIcon icon-name="note-text" class="size-4" />
                    <span>Note</span>
                </div>
                <div class="whitespace-pre-wrap break-words">{{ hoveredNote.get("note") || "Empty note" }}</div>
            </div>

            <!-- inline note editor (overlay) -->
            <div ref="noteOverlayElement" class="absolute z-40">
                <div
                    v-if="editingFeature && !isMobileScreen"
                    class="bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-700 p-4 w-64 transform -translate-x-1/2 -translate-y-full mb-6"
                >
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-1">
                            <MaterialDesignIcon icon-name="note-edit" class="size-4 text-amber-500" />
                            Edit Note
                        </span>
                        <button
                            class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                            @click="closeNoteEditor"
                        >
                            <MaterialDesignIcon icon-name="close" class="size-4" />
                        </button>
                    </div>
                    <textarea
                        v-model="noteText"
                        class="w-full h-24 p-2 text-sm bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-none resize-none text-gray-900 dark:text-zinc-100"
                        placeholder="Type your note here..."
                    ></textarea>
                    <div class="flex justify-between mt-3">
                        <button
                            class="px-3 py-1.5 text-xs font-semibold text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors flex items-center gap-1"
                            @click="deleteNote"
                        >
                            <MaterialDesignIcon icon-name="trash-can-outline" class="size-3.5" />
                            Delete
                        </button>
                        <button
                            class="px-3 py-1.5 text-xs font-semibold bg-amber-500 text-white hover:bg-amber-600 rounded-lg shadow-sm transition-colors"
                            @click="saveNote"
                        >
                            Save
                        </button>
                    </div>
                </div>
            </div>

            <!-- loading skeleton for map -->
            <div v-if="!isMapLoaded" class="absolute inset-0 z-0 bg-slate-100 dark:bg-zinc-900 animate-pulse">
                <div class="grid grid-cols-4 grid-rows-4 h-full w-full gap-1 p-1 opacity-20">
                    <div v-for="i in 16" :key="i" class="bg-slate-300 dark:bg-zinc-700 rounded-lg"></div>
                </div>
            </div>

            <!-- telemetry marker overlay -->
            <div
                v-if="selectedMarker"
                class="absolute bottom-4 left-4 right-4 sm:left-4 sm:right-auto sm:w-80 z-20 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden text-gray-900 dark:text-zinc-100"
            >
                <div class="p-4 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div
                            class="size-8 rounded-full flex items-center justify-center border-2"
                            :style="{
                                color: selectedMarker.peer?.lxmf_user_icon?.foreground_colour || '#3b82f6',
                                borderColor: selectedMarker.peer?.lxmf_user_icon?.foreground_colour || '#3b82f6',
                                backgroundColor: selectedMarker.peer?.lxmf_user_icon?.background_colour || '#ffffff',
                            }"
                        >
                            <v-icon
                                :icon="'mdi-' + (selectedMarker.peer?.lxmf_user_icon?.icon_name || 'account')"
                                size="18"
                            ></v-icon>
                        </div>
                        <div>
                            <h3 class="font-bold text-gray-900 dark:text-zinc-100 truncate w-40">
                                {{
                                    selectedMarker.peer?.display_name ||
                                    selectedMarker.telemetry.destination_hash.substring(0, 8)
                                }}
                            </h3>
                            <div class="text-[10px] font-mono text-gray-500 uppercase tracking-tighter">
                                {{ selectedMarker.telemetry.destination_hash }}
                            </div>
                        </div>
                    </div>
                    <button
                        class="text-gray-500 hover:text-gray-700 dark:hover:text-zinc-300"
                        @click="selectedMarker = null"
                    >
                        <v-icon icon="mdi-close" size="20"></v-icon>
                    </button>
                </div>
                <div class="p-4 space-y-3">
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                Latitude
                            </div>
                            <div class="font-mono">
                                {{ selectedMarker.telemetry.telemetry.location.latitude.toFixed(6) }}
                            </div>
                        </div>
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                Longitude
                            </div>
                            <div class="font-mono">
                                {{ selectedMarker.telemetry.telemetry.location.longitude.toFixed(6) }}
                            </div>
                        </div>
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">
                                Altitude
                            </div>
                            <div>{{ selectedMarker.telemetry.telemetry.location.altitude.toFixed(1) }}m</div>
                        </div>
                        <div>
                            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-0.5">Speed</div>
                            <div>{{ selectedMarker.telemetry.telemetry.location.speed.toFixed(1) }}km/h</div>
                        </div>
                    </div>

                    <div
                        v-if="selectedMarker.telemetry.physical_link"
                        class="pt-2 border-t border-gray-100 dark:border-zinc-800"
                    >
                        <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Signal</div>
                        <div class="flex gap-4 text-xs font-mono">
                            <span>RSSI: {{ selectedMarker.telemetry.physical_link.rssi }}</span>
                            <span>SNR: {{ selectedMarker.telemetry.physical_link.snr }}</span>
                            <span>Q: {{ selectedMarker.telemetry.physical_link.q }}%</span>
                        </div>
                    </div>

                    <div class="pt-2 text-[10px] text-gray-400 flex items-center gap-1">
                        <v-icon icon="mdi-clock-outline" size="12"></v-icon>
                        Updated: {{ formatTimestamp(selectedMarker.telemetry.timestamp) }}
                    </div>

                    <button
                        class="w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-bold transition-colors text-sm flex items-center justify-center gap-2"
                        @click="openChat(selectedMarker.telemetry.destination_hash)"
                    >
                        <v-icon icon="mdi-message-text" size="16"></v-icon>
                        Open Chat
                    </button>
                </div>
            </div>

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
                class="absolute top-4 left-1/2 -translate-x-1/2 z-20 w-80 bg-white dark:bg-zinc-900 rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden text-gray-900 dark:text-zinc-100"
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
                    <button
                        v-else
                        class="text-xs font-bold text-red-500 hover:text-red-600 uppercase tracking-tighter"
                        @click="cancelActiveExport"
                    >
                        {{ $t("common.cancel") }}
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
                class="absolute top-14 right-4 z-20 w-64 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden"
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
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Preset Servers</label>
                            <div class="grid grid-cols-1 gap-2 mb-4">
                                <button
                                    class="px-3 py-2 text-xs font-semibold rounded-lg transition-all border"
                                    :class="
                                        tileServerUrl.includes('openstreetmap.org')
                                            ? 'bg-blue-500 border-blue-600 text-white shadow-sm'
                                            : 'bg-white dark:bg-zinc-800 border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-zinc-300 hover:bg-gray-50 dark:hover:bg-zinc-700'
                                    "
                                    @click="setTileServer('osm')"
                                >
                                    {{ $t("map.tile_server_openstreetmap") }}
                                </button>
                            </div>

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
                            <label class="block text-xs font-bold text-gray-500 uppercase mb-1"
                                >MBTiles Storage Directory</label
                            >
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
                                        <span
                                            class="text-xs font-medium text-gray-900 dark:text-zinc-100 truncate"
                                            :title="file.name"
                                            >{{ file.name }}</span
                                        >
                                        <span class="text-[10px] text-gray-500"
                                            >{{ (file.size / 1024 / 1024).toFixed(1) }} MB</span
                                        >
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

        <!-- save drawing modal -->
        <div
            v-if="showSaveDrawingModal"
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
        >
            <div
                class="bg-white dark:bg-zinc-900 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
            >
                <div class="p-6">
                    <h2 class="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <MaterialDesignIcon icon-name="content-save-outline" class="size-6 text-blue-500" />
                        {{ $t("map.save_drawing_title") }}
                    </h2>
                    <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ $t("map.save_drawing_desc") }}</p>

                    <div class="mt-6">
                        <label
                            class="block text-xs font-bold text-gray-500 dark:text-zinc-500 uppercase tracking-widest mb-2"
                        >
                            {{ $t("map.drawing_name") }}
                        </label>
                        <input
                            ref="newDrawingNameInput"
                            v-model="newDrawingName"
                            type="text"
                            class="w-full px-4 py-3 bg-gray-50 dark:bg-zinc-800 border-none rounded-xl text-sm focus:ring-2 focus:ring-blue-500 transition-all dark:text-white"
                            :placeholder="$t('map.drawing_name_placeholder')"
                            @keyup.enter="saveDrawing"
                        />
                    </div>

                    <div class="mt-8 flex gap-3">
                        <button
                            type="button"
                            class="flex-1 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-zinc-700 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-800 transition"
                            @click="showSaveDrawingModal = false"
                        >
                            {{ $t("common.close") }}
                        </button>
                        <button
                            type="button"
                            class="flex-1 px-4 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-semibold shadow-lg shadow-blue-500/25 hover:bg-blue-500 transition active:scale-95 disabled:opacity-50"
                            :disabled="!newDrawingName.trim()"
                            @click="saveDrawing"
                        >
                            {{ $t("common.save") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- load drawing modal -->
        <div
            v-if="showLoadDrawingModal"
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
        >
            <div
                class="bg-white dark:bg-zinc-900 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200"
            >
                <div class="p-6">
                    <div class="flex items-center justify-between mb-6">
                        <h2 class="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                            <MaterialDesignIcon icon-name="folder-open-outline" class="size-6 text-blue-500" />
                            {{ $t("map.load_drawing_title") }}
                        </h2>
                        <button class="text-gray-400 hover:text-gray-600" @click="showLoadDrawingModal = false">
                            <MaterialDesignIcon icon-name="close" class="size-6" />
                        </button>
                    </div>

                    <div v-if="isLoadingDrawings" class="py-12 flex flex-col items-center justify-center">
                        <MaterialDesignIcon icon-name="loading" class="size-10 animate-spin text-blue-500 mb-4" />
                        <span class="text-sm font-medium text-gray-500">{{ $t("map.loading_drawings") }}</span>
                    </div>

                    <div
                        v-else-if="savedDrawings.length === 0"
                        class="py-12 flex flex-col items-center justify-center text-center"
                    >
                        <div
                            class="size-16 bg-gray-100 dark:bg-zinc-800 rounded-full flex items-center justify-center mb-4"
                        >
                            <MaterialDesignIcon icon-name="folder-outline" class="size-8 text-gray-400" />
                        </div>
                        <h3 class="text-lg font-bold text-gray-900 dark:text-white">{{ $t("map.no_drawings") }}</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ $t("map.no_drawings_desc") }}</p>
                    </div>

                    <div v-else class="max-h-[400px] overflow-y-auto space-y-2 pr-2">
                        <div
                            v-for="drawing in savedDrawings"
                            :key="drawing.id"
                            class="group p-4 bg-gray-50 dark:bg-zinc-800/50 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-2xl border border-transparent hover:border-blue-200 dark:hover:border-blue-800 transition-all cursor-pointer flex items-center justify-between"
                            @click="loadDrawing(drawing)"
                        >
                            <div class="flex-1 min-w-0 mr-4">
                                <div class="font-bold text-gray-900 dark:text-white truncate">{{ drawing.name }}</div>
                                <div class="text-xs text-gray-500 dark:text-zinc-500 mt-0.5">
                                    {{ $t("map.saved_on") }} {{ new Date(drawing.updated_at).toLocaleString() }}
                                </div>
                            </div>
                            <button
                                class="p-2 text-gray-400 hover:text-red-500 transition-colors"
                                :title="$t('common.delete')"
                                @click.stop="deleteDrawing(drawing)"
                            >
                                <MaterialDesignIcon icon-name="trash-can-outline" class="size-5" />
                            </button>
                        </div>
                    </div>

                    <div class="mt-8 flex justify-end">
                        <button
                            type="button"
                            class="px-6 py-2.5 rounded-xl border border-gray-200 dark:border-zinc-700 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-zinc-800 transition"
                            @click="showLoadDrawingModal = false"
                        >
                            {{ $t("common.close") }}
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- mobile note modal -->
        <transition name="fade">
            <div
                v-if="showNoteModal"
                class="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
                @click.self="closeNoteEditor"
            >
                <div
                    class="bg-white dark:bg-zinc-900 w-full max-w-lg rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden animate-slide-up sm:animate-fade-in"
                >
                    <div class="p-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                        <h3 class="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                            <MaterialDesignIcon icon-name="note-edit" class="size-5 text-amber-500" />
                            Edit Note
                        </h3>
                        <button
                            class="p-2 text-gray-400 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-full transition-colors"
                            @click="closeNoteEditor"
                        >
                            <MaterialDesignIcon icon-name="close" class="size-5" />
                        </button>
                    </div>
                    <div class="p-4">
                        <textarea
                            v-model="noteText"
                            class="w-full h-40 p-4 text-base bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-none resize-none text-gray-900 dark:text-zinc-100"
                            placeholder="Type your note here..."
                            autofocus
                        ></textarea>
                    </div>
                    <div class="p-4 bg-gray-50 dark:bg-zinc-800/50 flex justify-between gap-3">
                        <button
                            class="flex-1 px-4 py-3 text-sm font-bold text-red-500 hover:bg-red-100 dark:hover:bg-red-900/20 rounded-xl transition-colors flex items-center justify-center gap-2"
                            @click="deleteNote"
                        >
                            <MaterialDesignIcon icon-name="trash-can-outline" class="size-5" />
                            Delete
                        </button>
                        <button
                            class="flex-[2] px-4 py-3 text-sm font-bold bg-amber-500 text-white hover:bg-amber-600 rounded-xl shadow-lg shadow-amber-500/30 transition-colors"
                            @click="saveNote"
                        >
                            Save Note
                        </button>
                    </div>
                </div>
            </div>
        </transition>
    </div>
</template>

<script>
import "ol/ol.css";
import Map from "ol/Map";
import View from "ol/View";
import TileLayer from "ol/layer/Tile";
import VectorLayer from "ol/layer/Vector";
import XYZ from "ol/source/XYZ";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { Style, Text, Fill, Stroke, Circle as CircleStyle } from "ol/style";
import { fromLonLat, toLonLat } from "ol/proj";
import { defaults as defaultControls } from "ol/control";
import DragBox from "ol/interaction/DragBox";
import Draw from "ol/interaction/Draw";
import Modify from "ol/interaction/Modify";
import Snap from "ol/interaction/Snap";
import { getArea, getLength } from "ol/sphere";
import { LineString, Polygon } from "ol/geom";
import { unByKey } from "ol/Observable";
import Overlay from "ol/Overlay";
import GeoJSON from "ol/format/GeoJSON";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToastUtils from "../../js/ToastUtils";
import TileCache from "../../js/TileCache";
import Toggle from "../forms/Toggle.vue";
import WebSocketConnection from "../../js/WebSocketConnection";

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
            peers: {},

            // telemetry
            telemetryList: [],
            markerSource: null,
            markerLayer: null,
            selectedMarker: null,

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
            isMapLoaded: false,

            // drawing tools
            draw: null,
            modify: null,
            snap: null,
            drawSource: null,
            drawLayer: null,
            drawType: null, // 'Point', 'LineString', 'Polygon', 'Circle' or null
            isDrawing: false,
            drawingTools: [
                { type: "Point", icon: "map-marker-plus" },
                { type: "Note", icon: "note-text-outline" },
                { type: "LineString", icon: "vector-line" },
                { type: "Polygon", icon: "vector-polygon" },
                { type: "Circle", icon: "circle-outline" },
                { type: "Export", icon: "crop-free" },
            ],

            // measurement
            isMeasuring: false,
            sketch: null,
            helpTooltipElement: null,
            helpTooltip: null,
            measureTooltipElement: null,
            measureTooltip: null,

            // drawing storage
            savedDrawings: [],

            // note editing
            editingFeature: null,
            noteText: "",
            hoveredNote: null,
            noteOverlay: null,
            showNoteModal: false,
            showSaveDrawingModal: false,
            newDrawingName: "",
            isLoadingDrawings: false,
            showLoadDrawingModal: false,
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
    watch: {
        showSaveDrawingModal(val) {
            if (val) {
                this.$nextTick(() => {
                    this.$refs.newDrawingNameInput?.focus();
                });
            }
        },
    },
    async mounted() {
        await this.getConfig();

        // Load persisted map state
        try {
            const savedState = await TileCache.getMapState("last_view");
            if (savedState) {
                this.currentCenter = savedState.center || [0, 0];
                this.currentZoom = savedState.zoom || 2;
                if (savedState.offlineEnabled !== undefined) this.offlineEnabled = savedState.offlineEnabled;
                if (savedState.tileServerUrl) this.tileServerUrl = savedState.tileServerUrl;
                if (savedState.telemetry) this.telemetryList = savedState.telemetry;

                // Temporarily store drawings to restore after map/source init
                this._persistedDrawings = savedState.drawings;
            }
        } catch (e) {
            console.warn("Failed to load map state from cache", e);
        }

        this.initMap();

        if (this.telemetryList.length > 0) {
            this.updateMarkers();
        }

        // Restore drawings if any
        if (this._persistedDrawings && this.drawSource) {
            try {
                const format = new GeoJSON();
                const features = format.readFeatures(this._persistedDrawings, {
                    dataProjection: "EPSG:4326",
                    featureProjection: "EPSG:3857",
                });
                this.drawSource.addFeatures(features);
            } catch (e) {
                console.error("Failed to restore persisted drawings", e);
            }
            delete this._persistedDrawings;
        }
        await this.checkOfflineMap();
        await this.loadMBTilesList();

        await this.fetchPeers();
        await this.fetchTelemetryMarkers();

        // Listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        // Check for query params to center map (overrides saved state)
        if (this.$route.query.lat && this.$route.query.lon) {
            const lat = parseFloat(this.$route.query.lat);
            const lon = parseFloat(this.$route.query.lon);
            const zoom = parseInt(this.$route.query.zoom || 15);

            if (!isNaN(lat) && !isNaN(lon)) {
                this.map.getView().setCenter(fromLonLat([lon, lat]));
                this.map.getView().setZoom(zoom);
            }
        }

        // Listen for moveend to update coordinates in UI and save state
        if (this.map) {
            this.map.on("moveend", () => {
                const view = this.map.getView();
                this.currentCenter = toLonLat(view.getCenter());
                this.currentZoom = view.getZoom();
                this.saveMapState();
            });
        }

        // Check if onboarding tooltip should be shown
        this.checkOnboardingTooltip();

        // Add click outside handler for search
        document.addEventListener("click", this.handleClickOutside);

        // Check screen size for mobile
        this.checkScreenSize();
        window.addEventListener("resize", this.checkScreenSize);

        // Update info every few seconds
        this.reloadInterval = setInterval(() => {
            this.fetchTelemetryMarkers();
        }, 30000);
    },
    beforeUnmount() {
        if (this.reloadInterval) clearInterval(this.reloadInterval);
        if (this.exportInterval) clearInterval(this.exportInterval);
        if (this.searchTimeout) clearTimeout(this.searchTimeout);
        document.removeEventListener("click", this.handleClickOutside);
        window.removeEventListener("resize", this.checkScreenSize);
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    methods: {
        async saveMapState() {
            try {
                // Serialize drawings
                let drawings = null;
                if (this.drawSource) {
                    const format = new GeoJSON();
                    drawings = format.writeFeatures(this.drawSource.getFeatures());
                }

                // Use JSON.parse/stringify to strip Vue Proxies and ensure plain objects/arrays
                // This prevents DataCloneError when saving to IndexedDB
                const state = JSON.parse(
                    JSON.stringify({
                        center: this.currentCenter,
                        zoom: this.currentZoom,
                        offlineEnabled: this.offlineEnabled,
                        tileServerUrl: this.tileServerUrl,
                        drawings: drawings,
                        telemetry: this.telemetryList,
                    })
                );
                await TileCache.setMapState("last_view", state);
            } catch (e) {
                console.error("Failed to save map state", e);
            }
        },
        async getConfig() {
            try {
                const response = await window.axios.get("/api/v1/config");
                this.config = response.data.config;
                this.offlineEnabled = this.config.map_offline_enabled;
                this.cachingEnabled =
                    this.config.map_tile_cache_enabled !== undefined ? this.config.map_tile_cache_enabled : true;
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
            } catch {
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
            } catch {
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
            } catch {
                ToastUtils.error("Failed to save directory");
            }
        },
        initMap() {
            // Patch canvas getContext to address performance warning
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function (type, attributes) {
                if (type === "2d") {
                    attributes = attributes || {};
                    attributes.willReadFrequently = true;
                }
                return originalGetContext.call(this, type, attributes);
            };

            const defaultLat = parseFloat(this.config?.map_default_lat || 0);
            const defaultLon = parseFloat(this.config?.map_default_lon || 0);
            const defaultZoom = parseInt(this.config?.map_default_zoom || 2);

            // Use saved state if available, otherwise use defaults
            const startCenter =
                this.currentCenter[0] !== 0 || this.currentCenter[1] !== 0
                    ? fromLonLat(this.currentCenter)
                    : fromLonLat([defaultLon, defaultLat]);
            const startZoom = this.currentZoom !== 2 ? this.currentZoom : defaultZoom;

            this.map = new Map({
                target: this.$refs.mapContainer,
                layers: [
                    new TileLayer({
                        source: this.getTileSource(),
                    }),
                ],
                view: new View({
                    center: startCenter,
                    zoom: startZoom,
                }),
                controls: defaultControls({
                    attribution: false,
                    rotate: false,
                }),
            });

            // setup drawing layer
            this.drawSource = new VectorSource();
            this.drawLayer = new VectorLayer({
                source: this.drawSource,
                style: (feature) => {
                    const type = feature.get("type");
                    if (type === "note") {
                        return new Style({
                            image: new CircleStyle({
                                radius: 10,
                                fill: new Fill({
                                    color: "#f59e0b",
                                }),
                                stroke: new Stroke({
                                    color: "#ffffff",
                                    width: 2,
                                }),
                            }),
                            // Use a simple circle for now as custom fonts in canvas can be tricky
                            // or use the built-in Text style if we are sure it works
                        });
                    }
                    return new Style({
                        fill: new Fill({
                            color: "rgba(59, 130, 246, 0.2)",
                        }),
                        stroke: new Stroke({
                            color: "#3b82f6",
                            width: 3,
                        }),
                        image: new CircleStyle({
                            radius: 7,
                            fill: new Fill({
                                color: "#3b82f6",
                            }),
                        }),
                    });
                },
                zIndex: 50,
            });
            this.map.addLayer(this.drawLayer);

            this.noteOverlay = new Overlay({
                element: this.$refs.noteOverlayElement,
                autoPan: {
                    animation: {
                        duration: 250,
                    },
                },
            });
            this.map.addOverlay(this.noteOverlay);

            this.modify = new Modify({ source: this.drawSource });
            this.modify.on("modifyend", () => this.saveMapState());
            this.map.addInteraction(this.modify);

            this.snap = new Snap({ source: this.drawSource });
            this.map.addInteraction(this.snap);

            // setup telemetry markers
            this.markerSource = new VectorSource();
            this.markerLayer = new VectorLayer({
                source: this.markerSource,
                zIndex: 100,
            });
            this.map.addLayer(this.markerLayer);

            this.map.on("pointermove", this.handleMapPointerMove);
            this.map.on("click", (evt) => {
                this.handleMapClick(evt);
                const feature = this.map.forEachFeatureAtPixel(evt.pixel, (f) => f);
                if (feature && feature.get("telemetry")) {
                    this.onMarkerClick(feature);
                } else {
                    this.selectedMarker = null;
                }
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
            this.isMapLoaded = true;
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
                    } catch {
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
                if (response.data && response.data.loaded !== false && Object.keys(response.data).length > 0) {
                    this.metadata = response.data;
                    this.hasOfflineMap = true;

                    if (this.offlineEnabled) {
                        this.updateMapSource();
                    }
                } else {
                    this.hasOfflineMap = false;
                    this.metadata = null;
                    if (this.offlineEnabled) {
                        this.offlineEnabled = false;
                        this.updateMapSource();
                    }
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

            // Find and replace the tile layer (first layer usually)
            // or just clear and re-add everything correctly
            layers.clear();

            // 1. Tile layer
            layers.push(
                new TileLayer({
                    source: this.getTileSource(),
                })
            );

            // 2. Draw layer
            if (this.drawLayer) {
                layers.push(this.drawLayer);
            }

            // 3. Marker layer
            if (this.markerLayer) {
                layers.push(this.markerLayer);
            }
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
            await this.saveMapState();

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
        async cancelActiveExport() {
            if (!this.exportId) {
                this.exportStatus = null;
                return;
            }
            try {
                await window.axios.delete(`/api/v1/map/export/${this.exportId}`);
                this.exportStatus = null;
                this.exportId = null;
                ToastUtils.success("Export cancelled");
            } catch {
                ToastUtils.error("Failed to cancel export");
            }
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
                await this.loadMBTilesList();
                await this.checkOfflineMap();
                this.updateMapSource();
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
                await this.saveMapState();
            } catch {
                ToastUtils.error("Failed to save tile server URL");
            }
        },
        setTileServer(type) {
            if (type === "osm") {
                this.tileServerUrl = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
            }
            this.saveTileServerUrl();
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
        async fetchPeers() {
            if (!window.axios) return;
            try {
                const response = await window.axios.get("/api/v1/lxmf/conversations");
                const peers = {};
                for (const conv of response.data.conversations) {
                    peers[conv.destination_hash] = conv;
                }
                this.peers = peers;
            } catch (e) {
                console.error("Failed to fetch peers", e);
            }
        },

        // Drawing methods
        toggleDraw(type) {
            if (!this.map) return;
            if (this.drawType === type && !this.isMeasuring) {
                this.stopDrawing();
                return;
            }

            this.stopDrawing();
            this.isMeasuring = false;
            this.drawType = type;

            this.draw = new Draw({
                source: this.drawSource,
                type: type === "Note" ? "Point" : type,
            });

            this.draw.on("drawstart", () => {
                this.isDrawing = true;
            });

            this.draw.on("drawend", (evt) => {
                this.isDrawing = false;
                const feature = evt.feature;
                if (type === "Note") {
                    feature.set("type", "note");
                    feature.set("note", "");
                    // Open edit box after a short delay to let the feature settle
                    setTimeout(() => {
                        this.startEditingNote(feature);
                    }, 200);
                }
                // Use setTimeout to ensure the feature is actually in the source before saving
                setTimeout(() => this.saveMapState(), 100);
            });

            this.map.addInteraction(this.draw);
        },

        startEditingNote(feature) {
            this.editingFeature = feature;
            this.noteText = feature.get("note") || "";
            if (this.isMobileScreen) {
                this.showNoteModal = true;
            } else {
                this.updateNoteOverlay();
            }
        },

        updateNoteOverlay() {
            if (!this.editingFeature || !this.map) return;
            const geometry = this.editingFeature.getGeometry();
            const coord = geometry.getCoordinates();
            this.noteOverlay.setPosition(coord);
        },

        saveNote() {
            if (this.editingFeature) {
                this.editingFeature.set("note", this.noteText);
                this.saveMapState();
            }
            this.closeNoteEditor();
        },

        cancelNote() {
            // If it's a new note (no text and just added), we might want to remove it
            // but for now just close
            this.closeNoteEditor();
        },

        closeNoteEditor() {
            this.editingFeature = null;
            this.noteText = "";
            this.showNoteModal = false;
            if (this.noteOverlay) {
                this.noteOverlay.setPosition(undefined);
            }
        },

        deleteNote() {
            if (this.editingFeature) {
                this.drawSource.removeFeature(this.editingFeature);
                this.saveMapState();
            }
            this.closeNoteEditor();
        },

        handleMapPointerMove(evt) {
            if (evt.dragging || this.isDrawing || this.isMeasuring) return;

            const pixel = this.map.getEventPixel(evt.originalEvent);
            const feature = this.map.forEachFeatureAtPixel(pixel, (f) => f, {
                layerFilter: (l) => l === this.drawLayer,
            });

            if (feature && feature.get("type") === "note") {
                this.hoveredNote = feature;
                this.map.getTargetElement().style.cursor = "pointer";
            } else {
                this.hoveredNote = null;
                this.map.getTargetElement().style.cursor = "";
            }
        },

        handleMapClick(evt) {
            if (this.isDrawing || this.isMeasuring) return;

            const pixel = this.map.getEventPixel(evt.originalEvent);
            const feature = this.map.forEachFeatureAtPixel(pixel, (f) => f, {
                layerFilter: (l) => l === this.drawLayer,
            });

            if (feature && feature.get("type") === "note") {
                this.startEditingNote(feature);
            } else {
                this.closeNoteEditor();
            }
        },

        stopDrawing() {
            if (this.draw) {
                this.map.removeInteraction(this.draw);
                this.draw = null;
            }
            this.drawType = null;
            this.isDrawing = false;
            this.stopMeasuring();
        },

        clearDrawings() {
            if (confirm("Clear all drawings from the map?")) {
                this.drawSource.clear();
                // clear tooltips if any
                const overlays = this.map.getOverlays().getArray();
                for (let i = overlays.length - 1; i >= 0; i--) {
                    const overlay = overlays[i];
                    if (overlay.get("isMeasureTooltip")) {
                        this.map.removeOverlay(overlay);
                    }
                }
                this.saveMapState();
            }
        },

        // Measurement methods
        toggleMeasure() {
            if (!this.map) return;
            if (this.isMeasuring) {
                this.stopMeasuring();
                this.drawType = null;
                return;
            }

            this.stopDrawing();
            this.isMeasuring = true;
            this.drawType = "LineString";

            this.createMeasureTooltip();
            this.createHelpTooltip();

            this.draw = new Draw({
                source: this.drawSource,
                type: "LineString",
                style: new Style({
                    fill: new Fill({
                        color: "rgba(255, 255, 255, 0.2)",
                    }),
                    stroke: new Stroke({
                        color: "rgba(0, 0, 0, 0.5)",
                        lineDash: [10, 10],
                        width: 2,
                    }),
                    image: new CircleStyle({
                        radius: 5,
                        stroke: new Stroke({
                            color: "rgba(0, 0, 0, 0.7)",
                        }),
                        fill: new Fill({
                            color: "rgba(255, 255, 255, 0.2)",
                        }),
                    }),
                }),
            });
            this.map.addInteraction(this.draw);

            let listener;
            this.draw.on("drawstart", (evt) => {
                this.sketch = evt.feature;
                let tooltipCoord = evt.coordinate;

                listener = this.sketch.getGeometry().on("change", (evt) => {
                    const geom = evt.target;
                    let output;
                    if (geom instanceof Polygon) {
                        output = this.formatArea(geom);
                        tooltipCoord = geom.getInteriorPoint().getCoordinates();
                    } else if (geom instanceof LineString) {
                        output = this.formatLength(geom);
                        tooltipCoord = geom.getLastCoordinate();
                    }
                    this.measureTooltipElement.innerHTML = output;
                    this.measureTooltip.setPosition(tooltipCoord);
                });
            });

            this.draw.on("drawend", () => {
                this.measureTooltipElement.className = "ol-tooltip ol-tooltip-static";
                this.measureTooltip.setOffset([0, -7]);
                this.sketch = null;
                this.measureTooltipElement = null;
                this.createMeasureTooltip();
                unByKey(listener);
            });

            this.map.on("pointermove", this.pointerMoveHandler);
        },

        stopMeasuring() {
            this.isMeasuring = false;
            if (this.draw && this.map) {
                this.map.removeInteraction(this.draw);
                this.draw = null;
            }
            if (this.map) {
                this.map.un("pointermove", this.pointerMoveHandler);
            }
            if (this.helpTooltip && this.map) {
                this.map.removeOverlay(this.helpTooltip);
                this.helpTooltip = null;
            }
            this.sketch = null;
        },

        pointerMoveHandler(evt) {
            if (evt.dragging) return;
            let helpMsg = "Click to start drawing";
            if (this.sketch) {
                helpMsg = "Click to continue drawing, double-click to finish";
            }
            this.helpTooltipElement.innerHTML = helpMsg;
            this.helpTooltip.setPosition(evt.coordinate);
            this.helpTooltipElement.classList.remove("hidden");
        },

        formatLength(line) {
            const length = getLength(line);
            let output;
            let imperialOutput;

            // Metric
            if (length > 100) {
                output = Math.round((length / 1000) * 100) / 100 + " km";
            } else {
                output = Math.round(length * 100) / 100 + " m";
            }

            // Imperial
            const feet = length * 3.28084;
            if (feet > 5280) {
                const miles = length * 0.000621371;
                imperialOutput = Math.round(miles * 100) / 100 + " mi";
            } else {
                imperialOutput = Math.round(feet * 100) / 100 + " ft";
            }

            return `${output}<br/><span class="text-[10px] opacity-80">${imperialOutput}</span>`;
        },

        formatArea(polygon) {
            const area = getArea(polygon);
            let output;
            let imperialOutput;

            // Metric
            if (area > 10000) {
                output = Math.round((area / 1000000) * 100) / 100 + " km²";
            } else {
                output = Math.round(area * 100) / 100 + " m²";
            }

            // Imperial
            const sqFeet = area * 10.7639;
            if (sqFeet > 27878400) {
                // > 1 sq mile
                const sqMiles = area * 0.000000386102;
                imperialOutput = Math.round(sqMiles * 100) / 100 + " mi²";
            } else {
                imperialOutput = Math.round(sqFeet * 100) / 100 + " ft²";
            }

            return `${output}<br/><span class="text-[10px] opacity-80">${imperialOutput}</span>`;
        },

        createHelpTooltip() {
            if (!this.map) return;
            if (this.helpTooltipElement && this.helpTooltipElement.parentNode) {
                this.helpTooltipElement.parentNode.removeChild(this.helpTooltipElement);
            }
            this.helpTooltipElement = document.createElement("div");
            this.helpTooltipElement.className = "ol-tooltip hidden";
            this.helpTooltip = new Overlay({
                element: this.helpTooltipElement,
                offset: [15, 0],
                positioning: "center-left",
            });
            this.map.addOverlay(this.helpTooltip);
        },

        createMeasureTooltip() {
            if (!this.map) return;
            this.measureTooltipElement = document.createElement("div");
            this.measureTooltipElement.className = "ol-tooltip ol-tooltip-measure";
            this.measureTooltip = new Overlay({
                element: this.measureTooltipElement,
                offset: [0, -15],
                positioning: "bottom-center",
                stopEvent: false,
                insertFirst: false,
            });
            this.measureTooltip.set("isMeasureTooltip", true);
            this.map.addOverlay(this.measureTooltip);
        },

        // Drawing storage methods
        async openLoadDrawingModal() {
            this.showLoadDrawingModal = true;
            this.isLoadingDrawings = true;
            try {
                const response = await window.axios.get("/api/v1/map/drawings");
                this.savedDrawings = response.data.drawings;
            } catch {
                ToastUtils.error("Failed to load drawings");
            } finally {
                this.isLoadingDrawings = false;
            }
        },

        async saveDrawing() {
            if (!this.newDrawingName.trim()) return;
            if (!this.drawSource) {
                ToastUtils.error("Map not initialized");
                return;
            }

            const format = new GeoJSON();
            const features = this.drawSource.getFeatures();
            const json = format.writeFeatures(features);

            try {
                await window.axios.post("/api/v1/map/drawings", {
                    name: this.newDrawingName,
                    data: json,
                });
                ToastUtils.success("Drawing saved");
                this.showSaveDrawingModal = false;
                this.newDrawingName = "";
            } catch {
                ToastUtils.error("Failed to save drawing");
            }
        },

        async loadDrawing(drawing) {
            const format = new GeoJSON();
            const features = format.readFeatures(drawing.data, {
                dataProjection: "EPSG:4326",
                featureProjection: "EPSG:3857",
            });
            this.drawSource.clear();
            this.drawSource.addFeatures(features);
            this.showLoadDrawingModal = false;
            ToastUtils.success(`Loaded "${drawing.name}"`);
        },

        async deleteDrawing(drawing) {
            if (!confirm(`Delete drawing "${drawing.name}"?`)) return;
            try {
                await window.axios.delete(`/api/v1/map/drawings/${drawing.id}`);
                this.savedDrawings = this.savedDrawings.filter((d) => d.id !== drawing.id);
                ToastUtils.success("Deleted");
            } catch {
                ToastUtils.error("Failed to delete");
            }
        },

        goToMyLocation() {
            // Priority 1: Use telemetry data if available for our own hash
            if (this.config && this.config.identity_hash) {
                const myTelemetry = this.telemetryList.find((t) => t.destination_hash === this.config.identity_hash);
                if (myTelemetry && myTelemetry.telemetry?.location) {
                    const loc = myTelemetry.telemetry.location;
                    this.map.getView().animate({
                        center: fromLonLat([loc.longitude, loc.latitude]),
                        zoom: 15,
                        duration: 1000,
                    });
                    return;
                }
            }

            // Priority 2: Use browser geolocation if online or available
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        this.map.getView().animate({
                            center: fromLonLat([pos.coords.longitude, pos.coords.latitude]),
                            zoom: 15,
                            duration: 1000,
                        });
                    },
                    (err) => {
                        console.error("Geolocation failed", err);
                        ToastUtils.warning("Could not determine your location");
                    }
                );
            } else {
                ToastUtils.warning("Geolocation is not supported by your browser");
            }
        },
        async fetchTelemetryMarkers() {
            if (!window.axios) return;
            try {
                const response = await window.axios.get("/api/v1/telemetry/peers");
                this.telemetryList = response.data.telemetry;
                this.updateMarkers();
            } catch (e) {
                console.error("Failed to fetch telemetry", e);
            }
        },
        updateMarkers() {
            if (!this.markerSource) return;
            this.markerSource.clear();

            for (const t of this.telemetryList) {
                const loc = t.telemetry?.location;
                if (!loc || loc.latitude === undefined || loc.longitude === undefined) continue;

                const peer = this.peers[t.destination_hash];
                const displayName = peer?.display_name || t.destination_hash.substring(0, 8);

                const feature = new Feature({
                    geometry: new Point(fromLonLat([loc.longitude, loc.latitude])),
                    telemetry: t,
                    peer: peer,
                });

                // Default style
                let iconColor = "#3b82f6";
                let bgColor = "#ffffff";

                if (peer?.lxmf_user_icon) {
                    iconColor = peer.lxmf_user_icon.foreground_colour || iconColor;
                    bgColor = peer.lxmf_user_icon.background_colour || bgColor;
                }

                feature.setStyle(
                    new Style({
                        image: new CircleStyle({
                            radius: 8,
                            fill: new Fill({ color: bgColor }),
                            stroke: new Stroke({ color: iconColor, width: 2 }),
                        }),
                        text: new Text({
                            text: displayName,
                            offsetY: -15,
                            font: "bold 11px sans-serif",
                            fill: new Fill({ color: "#000" }),
                            stroke: new Stroke({ color: "#fff", width: 2 }),
                        }),
                    })
                );

                this.markerSource.addFeature(feature);
            }
        },
        onMarkerClick(feature) {
            this.selectedMarker = {
                telemetry: feature.get("telemetry"),
                peer: feature.get("peer"),
            };
        },
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            if (json.type === "lxmf.telemetry") {
                // Find and update or add to telemetryList
                const index = this.telemetryList.findIndex((t) => t.destination_hash === json.destination_hash);
                const entry = {
                    destination_hash: json.destination_hash,
                    timestamp: json.timestamp,
                    telemetry: json.telemetry,
                    updated_at: new Date().toISOString(),
                };

                if (index !== -1) {
                    this.telemetryList.splice(index, 1, entry);
                } else {
                    this.telemetryList.push(entry);
                }
                this.updateMarkers();
            }
        },
        formatTimestamp(ts) {
            return new Date(ts * 1000).toLocaleString();
        },
        openChat(hash) {
            this.$router.push({
                name: "messages",
                params: { destinationHash: hash },
            });
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

:deep(.ol-tooltip) {
    position: relative;
    background: rgba(0, 0, 0, 0.7);
    border-radius: 4px;
    color: white;
    padding: 4px 8px;
    opacity: 0.7;
    font-size: 12px;
    cursor: default;
    user-select: none;
    text-align: center;
    line-height: 1.2;
}
:deep(.ol-tooltip-measure) {
    opacity: 1;
    font-weight: bold;
}
:deep(.ol-tooltip-static) {
    background-color: #3b82f6;
    color: white;
    border: 1px solid white;
}
:deep(.ol-tooltip-measure:before),
:deep(.ol-tooltip-static:before) {
    border-top: 6px solid rgba(0, 0, 0, 0.7);
    border-right: 6px solid transparent;
    border-left: 6px solid transparent;
    content: "";
    position: absolute;
    bottom: -6px;
    margin-left: -7px;
    left: 50%;
}
:deep(.ol-tooltip-static:before) {
    border-top-color: #3b82f6;
}

@keyframes slide-up {
    from {
        transform: translateY(100%);
    }
    to {
        transform: translateY(0);
    }
}

@keyframes fade-in {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}

.animate-slide-up {
    animation: slide-up 0.3s ease-out;
}

.animate-fade-in {
    animation: fade-in 0.3s ease-out;
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
