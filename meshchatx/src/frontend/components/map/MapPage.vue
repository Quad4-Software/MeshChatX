<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col h-full w-full bg-white dark:bg-zinc-950 overflow-hidden">
        <!-- header -->
        <div
            class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-0 px-3 py-2 sm:px-4 border-b border-gray-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm z-10 relative"
        >
            <div class="hidden sm:flex items-center min-w-0 gap-2">
                <v-icon icon="mdi-map" class="text-blue-500 dark:text-blue-400 shrink-0" size="24"></v-icon>
                <h1 class="text-lg sm:text-xl font-black text-gray-900 dark:text-white truncate">
                    {{ $t("map.title") }}
                </h1>
            </div>

            <div
                class="flex flex-wrap items-center gap-x-1.5 gap-y-2 sm:ml-auto sm:flex-nowrap sm:gap-2 sm:justify-end min-w-0"
            >
                <!-- offline/online toggle -->
                <div class="flex items-center bg-gray-100 dark:bg-zinc-800 rounded-lg p-0.5 sm:p-1 min-w-0 max-w-full">
                    <button
                        :class="
                            discoveredVisible
                                ? 'bg-white dark:bg-zinc-700 shadow-xs text-emerald-600 dark:text-emerald-400'
                                : 'text-gray-500 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-zinc-700'
                        "
                        class="p-1.5 sm:p-2 rounded-lg transition-colors shrink-0"
                        :title="discoveredVisible ? 'Hide Discovered Interfaces' : 'Show Discovered Interfaces'"
                        :aria-pressed="discoveredVisible"
                        @click="toggleDiscoveredNodes"
                    >
                        <MaterialDesignIcon icon-name="map-marker-radius" class="size-[18px] sm:size-5" />
                    </button>
                    <button
                        :class="
                            !offlineEnabled
                                ? 'bg-white dark:bg-zinc-700 shadow-xs text-blue-600 dark:text-blue-400'
                                : 'text-gray-500 dark:text-gray-300'
                        "
                        class="px-2 py-1 text-xs sm:px-3 sm:text-sm font-medium rounded-md transition-all shrink-0"
                        @click="toggleOffline(false)"
                    >
                        {{ $t("map.online_mode") }}
                    </button>
                    <button
                        :class="
                            offlineEnabled
                                ? 'bg-white dark:bg-zinc-700 shadow-xs text-blue-600 dark:text-blue-400'
                                : 'text-gray-500 dark:text-gray-300'
                        "
                        class="px-2 py-1 text-xs sm:px-3 sm:text-sm font-medium rounded-md transition-all shrink-0"
                        @click="toggleOffline(true)"
                    >
                        {{ $t("map.offline_mode") }}
                    </button>
                </div>

                <!-- upload: icon on mobile, full label from sm -->
                <button
                    type="button"
                    class="inline-flex items-center justify-center sm:gap-1 p-2 sm:px-3 sm:py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg shadow-xs transition-colors text-sm font-medium shrink-0"
                    :title="$t('map.upload_mbtiles')"
                    @click="$refs.fileInput.click()"
                >
                    <MaterialDesignIcon icon-name="upload" class="size-[18px] sm:size-4" />
                    <span class="hidden sm:inline">{{ $t("map.upload_mbtiles") }}</span>
                </button>
                <input ref="fileInput" type="file" accept=".mbtiles" class="hidden" @change="onFileSelected" />

                <button
                    v-if="!isPopoutMode"
                    type="button"
                    class="hidden sm:flex p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-full transition-colors shrink-0"
                    :title="$t('map.pop_out')"
                    @click="openMapPopout"
                >
                    <MaterialDesignIcon icon-name="open-in-new" class="size-[18px] sm:size-5" />
                </button>
                <!-- search toggle (mobile only) -->
                <button
                    v-if="!offlineEnabled"
                    type="button"
                    class="sm:hidden p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-full transition-colors shrink-0"
                    :title="$t('map.search_placeholder')"
                    @click="toggleMobileSearch"
                >
                    <MaterialDesignIcon :icon-name="isMobileSearchOpen ? 'close' : 'magnify'" class="size-[18px]" />
                </button>
                <!-- settings button -->
                <button
                    type="button"
                    class="p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-full transition-colors shrink-0"
                    @click="isSettingsOpen = !isSettingsOpen"
                >
                    <MaterialDesignIcon icon-name="cog" class="size-[18px] sm:size-5" />
                </button>
            </div>
        </div>

        <!-- map container (h-full so absolute overlays can use max-h-full / inset height) -->
        <div ref="mapViewOverlayRoot" class="relative flex-1 min-h-0 h-full">
            <MapDrawingToolbar
                ref="mapDrawingToolbar"
                :tools="drawingTools"
                :draw-type="drawType"
                :measuring="isMeasuring"
                :bearing-mode="isBearingMode"
                :bearing-from-gps="bearingFromGps"
                :export-mode="isExportMode"
                :selected-feature="selectedFeature"
                @toggle-draw="toggleDraw"
                @toggle-export="toggleExportMode"
                @toggle-measure="toggleMeasure"
                @toggle-bearing="toggleBearingMode"
                @bearing-from-here="startBearingFromMyLocation"
                @clear="clearDrawings"
                @edit-note="startEditingNote"
                @delete-feature="deleteSelectedFeature"
                @save="showSaveDrawingModal = true"
                @load="openLoadDrawingModal"
                @locate="goToMyLocation"
                @share-view="shareMapView"
                @ping-here="openPingModalFromMapCenter"
            />

            <MapBearingInstructions
                v-if="isBearingMode"
                :from-gps-active="bearingFromGps"
                :awaiting-second-tap="bearingFromGps || !!bearingFirstMapCoord"
                @use-my-location="startBearingFromMyLocation"
            />

            <div
                v-if="!offlineEnabled"
                v-show="!isMobileScreen || isMobileSearchOpen"
                ref="searchContainer"
                class="absolute left-4 right-4 top-[calc(0.5rem+2.75rem+0.5rem)] z-30 sm:top-2 sm:left-auto sm:right-4 sm:w-80 md:max-lg:w-72 lg:w-80"
            >
                <MapSearchBar
                    v-model="searchQuery"
                    :results="searchResults"
                    :error="searchError"
                    :searching="isSearching"
                    :show-results="isSearchFocused"
                    @input="onSearchInput"
                    @search="performSearch"
                    @clear="clearSearch"
                    @focus="isSearchFocused = true"
                    @select="selectSearchResult"
                />
            </div>

            <div
                ref="mapContainer"
                class="absolute inset-0"
                :class="{ 'cursor-crosshair': isExportMode }"
                @dragover.prevent="onMapDragOver"
                @dragleave="onMapDragLeave"
                @drop.prevent="onMapDrop"
            ></div>

            <!-- Drag-and-drop file indicator -->
            <div
                v-if="isMapDropTarget"
                class="absolute inset-0 z-40 flex flex-col items-center justify-center bg-blue-500/20 backdrop-blur-sm border-4 border-blue-500 border-dashed m-4 rounded-2xl pointer-events-none transition-opacity"
            >
                <MaterialDesignIcon icon-name="map-plus" class="w-16 h-16 text-blue-600 dark:text-blue-400 mb-4" />
                <h3 class="text-lg font-bold text-blue-700 dark:text-blue-300">{{ $t("map.drop_geo_files") }}</h3>
                <p class="text-sm text-blue-600 dark:text-blue-400 mt-1">{{ $t("map.drop_map_files_hint") }}</p>
            </div>

            <!-- note hover tooltip -->
            <div
                v-if="
                    hoveredFeature &&
                    (hoveredFeature.get('note') ||
                        (hoveredFeature.get('telemetry') && hoveredFeature.get('telemetry').note)) &&
                    !editingFeature
                "
                class="absolute pointer-events-none z-50 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-sm border border-gray-200 dark:border-zinc-700 rounded-lg shadow-xl p-2 text-sm text-gray-900 dark:text-zinc-100 max-w-xs transform -translate-x-1/2 -translate-y-full mb-4"
                :style="{
                    left: map.getPixelFromCoordinate(hoveredFeature.getGeometry().getCoordinates())[0] + 'px',
                    top: map.getPixelFromCoordinate(hoveredFeature.getGeometry().getCoordinates())[1] + 'px',
                }"
            >
                <div class="font-bold flex items-center gap-1 mb-1 text-amber-500">
                    <MaterialDesignIcon icon-name="note-text" class="size-4" />
                    <span>{{
                        hoveredFeature.get("telemetry") ? hoveredFeature.get("peer")?.display_name || "Peer" : "Note"
                    }}</span>
                </div>
                <div class="whitespace-pre-wrap wrap-break-word">
                    {{ hoveredFeature.get("note") || hoveredFeature.get("telemetry")?.note }}
                </div>
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
                        class="w-full h-24 p-2 text-sm bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-hidden resize-none text-gray-900 dark:text-zinc-100"
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
                            class="px-3 py-1.5 text-xs font-semibold bg-amber-500 text-white hover:bg-amber-600 rounded-lg shadow-xs transition-colors"
                            @click="saveNote"
                        >
                            Save
                        </button>
                    </div>
                </div>
            </div>

            <div ref="drawFeatureInfoElement" class="absolute z-45 pointer-events-none">
                <div
                    v-show="drawFeatureInfoPayload"
                    class="info-popup pointer-events-auto min-w-44 max-w-[min(18rem,calc(100vw-2rem))] rounded-xl border border-gray-200 dark:border-zinc-700 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-sm shadow-xl px-3 py-2.5 transform -translate-x-1/2 -translate-y-full mb-2 overflow-x-hidden"
                >
                    <template v-if="drawFeatureInfoPayload">
                        <div v-if="drawFeatureInfoPayload.iconSrc" class="flex justify-center mb-2">
                            <img
                                :src="drawFeatureInfoPayload.iconSrc"
                                alt=""
                                class="max-h-12 max-w-18 object-contain rounded-sm border border-gray-100 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-800/50"
                            />
                        </div>
                        <div
                            v-if="drawFeatureInfoPayload.name"
                            class="text-xs font-bold text-gray-900 dark:text-zinc-100 leading-snug mb-1"
                        >
                            {{ drawFeatureInfoPayload.name }}
                        </div>
                        <div
                            v-if="drawFeatureInfoPayload.description && !drawFeatureInfoPayload.descriptionIsHtml"
                            class="text-[11px] text-gray-600 dark:text-zinc-400 whitespace-pre-wrap wrap-break-word leading-snug"
                        >
                            {{ drawFeatureInfoPayload.description }}
                        </div>
                        <!-- eslint-disable vue/no-v-html -->
                        <div
                            v-else-if="drawFeatureDescriptionSanitized"
                            class="text-[11px] text-gray-600 dark:text-zinc-400 prose prose-sm dark:prose-invert max-w-none leading-snug [&_*]:!bg-transparent [&_*]:!text-inherit"
                            v-html="drawFeatureDescriptionSanitized"
                        ></div>
                        <!-- eslint-enable vue/no-v-html -->
                        <dl
                            v-if="drawFeatureInfoPayload.extended.length"
                            class="mt-2 space-y-1 border-t border-gray-100 dark:border-zinc-800 pt-2 overflow-hidden"
                        >
                            <template v-for="row in drawFeatureInfoPayload.extended" :key="row.key">
                                <div class="grid grid-cols-[minmax(0,40%)_1fr] gap-x-2 gap-y-0.5 text-[10px] min-w-0">
                                    <dt
                                        class="font-semibold text-gray-500 dark:text-zinc-500 truncate"
                                        :title="row.key"
                                    >
                                        {{ row.key }}
                                    </dt>
                                    <dd class="text-gray-800 dark:text-zinc-200 truncate m-0" :title="row.value">
                                        {{ row.value }}
                                    </dd>
                                </div>
                            </template>
                        </dl>
                    </template>
                </div>
            </div>

            <!-- context menu -->
            <ContextMenuPanel
                :show="showContextMenu"
                :x="contextMenuPos.x"
                :y="contextMenuPos.y"
                panel-class="z-120 overflow-hidden text-sm"
            >
                <template #header>
                    <div
                        class="px-3 py-2 font-semibold border-b border-gray-100 dark:border-zinc-800 text-gray-700 dark:text-zinc-200"
                    >
                        {{ contextMenuFeature ? "Feature actions" : "Map actions" }}
                    </div>
                </template>
                <ContextMenuItem v-if="contextMenuFeature" @click="contextSelectFeature">
                    <MaterialDesignIcon icon-name="cursor-default" class="size-4" />
                    Select / Move
                </ContextMenuItem>
                <ContextMenuItem v-if="contextMenuFeature" @click="contextAddNote">
                    <MaterialDesignIcon icon-name="note-edit" class="size-4" />
                    Add / Edit Note
                </ContextMenuItem>
                <ContextMenuItem
                    v-if="contextMenuFeature && !contextMenuFeature.get('telemetry')"
                    item-class="text-red-600 dark:text-red-400"
                    @click="contextDeleteFeature"
                >
                    <MaterialDesignIcon icon-name="delete" class="size-4" />
                    Delete
                </ContextMenuItem>
                <ContextMenuItem @click="contextCopyCoords">
                    <MaterialDesignIcon icon-name="crosshairs-gps" class="size-4" />
                    Copy coords
                </ContextMenuItem>
                <ContextMenuItem @click="contextPingHere">
                    <MaterialDesignIcon icon-name="send" class="size-4" />
                    {{ $t("map.ping_here") }}
                </ContextMenuItem>
                <ContextMenuItem v-if="!contextMenuFeature" @click="contextClearMap">
                    <MaterialDesignIcon icon-name="delete-sweep" class="size-4" />
                    Clear drawings
                </ContextMenuItem>
            </ContextMenuPanel>

            <!-- loading skeleton for map -->
            <div v-if="!isMapLoaded" class="absolute inset-0 z-0 bg-slate-100 dark:bg-zinc-900 animate-pulse">
                <div class="grid grid-cols-4 grid-rows-4 h-full w-full gap-1 p-1 opacity-20">
                    <div v-for="i in 16" :key="i" class="bg-slate-300 dark:bg-zinc-700 rounded-lg"></div>
                </div>
            </div>

            <MapMarkerPanel
                v-if="selectedMarker"
                :marker="selectedMarker"
                :mini-chat-open="isMiniChatOpen"
                @close="selectedMarker = null"
                @toggle-tracking="toggleTracking"
                @toggle-mini-chat="isMiniChatOpen = !isMiniChatOpen"
            />

            <MapClusterPanel
                v-if="selectedCluster && !selectedMarker"
                :cluster="selectedCluster"
                @close="closeClusterPanel"
                @select="selectClusterItem"
            />

            <MapExportInstructions
                v-if="isExportMode && !selectedBbox"
                :presets="exportRegionPresets"
                @select-preset="applyExportRegionPreset"
            />

            <MapExportConfigPanel
                v-if="isExportMode && selectedBbox"
                v-model:min-zoom="exportMinZoom"
                v-model:max-zoom="exportMaxZoom"
                :estimated-tiles="estimatedTiles"
                :exporting="isExporting"
                :tile-limit-exceeded="exportTileLimitExceeded"
                @cancel="cancelExport"
                @start="startExport"
            />

            <MapExportProgressPanel
                v-if="exportStatus"
                :status="exportStatus"
                :export-id="exportId"
                @dismiss="exportStatus = null"
                @cancel="cancelActiveExport"
                @show-offline-maps="isSettingsOpen = true"
            />

            <MapLoadingOverlay v-if="isUploading" />

            <div
                v-if="showMapPingModal"
                class="fixed inset-0 z-200 flex items-center justify-center bg-black/40 p-4"
                role="dialog"
                aria-modal="true"
                @click.self="showMapPingModal = false"
            >
                <div
                    class="bg-white dark:bg-zinc-900 rounded-xl shadow-2xl max-w-md w-full p-4 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100"
                >
                    <div class="flex items-center justify-between mb-3">
                        <h3 class="font-bold text-lg">{{ $t("map.ping_modal_title") }}</h3>
                        <button
                            type="button"
                            class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-800"
                            @click="showMapPingModal = false"
                        >
                            <MaterialDesignIcon icon-name="close" class="size-5" />
                        </button>
                    </div>
                    <p class="text-xs text-gray-500 dark:text-zinc-400 mb-2">
                        {{ mapPingSummary }}
                    </p>
                    <label class="block text-[10px] font-bold text-gray-400 uppercase mb-1">{{
                        $t("map.ping_destination")
                    }}</label>
                    <select
                        v-model="pingDestinationHash"
                        class="w-full mb-2 bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg px-3 py-2 text-sm"
                    >
                        <option value="">{{ $t("map.ping_pick_conversation") }}</option>
                        <option v-for="p in conversationOptions" :key="p.hash" :value="p.hash">
                            {{ p.label }}
                        </option>
                    </select>
                    <button
                        type="button"
                        class="w-full py-2 mb-3 text-sm font-bold bg-blue-500 hover:bg-blue-600 text-white rounded-lg"
                        :disabled="!pingDestinationHash"
                        @click="sendMapPing"
                    >
                        {{ $t("map.ping_send") }}
                    </button>
                    <button
                        type="button"
                        class="w-full py-2 text-sm font-semibold bg-gray-100 dark:bg-zinc-800 rounded-lg"
                        @click="showMapPingModal = false"
                    >
                        {{ $t("common.cancel") }}
                    </button>
                </div>
            </div>

            <!-- scale line: bottom-right so it never stacks over the lat/lon readout (bottom-left); hidden on small screens -->
            <div
                v-show="!isMobileScreen"
                ref="scaleLineMount"
                class="ol-scale-line-host absolute z-10 bottom-4 right-4 sm:bottom-4 max-sm:bottom-22 pointer-events-auto min-w-[120px] max-w-[min(55vw,14rem)]"
                :class="{ 'ol-scale-line-host--dark-basemap': isDarkRasterBasemap }"
            ></div>

            <!-- map info overlay (north + metadata + coords) -->
            <div
                class="absolute bottom-4 left-4 z-10 flex flex-col gap-2 pointer-events-none max-w-[min(100vw-2rem,22rem)]"
            >
                <div
                    class="flex flex-col items-center justify-end text-gray-800 dark:text-zinc-100 bg-white/80 dark:bg-zinc-900/80 border border-gray-200 dark:border-zinc-800 rounded-lg px-2 py-1 shadow-xs pointer-events-auto w-fit"
                    :title="$t('map.north_up')"
                >
                    <div
                        class="flex flex-col items-center justify-end origin-center"
                        :style="northIndicatorRotateStyle"
                    >
                        <span class="text-[10px] font-black leading-none">N</span>
                        <MaterialDesignIcon
                            icon-name="navigation"
                            class="size-5 text-blue-600 dark:text-blue-400 -mb-0.5"
                        />
                    </div>
                </div>
                <div
                    v-if="metadata && metadata.name && !metadata.name.startsWith('Map Export')"
                    class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm border border-gray-200 dark:border-zinc-800 p-2 rounded-lg text-xs text-gray-600 dark:text-zinc-400 pointer-events-auto shadow-xs"
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
                    class="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm border border-gray-200 dark:border-zinc-800 p-2 rounded-lg text-[10px] text-gray-600 dark:text-zinc-400 pointer-events-auto shadow-xs flex flex-col space-y-0.5"
                >
                    <div class="flex justify-between space-x-4">
                        <span class="opacity-50 uppercase tracking-tighter">Lat</span>
                        <span class="text-gray-900 dark:text-zinc-100 tabular-nums">{{
                            displayCoords[1].toFixed(6)
                        }}</span>
                    </div>
                    <div class="flex justify-between space-x-4">
                        <span class="opacity-50 uppercase tracking-tighter">Lon</span>
                        <span class="text-gray-900 dark:text-zinc-100 tabular-nums">{{
                            displayCoords[0].toFixed(6)
                        }}</span>
                    </div>
                </div>
            </div>

            <!-- controls overlay -->
            <div
                v-if="isSettingsOpen"
                ref="settingsPanel"
                class="absolute z-20 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xs rounded-xl shadow-2xl border border-gray-200 dark:border-zinc-800 overflow-hidden flex flex-col min-h-0 animate-in fade-in zoom-in-95 duration-200"
                :class="
                    settingsPanelPos
                        ? 'w-96 max-w-[min(100vw-2rem,28rem)] max-h-full'
                        : isMobileScreen
                          ? 'left-2 right-2 top-14 bottom-2 w-auto max-w-none'
                          : 'top-14 right-4 w-96 max-w-[min(100vw-2rem,28rem)] max-h-full'
                "
                :style="
                    settingsPanelPos
                        ? { left: `${settingsPanelPos.left}px`, top: `${settingsPanelPos.top}px` }
                        : undefined
                "
            >
                <div
                    ref="settingsPanelHeader"
                    class="p-3 border-b border-gray-200 dark:border-zinc-800 flex items-center justify-between shrink-0 bg-gray-50/50 dark:bg-zinc-800/50 touch-none select-none cursor-grab active:cursor-grabbing"
                    @pointerdown="onSettingsPanelPointerDown"
                    @pointermove="onSettingsPanelPointerMove"
                    @pointerup="onSettingsPanelPointerUp"
                    @pointercancel="onSettingsPanelPointerUp"
                >
                    <div class="flex items-center space-x-2">
                        <MaterialDesignIcon icon-name="cog" class="size-4 text-gray-500 dark:text-gray-300" />
                        <h3 class="font-bold text-gray-900 dark:text-zinc-100 text-xs uppercase tracking-widest">
                            {{ $t("app.settings") }}
                        </h3>
                    </div>
                    <button
                        type="button"
                        class="p-1 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded-lg transition-colors text-gray-500 dark:text-gray-300 cursor-pointer"
                        @pointerdown.stop
                        @click="isSettingsOpen = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-4" />
                    </button>
                </div>

                <div class="p-3 space-y-4 overflow-y-auto scrollbar-thin flex-1">
                    <!-- Quick Actions -->
                    <div class="grid grid-cols-2 gap-2">
                        <button
                            class="flex items-center justify-center space-x-1.5 px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight shadow-xs active:scale-95"
                            @click="setAsDefaultView"
                        >
                            <MaterialDesignIcon icon-name="pin" class="size-3" />
                            <span>Set Default</span>
                        </button>

                        <button
                            class="flex items-center justify-center space-x-1.5 px-2 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-gray-700 dark:text-zinc-300 rounded-lg transition-all text-[10px] font-bold uppercase tracking-tight active:scale-95"
                            @click="clearCache"
                        >
                            <MaterialDesignIcon icon-name="trash-can-outline" class="size-3" />
                            <span>Clear Cache</span>
                        </button>
                    </div>

                    <MapVectorExchangePanel
                        :disabled="!drawSource"
                        :has-features="hasVectorDrawFeatures"
                        @import-features="onVectorExchangeImport"
                        @import-error="onVectorExchangeImportError"
                        @export-geojson="exportVectorGeoJson"
                        @export-kml="exportVectorKml"
                        @export-kmz="exportVectorKmz"
                    />

                    <!-- Map Style Presets -->
                    <div v-if="!offlineEnabled" class="space-y-2">
                        <div class="flex items-center justify-between">
                            <label class="text-[10px] font-bold text-gray-400 uppercase tracking-widest"
                                >Map Styles</label
                            >
                            <div class="h-px flex-1 bg-gray-100 dark:bg-zinc-800 ml-3"></div>
                        </div>
                        <div class="grid grid-cols-5 gap-1">
                            <button
                                v-for="style in [
                                    { id: 'openfreemap', label: 'OFM' },
                                    { id: 'osm', label: 'OSM' },
                                    { id: 'carto-dark', label: 'Dark' },
                                    { id: 'carto-voyager', label: 'Voy' },
                                    { id: 'carto-light', label: 'Lite' },
                                ]"
                                :key="style.id"
                                class="py-1.5 text-[8px] font-bold uppercase rounded-md transition-all border leading-tight"
                                :class="
                                    (style.id === 'openfreemap' &&
                                        tileServerUrl.includes('tiles.openfreemap.org/styles/')) ||
                                    (style.id === 'osm' && tileServerUrl.includes('openstreetmap.org')) ||
                                    (style.id === 'carto-dark' &&
                                        tileServerUrl.includes('basemaps.cartocdn.com/dark_all')) ||
                                    (style.id === 'carto-voyager' && tileServerUrl.includes('rastertiles/voyager')) ||
                                    (style.id === 'carto-light' &&
                                        tileServerUrl.includes('basemaps.cartocdn.com/light_all'))
                                        ? 'bg-blue-500 border-blue-600 text-white shadow-xs ring-2 ring-blue-500/20'
                                        : 'bg-white dark:bg-zinc-900 border-gray-200 dark:border-zinc-800 text-gray-500 dark:text-zinc-400 hover:bg-gray-50 dark:hover:bg-zinc-800'
                                "
                                @click="setTileServer(style.id)"
                            >
                                {{ style.label }}
                            </button>
                        </div>

                        <div class="space-y-1">
                            <label
                                class="text-[9px] font-bold text-gray-500 dark:text-zinc-500 uppercase flex items-center"
                            >
                                <MaterialDesignIcon icon-name="link-variant" class="size-3 mr-1" />
                                Tile Server URL
                            </label>
                            <input
                                v-model="tileServerUrl"
                                type="text"
                                class="w-full bg-gray-50/50 dark:bg-zinc-950/50 border border-gray-200 dark:border-zinc-800 rounded-lg px-2 py-1.5 text-[10px] dark:text-zinc-100 font-mono focus:ring-1 focus:ring-blue-500 transition-all outline-hidden"
                                :placeholder="$t('map.tile_server_url_placeholder')"
                                @blur="saveTileServerUrl"
                            />
                        </div>

                        <div class="space-y-1">
                            <label
                                class="text-[9px] font-bold text-gray-500 dark:text-zinc-500 uppercase flex items-center"
                            >
                                <MaterialDesignIcon icon-name="magnify" class="size-3 mr-1" />
                                Geocoder API
                            </label>
                            <input
                                v-model="nominatimApiUrl"
                                type="text"
                                class="w-full bg-gray-50/50 dark:bg-zinc-950/50 border border-gray-200 dark:border-zinc-800 rounded-lg px-2 py-1.5 text-[10px] dark:text-zinc-100 font-mono focus:ring-1 focus:ring-blue-500 transition-all outline-hidden"
                                :placeholder="$t('map.nominatim_api_url_placeholder')"
                                @blur="saveNominatimApiUrl"
                            />
                        </div>
                    </div>

                    <!-- Live Tracking -->
                    <div class="space-y-2">
                        <div class="flex items-center justify-between">
                            <label class="text-[10px] font-bold text-gray-400 uppercase tracking-widest"
                                >Live Tracking</label
                            >
                            <div class="h-px flex-1 bg-gray-100 dark:bg-zinc-800 ml-3"></div>
                        </div>
                        <div v-if="trackedPeers.length === 0" class="text-[10px] text-gray-500 italic px-2">
                            No peers currently being tracked.
                        </div>
                        <div v-else class="space-y-1">
                            <div
                                v-for="peer in trackedPeers"
                                :key="peer.destination_hash"
                                class="flex items-center justify-between p-2 bg-gray-50 dark:bg-zinc-800/50 rounded-lg group"
                            >
                                <div class="flex flex-col min-w-0">
                                    <span class="text-[10px] font-bold text-gray-900 dark:text-zinc-100 truncate">
                                        {{
                                            peers[peer.destination_hash]?.display_name ||
                                            peer.destination_hash.substring(0, 8)
                                        }}
                                    </span>
                                    <span class="text-[8px] text-gray-500 font-mono">
                                        {{ peer.destination_hash }}
                                    </span>
                                </div>
                                <button
                                    class="p-1 text-red-400 hover:text-red-600 transition-colors opacity-0 group-hover:opacity-100"
                                    title="Stop Tracking"
                                    @click="toggleTracking(peer.destination_hash)"
                                >
                                    <MaterialDesignIcon icon-name="close-circle" class="size-3" />
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- MBTiles Section -->
                    <div class="space-y-3 pt-1">
                        <div class="flex items-center justify-between">
                            <label class="text-[10px] font-bold text-gray-400 uppercase tracking-widest"
                                >Offline Maps</label
                            >
                            <div class="h-px flex-1 bg-gray-100 dark:bg-zinc-800 ml-3"></div>
                        </div>

                        <div
                            class="flex items-center justify-between py-1 px-2 bg-gray-50/50 dark:bg-zinc-800/30 rounded-lg border border-gray-100 dark:border-zinc-800"
                        >
                            <span
                                class="text-[10px] font-bold text-gray-600 dark:text-zinc-400 uppercase tracking-tight"
                                >Tile Caching</span
                            >
                            <Toggle :model-value="cachingEnabled" @update:model-value="toggleCaching" />
                        </div>

                        <div class="space-y-1">
                            <label
                                class="text-[9px] font-bold text-gray-500 dark:text-zinc-500 uppercase flex items-center"
                            >
                                <MaterialDesignIcon icon-name="folder-outline" class="size-3 mr-1" />
                                Storage Path
                            </label>
                            <input
                                v-model="mbtilesDir"
                                type="text"
                                class="w-full bg-gray-50/50 dark:bg-zinc-950/50 border border-gray-200 dark:border-zinc-800 rounded-lg px-2 py-1.5 text-[10px] dark:text-zinc-100 font-mono focus:ring-1 focus:ring-blue-500 transition-all outline-hidden"
                                placeholder="Default storage"
                                @blur="saveMBTilesDir"
                            />
                        </div>

                        <div v-if="mbtilesList.length > 0" class="space-y-1.5">
                            <div class="flex items-center space-x-2 pb-0.5">
                                <MaterialDesignIcon icon-name="database-outline" class="size-3 text-blue-500" />
                                <span
                                    class="text-[10px] font-bold text-gray-700 dark:text-zinc-300 uppercase tracking-tight"
                                    >MBTiles Library</span
                                >
                            </div>
                            <div class="space-y-1 max-h-40 overflow-y-auto pr-1 scrollbar-thin">
                                <div
                                    v-for="file in mbtilesList"
                                    :key="file.name"
                                    class="flex items-center justify-between p-2 rounded-xl"
                                    :class="
                                        file.is_active
                                            ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50'
                                            : 'bg-white dark:bg-zinc-900 border border-gray-100 dark:border-zinc-800 shadow-xs'
                                    "
                                >
                                    <div class="flex flex-col min-w-0 flex-1 mr-2">
                                        <span
                                            class="text-[10px] font-bold text-gray-900 dark:text-zinc-100 truncate leading-none mb-1"
                                            :title="file.name"
                                            >{{ file.name }}</span
                                        >
                                        <div class="flex items-center space-x-2">
                                            <span class="text-[8px] font-black text-gray-400 uppercase tabular-nums"
                                                >{{ (file.size / 1024 / 1024).toFixed(1) }} MB</span
                                            >
                                            <span
                                                v-if="file.is_active"
                                                class="text-[8px] font-black text-blue-500 uppercase"
                                                >Active</span
                                            >
                                        </div>
                                    </div>
                                    <div class="flex items-center space-x-1">
                                        <button
                                            v-if="!file.is_active"
                                            class="p-1.5 text-blue-500 hover:bg-blue-500 hover:text-white rounded-lg transition-all active:scale-90"
                                            title="Set as active"
                                            @click="setActiveMBTiles(file.name)"
                                        >
                                            <MaterialDesignIcon icon-name="check" class="size-3.5" />
                                        </button>
                                        <button
                                            class="p-1.5 text-red-500 hover:bg-red-500 hover:text-white rounded-lg transition-all active:scale-90"
                                            title="Delete"
                                            @click="deleteMBTiles(file.name)"
                                        >
                                            <MaterialDesignIcon icon-name="delete-outline" class="size-3.5" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Footer Stats -->
                <div
                    class="p-2.5 bg-gray-50 dark:bg-zinc-800/50 border-t border-gray-200 dark:border-zinc-800 shrink-0"
                >
                    <div class="grid grid-cols-3 gap-2">
                        <div class="flex flex-col items-center">
                            <span class="text-[8px] font-black text-gray-400 uppercase tracking-tighter mb-0.5"
                                >Zoom</span
                            >
                            <span
                                class="text-[10px] font-bold text-gray-700 dark:text-zinc-300 leading-none tabular-nums"
                                >{{ currentZoom.toFixed(1) }}</span
                            >
                        </div>
                        <div class="flex flex-col items-center border-x border-gray-200 dark:border-zinc-700">
                            <span class="text-[8px] font-black text-gray-400 uppercase tracking-tighter mb-0.5"
                                >Lat</span
                            >
                            <span
                                class="text-[10px] font-bold text-gray-700 dark:text-zinc-300 leading-none tabular-nums"
                                >{{ displayCoords[1].toFixed(4) }}</span
                            >
                        </div>
                        <div class="flex flex-col items-center">
                            <span class="text-[8px] font-black text-gray-400 uppercase tracking-tighter mb-0.5"
                                >Lon</span
                            >
                            <span
                                class="text-[10px] font-bold text-gray-700 dark:text-zinc-300 leading-none tabular-nums"
                                >{{ displayCoords[0].toFixed(4) }}</span
                            >
                        </div>
                    </div>
                </div>
            </div>

            <div
                v-if="!offlineEnabled && showTileConnectivityBanner"
                class="absolute top-14 left-1/2 -translate-x-1/2 z-30 w-full max-w-md px-4 animate-in fade-in slide-in-from-top-4 duration-500"
            >
                <div
                    class="rounded-xl shadow-2xl p-4 flex items-start gap-3 border border-zinc-700/80 bg-zinc-900 text-zinc-100 dark:border-zinc-600 dark:bg-zinc-950"
                >
                    <MaterialDesignIcon icon-name="wifi-off" class="size-6 shrink-0 mt-0.5 text-amber-400" />
                    <div class="flex-1 min-w-0 space-y-2">
                        <p class="text-sm font-semibold leading-snug text-white">
                            {{ $t("map.tile_connectivity_title") }}
                        </p>
                        <p class="text-xs leading-relaxed text-zinc-300">
                            {{ $t("map.tile_connectivity_body") }}
                        </p>
                        <div class="flex flex-wrap gap-2 pt-1">
                            <button
                                type="button"
                                class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
                                @click="retryMapTiles"
                            >
                                {{ $t("map.tile_connectivity_retry") }}
                            </button>
                            <button
                                v-if="hasOfflineMap"
                                type="button"
                                class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-700 hover:bg-zinc-600 text-white transition-colors"
                                @click="switchToOfflineFromTileBanner"
                            >
                                {{ $t("map.tile_connectivity_use_offline") }}
                            </button>
                            <button
                                type="button"
                                class="px-3 py-1.5 rounded-lg text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition-colors"
                                @click="dismissTileConnectivityBanner"
                            >
                                {{ $t("map.tile_connectivity_dismiss") }}
                            </button>
                            <button
                                type="button"
                                class="px-3 py-1.5 rounded-lg text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition-colors"
                                @click="
                                    dismissTileConnectivityBanner();
                                    isSettingsOpen = true;
                                "
                            >
                                {{ $t("map.settings") }}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- onboarding tooltip -->
            <div
                v-if="showOnboardingTooltip"
                class="fixed inset-0 z-100 pointer-events-none"
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
        </div>

        <!-- save drawing modal -->
        <div
            v-if="showSaveDrawingModal"
            class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs"
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
            class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs"
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
                class="fixed inset-0 z-100 flex items-end sm:items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
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
                            class="w-full h-40 p-4 text-base bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-transparent outline-hidden resize-none text-gray-900 dark:text-zinc-100"
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
                            class="flex-2 px-4 py-3 text-sm font-bold bg-amber-500 text-white hover:bg-amber-600 rounded-xl shadow-lg shadow-amber-500/30 transition-colors"
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
import { markRaw } from "vue";
import "ol/ol.css";
import "../../js/mapVectorWebFonts.js";
import { apply as applyMapboxStyle } from "ol-mapbox-style";
import Map from "ol/Map";
import View from "ol/View";
import LayerGroup from "ol/layer/Group";
import TileLayer from "ol/layer/Tile";
import VectorLayer from "ol/layer/Vector";
import XYZ from "ol/source/XYZ";
import TileState from "ol/TileState";
import VectorSource from "ol/source/Vector";
import Feature from "ol/Feature";
import Point from "ol/geom/Point";
import { getMdiIconPath } from "../../js/mdiIconNames.js";
import { Style, Text, Fill, Stroke, Circle as CircleStyle, Icon } from "ol/style";
import { shared as olIconCache } from "ol/style/IconImageCache";
import { fromLonLat, toLonLat } from "ol/proj";
import { defaults as defaultControls } from "ol/control";
import ScaleLine from "ol/control/ScaleLine";
import DragBox from "ol/interaction/DragBox";
import Draw from "ol/interaction/Draw";
import Modify from "ol/interaction/Modify";
import Snap from "ol/interaction/Snap";
import Select from "ol/interaction/Select";
import Translate from "ol/interaction/Translate";
import { getArea, getLength } from "ol/sphere";
import { LineString, Polygon, Circle } from "ol/geom";
import { fromCircle } from "ol/geom/Polygon";
import { unByKey } from "ol/Observable";
import Overlay from "ol/Overlay";
import GeoJSON from "ol/format/GeoJSON";
import {
    extend as extendExtent,
    extendCoordinate,
    createEmpty as createEmptyExtent,
    isEmpty as isExtentEmpty,
} from "ol/extent";
import {
    extentDiagonal as computeExtentDiagonal,
    buildClusterItems as buildClusterItemsHelper,
} from "./internal/clusterUtils.js";
import { getDiscoveredIconName as getDiscoveredIconNameHelper } from "./internal/discoveredIcons.js";
import {
    dedupeDiscoveredMapNodes as dedupeDiscoveredMapNodesHelper,
    dedupeTelemetryMarkersForMap as dedupeTelemetryMarkersForMapHelper,
} from "./internal/mapDedupe.js";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ContextMenuItem from "../contextmenu/ContextMenuItem.vue";
import ContextMenuPanel from "../contextmenu/ContextMenuPanel.vue";
import DOMPurify from "dompurify";
import ToastUtils from "../../js/ToastUtils";
import TileCache from "../../js/TileCache";
import { detectRasterTileProviderId, nextRasterTileProviderId, TILE_PROVIDER_URLS } from "../../js/mapTileProviders.js";
import {
    fetchTileBlobWithRetry,
    fetchJsonWithRetry,
    buildNominatimSearchUrl,
    NOMINATIM_FETCH_TIMEOUT_MS,
    NOMINATIM_FETCH_RETRIES,
    NOMINATIM_FETCH_RETRY_BASE_DELAY_MS,
} from "../../js/mapTileNetwork";
import Toggle from "../forms/Toggle.vue";
import WebSocketConnection from "../../js/WebSocketConnection";
import MapClusterPanel from "./internal/MapClusterPanel.vue";
import MapMarkerPanel from "./internal/MapMarkerPanel.vue";
import MapDrawingToolbar from "./internal/MapDrawingToolbar.vue";
import MapBearingInstructions from "./internal/MapBearingInstructions.vue";
import MapSearchBar from "./internal/MapSearchBar.vue";
import MapExportInstructions from "./internal/MapExportInstructions.vue";
import MapExportConfigPanel from "./internal/MapExportConfigPanel.vue";
import MapExportProgressPanel from "./internal/MapExportProgressPanel.vue";
import MapLoadingOverlay from "./internal/MapLoadingOverlay.vue";
import MapVectorExchangePanel from "./internal/MapVectorExchangePanel.vue";
import { buildMeshchatMapUri, buildWebHashMapUrl } from "../../js/mapLinkUtils.js";
import { readGeoJsonToFeatures, writeFeaturesToGeoJson } from "../../js/mapExchange/geoJsonCodec.js";
import { readKmlToFeatures, writeFeaturesToKml } from "../../js/mapExchange/kmlCodec.js";
import { readKmzToFeatures, writeFeaturesToKmzBlob } from "../../js/mapExchange/kmzCodec.js";
import { getDrawFeatureMetadataPayload, getFeatureAnchorCoordinate } from "../../js/mapExchange/metadataUtils.js";
import { styleFromMcxProperties } from "../../js/mapExchange/styleFromProperties.js";
import { computeSegmentMetrics, buildBearingOverlayHtml, buildBearingLiveTooltipHtml } from "../../js/mapGeodesy.js";

const OPENFREEMAP_DEFAULT_STYLE = "https://tiles.openfreemap.org/styles/bright";
const DEFAULT_OSM_RASTER = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const OFFLINE_MB_TILES_URL = "/api/v1/map/tiles/{z}/{x}/{y}.png";
const OFFLINE_TRANSPARENT_TILE_PNG =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

const MAX_EXPORT_TILES = 200000;

const WORLD_MBTILES_BBOX = [-180, -85.051129, 180, 85.051129];

const MAP_FEATURE_HIT_TOLERANCE = 15;

export default {
    name: "MapPage",
    components: {
        ContextMenuItem,
        ContextMenuPanel,
        MaterialDesignIcon,
        Toggle,
        MapClusterPanel,
        MapMarkerPanel,
        MapDrawingToolbar,
        MapBearingInstructions,
        MapSearchBar,
        MapExportInstructions,
        MapExportConfigPanel,
        MapExportProgressPanel,
        MapLoadingOverlay,
        MapVectorExchangePanel,
    },
    data() {
        return {
            map: null,
            offlineEnabled: false,
            hasOfflineMap: false,
            metadata: null,
            isUploading: false,
            isMapDropTarget: false,
            isSettingsOpen: false,
            settingsPanelPos: null,
            settingsPanelDrag: null,
            currentCenter: [0, 0],
            currentZoom: 2,
            cursorCoords: null,
            config: null,
            peers: {},

            // telemetry
            telemetryList: [],
            markerSource: null,
            markerLayer: null,
            historySource: null,
            historyLayer: null,
            selectedMarker: null,
            selectedCluster: null,
            isMiniChatOpen: false,
            queryMarker: null,
            discoveredMarkers: [],
            discoveredVisible: false,

            // caching
            cachingEnabled: true,

            // tile server
            tileServerUrl: DEFAULT_OSM_RASTER,

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
            isMobileSearchOpen: false,
            mapViewRotationRad: 0,

            // MBTiles management
            mbtilesList: [],
            mbtilesDir: "",
            isMapLoaded: false,
            tileErrorCount: 0,
            tileProvidersAttempted: [],
            tileFailoverInProgress: false,
            showTileConnectivityBanner: false,
            tileConnectivityBannerTimer: null,

            // drawing tools
            draw: null,
            modify: null,
            snap: null,
            drawSource: null,
            drawLayer: null,
            drawType: null, // 'Point', 'LineString', 'Polygon', 'Circle' or null
            isDrawing: false,
            drawingTools: [
                { type: "Select", icon: "cursor-default" },
                { type: "Point", icon: "map-marker-plus" },
                { type: "LineString", icon: "vector-line" },
                { type: "Polygon", icon: "vector-polygon" },
                { type: "Circle", icon: "circle-outline" },
                { type: "Export", icon: "crop-free" },
            ],

            // measurement
            isMeasuring: false,
            isBearingMode: false,
            bearingFromGps: false,
            bearingGpsMapCoord: null,
            bearingFirstMapCoord: null,
            bearingPreviewFeature: null,
            sketch: null,
            helpTooltipElement: null,
            helpTooltip: null,
            measureTooltipElement: null,
            measureTooltip: null,
            measurementOverlays: [],

            // drawing storage
            savedDrawings: [],

            // note editing
            editingFeature: null,
            noteText: "",
            hoveredFeature: null,
            hoveredMarker: null,
            noteOverlay: null,
            drawFeatureInfoOverlay: null,
            drawFeatureInfoPayload: null,
            showNoteModal: false,
            showSaveDrawingModal: false,
            newDrawingName: "",
            isLoadingDrawings: false,
            showLoadDrawingModal: false,
            styleCache: {},
            selectedFeature: null,
            select: null,
            translate: null,
            // context menu
            showContextMenu: false,
            contextMenuPos: { x: 0, y: 0 },
            contextMenuFeature: null,
            contextMenuCoord: null,

            showMapPingModal: false,
            pingDestinationHash: "",
            mapPingLat: 0,
            mapPingLon: 0,
            mapPingZoom: 10,

            exportRegionPresets: [
                { id: "world", bbox: WORLD_MBTILES_BBOX.slice(), minZoom: 0, maxZoom: 4 },
                { id: "europe", bbox: [-12, 35, 40, 72], minZoom: 0, maxZoom: 10 },
                { id: "north_america", bbox: [-170, 15, -50, 72], minZoom: 0, maxZoom: 10 },
                { id: "south_america", bbox: [-82, -56, -34, 14], minZoom: 0, maxZoom: 10 },
                { id: "africa", bbox: [-20, -36, 52, 38], minZoom: 0, maxZoom: 10 },
                { id: "asia", bbox: [25, -12, 145, 55], minZoom: 0, maxZoom: 10 },
                { id: "oceania", bbox: [110, -48, 179, 0], minZoom: 0, maxZoom: 10 },
            ],
        };
    },
    computed: {
        popoutRouteType() {
            if (this.$route?.meta?.popoutType) {
                return this.$route.meta.popoutType;
            }
            return this.$route?.query?.popout ?? this.getHashPopoutValue();
        },
        isDarkRasterBasemap() {
            const u = (this.tileServerUrl || "").toLowerCase();
            return u.includes("dark_all");
        },
        isPopoutMode() {
            return this.popoutRouteType === "map";
        },
        trackedPeers() {
            return this.telemetryList.filter((t) => t.is_tracking);
        },
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
        displayCoords() {
            return this.cursorCoords || this.currentCenter;
        },
        northIndicatorRotateStyle() {
            const r = this.mapViewRotationRad || 0;
            return {
                transform: `rotate(${-r}rad)`,
                transformOrigin: "center center",
            };
        },
        hasVectorDrawFeatures() {
            return Boolean(this.drawSource && this.drawSource.getFeatures().length > 0);
        },
        exportTileLimitExceeded() {
            return this.estimatedTiles > MAX_EXPORT_TILES;
        },
        conversationOptions() {
            const out = [];
            for (const c of Object.values(this.peers || {})) {
                const hash = c.destination_hash;
                if (!hash) {
                    continue;
                }
                const name = (c.display_name || "").trim();
                const label = name ? `${name} (${hash.substring(0, 8)}…)` : hash;
                out.push({ hash, label });
            }
            out.sort((a, b) => a.label.localeCompare(b.label));
            return out;
        },
        mapPingSummary() {
            return `${this.mapPingLat.toFixed(6)}, ${this.mapPingLon.toFixed(6)} @ z${Math.round(this.mapPingZoom)}`;
        },
        drawFeatureDescriptionSanitized() {
            const p = this.drawFeatureInfoPayload;
            if (!p || !p.description?.trim() || !p.descriptionIsHtml) {
                return "";
            }
            return DOMPurify.sanitize(p.description, {
                USE_PROFILES: { html: true },
                FORBID_ATTR: ["style"],
            });
        },
    },
    watch: {
        isSettingsOpen(open) {
            if (open) {
                this.$nextTick(() => this.clampSettingsPanelIntoView());
            }
        },
        selectedMarker(newVal, oldVal) {
            // Close mini-chat if the selected peer changed
            if (!newVal || !oldVal || newVal.telemetry?.destination_hash !== oldVal.telemetry?.destination_hash) {
                this.isMiniChatOpen = false;
            }
        },
        showSaveDrawingModal(val) {
            if (val) {
                this.$nextTick(() => {
                    this.$refs.newDrawingNameInput?.focus();
                });
            }
        },
        "$route.query": {
            handler() {
                const name = this.$route.name;
                if (name !== "map" && name !== "map-popout") {
                    return;
                }
                if (!this.map || !this.markerSource) {
                    return;
                }
                this.applyMapViewFromRoute();
            },
            deep: true,
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
        try {
            const lo = localStorage.getItem("meshchatx.map.offlineMode");
            if (lo === "1") this.offlineEnabled = true;
            else if (lo === "0") this.offlineEnabled = false;
        } catch {
            /* ignore */
        }

        await this.initMap();

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
                console.log("Restoring persisted drawings, count:", features.length);
                this.drawSource.addFeatures(features);
                this.rebuildMeasurementOverlays();
            } catch (e) {
                console.error("Failed to restore persisted drawings", e);
            }
            delete this._persistedDrawings;
        }
        await this.checkOfflineMap();
        await this.loadMBTilesList();

        await this.fetchPeers();
        await this.fetchTelemetryMarkers();

        // Handle view modes
        if (this.$route.query.view === "discovered") {
            await this.mapDiscoveredNodes();
        }

        // Listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        this.applyMapViewFromRoute();

        // Listen for moveend to update coordinates in UI and save state
        if (this.map) {
            this.map.on("moveend", () => {
                const view = this.map.getView();
                this.currentCenter =
                    view && typeof view.getCenter === "function" ? toLonLat(view.getCenter()) : this.currentCenter;
                this.currentZoom = view && typeof view.getZoom === "function" ? view.getZoom() : this.currentZoom;
                this.saveMapState();
                this.updateMarkers();
            });
        }

        // Check if onboarding tooltip should be shown
        this.checkOnboardingTooltip();

        // Add click outside handler for search
        document.addEventListener("click", this.handleClickOutside);

        // Check screen size for mobile
        this.checkScreenSize();
        window.addEventListener("resize", this.checkScreenSize);

        document.addEventListener("keydown", this.onDeleteKey);

        // Update info every few seconds
        this.reloadInterval = setInterval(() => {
            this.fetchTelemetryMarkers();
        }, 30000);
    },
    beforeUnmount() {
        if (this.map && this.map.getViewport()) {
            this.map.getViewport().removeEventListener("contextmenu", this.onContextMenu);
        }
        document.removeEventListener("click", this.handleGlobalClick);
        if (this._saveStateTimer) {
            clearTimeout(this._saveStateTimer);
            this._saveStateTimer = null;
        }
        if (this._pendingSaveResolvers && this._pendingSaveResolvers.length > 0) {
            const pending = this._pendingSaveResolvers.slice();
            this._pendingSaveResolvers = [];
            this.saveMapStateImmediate().then(() => pending.forEach((p) => p.resolve()));
        }
        if (this.reloadInterval) clearInterval(this.reloadInterval);
        if (this.exportInterval) clearInterval(this.exportInterval);
        if (this.searchTimeout) clearTimeout(this.searchTimeout);
        if (this.tileConnectivityBannerTimer) {
            clearTimeout(this.tileConnectivityBannerTimer);
            this.tileConnectivityBannerTimer = null;
        }
        document.removeEventListener("click", this.handleClickOutside);
        window.removeEventListener("resize", this.checkScreenSize);
        document.removeEventListener("keydown", this.onDeleteKey);
        WebSocketConnection.off("message", this.onWebsocketMessage);
        if (this._pointerMoveRaf != null) {
            cancelAnimationFrame(this._pointerMoveRaf);
            this._pointerMoveRaf = null;
        }
        if (this.settingsPanelDrag?.rafId != null) {
            cancelAnimationFrame(this.settingsPanelDrag.rafId);
            this.settingsPanelDrag.rafId = null;
        }
        const settingsEl = this.$refs.settingsPanel;
        if (settingsEl) {
            settingsEl.style.transform = "";
            settingsEl.style.willChange = "";
        }
        if (this.map) {
            const v = this.map.getView();
            if (v && typeof v.un === "function") {
                v.un("change:rotation", this.syncMapNorthIndicatorFromViewRotation);
            }
            this.map.setTarget(null);
            this.map = null;
        }
    },
    methods: {
        syncMapNorthIndicatorFromViewRotation() {
            if (!this.map) {
                return;
            }
            const view = this.map.getView();
            if (!view || typeof view.getRotation !== "function") {
                return;
            }
            this.mapViewRotationRad = view.getRotation();
        },
        saveMapState() {
            if (!this._pendingSaveResolvers) {
                this._pendingSaveResolvers = [];
            }
            return new Promise((resolve, reject) => {
                this._pendingSaveResolvers.push({ resolve, reject });
                if (this._saveStateTimer) clearTimeout(this._saveStateTimer);
                this._saveStateTimer = setTimeout(async () => {
                    const pending = this._pendingSaveResolvers.slice();
                    this._pendingSaveResolvers = [];
                    this._saveStateTimer = null;
                    try {
                        await this.saveMapStateImmediate();
                        pending.forEach((p) => p.resolve());
                    } catch (e) {
                        pending.forEach((p) => p.reject(e));
                    }
                }, 150);
            });
        },
        async saveMapStateImmediate() {
            try {
                let drawings = null;
                if (this.drawSource) {
                    const format = new GeoJSON();
                    const features = this.serializeFeatures(this.drawSource.getFeatures());
                    drawings = format.writeFeatures(features, {
                        dataProjection: "EPSG:4326",
                        featureProjection: "EPSG:3857",
                    });
                }
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
                console.log("Map state persisted to cache, drawings size:", drawings ? drawings.length : 0);
            } catch (e) {
                console.error("Failed to save map state", e);
            }
        },
        async getConfig() {
            try {
                const response = await window.api.get("/api/v1/config");
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
                const response = await window.api.get("/api/v1/map/mbtiles");
                this.mbtilesList = response.data;
            } catch (e) {
                console.error("Failed to load MBTiles list", e);
            }
        },
        async setActiveMBTiles(filename) {
            try {
                await window.api.post("/api/v1/map/mbtiles/active", { filename });
                await this.checkOfflineMap();
                await this.loadMBTilesList();
                ToastUtils.success(this.$t("map.source_updated"));
            } catch {
                ToastUtils.error(this.$t("map.failed_set_active"));
            }
        },
        async deleteMBTiles(filename) {
            if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
            try {
                await window.api.delete(`/api/v1/map/mbtiles/${filename}`);
                await this.loadMBTilesList();
                if (this.metadata && this.metadata.path && this.metadata.path.endsWith(filename)) {
                    await this.checkOfflineMap();
                }
                ToastUtils.success(this.$t("map.file_deleted"));
            } catch {
                ToastUtils.error(this.$t("map.failed_delete_file"));
            }
        },
        async saveMBTilesDir() {
            try {
                await window.api.patch("/api/v1/config", {
                    map_mbtiles_dir: this.mbtilesDir,
                });
                ToastUtils.success(this.$t("map.storage_saved"));
                this.loadMBTilesList();
            } catch {
                ToastUtils.error(this.$t("map.failed_save_storage"));
            }
        },
        async initMap() {
            const defaultLat = parseFloat(this.config?.map_default_lat || 0);
            const defaultLon = parseFloat(this.config?.map_default_lon || 0);
            const defaultZoom = parseInt(this.config?.map_default_zoom || 2);

            // Use saved state if available, otherwise use defaults
            const startCenter =
                this.currentCenter[0] !== 0 || this.currentCenter[1] !== 0
                    ? fromLonLat(this.currentCenter)
                    : fromLonLat([defaultLon, defaultLat]);
            const startZoom = this.currentZoom !== 2 ? this.currentZoom : defaultZoom;

            const baseLayer = await this.buildBaseMapLayer();
            const mapPixelRatio = Math.min(typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1, 2);
            this.map = new Map({
                target: this.$refs.mapContainer,
                layers: [baseLayer],
                view: new View({
                    center: startCenter,
                    zoom: startZoom,
                }),
                controls: defaultControls({
                    attribution: false,
                    rotate: false,
                }),
                pixelRatio: mapPixelRatio,
                maxTilesLoading: 48,
            });

            const mapView = this.map.getView();
            if (mapView && typeof mapView.on === "function" && typeof mapView.getRotation === "function") {
                mapView.on("change:rotation", this.syncMapNorthIndicatorFromViewRotation);
                this.syncMapNorthIndicatorFromViewRotation();
            }

            // setup drawing layer
            this.drawSource = new VectorSource();
            this.drawLayer = new VectorLayer({
                source: this.drawSource,
                style: (feature, resolution) => {
                    const own = feature.getStyle();
                    if (own != null) {
                        if (typeof own === "function") {
                            return own(feature, resolution);
                        }
                        return own;
                    }
                    const fromProps = styleFromMcxProperties(feature);
                    if (fromProps) {
                        return fromProps;
                    }
                    const type = feature.get("type");
                    const geometry = feature.getGeometry();
                    const geomType = geometry ? geometry.getType() : null;

                    if (type === "note" || geomType === "Point") {
                        const isNote = type === "note";
                        return this.createMarkerStyle({
                            iconColor: isNote ? "#f59e0b" : "#3b82f6",
                            bgColor: "#ffffff",
                            label: isNote && feature.get("note") ? "Note" : "",
                            isStale: false,
                            iconPath: isNote
                                ? "M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"
                                : null,
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
            this.attachDrawPersistence();

            this.noteOverlay = new Overlay({
                element: this.$refs.noteOverlayElement,
                autoPan: {
                    animation: {
                        duration: 250,
                    },
                },
            });
            this.map.addOverlay(this.noteOverlay);

            this.drawFeatureInfoOverlay = new Overlay({
                element: this.$refs.drawFeatureInfoElement,
                offset: [0, -10],
                positioning: "bottom-center",
                stopEvent: false,
            });
            this.map.addOverlay(this.drawFeatureInfoOverlay);

            this.modify = new Modify({ source: this.drawSource });
            this.modify.on("modifystart", (e) => {
                const feats = (e.features && e.features.getArray()) || this.select.getFeatures().getArray();
                feats.forEach((f) => this.clearMeasurementOverlay(f));
            });
            this.modify.on("modifyend", (e) => {
                const feats = (e.features && e.features.getArray()) || this.select.getFeatures().getArray();
                feats.forEach((f) => this.finalizeMeasurementOverlay(f));
                this.saveMapState();
                this.syncDrawFeatureInfoOverlay();
            });
            this.map.addInteraction(this.modify);

            this.select = new Select({
                layers: [this.drawLayer],
                hitTolerance: MAP_FEATURE_HIT_TOLERANCE,
                style: null, // Keep original feature style
            });
            this.select.on("select", (e) => {
                const picked = e.selected[0];
                this.selectedFeature = picked ? markRaw(picked) : null;
                this.syncDrawFeatureInfoOverlay();
            });
            this.map.addInteraction(this.select);

            this.translate = new Translate({
                features: this.select.getFeatures(),
                layers: [this.drawLayer], // Only move drawing layer items, not telemetry
            });
            this.translate.on("translateend", (e) => {
                const feats = (e.features && e.features.getArray()) || this.select.getFeatures().getArray();
                feats.forEach((f) => this.finalizeMeasurementOverlay(f));
                this.saveMapState();
                this.syncDrawFeatureInfoOverlay();
            });
            this.map.addInteraction(this.translate);

            // Default to Select tool
            this.drawType = "Select";
            this.select.setActive(true);
            this.translate.setActive(true);
            this.modify.setActive(true);

            this.snap = new Snap({ source: this.drawSource });
            this.map.addInteraction(this.snap);

            // Right-click context menu
            this.map.getViewport().addEventListener("contextmenu", this.onContextMenu);

            // setup history layer (trail)
            this.historySource = new VectorSource();
            this.historyLayer = new VectorLayer({
                source: this.historySource,
                style: new Style({
                    stroke: new Stroke({
                        color: "rgba(234, 179, 8, 0.6)", // yellow-500 light
                        width: 3,
                        lineDash: [10, 10], // dashed trail
                    }),
                }),
                zIndex: 40,
            });
            this.map.addLayer(this.historyLayer);

            // setup telemetry markers
            this.markerSource = new VectorSource();
            this.markerLayer = new VectorLayer({
                source: this.markerSource,
                style: (feature) => {
                    const isHovered = this.hoveredMarker === feature;

                    if (feature.get("cluster")) {
                        const style = this.createClusterStyle(feature.get("clusterCount") || 0, isHovered);
                        style.setZIndex(isHovered ? 1000 : 200);
                        return style;
                    }

                    const scale = isHovered ? 0.85 : 0.6;
                    const zIndex = isHovered ? 1000 : 100;

                    const t = feature.get("telemetry");
                    const peer = feature.get("peer");
                    const disc = feature.get("discovered");

                    let displayName = "";
                    let isStale = false;
                    let iconColor = "#2563eb";
                    let bgColor = "#ffffff";
                    let iconPath = null;

                    if (t) {
                        displayName = peer?.display_name || t.destination_hash.substring(0, 8);
                        // Calculate staleness
                        const now = Date.now();
                        const updatedAt = t.updated_at
                            ? new Date(t.updated_at).getTime()
                            : t.timestamp
                              ? t.timestamp * 1000
                              : now;
                        isStale = now - updatedAt > 10 * 60 * 1000;

                        if (peer?.lxmf_user_icon) {
                            iconColor = peer.lxmf_user_icon.foreground_colour || iconColor;
                            bgColor = peer.lxmf_user_icon.background_colour || bgColor;
                            if (peer.lxmf_user_icon.icon_name) {
                                iconPath = this.getMdiPath(peer.lxmf_user_icon.icon_name);
                            }
                        }
                    } else if (disc) {
                        displayName = disc.name;
                        iconColor = "#10b981"; // emerald-500
                        bgColor = "#d1fae5"; // emerald-100
                        iconPath = this.getMdiPath(this.getDiscoveredIconName(disc));
                    } else if (feature === this.queryMarker) {
                        displayName = "Search Result";
                        iconColor = "#ef4444";
                    }

                    const style = this.createMarkerStyle({
                        iconColor,
                        bgColor,
                        label: displayName,
                        isStale,
                        iconPath,
                        scale,
                        isTracking: t ? t.is_tracking : false,
                    });
                    style.setZIndex(zIndex);
                    return style;
                },
                zIndex: 100,
            });
            this.map.addLayer(this.markerLayer);

            this.map.on("pointermove", this.handleMapPointerMove);
            this.map.on("click", (evt) => {
                if (this.isBearingMode) {
                    this.handleBearingClick(evt);
                    this.closeContextMenu();
                    return;
                }
                this.handleMapClick(evt);
                this.closeContextMenu();
                const feature = this.map.forEachFeatureAtPixel(evt.pixel, (f) => f, {
                    hitTolerance: MAP_FEATURE_HIT_TOLERANCE,
                });
                if (feature && feature.get("cluster")) {
                    this.openCluster(feature);
                } else if (feature && (feature.get("telemetry") || feature.get("discovered"))) {
                    this.onMarkerClick(feature);
                    this.selectedCluster = null;
                } else {
                    this.selectedMarker = null;
                    this.selectedCluster = null;
                    if (feature && this.drawLayer) {
                        this.selectedFeature = markRaw(feature);
                        this.syncDrawFeatureInfoOverlay();
                    }
                }

                // Deselect drawing if clicking empty space
                if (!feature && this.select) {
                    this.select.getFeatures().clear();
                    this.selectedFeature = null;
                    this.syncDrawFeatureInfoOverlay();
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
            await this.$nextTick();
            if (this.$refs.scaleLineMount) {
                this.map.addControl(
                    new ScaleLine({
                        target: this.$refs.scaleLineMount,
                        units: "metric",
                        bar: true,
                        text: true,
                    })
                );
            }
            this.isMapLoaded = true;

            // Close context menu when clicking elsewhere
            document.addEventListener("click", this.handleGlobalClick);
        },
        applyExportRegionPreset(preset) {
            if (!preset || !preset.bbox) {
                return;
            }
            this.selectedBbox = preset.bbox.slice();
            this.exportMinZoom = preset.minZoom;
            this.exportMaxZoom = preset.maxZoom;
        },
        applyLayersFromRouteString(layersStr) {
            if (!layersStr || typeof layersStr !== "string") {
                return;
            }
            const parts = layersStr
                .split(",")
                .map((s) => s.trim().toLowerCase())
                .filter(Boolean);
            if (parts.includes("discovered")) {
                this.mapDiscoveredNodes({ skipFit: true, silent: true });
            }
        },
        applyMapViewFromRoute() {
            if (!this.map || !this.markerSource) {
                return;
            }
            const q = this.$route.query || {};
            const latRaw = q.lat;
            const lonRaw = q.lon;
            if (latRaw == null || lonRaw == null || latRaw === "" || lonRaw === "") {
                if (q.layers) {
                    this.applyLayersFromRouteString(String(q.layers));
                }
                return;
            }
            const lat = parseFloat(latRaw);
            const lon = parseFloat(lonRaw);
            const zRaw = q.zoom != null && q.zoom !== "" ? q.zoom : q.z;
            let zoom = parseFloat(zRaw != null && zRaw !== "" ? zRaw : "15");
            if (!Number.isFinite(zoom)) {
                zoom = 15;
            }
            zoom = Math.max(0, Math.min(22, zoom));
            const label = (q.label != null && String(q.label)) || "Target";

            if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
                return;
            }

            if (this.queryMarker) {
                this.markerSource.removeFeature(this.queryMarker);
                this.queryMarker = null;
            }

            this.map.getView().setCenter(fromLonLat([lon, lat]));
            this.map.getView().setZoom(zoom);

            const feature = new Feature({
                geometry: new Point(fromLonLat([lon, lat])),
                originalCoord: fromLonLat([lon, lat]),
            });
            feature.setStyle(
                this.createMarkerStyle({
                    iconColor: "#2563eb",
                    bgColor: "#bfdbfe",
                    label: String(label),
                    isStale: false,
                    iconPath: null,
                })
            );
            this.queryMarker = feature;
            this.markerSource.addFeature(feature);

            if (q.layers) {
                this.applyLayersFromRouteString(String(q.layers));
            }
        },
        layersTagForShare() {
            return this.discoveredVisible ? "discovered" : "";
        },
        async shareMapView() {
            if (!this.map) {
                return;
            }
            const view = this.map.getView();
            const c = toLonLat(view.getCenter());
            const z = view.getZoom();
            const lat = c[1];
            const lon = c[0];
            const layers = this.layersTagForShare();
            const mesh = buildMeshchatMapUri({ lat, lon, zoom: z, layers });
            const web = buildWebHashMapUrl({ lat, lon, zoom: z, layers });
            const text = `${this.$t("map.share_message_prefix")} ${mesh}\n${web}`;
            try {
                if (navigator?.clipboard?.writeText) {
                    await navigator.clipboard.writeText(text);
                    ToastUtils.success(this.$t("map.share_copied"));
                } else {
                    ToastUtils.info(text);
                }
            } catch (e) {
                console.error(e);
                ToastUtils.warning(web);
            }
        },
        openPingModalFromMapCenter() {
            if (!this.map) {
                return;
            }
            const view = this.map.getView();
            const c = toLonLat(view.getCenter());
            this.mapPingLat = c[1];
            this.mapPingLon = c[0];
            this.mapPingZoom = view.getZoom();
            this.pingDestinationHash = "";
            this.showMapPingModal = true;
        },
        openPingModalAt(lat, lon, zoom) {
            this.mapPingLat = lat;
            this.mapPingLon = lon;
            this.mapPingZoom = zoom;
            this.pingDestinationHash = "";
            this.showMapPingModal = true;
        },
        async sendMapPing() {
            const hash = (this.pingDestinationHash || "").trim();
            if (!hash || hash.length !== 32) {
                ToastUtils.error(this.$t("map.ping_invalid_destination"));
                return;
            }
            const layers = this.layersTagForShare();
            const uri = buildMeshchatMapUri({
                lat: this.mapPingLat,
                lon: this.mapPingLon,
                zoom: this.mapPingZoom,
                layers,
                label: "Ping",
            });
            const content = `${this.$t("map.ping_message_prefix")} ${uri}`;
            try {
                await window.api.post("/api/v1/lxmf-messages/send", {
                    lxmf_message: {
                        destination_hash: hash,
                        content,
                    },
                });
                ToastUtils.success(this.$t("map.ping_sent"));
                this.showMapPingModal = false;
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("map.ping_failed"));
            }
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
        isDefaultOnlineUrl(url) {
            if (!url) return false;
            const onlinePatterns = [
                "openstreetmap.org",
                "openfreemap.org",
                "cartocdn.com",
                "thunderforest.com",
                "stamen.com",
                "google.com",
                "mapbox.com",
                "arcgisonline.com",
                "wmflabs.org",
                "maptiler.com",
            ];
            const lowerUrl = url.toLowerCase();
            return onlinePatterns.some((pattern) => lowerUrl.includes(pattern));
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
                const timeoutId = setTimeout(() => controller.abort(), 8000);
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
        isOpenFreeMapStyleUrl(url) {
            return typeof url === "string" && url.includes("tiles.openfreemap.org/styles/");
        },
        isKnownDefaultBasemapUrl(url) {
            const normalized = (url || "").trim();
            return normalized === OPENFREEMAP_DEFAULT_STYLE || normalized === DEFAULT_OSM_RASTER;
        },
        resolveRasterTileUrl(url) {
            const normalized = (url || DEFAULT_OSM_RASTER).trim();
            if (this.isOpenFreeMapStyleUrl(normalized)) {
                return DEFAULT_OSM_RASTER;
            }
            return normalized;
        },
        getExportToolButtonEl() {
            const toolbar = this.$refs.mapDrawingToolbar;
            if (!toolbar) return null;
            const ref = toolbar.$refs.exportToolButton;
            if (!ref) return null;
            return Array.isArray(ref) ? ref[0] : ref;
        },
        usesOfflineMbtilesRaster() {
            if (!this.offlineEnabled) return false;
            const customTileUrl = this.tileServerUrl || DEFAULT_OSM_RASTER;
            const isCustomLocal = this.isLocalUrl(customTileUrl);
            if (isCustomLocal) return false;
            const isDefaultOnline = this.isDefaultOnlineUrl(customTileUrl);
            if (isDefaultOnline) return true;
            if (!this.isKnownDefaultBasemapUrl(customTileUrl)) return false;
            return true;
        },
        async buildBaseMapLayer() {
            const url = (this.tileServerUrl || DEFAULT_OSM_RASTER).trim();
            if (!this.offlineEnabled && !this.cachingEnabled && this.isOpenFreeMapStyleUrl(url)) {
                const group = new LayerGroup();
                await applyMapboxStyle(group, url);
                return group;
            }
            if (this.cachingEnabled && this.usesOfflineMbtilesRaster()) {
                return new LayerGroup({
                    layers: [
                        new TileLayer({
                            source: this.getOfflineRasterCacheOnlySource(),
                            preload: 2,
                            transition: 0,
                            cacheSize: 896,
                        }),
                        new TileLayer({
                            source: this.getOfflineMbtilesTopSource(),
                            preload: 2,
                            transition: 0,
                            cacheSize: 896,
                        }),
                    ],
                });
            }
            return new TileLayer({
                source: this.getTileSource(),
                preload: 2,
                transition: 0,
                cacheSize: 896,
            });
        },
        /**
         * Decode tile blobs off the critical path where possible (createImageBitmap)
         * and avoid object URLs when bitmap path succeeds.
         */
        async fastApplyBlobToTile(tile, blob) {
            if (typeof createImageBitmap === "function") {
                try {
                    const bitmap = await createImageBitmap(blob);
                    tile.setImage(bitmap);
                    return;
                } catch {
                    /* fall through */
                }
            }
            const el = tile.getImage();
            if (el && "src" in el) {
                const url = URL.createObjectURL(blob);
                el.src = url;
                setTimeout(() => URL.revokeObjectURL(url), 10000);
                return;
            }
            await this.applyRasterPlaceholderTile(tile, "dark");
        },
        async applyRasterPlaceholderTile(tile, variant) {
            const isTransparent = variant === "transparent";
            if (typeof createImageBitmap === "function") {
                try {
                    const c = document.createElement("canvas");
                    const size = isTransparent ? 1 : 256;
                    c.width = size;
                    c.height = size;
                    const ctx = c.getContext("2d");
                    if (isTransparent) {
                        ctx.clearRect(0, 0, 1, 1);
                    } else {
                        ctx.fillStyle = "#18181b";
                        ctx.fillRect(0, 0, size, size);
                    }
                    const bitmap = await createImageBitmap(c);
                    tile.setImage(bitmap);
                    tile.setState(TileState.LOADED);
                    return;
                } catch {
                    /* fall through */
                }
            }
            const el = tile.getImage();
            if (el && "src" in el) {
                el.removeAttribute("crossorigin");
                if (isTransparent) {
                    el.src = OFFLINE_TRANSPARENT_TILE_PNG;
                } else {
                    const c = document.createElement("canvas");
                    c.width = 1;
                    c.height = 1;
                    const ctx = c.getContext("2d");
                    ctx.fillStyle = "#18181b";
                    ctx.fillRect(0, 0, 1, 1);
                    el.src = c.toDataURL("image/png");
                }
                tile.setState(TileState.LOADED);
                return;
            }
            tile.setState(TileState.ERROR);
        },
        parseZxyFromTileUrl(url) {
            if (typeof url !== "string") return null;
            const m = url.match(/\/(\d+)\/(\d+)\/(\d+)\.(?:png|jpg|jpeg|webp)(\?|$)/i);
            if (!m) return null;
            return [parseInt(m[1], 10), parseInt(m[2], 10), parseInt(m[3], 10)];
        },
        expandRasterTileUrlTemplates(template, z, x, y) {
            const out = [];
            if (typeof template !== "string") return out;
            if (!template.includes("{z}") || !template.includes("{x}") || !template.includes("{y}")) return out;
            const zs = String(z);
            const xs = String(x);
            const ys = String(y);
            if (template.includes("{r}")) {
                const a = template
                    .replaceAll("{z}", zs)
                    .replaceAll("{x}", xs)
                    .replaceAll("{y}", ys)
                    .replaceAll("{r}", "");
                out.push(a);
                const b = template
                    .replaceAll("{z}", zs)
                    .replaceAll("{x}", xs)
                    .replaceAll("{y}", ys)
                    .replaceAll("{r}", "@2x");
                if (!out.includes(b)) out.push(b);
            } else {
                out.push(template.replaceAll("{z}", zs).replaceAll("{x}", xs).replaceAll("{y}", ys));
            }
            return out;
        },
        offlineTileCacheLookupUrls(tileCoord, primarySrc) {
            let z;
            let x;
            let y;
            if (Array.isArray(tileCoord) && tileCoord.length >= 3) {
                z = tileCoord[0];
                x = tileCoord[1];
                y = tileCoord[2];
            } else {
                const parsed = this.parseZxyFromTileUrl(primarySrc);
                if (!parsed) return primarySrc ? [primarySrc] : [];
                [z, x, y] = parsed;
            }
            const ordered = [];
            const push = (u) => {
                if (typeof u === "string" && u.length > 0 && !ordered.includes(u)) ordered.push(u);
            };
            push(primarySrc);
            const ts = this.resolveRasterTileUrl(this.tileServerUrl || DEFAULT_OSM_RASTER);
            for (const u of this.expandRasterTileUrlTemplates(ts, z, x, y)) push(u);
            return ordered;
        },
        offlineCachedRasterOnlyLookupUrls(tileCoord, primarySrc) {
            let z;
            let x;
            let y;
            if (Array.isArray(tileCoord) && tileCoord.length >= 3) {
                z = tileCoord[0];
                x = tileCoord[1];
                y = tileCoord[2];
            } else {
                const parsed = this.parseZxyFromTileUrl(primarySrc);
                if (!parsed) return [];
                [z, x, y] = parsed;
            }
            const ordered = [];
            const push = (u) => {
                if (typeof u === "string" && u.length > 0 && !ordered.includes(u)) ordered.push(u);
            };
            const ts = this.resolveRasterTileUrl(this.tileServerUrl || DEFAULT_OSM_RASTER);
            for (const u of this.expandRasterTileUrlTemplates(ts, z, x, y)) push(u);
            return ordered;
        },
        async tryApplyCachedRasterTilesOnly(tile, src) {
            if (!this.cachingEnabled) return false;
            const coord = typeof tile.getTileCoord === "function" ? tile.getTileCoord() : null;
            const urls = this.offlineCachedRasterOnlyLookupUrls(coord, src);
            for (const key of urls) {
                try {
                    const cached = await TileCache.getTile(key);
                    if (cached) {
                        await this.fastApplyBlobToTile(tile, cached);
                        return true;
                    }
                } catch {
                    /* ignore */
                }
            }
            return false;
        },
        getOfflineRasterCacheOnlySource() {
            const source = new XYZ({
                url: OFFLINE_MB_TILES_URL,
                crossOrigin: "anonymous",
                transition: 0,
            });
            source.setTileLoadFunction(async (tile, src) => {
                if (await this.tryApplyCachedRasterTilesOnly(tile, src)) return;
                await this.applyRasterPlaceholderTile(tile, "dark");
            });
            return source;
        },
        getOfflineMbtilesTopSource() {
            const source = new XYZ({
                url: OFFLINE_MB_TILES_URL,
                crossOrigin: "anonymous",
                transition: 0,
            });
            source.setTileLoadFunction(async (tile, src) => {
                const result = await fetchTileBlobWithRetry(src, { credentials: "omit" }, {});
                if (result.ok) {
                    await this.fastApplyBlobToTile(tile, result.blob);
                    return;
                }
                await this.applyRasterPlaceholderTile(tile, "transparent");
            });
            return source;
        },
        async tryApplyCachedTileForOfflineView(tile, src) {
            if (!this.cachingEnabled) return false;
            const coord = typeof tile.getTileCoord === "function" ? tile.getTileCoord() : null;
            const urls = this.offlineTileCacheLookupUrls(coord, src);
            for (const key of urls) {
                try {
                    const cached = await TileCache.getTile(key);
                    if (cached) {
                        await this.fastApplyBlobToTile(tile, cached);
                        return true;
                    }
                } catch {
                    /* ignore */
                }
            }
            return false;
        },
        getTileSource() {
            const isOffline = this.offlineEnabled;
            const customTileUrl = this.tileServerUrl || DEFAULT_OSM_RASTER;
            const isCustomLocal = this.isLocalUrl(customTileUrl);
            const isDefaultOnline = this.isDefaultOnlineUrl(customTileUrl);

            let tileUrl;
            if (isOffline) {
                // If it's a known online URL, force offline tiles from MBTiles
                if (isDefaultOnline) {
                    tileUrl = OFFLINE_MB_TILES_URL;
                } else if (isCustomLocal) {
                    // It's a local/mesh URL, allow it
                    tileUrl = customTileUrl;
                } else if (!this.isKnownDefaultBasemapUrl(customTileUrl)) {
                    // It's a custom URL that isn't a known online one,
                    // assume it might be a local mesh server with a domain.
                    tileUrl = customTileUrl;
                } else {
                    tileUrl = OFFLINE_MB_TILES_URL;
                }
            } else {
                tileUrl = this.resolveRasterTileUrl(customTileUrl);
            }

            const source = new XYZ({
                url: tileUrl,
                crossOrigin: "anonymous",
                transition: 0,
            });

            if (!isOffline && source && typeof source.on === "function") {
                source.on("tileloadend", () => {
                    this.onOnlineRasterTileLoadedOk();
                });
            }

            if (isOffline) {
                source.setTileLoadFunction(async (tile, src) => {
                    const result = await fetchTileBlobWithRetry(src, { credentials: "omit" }, {});
                    if (result.ok) {
                        await this.fastApplyBlobToTile(tile, result.blob);
                        return;
                    }
                    if (await this.tryApplyCachedTileForOfflineView(tile, src)) return;
                    await this.applyRasterPlaceholderTile(tile, "dark");
                });
            } else {
                source.setTileLoadFunction(async (tile, src) => {
                    if (this.cachingEnabled) {
                        try {
                            const cached = await TileCache.getTile(src);
                            if (cached) {
                                await this.fastApplyBlobToTile(tile, cached);
                                return;
                            }
                        } catch {
                            /* ignore */
                        }
                    }

                    const result = await fetchTileBlobWithRetry(src, { credentials: "omit" }, {});
                    if (result.ok) {
                        await this.fastApplyBlobToTile(tile, result.blob);
                        if (this.cachingEnabled) {
                            queueMicrotask(() => {
                                TileCache.setTile(src, result.blob).catch(() => {});
                            });
                        }
                        return;
                    }
                    await this.applyRasterPlaceholderTile(tile, "dark");
                    this.onOnlineRasterTileLoadFailure();
                });
            }

            return source;
        },
        onOnlineRasterTileLoadedOk() {
            this.tileErrorCount = Math.max(0, this.tileErrorCount - 4);
            if (this.tileErrorCount === 0) {
                this.tileProvidersAttempted = [];
            }
        },
        onOnlineRasterTileLoadFailure() {
            if (this.offlineEnabled || this.tileFailoverInProgress) {
                return;
            }
            this.tileErrorCount++;
            if (this.tileErrorCount > 10) {
                this.tileErrorCount = 0;
                this.tryTileProviderFailoverOrOffline();
            }
        },
        async tryTileProviderFailoverOrOffline() {
            if (this.offlineEnabled || this.tileFailoverInProgress) {
                return;
            }
            const currentId = detectRasterTileProviderId(this.tileServerUrl);
            const nextId = nextRasterTileProviderId(currentId, this.tileProvidersAttempted);
            if (nextId) {
                this.tileFailoverInProgress = true;
                if (currentId) {
                    this.tileProvidersAttempted.push(currentId);
                }
                this.dismissTileConnectivityBanner();
                const label = this.tileProviderLabel(nextId);
                ToastUtils.info(this.$t("map.tile_failover_trying", { provider: label }));
                this.setTileServer(nextId);
                this.tileFailoverInProgress = false;
                return;
            }
            if (this.hasOfflineMap) {
                ToastUtils.info(this.$t("map.tile_failover_offline"));
                await this.switchToOfflineFromTileBanner();
                return;
            }
            this.showTileConnectivityBanner = true;
            if (this.tileConnectivityBannerTimer) {
                clearTimeout(this.tileConnectivityBannerTimer);
            }
            this.tileConnectivityBannerTimer = setTimeout(() => {
                this.showTileConnectivityBanner = false;
                this.tileConnectivityBannerTimer = null;
            }, 45000);
        },
        tileProviderLabel(providerId) {
            const labels = {
                openfreemap: "OpenFreeMap",
                osm: "OSM",
                "carto-dark": "Carto Dark",
                "carto-voyager": "Carto Voyager",
                "carto-light": "Carto Light",
            };
            return labels[providerId] || providerId;
        },
        dismissTileConnectivityBanner() {
            this.showTileConnectivityBanner = false;
            if (this.tileConnectivityBannerTimer) {
                clearTimeout(this.tileConnectivityBannerTimer);
                this.tileConnectivityBannerTimer = null;
            }
        },
        refreshBaseMapTileSources() {
            if (!this.map) return;
            const base = this.map.getLayers().item(0);
            if (!base) return;
            const walk = (layer) => {
                const s = layer.getSource && layer.getSource();
                if (s && typeof s.refresh === "function") {
                    s.refresh();
                }
                const inner = layer.getLayers && layer.getLayers();
                if (inner && typeof inner.forEach === "function") {
                    inner.forEach(walk);
                }
            };
            walk(base);
        },
        retryMapTiles() {
            this.tileErrorCount = 0;
            this.dismissTileConnectivityBanner();
            this.refreshBaseMapTileSources();
        },
        async switchToOfflineFromTileBanner() {
            this.dismissTileConnectivityBanner();
            await this.toggleOffline(true);
        },
        async checkOfflineMap() {
            try {
                const response = await window.api.get("/api/v1/map/offline");
                if (response.data && response.data.loaded !== false && Object.keys(response.data).length > 0) {
                    this.metadata = response.data;
                    this.hasOfflineMap = true;

                    if (this.offlineEnabled) {
                        await this.updateMapSource();
                    }
                } else {
                    this.hasOfflineMap = false;
                    this.metadata = null;
                    if (this.offlineEnabled) {
                        await this.updateMapSource();
                    }
                }
            } catch {
                this.hasOfflineMap = false;
                this.metadata = null;
                if (this.offlineEnabled) {
                    await this.updateMapSource();
                }
            }
        },
        async updateMapSource() {
            if (!this.map) return;
            const layers = this.map.getLayers();

            // Find and replace the tile layer (first layer usually)
            // or just clear and re-add everything correctly
            layers.clear();

            layers.push(await this.buildBaseMapLayer());

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
            this.tileErrorCount = 0;
            this.dismissTileConnectivityBanner();

            if (enabled) {
                const defaultNominatimUrl = "https://nominatim.openstreetmap.org";

                const isCustomTileLocal = this.isLocalUrl(this.tileServerUrl);
                const isDefaultTileOnline = this.isDefaultOnlineUrl(this.tileServerUrl);
                const hasCustomTile = this.tileServerUrl && !this.isKnownDefaultBasemapUrl(this.tileServerUrl);

                const isCustomNominatimLocal = this.isLocalUrl(this.nominatimApiUrl);
                const isDefaultNominatimOnline = this.isDefaultOnlineUrl(this.nominatimApiUrl);
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
            try {
                localStorage.setItem("meshchatx.map.offlineMode", enabled ? "1" : "0");
            } catch {
                /* ignore */
            }
            if (enabled) {
                this.isExportMode = false;
                this.clearSearch();
            }
            await this.updateMapSource();
            await this.saveMapState();

            // Persist setting
            try {
                await window.api.patch("/api/v1/config", {
                    map_offline_enabled: enabled,
                });
            } catch (e) {
                console.error("Failed to save offline setting", e);
            }
        },
        async toggleCaching(enabled) {
            this.cachingEnabled = enabled;
            this.tileErrorCount = 0;
            this.dismissTileConnectivityBanner();
            try {
                await window.api.patch("/api/v1/config", {
                    map_tile_cache_enabled: enabled,
                });
                await this.updateMapSource();
            } catch (e) {
                console.error("Failed to save caching setting", e);
            }
        },
        toggleExportMode() {
            this.isExportMode = !this.isExportMode;
            if (this.isExportMode) {
                this.stopBearingMode();
            }
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
                await window.api.delete(`/api/v1/map/export/${this.exportId}`);
                this.exportStatus = null;
                this.exportId = null;
                ToastUtils.success(this.$t("map.export_cancelled"));
            } catch {
                ToastUtils.error(this.$t("map.failed_cancel_export"));
            }
        },
        async startExport() {
            if (!this.selectedBbox || this.exportTileLimitExceeded) return;
            this.isExporting = true;
            try {
                const response = await window.api.post("/api/v1/map/export", {
                    bbox: this.selectedBbox,
                    min_zoom: this.exportMinZoom,
                    max_zoom: this.exportMaxZoom,
                    name: `Map Export ${new Date().toLocaleString()}`,
                });
                this.exportId = response.data.export_id;
                this.isExportMode = false;
                this.selectedBbox = null;
                this.pollExportStatus();
            } catch (e) {
                const msg = e.response?.data?.error || this.$t("map.failed_start_export");
                ToastUtils.error(msg);
                this.isExporting = false;
            }
        },
        pollExportStatus() {
            if (this.exportInterval) clearInterval(this.exportInterval);
            this.exportInterval = setInterval(async () => {
                try {
                    const response = await window.api.get(`/api/v1/map/export/${this.exportId}`);
                    this.exportStatus = response.data;
                    if (this.exportStatus.status === "completed" || this.exportStatus.status === "failed") {
                        clearInterval(this.exportInterval);
                        this.isExporting = false;
                        if (this.exportStatus.status === "completed") {
                            this.loadMBTilesList();
                        }
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

            await this.uploadMbtilesFile(file);
            event.target.value = "";
        },
        isMbtilesFile(file) {
            return Boolean(file?.name && file.name.toLowerCase().endsWith(".mbtiles"));
        },
        async uploadMbtilesFile(file) {
            if (!this.isMbtilesFile(file)) {
                ToastUtils.error(this.$t("map.select_mbtiles_error"));
                return false;
            }

            this.isUploading = true;
            const formData = new FormData();
            formData.append("file", file, file.name);

            try {
                const response = await window.api.post("/api/v1/map/offline", formData);

                this.metadata = response.data.metadata;
                this.hasOfflineMap = true;
                this.offlineEnabled = true;
                try {
                    localStorage.setItem("meshchatx.map.offlineMode", "1");
                } catch {
                    /* ignore */
                }
                await this.loadMBTilesList();
                await this.checkOfflineMap();
                await this.updateMapSource();
                ToastUtils.success(this.$t("map.upload_success"));

                if (this.metadata.bounds) {
                    const bounds = this.metadata.bounds.split(",").map(parseFloat);
                    if (bounds.length === 4) {
                        const extent = [...fromLonLat([bounds[0], bounds[1]]), ...fromLonLat([bounds[2], bounds[3]])];
                        this.map.getView().fit(extent, { padding: [20, 20, 20, 20] });
                    }
                }
                return true;
            } catch (e) {
                const error = e.response?.data?.error || e.message;
                ToastUtils.error(this.$t("map.upload_failed") + ": " + error);
                return false;
            } finally {
                this.isUploading = false;
            }
        },
        async setAsDefaultView() {
            if (!this.map) return;
            const view = this.map.getView();
            const center = toLonLat(view.getCenter());
            const zoom = Math.round(view.getZoom());

            try {
                await window.api.patch("/api/v1/config", {
                    map_default_lat: center[1],
                    map_default_lon: center[0],
                    map_default_zoom: zoom,
                });
                ToastUtils.success(this.$t("map.view_saved"));
            } catch {
                ToastUtils.error(this.$t("map.failed_save_view"));
            }
        },
        async clearCache() {
            try {
                await TileCache.clear();
                this.dismissTileConnectivityBanner();
                ToastUtils.success(this.$t("map.cache_cleared"));
            } catch {
                ToastUtils.error(this.$t("map.failed_clear_cache"));
            }
        },
        async saveTileServerUrl() {
            try {
                await window.api.patch("/api/v1/config", {
                    map_tile_server_url: this.tileServerUrl,
                });
                this.dismissTileConnectivityBanner();
                await this.updateMapSource();
                ToastUtils.success(this.$t("map.tile_server_saved"));
                await this.saveMapState();
            } catch {
                ToastUtils.error(this.$t("map.failed_save_tile_server"));
            }
        },
        setTileServer(type) {
            this.tileErrorCount = 0;
            this.tileProvidersAttempted = [];
            this.dismissTileConnectivityBanner();
            const url = TILE_PROVIDER_URLS[type];
            if (url) {
                this.tileServerUrl = url;
            }
            this.saveTileServerUrl();
        },
        async saveNominatimApiUrl() {
            try {
                await window.api.patch("/api/v1/config", {
                    map_nominatim_api_url: this.nominatimApiUrl,
                });
                ToastUtils.success(this.$t("map.nominatim_api_saved"));
            } catch {
                ToastUtils.error(this.$t("map.failed_save_nominatim"));
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
                const exportButton = this.getExportToolButtonEl();
                if (!exportButton || !this.$refs.tooltipElement) return;

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
            const isDefaultOnline = this.isDefaultOnlineUrl(this.nominatimApiUrl);

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
                const url = buildNominatimSearchUrl(this.nominatimApiUrl, this.searchQuery);
                const result = await fetchJsonWithRetry(
                    url,
                    {
                        headers: {
                            "User-Agent": "ReticulumMeshChatX/1.0",
                        },
                    },
                    {
                        timeoutMs: NOMINATIM_FETCH_TIMEOUT_MS,
                        retries: NOMINATIM_FETCH_RETRIES,
                        retryBaseDelayMs: NOMINATIM_FETCH_RETRY_BASE_DELAY_MS,
                    }
                );

                if (!result.ok) {
                    if (result.status) {
                        this.searchError = `${this.$t("map.search_error")} (HTTP ${result.status})`;
                    } else if (result.error && result.error.name === "AbortError") {
                        this.searchError = this.$t("map.search_timeout_error");
                    } else {
                        this.searchError = this.$t("map.search_connection_error");
                    }
                    return;
                }

                const data = await result.response.json();

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
                this.searchError = this.$t("map.search_error") + ": " + (e.message || String(e));
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
            if (!this.isMobileScreen) {
                this.isMobileSearchOpen = false;
            }
            this.clampSettingsPanelIntoView();
        },
        clampSettingsPanelIntoView() {
            if (!this.isSettingsOpen || !this.settingsPanelPos) {
                return;
            }
            const root = this.$refs.mapViewOverlayRoot;
            const panel = this.$refs.settingsPanel;
            if (!root || !panel) {
                return;
            }
            const margin = 6;
            const w = panel.offsetWidth;
            const h = panel.offsetHeight;
            const maxLeft = Math.max(margin, root.clientWidth - w - margin);
            const maxTop = Math.max(margin, root.clientHeight - h - margin);
            const left = Math.min(Math.max(this.settingsPanelPos.left, margin), maxLeft);
            const top = Math.min(Math.max(this.settingsPanelPos.top, margin), maxTop);
            if (left !== this.settingsPanelPos.left || top !== this.settingsPanelPos.top) {
                this.settingsPanelPos = { left, top };
            }
        },
        onSettingsPanelPointerDown(e) {
            if (e.pointerType === "mouse" && e.button !== 0) {
                return;
            }
            if (e.target.closest("button")) {
                return;
            }
            const root = this.$refs.mapViewOverlayRoot;
            const panel = this.$refs.settingsPanel;
            const header = this.$refs.settingsPanelHeader;
            if (!root || !panel || !header) {
                return;
            }
            const rootRect = root.getBoundingClientRect();
            const panelRect = panel.getBoundingClientRect();
            if (!this.settingsPanelPos) {
                this.settingsPanelPos = {
                    left: panelRect.left - rootRect.left,
                    top: panelRect.top - rootRect.top,
                };
            }
            header.setPointerCapture(e.pointerId);
            const anchorLeft = this.settingsPanelPos.left;
            const anchorTop = this.settingsPanelPos.top;
            this.settingsPanelDrag = {
                pointerId: e.pointerId,
                startClientX: e.clientX,
                startClientY: e.clientY,
                lastClientX: e.clientX,
                lastClientY: e.clientY,
                anchorLeft,
                anchorTop,
                rafId: null,
            };
            panel.style.willChange = "transform";
        },
        settingsPanelDragClamped() {
            const d = this.settingsPanelDrag;
            if (!d) {
                return null;
            }
            const root = this.$refs.mapViewOverlayRoot;
            const panel = this.$refs.settingsPanel;
            if (!root || !panel) {
                return null;
            }
            const margin = 6;
            const dx = d.lastClientX - d.startClientX;
            const dy = d.lastClientY - d.startClientY;
            let left = d.anchorLeft + dx;
            let top = d.anchorTop + dy;
            const maxLeft = Math.max(margin, root.clientWidth - panel.offsetWidth - margin);
            const maxTop = Math.max(margin, root.clientHeight - panel.offsetHeight - margin);
            left = Math.min(Math.max(left, margin), maxLeft);
            top = Math.min(Math.max(top, margin), maxTop);
            return {
                left,
                top,
                tx: left - d.anchorLeft,
                ty: top - d.anchorTop,
            };
        },
        scheduleSettingsPanelDragRaf() {
            const d = this.settingsPanelDrag;
            if (!d || d.rafId != null) {
                return;
            }
            d.rafId = requestAnimationFrame(() => {
                d.rafId = null;
                const panel = this.$refs.settingsPanel;
                const fin = this.settingsPanelDragClamped();
                if (!panel || !fin) {
                    return;
                }
                panel.style.transform = `translate3d(${fin.tx}px,${fin.ty}px,0)`;
            });
        },
        onSettingsPanelPointerMove(e) {
            if (!this.settingsPanelDrag || this.settingsPanelDrag.pointerId !== e.pointerId) {
                return;
            }
            this.settingsPanelDrag.lastClientX = e.clientX;
            this.settingsPanelDrag.lastClientY = e.clientY;
            this.scheduleSettingsPanelDragRaf();
        },
        onSettingsPanelPointerUp(e) {
            if (!this.settingsPanelDrag || this.settingsPanelDrag.pointerId !== e.pointerId) {
                return;
            }
            const d = this.settingsPanelDrag;
            if (d.rafId != null) {
                cancelAnimationFrame(d.rafId);
                d.rafId = null;
            }
            d.lastClientX = e.clientX;
            d.lastClientY = e.clientY;
            const panel = this.$refs.settingsPanel;
            const fin = this.settingsPanelDragClamped();
            if (panel) {
                panel.style.transform = "";
                panel.style.willChange = "";
            }
            if (fin) {
                this.settingsPanelPos = { left: fin.left, top: fin.top };
            }
            const header = this.$refs.settingsPanelHeader;
            if (header) {
                try {
                    header.releasePointerCapture(e.pointerId);
                } catch {
                    /* already released */
                }
            }
            this.settingsPanelDrag = null;
        },
        toggleMobileSearch() {
            this.isMobileSearchOpen = !this.isMobileSearchOpen;
            if (this.isMobileSearchOpen) {
                this.$nextTick(() => {
                    const input = this.$refs.searchContainer?.querySelector("input");
                    if (input) {
                        input.focus();
                    }
                });
            } else {
                this.isSearchFocused = false;
            }
        },
        async fetchPeers() {
            if (!window.api) return;
            try {
                const response = await window.api.get("/api/v1/lxmf/conversations");
                const peers = {};
                for (const conv of response.data.conversations) {
                    peers[conv.destination_hash] = conv;
                }
                this.peers = peers;
            } catch (e) {
                console.error("Failed to fetch peers", e);
            }
        },

        attachDrawPersistence() {
            if (!this.drawSource) return;
            const persist = () => this.saveMapState();
            this.drawSource.on("addfeature", persist);
            this.drawSource.on("removefeature", persist);
            this.drawSource.on("changefeature", persist);
            this.drawSource.on("clear", persist);
            this.drawSource.on("clear", () => olIconCache.clear());
        },

        deleteSelectedFeature() {
            if (this.selectedFeature && this.drawSource) {
                this.clearMeasurementOverlay(this.selectedFeature);
                this.drawSource.removeFeature(this.selectedFeature);
                if (this.select) this.select.getFeatures().clear();
                this.selectedFeature = null;
                this.syncDrawFeatureInfoOverlay();
                this.saveMapState();
            }
        },

        syncDrawFeatureInfoOverlay() {
            if (!this.drawFeatureInfoOverlay || !this.map || !this.drawSource) {
                return;
            }
            const f = this.selectedFeature;
            if (!f || !this.drawSource.hasFeature(f)) {
                this.drawFeatureInfoOverlay.setPosition(undefined);
                this.drawFeatureInfoPayload = null;
                return;
            }
            const payload = getDrawFeatureMetadataPayload(f);
            if (!payload) {
                this.drawFeatureInfoOverlay.setPosition(undefined);
                this.drawFeatureInfoPayload = null;
                return;
            }
            this.drawFeatureInfoPayload = payload;
            const coord = getFeatureAnchorCoordinate(f);
            if (!coord) {
                this.drawFeatureInfoOverlay.setPosition(undefined);
                return;
            }
            this.drawFeatureInfoOverlay.setPosition(coord);
        },

        // Drawing methods
        toggleDraw(type) {
            if (!this.map) return;
            if (this.drawType === type && !this.isDrawing) {
                this.stopDrawing();
                return;
            }

            this.stopDrawing();
            this.isMeasuring = false;
            this.stopBearingMode();
            this.drawType = type;

            if (type === "Select") {
                if (this.select) this.select.setActive(true);
                if (this.translate) this.translate.setActive(true);
                if (this.modify) this.modify.setActive(true);
                return;
            }

            // Disable selection/translation while drawing
            if (this.select) this.select.setActive(false);
            if (this.translate) this.translate.setActive(false);
            if (this.modify) this.modify.setActive(false);

            this.draw = new Draw({
                source: this.drawSource,
                type: type,
            });

            this.draw.on("drawstart", (evt) => {
                this.isDrawing = true;
                this.sketch = evt.feature;

                // For LineString, Polygon, and Circle, show measure tooltip while drawing
                if (type === "LineString" || type === "Polygon" || type === "Circle") {
                    this.createMeasureTooltip();
                    this._drawListener = this.sketch.getGeometry().on("change", (e) => {
                        const geom = e.target;
                        let output;
                        let tooltipCoord;
                        if (geom instanceof Polygon) {
                            output = this.formatArea(geom);
                            tooltipCoord = geom.getInteriorPoint().getCoordinates();
                        } else if (geom instanceof LineString) {
                            output = this.formatLength(geom);
                            tooltipCoord = geom.getLastCoordinate();
                        } else if (geom instanceof Circle) {
                            const radius = geom.getRadius();
                            const center = geom.getCenter();
                            // Calculate radius distance in projection (sphere-aware)
                            const edge = [center[0] + radius, center[1]];
                            const line = new LineString([center, edge]);
                            output = `Radius: ${this.formatLength(line)}`;
                            tooltipCoord = edge;
                        }
                        if (output) {
                            this.measureTooltipElement.innerHTML = output;
                            this.measureTooltip.setPosition(tooltipCoord);
                        }
                    });
                }
            });

            this.draw.on("drawend", (evt) => {
                this.isDrawing = false;
                const feature = evt.feature;
                feature.set("type", "draw"); // Tag as custom drawing for styling

                // Clean up sketch listener and tooltips unless it was the Measure tool
                if (this._drawListener) {
                    unByKey(this._drawListener);
                    this._drawListener = null;
                }
                this.sketch = null;

                // Finalize measurement overlay for the drawn feature
                this.finalizeMeasurementOverlay(feature);
                this.cleanupMeasureTooltip();

                // Re-enable select/translate/modify after drawing
                if (this.select) this.select.setActive(true);
                if (this.translate) this.translate.setActive(true);
                if (this.modify) this.modify.setActive(true);
                this.drawType = "Select";

                setTimeout(() => this.saveMapState(), 100);
            });

            this.map.addInteraction(this.draw);
        },

        startEditingNote(feature) {
            this.editingFeature = feature;
            const telemetry = feature.get("telemetry");
            this.noteText = telemetry ? telemetry.note || "" : feature.get("note") || "";
            if (this.isMobileScreen) {
                this.showNoteModal = true;
            } else {
                this.updateNoteOverlay();
            }
        },

        updateNoteOverlay() {
            if (!this.editingFeature || !this.map) return;
            const geometry = this.editingFeature.getGeometry();
            let coord;
            if (geometry instanceof Point) {
                coord = geometry.getCoordinates();
            } else if (geometry instanceof LineString) {
                coord = geometry.getCoordinateAt(0.5); // Middle of line
            } else if (geometry instanceof Polygon) {
                coord = geometry.getInteriorPoint().getCoordinates();
            } else if (geometry instanceof Circle) {
                coord = geometry.getCenter();
            } else {
                coord = this.map.getView().getCenter();
            }
            this.noteOverlay.setPosition(coord);
        },

        saveNote() {
            if (this.editingFeature) {
                const telemetry = this.editingFeature.get("telemetry");
                if (telemetry) {
                    telemetry.note = this.noteText;
                } else {
                    this.editingFeature.set("note", this.noteText);
                }
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

        // Measurement helpers
        cleanupMeasureTooltip() {
            if (this.measureTooltipElement && this.measureTooltipElement.parentNode) {
                this.measureTooltipElement.parentNode.removeChild(this.measureTooltipElement);
            }
            if (this.measureTooltip) {
                this.map.removeOverlay(this.measureTooltip);
            }
            this.measureTooltipElement = null;
            this.measureTooltip = null;
        },
        getMeasurementForGeometry(geom) {
            if (geom instanceof Polygon) {
                return {
                    text: this.formatArea(geom),
                    coord: geom.getInteriorPoint().getCoordinates(),
                };
            }
            if (geom instanceof LineString) {
                return {
                    text: this.formatLength(geom),
                    coord: geom.getLastCoordinate(),
                };
            }
            if (geom instanceof Circle) {
                const center = geom.getCenter();
                const edge = [center[0] + geom.getRadius(), center[1]];
                const line = new LineString([center, edge]);
                return {
                    text: `Radius: ${this.formatLength(line)}`,
                    coord: edge,
                };
            }
            return null;
        },
        clearMeasurementOverlay(feature) {
            const overlay = feature.get("_measureOverlay");
            if (overlay) {
                this.map.removeOverlay(overlay);
                feature.unset("_measureOverlay", true);
            }
        },
        finalizeMeasurementOverlay(feature) {
            if (!this.map) return;
            this.clearMeasurementOverlay(feature);
            if (feature.get("bearingPreview")) {
                return;
            }
            if (feature.get("segmentKind") === "bearing") {
                let metrics = feature.get("bearingMetrics");
                if (!metrics) {
                    const g = feature.getGeometry();
                    if (g && g.getType() === "LineString") {
                        const c = g.getCoordinates();
                        if (c.length === 2) {
                            const p0 = toLonLat(c[0]);
                            const p1 = toLonLat(c[1]);
                            metrics = computeSegmentMetrics(p0[0], p0[1], p1[0], p1[1]);
                            feature.set("bearingMetrics", metrics);
                        }
                    }
                }
                if (!metrics) {
                    return;
                }
                const g = feature.getGeometry();
                const coord =
                    g && g.getType() === "LineString"
                        ? /** @type {import("ol/geom/LineString").default} */ (g).getCoordinateAt(0.5)
                        : null;
                if (!coord) {
                    return;
                }
                const el = document.createElement("div");
                el.className = "ol-tooltip ol-tooltip-static";
                el.innerHTML = buildBearingOverlayHtml(metrics, (k) => this.$t(k));
                const overlay = new Overlay({
                    element: el,
                    offset: [0, -7],
                    positioning: "bottom-center",
                });
                overlay.set("isMeasureTooltip", true);
                this.map.addOverlay(overlay);
                overlay.setPosition(coord);
                feature.set("_measureOverlay", overlay);
                return;
            }
            const geom = feature.getGeometry();
            const measurement = this.getMeasurementForGeometry(geom);
            if (!measurement) return;
            const el = document.createElement("div");
            el.className = "ol-tooltip ol-tooltip-static";
            el.innerHTML = measurement.text;
            const overlay = new Overlay({
                element: el,
                offset: [0, -7],
                positioning: "bottom-center",
            });
            overlay.set("isMeasureTooltip", true);
            this.map.addOverlay(overlay);
            overlay.setPosition(measurement.coord);
            feature.set("_measureOverlay", overlay);
        },
        rebuildMeasurementOverlays() {
            if (!this.drawSource || !this.map) return;
            // Remove all existing measure overlays
            const overlays = this.map.getOverlays().getArray();
            for (let i = overlays.length - 1; i >= 0; i--) {
                const ov = overlays[i];
                if (ov.get && ov.get("isMeasureTooltip")) {
                    this.map.removeOverlay(ov);
                }
            }
            // Rebuild for all features
            this.drawSource.getFeatures().forEach((f) => {
                if (f.get("bearingPreview")) {
                    return;
                }
                f.unset("_measureOverlay", true);
                this.finalizeMeasurementOverlay(f);
            });
        },
        serializeFeatures(features) {
            return features
                .filter((f) => !f.get("bearingPreview"))
                .map((f) => {
                    const clone = f.clone();
                    clone.unset("_measureOverlay", true); // avoid circular refs
                    const geom = clone.getGeometry();
                    if (geom instanceof Circle) {
                        clone.setGeometry(fromCircle(geom, 128));
                    }
                    const st = f.getStyle();
                    if (st != null && typeof st !== "function") {
                        clone.setStyle(st);
                    }
                    return clone;
                });
        },
        // Context menu handlers
        onContextMenu(evt) {
            if (!this.map) return;
            evt.preventDefault();
            const pixel = this.map.getEventPixel(evt);
            const feature = this.map.forEachFeatureAtPixel(pixel, (f) => f, {
                hitTolerance: MAP_FEATURE_HIT_TOLERANCE,
            });
            this.contextMenuFeature = feature || null;
            this.contextMenuCoord = toLonLat(this.map.getCoordinateFromPixel(pixel));
            this.contextMenuPos = { x: evt.clientX, y: evt.clientY };
            if (feature && this.select) {
                this.select.getFeatures().clear();
                this.select.getFeatures().push(feature);
                this.selectedFeature = markRaw(feature);
            }
            this.showContextMenu = true;
        },
        closeContextMenu() {
            this.showContextMenu = false;
        },
        contextSelectFeature() {
            if (!this.contextMenuFeature || !this.select || !this.translate) {
                this.closeContextMenu();
                return;
            }
            this.select.setActive(true);
            this.translate.setActive(true);
            this.modify?.setActive(true);
            this.select.getFeatures().clear();
            this.select.getFeatures().push(this.contextMenuFeature);
            this.selectedFeature = markRaw(this.contextMenuFeature);
            this.drawType = "Select";
            this.closeContextMenu();
        },
        contextDeleteFeature() {
            if (this.contextMenuFeature && !this.contextMenuFeature.get("telemetry")) {
                this.drawSource.removeFeature(this.contextMenuFeature);
                this.saveMapState();
            }
            this.closeContextMenu();
        },
        onDeleteKey(e) {
            if (e.key !== "Delete" && e.key !== "Backspace") return;
            if (
                e.target &&
                (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable)
            )
                return;
            const f = this.selectedFeature;
            if (!f || f.get("telemetry")) return;
            this.drawSource.removeFeature(f);
            this.selectedFeature = null;
            this.syncDrawFeatureInfoOverlay();
            this.saveMapState();
        },
        contextAddNote() {
            if (this.contextMenuFeature) {
                this.startEditingNote(this.contextMenuFeature);
            }
            this.closeContextMenu();
        },
        async contextCopyCoords() {
            if (!this.contextMenuCoord) {
                this.closeContextMenu();
                return;
            }
            const [lon, lat] = this.contextMenuCoord;
            const text = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;
            try {
                if (navigator?.clipboard?.writeText) {
                    await navigator.clipboard.writeText(text);
                    ToastUtils.success(this.$t("map.copied_coordinates"));
                } else {
                    ToastUtils.success(text);
                }
            } catch (e) {
                console.error("Copy failed", e);
                ToastUtils.warning(text);
            }
            this.closeContextMenu();
        },
        contextPingHere() {
            if (!this.contextMenuCoord || !this.map) {
                this.closeContextMenu();
                return;
            }
            const [lon, lat] = this.contextMenuCoord;
            const z = this.map.getView().getZoom();
            this.openPingModalAt(lat, lon, z);
            this.closeContextMenu();
        },
        contextClearMap() {
            this.clearDrawings();
            this.closeContextMenu();
        },
        // Clear all overlays on escape/context close
        handleGlobalClick() {
            if (this.showContextMenu) {
                this.closeContextMenu();
            }
        },

        handleMapPointerMove(evt) {
            if (!this.map) return;
            const lonLat = toLonLat(evt.coordinate);
            this.cursorCoords = [lonLat[0], lonLat[1]];
            if (this.isBearingMode && !evt.dragging) {
                this.updateBearingPointerUi(evt);
            }
            if (evt.dragging || this.isDrawing || this.isMeasuring) return;

            const pixel = this.map.getEventPixel(evt.originalEvent);
            if (this._pointerMoveRaf != null) {
                this._pendingPointerPixel = pixel;
                return;
            }
            this._pendingPointerPixel = pixel;
            this._pointerMoveRaf = requestAnimationFrame(() => {
                this._pointerMoveRaf = null;
                const p = this._pendingPointerPixel;
                this._pendingPointerPixel = null;
                if (!this.map || !p) return;

                const feature = this.map.forEachFeatureAtPixel(p, (f) => f, {
                    hitTolerance: MAP_FEATURE_HIT_TOLERANCE,
                });

                if (feature) {
                    const hasNote = feature.get("note") || (feature.get("telemetry") && feature.get("telemetry").note);
                    if (hasNote) {
                        this.hoveredFeature = feature;
                    } else {
                        this.hoveredFeature = null;
                    }

                    const isMarker = feature.get("telemetry") || feature.get("discovered") || feature.get("cluster");
                    if (isMarker && this.hoveredMarker !== feature) {
                        const oldHovered = this.hoveredMarker;
                        this.hoveredMarker = feature;
                        feature.changed();
                        if (oldHovered) oldHovered.changed();
                    }

                    this.map.getTargetElement().style.cursor = "pointer";
                } else {
                    this.hoveredFeature = null;
                    if (this.hoveredMarker) {
                        const oldHovered = this.hoveredMarker;
                        this.hoveredMarker = null;
                        oldHovered.changed();
                    }
                    this.map.getTargetElement().style.cursor = "";
                }
            });
        },

        handleMapClick(evt) {
            if (this.isDrawing || this.isMeasuring || this.isBearingMode) return;

            const pixel = this.map.getEventPixel(evt.originalEvent);
            const feature = this.map.forEachFeatureAtPixel(pixel, (f) => f, {
                layerFilter: (l) => l === this.drawLayer,
                hitTolerance: MAP_FEATURE_HIT_TOLERANCE,
            });

            if (feature && feature.get("type") === "note") {
                this.startEditingNote(feature);
            } else {
                this.closeNoteEditor();
            }
        },

        stopDrawing() {
            this.stopBearingMode();
            if (this.draw) {
                this.map.removeInteraction(this.draw);
                this.draw = null;
            }
            if (this.select) this.select.setActive(true);
            if (this.translate) this.translate.setActive(true);
            if (this.modify) this.modify.setActive(true);
            this.drawType = null;
            this.isDrawing = false;
            this.stopMeasuring();
        },

        clearDrawings() {
            if (confirm("Clear all drawings from the map?")) {
                this.drawSource.clear();
                if (this.select) {
                    this.select.getFeatures().clear();
                }
                this.selectedFeature = null;
                this.syncDrawFeatureInfoOverlay();
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

        stopBearingMode() {
            if (!this.isBearingMode) {
                return;
            }
            this.removeBearingPreview();
            this.cleanupBearingTooltips();
            this.isBearingMode = false;
            this.bearingFromGps = false;
            this.bearingGpsMapCoord = null;
            this.bearingFirstMapCoord = null;
            if (this.drawType === "Bearing") {
                this.drawType = null;
            }
            if (this.select) {
                this.select.setActive(true);
            }
            if (this.translate) {
                this.translate.setActive(true);
            }
            if (this.modify) {
                this.modify.setActive(true);
            }
        },

        cleanupBearingTooltips() {
            this.cleanupMeasureTooltip();
            if (this.helpTooltip && this.map) {
                this.map.removeOverlay(this.helpTooltip);
                this.helpTooltip = null;
            }
            this.helpTooltipElement = null;
        },

        setupBearingTooltips() {
            if (!this.map) {
                return;
            }
            this.cleanupBearingTooltips();
            this.createHelpTooltip();
            this.createMeasureTooltip();
            if (this.helpTooltipElement) {
                this.helpTooltipElement.classList.remove("hidden");
            }
        },

        toggleBearingMode() {
            if (!this.map) {
                return;
            }
            if (this.isBearingMode) {
                this.stopBearingMode();
                return;
            }
            this.stopDrawing();
            this.isMeasuring = false;
            this.bearingFromGps = false;
            this.bearingGpsMapCoord = null;
            this.bearingFirstMapCoord = null;
            this.isBearingMode = true;
            this.drawType = "Bearing";
            if (this.select) {
                this.select.setActive(false);
            }
            if (this.translate) {
                this.translate.setActive(false);
            }
            if (this.modify) {
                this.modify.setActive(false);
            }
            this.setupBearingTooltips();
        },

        async resolveMyLocationWgs84() {
            if (this.config?.location_source === "manual") {
                const lat = parseFloat(this.config.location_manual_lat);
                const lon = parseFloat(this.config.location_manual_lon);
                if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
                    return { lon, lat };
                }
            }
            if (this.config && this.config.identity_hash) {
                const myTelemetry = this.telemetryList.find((t) => t.destination_hash === this.config.identity_hash);
                if (myTelemetry && myTelemetry.telemetry?.location) {
                    const loc = myTelemetry.telemetry.location;
                    if (loc.longitude != null && loc.latitude != null) {
                        return { lon: loc.longitude, lat: loc.latitude };
                    }
                }
            }
            if (!navigator.geolocation) {
                return null;
            }
            return new Promise((resolve) => {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        resolve({ lon: pos.coords.longitude, lat: pos.coords.latitude });
                    },
                    () => resolve(null),
                    { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
                );
            });
        },

        async startBearingFromMyLocation() {
            if (!this.map) {
                return;
            }
            const loc = await this.resolveMyLocationWgs84();
            if (!loc) {
                ToastUtils.warning(this.$t("map.location_not_determined"));
                return;
            }
            this.stopDrawing();
            this.bearingFirstMapCoord = null;
            this.removeBearingPreview();
            this.isBearingMode = true;
            this.bearingFromGps = true;
            this.bearingGpsMapCoord = fromLonLat([loc.lon, loc.lat]);
            this.drawType = "Bearing";
            if (this.select) {
                this.select.setActive(false);
            }
            if (this.translate) {
                this.translate.setActive(false);
            }
            if (this.modify) {
                this.modify.setActive(false);
            }
            this.setupBearingTooltips();
        },

        handleBearingClick(evt) {
            const coord = evt.coordinate;
            if (this.bearingFromGps && this.bearingGpsMapCoord) {
                this.finishBearingSegment(this.bearingGpsMapCoord, coord);
                return;
            }
            if (!this.bearingFirstMapCoord) {
                this.bearingFirstMapCoord = coord;
                return;
            }
            this.finishBearingSegment(this.bearingFirstMapCoord, coord);
        },

        finishBearingSegment(startMapCoord, endMapCoord) {
            if (!this.map || !this.drawSource) {
                return;
            }
            const ll0 = toLonLat(startMapCoord);
            const ll1 = toLonLat(endMapCoord);
            const metrics = computeSegmentMetrics(ll0[0], ll0[1], ll1[0], ll1[1]);
            this.removeBearingPreview();
            const line = new LineString([startMapCoord, endMapCoord]);
            const feature = new Feature({
                geometry: line,
                type: "draw",
                segmentKind: "bearing",
                bearingMetrics: metrics,
            });
            this.drawSource.addFeature(feature);
            this.finalizeMeasurementOverlay(feature);
            this.stopBearingMode();
            if (this.select) {
                this.select.setActive(true);
            }
            if (this.translate) {
                this.translate.setActive(true);
            }
            if (this.modify) {
                this.modify.setActive(true);
            }
            setTimeout(() => this.saveMapState(), 100);
        },

        removeBearingPreview() {
            if (this.bearingPreviewFeature && this.drawSource) {
                this.drawSource.removeFeature(this.bearingPreviewFeature);
            }
            this.bearingPreviewFeature = null;
        },

        ensureBearingPreviewLine(endMapCoord) {
            if (!this.drawSource) {
                return;
            }
            const origin = this.bearingFromGps ? this.bearingGpsMapCoord : this.bearingFirstMapCoord;
            if (!origin) {
                return;
            }
            if (!this.bearingPreviewFeature) {
                const f = new Feature({
                    geometry: new LineString([origin, endMapCoord]),
                    type: "draw",
                    bearingPreview: true,
                });
                f.setStyle(
                    new Style({
                        stroke: new Stroke({
                            color: "rgba(13, 148, 136, 0.85)",
                            width: 2,
                            lineDash: [8, 6],
                        }),
                    })
                );
                this.drawSource.addFeature(f);
                this.bearingPreviewFeature = f;
            } else {
                /** @type {import("ol/geom/LineString").default} */ (
                    this.bearingPreviewFeature.getGeometry()
                ).setCoordinates([origin, endMapCoord]);
            }
        },

        updateBearingPointerUi(evt) {
            const origin = this.bearingFromGps ? this.bearingGpsMapCoord : this.bearingFirstMapCoord;
            if (this.helpTooltip && this.helpTooltipElement) {
                const msg = !origin ? this.$t("map.bearing_help_first") : this.$t("map.bearing_help_drag");
                this.helpTooltipElement.textContent = msg;
                this.helpTooltip.setPosition(evt.coordinate);
                this.helpTooltipElement.classList.remove("hidden");
            }
            if (!origin) {
                return;
            }
            this.ensureBearingPreviewLine(evt.coordinate);
            const ll0 = toLonLat(origin);
            const ll1 = toLonLat(evt.coordinate);
            const metrics = computeSegmentMetrics(ll0[0], ll0[1], ll1[0], ll1[1]);
            if (!this.measureTooltipElement || !this.measureTooltip) {
                this.createMeasureTooltip();
            }
            if (this.measureTooltipElement && this.measureTooltip) {
                this.measureTooltipElement.className = "ol-tooltip ol-tooltip-measure";
                this.measureTooltipElement.innerHTML = buildBearingLiveTooltipHtml(metrics, (k) => this.$t(k));
                this.measureTooltip.setPosition(evt.coordinate);
            }
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
                const response = await window.api.get("/api/v1/map/drawings");
                this.savedDrawings = response.data.drawings;
            } catch {
                ToastUtils.error(this.$t("map.failed_load_drawings"));
            } finally {
                this.isLoadingDrawings = false;
            }
        },

        async saveDrawing() {
            if (!this.newDrawingName.trim()) return;
            if (!this.drawSource) {
                ToastUtils.error(this.$t("map.not_initialized"));
                return;
            }

            const format = new GeoJSON();
            const features = this.serializeFeatures(this.drawSource.getFeatures());
            const json = format.writeFeatures(features, {
                dataProjection: "EPSG:4326",
                featureProjection: "EPSG:3857",
            });

            try {
                await window.api.post("/api/v1/map/drawings", {
                    name: this.newDrawingName,
                    data: json,
                });
                ToastUtils.success(this.$t("map.drawing_saved"));
                this.showSaveDrawingModal = false;
                this.newDrawingName = "";
            } catch {
                ToastUtils.error(this.$t("map.failed_save_drawing"));
            }
        },

        async loadDrawing(drawing) {
            const format = new GeoJSON();
            const features = format.readFeatures(drawing.data, {
                dataProjection: "EPSG:4326",
                featureProjection: "EPSG:3857",
            });
            this.drawSource.clear();
            if (this.select) {
                this.select.getFeatures().clear();
            }
            this.selectedFeature = null;
            this.syncDrawFeatureInfoOverlay();
            this.drawSource.addFeatures(features);
            this.rebuildMeasurementOverlays();
            await this.saveMapState();
            this.showLoadDrawingModal = false;
            ToastUtils.success(`Loaded "${drawing.name}"`);
        },

        onVectorExchangeImport({ features, merge }) {
            if (!this.drawSource || !features?.length) {
                ToastUtils.warning(this.$t("map.vector_import_empty"));
                return;
            }
            if (!merge) {
                this.drawSource.clear();
                if (this.select) {
                    this.select.getFeatures().clear();
                }
                this.selectedFeature = null;
                this.syncDrawFeatureInfoOverlay();
            }
            for (const f of features) {
                if (f.get("type") == null || f.get("type") === "") {
                    f.set("type", "draw");
                }
            }
            this.drawSource.addFeatures(features);
            this.rebuildMeasurementOverlays();
            this.saveMapState();
            ToastUtils.success(this.$t("map.vector_import_ok", { count: features.length }));
        },

        onVectorExchangeImportError() {
            ToastUtils.error(this.$t("map.vector_import_failed"));
        },

        onMapDragOver(ev) {
            if (ev.dataTransfer && ev.dataTransfer.types.includes("Files")) {
                this.isMapDropTarget = true;
            }
        },
        onMapDragLeave() {
            this.isMapDropTarget = false;
        },
        async onMapDrop(ev) {
            this.isMapDropTarget = false;
            const files = Array.from(ev.dataTransfer?.files || []);
            if (!files.length) return;

            const mbtilesFiles = files.filter((f) => this.isMbtilesFile(f));
            const geoFiles = files.filter((f) => {
                const name = f.name.toLowerCase();
                return (
                    name.endsWith(".geojson") ||
                    name.endsWith(".json") ||
                    name.endsWith(".kml") ||
                    name.endsWith(".kmz")
                );
            });
            if (!mbtilesFiles.length && !geoFiles.length) {
                ToastUtils.warning(this.$t("map.drop_no_supported_files"));
                return;
            }

            for (const file of mbtilesFiles) {
                await this.uploadMbtilesFile(file);
            }

            for (const file of geoFiles) {
                try {
                    const name = file.name.toLowerCase();
                    let features = [];
                    if (name.endsWith(".kmz")) {
                        const buf = await this.readFileArrayBuffer(file);
                        features = await readKmzToFeatures(buf, "EPSG:3857");
                    } else if (name.endsWith(".kml")) {
                        const text = await this.readFileText(file);
                        features = readKmlToFeatures(text, "EPSG:3857");
                    } else {
                        const text = await this.readFileText(file);
                        features = readGeoJsonToFeatures(text, "EPSG:3857");
                    }
                    this.onVectorExchangeImport({ features, merge: true });
                } catch (e) {
                    console.error("Map drop import failed:", e);
                    ToastUtils.error(this.$t("map.vector_import_failed") + ` — ${file.name}`);
                }
            }
        },
        readFileText(file) {
            return new Promise((resolve, reject) => {
                const r = new FileReader();
                r.onload = () => resolve(String(r.result || ""));
                r.onerror = () => reject(new Error("read failed"));
                r.readAsText(file);
            });
        },
        readFileArrayBuffer(file) {
            return new Promise((resolve, reject) => {
                const r = new FileReader();
                r.onload = () => resolve(/** @type {ArrayBuffer} */ (r.result));
                r.onerror = () => reject(new Error("read failed"));
                r.readAsArrayBuffer(file);
            });
        },

        exportVectorGeoJson() {
            if (!this.drawSource || !this.hasVectorDrawFeatures) {
                return;
            }
            const raw = this.drawSource.getFeatures();
            const features = this.serializeFeatures(raw);
            const text = writeFeaturesToGeoJson(features, "EPSG:3857");
            const name = `meshchatx-drawings-${new Date().toISOString().slice(0, 10)}.geojson`;
            this.downloadTextFile(name, text, "application/geo+json");
            ToastUtils.success(this.$t("map.vector_export_ok"));
        },

        exportVectorKml() {
            if (!this.drawSource || !this.hasVectorDrawFeatures) {
                return;
            }
            const raw = this.drawSource.getFeatures();
            const features = this.serializeFeatures(raw);
            const text = writeFeaturesToKml(features, "EPSG:3857");
            const name = `meshchatx-drawings-${new Date().toISOString().slice(0, 10)}.kml`;
            this.downloadTextFile(name, text, "application/vnd.google-earth.kml+xml");
            ToastUtils.success(this.$t("map.vector_export_ok"));
        },

        async exportVectorKmz() {
            if (!this.drawSource || !this.hasVectorDrawFeatures) {
                return;
            }
            const raw = this.drawSource.getFeatures();
            const features = this.serializeFeatures(raw);
            try {
                const blob = await writeFeaturesToKmzBlob(features, "EPSG:3857");
                const name = `meshchatx-drawings-${new Date().toISOString().slice(0, 10)}.kmz`;
                this.downloadBlobFile(name, blob, "application/vnd.google-earth.kmz");
                ToastUtils.success(this.$t("map.vector_export_ok"));
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("map.vector_import_failed"));
            }
        },

        downloadBlobFile(filename, blob, mime) {
            const b = new Blob([blob], { type: mime });
            const url = URL.createObjectURL(b);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            a.rel = "noopener";
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        },

        downloadTextFile(filename, text, mime) {
            const blob = new Blob([text], { type: mime });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            a.rel = "noopener";
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        },

        async deleteDrawing(drawing) {
            if (!confirm(`Delete drawing "${drawing.name}"?`)) return;
            try {
                await window.api.delete(`/api/v1/map/drawings/${drawing.id}`);
                this.savedDrawings = this.savedDrawings.filter((d) => d.id !== drawing.id);
                ToastUtils.success(this.$t("map.deleted"));
            } catch {
                ToastUtils.error(this.$t("map.failed_delete"));
            }
        },

        goToMyLocation() {
            // Priority 1: Use manual location if configured
            if (this.config?.location_source === "manual") {
                const lat = parseFloat(this.config.location_manual_lat);
                const lon = parseFloat(this.config.location_manual_lon);
                if (!isNaN(lat) && !isNaN(lon)) {
                    this.map.getView().animate({
                        center: fromLonLat([lon, lat]),
                        zoom: 15,
                        duration: 1000,
                    });
                    return;
                }
            }

            // Priority 2: Use telemetry data if available for our own hash
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
                        ToastUtils.warning(this.$t("map.location_not_determined"));
                    }
                );
            } else {
                ToastUtils.warning(this.$t("map.geolocation_not_supported"));
            }
        },
        async fetchTelemetryMarkers() {
            if (!window.api) return;
            try {
                const response = await window.api.get("/api/v1/telemetry/peers");
                this.telemetryList = response.data.telemetry;
                this.updateMarkers();
            } catch (e) {
                console.error("Failed to fetch telemetry", e);
            }
        },
        dedupeTelemetryMarkersForMap(telemetryList) {
            return dedupeTelemetryMarkersForMapHelper(telemetryList, this.peers || {});
        },
        dedupeDiscoveredMapNodes(nodes) {
            return dedupeDiscoveredMapNodesHelper(nodes);
        },
        updateMarkers() {
            if (!this.markerSource) return;
            this.markerSource.clear();

            const candidates = [];

            for (const t of this.dedupeTelemetryMarkersForMap(this.telemetryList)) {
                const loc = t.telemetry?.location;
                if (!loc || loc.latitude === undefined || loc.longitude === undefined) continue;
                const coord = fromLonLat([loc.longitude, loc.latitude]);
                const feature = new Feature({
                    geometry: new Point(coord),
                    telemetry: t,
                    peer: this.peers[t.destination_hash],
                    originalCoord: coord,
                });
                candidates.push({ feature, coord, clusterable: true });
            }

            if (this.discoveredMarkers && this.discoveredMarkers.length > 0) {
                for (const feature of this.discoveredMarkers) {
                    const coord = feature.get("originalCoord") || feature.getGeometry().getCoordinates();
                    if (!feature.get("originalCoord")) feature.set("originalCoord", coord);
                    candidates.push({ feature, coord, clusterable: true });
                }
            }

            const view = this.map.getView();
            const resolution = view && typeof view.getResolution === "function" ? view.getResolution() : 1;
            const safeResolution = Number.isFinite(resolution) && resolution > 0 ? resolution : 1;
            const clusterPixelDistance = 38;
            const clusterCoordDistance = clusterPixelDistance * safeResolution;
            const sqClusterCoordDistance = clusterCoordDistance * clusterCoordDistance;

            const visited = new Array(candidates.length).fill(false);
            for (let i = 0; i < candidates.length; i++) {
                if (visited[i]) continue;
                visited[i] = true;
                const seed = candidates[i];
                const groupItems = [seed];

                if (seed.clusterable) {
                    for (let j = i + 1; j < candidates.length; j++) {
                        if (visited[j] || !candidates[j].clusterable) continue;
                        const dx = candidates[j].coord[0] - seed.coord[0];
                        const dy = candidates[j].coord[1] - seed.coord[1];
                        if (dx * dx + dy * dy <= sqClusterCoordDistance) {
                            visited[j] = true;
                            groupItems.push(candidates[j]);
                        }
                    }
                }

                if (groupItems.length === 1) {
                    const feature = seed.feature;
                    const originalCoord = feature.get("originalCoord") || seed.coord;
                    feature.setGeometry(new Point(originalCoord));
                    this.markerSource.addFeature(feature);
                    continue;
                }

                let cx = 0;
                let cy = 0;
                for (const item of groupItems) {
                    cx += item.coord[0];
                    cy += item.coord[1];
                }
                cx /= groupItems.length;
                cy /= groupItems.length;

                const clusterFeature = new Feature({
                    geometry: new Point([cx, cy]),
                    cluster: true,
                    clusterCount: groupItems.length,
                    clusterItems: groupItems.map((g) => g.feature),
                    originalCoord: [cx, cy],
                });
                this.markerSource.addFeature(clusterFeature);
            }

            if (this.queryMarker) {
                const coord = this.queryMarker.get("originalCoord") || this.queryMarker.getGeometry().getCoordinates();
                if (!this.queryMarker.get("originalCoord")) this.queryMarker.set("originalCoord", coord);
                this.queryMarker.setGeometry(new Point(coord));
                this.markerSource.addFeature(this.queryMarker);
            }
        },
        createClusterStyle(count, isHovered) {
            const cacheKey = `cluster-${count}-${isHovered ? "h" : "n"}`;
            if (this.styleCache[cacheKey]) return this.styleCache[cacheKey];

            const radius = isHovered ? 20 : 18;
            const style = new Style({
                image: new CircleStyle({
                    radius,
                    fill: new Fill({ color: "rgba(37, 99, 235, 0.92)" }),
                    stroke: new Stroke({ color: "#ffffff", width: 2 }),
                }),
                text: new Text({
                    text: String(count),
                    font: "bold 13px sans-serif",
                    fill: new Fill({ color: "#ffffff" }),
                    stroke: new Stroke({ color: "rgba(0,0,0,0.35)", width: 1 }),
                }),
            });
            this.styleCache[cacheKey] = style;
            return style;
        },
        buildClusterItems(feature) {
            return buildClusterItemsHelper(feature);
        },
        /**
         * Open the cluster details overlay and zoom the viewport to encompass
         * the cluster's items. Always called when a user clicks a cluster
         * marker on the map.
         */
        openCluster(feature) {
            if (!feature) return;
            const items = this.buildClusterItems(feature);
            this.selectedMarker = null;
            this.selectedCluster = {
                count: items.length || feature.get("clusterCount") || 0,
                items,
            };
            this.zoomToCluster(feature);
        },
        closeClusterPanel() {
            this.selectedCluster = null;
        },
        selectClusterItem(item) {
            if (!item || !item.feature) return;
            const view = this.map ? this.map.getView() : null;
            const coord = item.coord;
            if (view && coord && Array.isArray(coord) && coord.length >= 2) {
                const currentZoom = (typeof view.getZoom === "function" && view.getZoom()) || 12;
                if (typeof view.animate === "function") {
                    view.animate({
                        center: coord,
                        zoom: Math.min(currentZoom + 2, 19),
                        duration: 300,
                    });
                }
            }
            this.onMarkerClick(item.feature);
            this.selectedCluster = null;
        },
        extentDiagonal(extent) {
            return computeExtentDiagonal(extent);
        },
        /**
         * Smoothly zoom the viewport to fit a cluster's contents. Handles the
         * tricky cases that previously made clustering feel "weird":
         *   - all items at the same coordinate -> animate-zoom to that point
         *   - cluster spans less than ~1px       -> treat as point
         *   - cluster fits in the current view   -> still zoom in (don't sit
         *     at the same zoom level after a click)
         *   - very large clusters                -> respect a sensible maxZoom
         */
        zoomToCluster(feature) {
            if (!feature || !this.map) return;
            const items = feature.get("clusterItems") || [];
            if (items.length === 0) return;

            const view = this.map.getView();
            const currentZoom = (typeof view.getZoom === "function" && view.getZoom()) || 12;
            const viewMaxZoom = typeof view.getMaxZoom === "function" ? view.getMaxZoom() : 19;
            const safeMaxZoom = Number.isFinite(viewMaxZoom) ? viewMaxZoom : 19;

            const extent = createEmptyExtent();
            const coords = [];
            for (const item of items) {
                const coord =
                    item.get("originalCoord") ||
                    (typeof item.getGeometry === "function" && item.getGeometry()
                        ? item.getGeometry().getCoordinates()
                        : null);
                if (coord && Array.isArray(coord) && coord.length >= 2) {
                    coords.push(coord);
                    extendCoordinate(extent, coord);
                }
            }

            if (coords.length === 0) return;

            const resolution = typeof view.getResolution === "function" ? view.getResolution() : 1;
            const safeResolution = Number.isFinite(resolution) && resolution > 0 ? resolution : 1;
            const diagonal = this.extentDiagonal(extent);
            const isDegenerate = isExtentEmpty(extent) || diagonal <= safeResolution;

            if (isDegenerate) {
                let cx = 0;
                let cy = 0;
                for (const c of coords) {
                    cx += c[0];
                    cy += c[1];
                }
                cx /= coords.length;
                cy /= coords.length;
                const targetZoom = Math.min(currentZoom + 4, safeMaxZoom);
                if (typeof view.animate === "function") {
                    view.animate({ center: [cx, cy], zoom: targetZoom, duration: 400 });
                } else {
                    if (typeof view.setCenter === "function") view.setCenter([cx, cy]);
                    if (typeof view.setZoom === "function") view.setZoom(targetZoom);
                }
                return;
            }

            if (typeof view.fit === "function") {
                view.fit(extent, {
                    padding: [80, 80, 80, 80],
                    maxZoom: Math.min(currentZoom + 3, safeMaxZoom),
                    duration: 400,
                });
            }

            this.$nextTick(() => {
                const newZoom = (typeof view.getZoom === "function" && view.getZoom()) || currentZoom;
                if (newZoom <= currentZoom + 0.01) {
                    const targetZoom = Math.min(currentZoom + 1, safeMaxZoom);
                    if (typeof view.animate === "function") {
                        view.animate({ zoom: targetZoom, duration: 250 });
                    } else if (typeof view.setZoom === "function") {
                        view.setZoom(targetZoom);
                    }
                }
            });
        },
        createMarkerStyle({ iconColor, bgColor, label, isStale, iconPath, scale = 0.6, isTracking = false }) {
            const cacheKey = `${iconColor}-${bgColor}-${label}-${isStale}-${iconPath || "default"}-${scale}-${isTracking}`;
            if (this.styleCache[cacheKey]) return this.styleCache[cacheKey];

            const markerFill = isStale ? "#d1d5db" : bgColor;
            const markerStroke = isStale ? "#9ca3af" : iconColor;
            const path =
                iconPath ||
                "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7Zm0 11a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z";

            const baseSize = isTracking ? 32 : 24;
            const renderSize = baseSize * 2;

            let svg = "";
            if (isTracking) {
                svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${renderSize}" height="${renderSize}" viewBox="0 0 32 32">
                    <circle cx="16" cy="16" r="10" fill="none" stroke="#3b82f6" stroke-width="2">
                        <animate attributeName="r" from="10" to="15" dur="1.5s" repeatCount="indefinite" />
                        <animate attributeName="stroke-opacity" from="1" to="0" dur="1.5s" repeatCount="indefinite" />
                    </circle>
                    <circle cx="16" cy="16" r="10" fill="#3b82f6" fill-opacity="0.2">
                        <animate attributeName="r" from="8" to="12" dur="1.5s" repeatCount="indefinite" />
                    </circle>
                    <g transform="translate(4,4)">
                        <path d="${path}" fill="${markerFill}" stroke="${markerStroke}" stroke-width="1.5"/>
                    </g>
                </svg>`;
            } else {
                svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${renderSize}" height="${renderSize}" viewBox="0 0 24 24"><path d="${path}" fill="${markerFill}" stroke="${markerStroke}" stroke-width="1.5"/></svg>`;
            }

            const svgBytes = new TextEncoder().encode(svg);
            let svgBinary = "";
            const chunkSize = 8192;
            for (let i = 0; i < svgBytes.length; i += chunkSize) {
                const sub = svgBytes.subarray(i, i + chunkSize);
                svgBinary += String.fromCharCode(...sub);
            }
            const src = "data:image/svg+xml;base64," + btoa(svgBinary);

            const displayHeight = renderSize * scale;
            const labelOffset = -(displayHeight + 6);

            const style = new Style({
                image: new Icon({
                    src: src,
                    anchor: [0.5, 1],
                    scale: scale,
                    imgSize: [renderSize, renderSize],
                }),
                text: new Text({
                    text: label,
                    offsetY: labelOffset,
                    font: "bold 12px sans-serif",
                    fill: new Fill({ color: isStale ? "#6b7280" : "#111827" }),
                    stroke: new Stroke({ color: "#ffffff", width: 3 }),
                }),
            });

            this.styleCache[cacheKey] = style;
            return style;
        },
        onMarkerClick(feature) {
            this.selectedMarker = {
                telemetry: feature.get("telemetry"),
                peer: feature.get("peer"),
                discovered: feature.get("discovered"),
            };

            // draw path for telemetry markers
            if (this.selectedMarker.telemetry) {
                this.drawTelemetryPath(this.selectedMarker.telemetry.destination_hash);
            } else {
                this.clearTelemetryPath();
            }
        },
        async drawTelemetryPath(hash) {
            this.clearTelemetryPath();
            try {
                const response = await window.api.get(`/api/v1/telemetry/history/${hash}?limit=50`);
                const history = response.data.telemetry;
                if (!history || history.length < 2) return;

                // collect coordinates
                const coords = [];
                for (const entry of history) {
                    const loc = entry.telemetry?.location;
                    if (loc && loc.latitude !== undefined && loc.longitude !== undefined) {
                        coords.push(fromLonLat([loc.longitude, loc.latitude]));
                    }
                }

                if (coords.length < 2) return;

                // create line feature
                const line = new LineString(coords);
                const feature = new Feature({
                    geometry: line,
                    type: "history_trail",
                });

                if (this.historySource) {
                    this.historySource.addFeature(feature);
                }
            } catch (e) {
                console.error("Failed to draw telemetry path", e);
            }
        },
        clearTelemetryPath() {
            if (this.historySource) {
                this.historySource.clear();
            }
        },
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            if (json.type === "lxmf.telemetry") {
                // Find and update or add to telemetryList
                const index = this.telemetryList.findIndex((t) => t.destination_hash === json.destination_hash);
                const oldEntry = index !== -1 ? this.telemetryList[index] : null;
                const entry = {
                    destination_hash: json.destination_hash,
                    timestamp: json.timestamp,
                    telemetry: json.telemetry,
                    updated_at: new Date().toISOString(),
                    is_tracking:
                        json.is_tracking !== undefined ? json.is_tracking : oldEntry ? oldEntry.is_tracking : false,
                    physical_link: json.physical_link || oldEntry?.physical_link,
                };

                if (index !== -1) {
                    this.telemetryList.splice(index, 1, entry);
                } else {
                    this.telemetryList.push(entry);
                }

                // Show notification for tracked peers
                if (entry.telemetry?.location) {
                    const peer = this.peers[json.destination_hash];
                    const name = peer?.display_name || json.destination_hash.substring(0, 8);
                    const isTracked = this.telemetryList.find(
                        (t) => t.destination_hash === json.destination_hash
                    )?.is_tracking;

                    if (isTracked) {
                        ToastUtils.info(
                            `Live update: ${name} is at ${entry.telemetry.location.latitude.toFixed(4)}, ${entry.telemetry.location.longitude.toFixed(4)}`
                        );
                    }

                    // Update trail if this marker is currently selected
                    if (this.selectedMarker?.telemetry?.destination_hash === json.destination_hash) {
                        this.drawTelemetryPath(json.destination_hash);
                    }
                }

                this.updateMarkers();
            }
        },
        formatTimestamp(ts) {
            return new Date(ts * 1000).toLocaleString();
        },
        getMdiPath(iconName) {
            if (!iconName) return null;
            const path = getMdiIconPath(iconName);
            return path || null;
        },
        openChat(hash) {
            this.$router.push({
                name: "messages",
                params: { destinationHash: hash },
            });
        },
        async toggleTracking(hash) {
            try {
                const response = await window.api.post(`/api/v1/telemetry/tracking/${hash}/toggle`, {
                    is_tracking: this.selectedMarker.telemetry.is_tracking ? false : true,
                });
                if (this.selectedMarker && this.selectedMarker.telemetry.destination_hash === hash) {
                    this.selectedMarker.telemetry.is_tracking = response.data.is_tracking;
                }
                // Also update in telemetryList
                const t = this.telemetryList.find((t) => t.destination_hash === hash);
                if (t) t.is_tracking = response.data.is_tracking;

                ToastUtils.success(response.data.is_tracking ? "Live tracking enabled" : "Live tracking disabled");
            } catch (e) {
                console.error("Failed to toggle tracking", e);
                ToastUtils.error("Failed to update tracking status");
            }
        },
        async toggleDiscoveredNodes() {
            if (this.discoveredVisible) {
                this.hideDiscoveredNodes();
                return;
            }
            await this.mapDiscoveredNodes();
        },
        hideDiscoveredNodes() {
            this.discoveredMarkers = [];
            this.discoveredVisible = false;
            if (this.selectedMarker?.discovered) {
                this.selectedMarker = null;
                this.clearTelemetryPath();
            }
            this.updateMarkers();
        },
        getDiscoveredIconName(node) {
            return getDiscoveredIconNameHelper(node);
        },
        async mapDiscoveredNodes(options = {}) {
            const skipFit = options.skipFit === true;
            const silent = options.silent === true;
            try {
                const response = await window.api.get("/api/v1/reticulum/discovered-interfaces");
                const discovered = response.data?.interfaces ?? [];
                const nodesWithLoc = discovered.filter((n) => n.latitude != null && n.longitude != null);
                const nodesDeduped = this.dedupeDiscoveredMapNodes(nodesWithLoc);

                if (nodesDeduped.length === 0) {
                    if (!silent) {
                        ToastUtils.info(this.$t("map.no_nodes_location"));
                    }
                    return;
                }

                const extent = createEmptyExtent();
                this.discoveredMarkers = [];

                for (const node of nodesDeduped) {
                    const coord = fromLonLat([node.longitude, node.latitude]);
                    extendExtent(extent, coord);

                    const feature = new Feature({
                        geometry: new Point(coord),
                        originalCoord: coord,
                        discovered: node,
                    });
                    this.discoveredMarkers.push(feature);
                }

                this.discoveredVisible = true;
                this.updateMarkers();

                if (!skipFit && !isExtentEmpty(extent)) {
                    this.map.getView().fit(extent, {
                        padding: [100, 100, 100, 100],
                        maxZoom: 12,
                        duration: 1000,
                    });
                }

                if (!silent) {
                    ToastUtils.success(`Mapped ${nodesDeduped.length} discovered nodes`);
                }
            } catch (e) {
                console.error("Failed to map discovered nodes", e);
                if (!silent) {
                    ToastUtils.error(this.$t("map.failed_fetch_nodes"));
                }
            }
        },
        openMapPopout() {
            const url = `${window.location.origin}${window.location.pathname}#/popout/map`;
            window.open(url, "_blank", "width=960,height=720,noopener");
        },
        getHashPopoutValue() {
            const hash = window.location.hash || "";
            const match = hash.match(/popout=([^&]+)/);
            return match ? decodeURIComponent(match[1]) : null;
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

.ol-scale-line-host :deep(.ol-scale-line),
.ol-scale-line-host :deep(.ol-scale-bar) {
    position: relative;
    bottom: auto;
    left: auto;
    right: auto;
    top: auto;
    background: rgba(255, 255, 255, 0.85);
    border-radius: 6px;
    padding: 2px 4px;
    max-width: 100%;
}
.dark .ol-scale-line-host :deep(.ol-scale-line),
.dark .ol-scale-line-host :deep(.ol-scale-bar) {
    background: rgba(24, 24, 27, 0.9);
}

.ol-scale-line-host--dark-basemap :deep(.ol-scale-line),
.ol-scale-line-host--dark-basemap :deep(.ol-scale-bar) {
    background: transparent;
    --ol-background-color: rgba(255, 255, 255, 0.14);
    --ol-partial-background-color: transparent;
    --ol-foreground-color: #ffffff;
    --ol-subtle-foreground-color: rgba(255, 255, 255, 0.4);
}

.ol-scale-line-host--dark-basemap :deep(.ol-scale-step-text),
.ol-scale-line-host--dark-basemap :deep(.ol-scale-text) {
    text-shadow:
        0 0 2px rgba(0, 0, 0, 0.9),
        0 1px 3px rgba(0, 0, 0, 0.85);
}

@media (max-width: 639px) {
    :deep(.ol-zoom) {
        left: auto;
        right: 0.75rem;
        top: auto;
        bottom: 0.75rem;
        z-index: 12;
    }
}
</style>
