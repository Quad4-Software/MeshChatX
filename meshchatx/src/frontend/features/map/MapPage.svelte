<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import Map from "ol/Map";
    import View from "ol/View";
    import { fromLonLat, toLonLat } from "ol/proj";
    import VectorLayer from "ol/layer/Vector";
    import VectorSource from "ol/source/Vector";
    import TileLayer from "ol/layer/Tile";
    import { Draw, Modify, Snap } from "ol/interaction";
    import GeoJSON from "ol/format/GeoJSON";

    import MapHeaderBar from "./components/MapHeaderBar.svelte";
    import MapDrawingToolbar from "./components/MapDrawingToolbar.svelte";
    import MapBearingInstructions from "./components/MapBearingInstructions.svelte";
    import MapSearchBar from "./components/MapSearchBar.svelte";
    import MapMarkerPanel from "./components/MapMarkerPanel.svelte";
    import MapClusterPanel from "./components/MapClusterPanel.svelte";
    import MapSettingsPanel from "./components/MapSettingsPanel.svelte";
    import MapDrawFeatureInfoPanel from "./components/MapDrawFeatureInfoPanel.svelte";
    import MapToolsDrawer from "./components/MapToolsDrawer.svelte";
    import MapSaveDrawingModal from "./components/MapSaveDrawingModal.svelte";
    import MapLoadDrawingModal from "./components/MapLoadDrawingModal.svelte";
    import MapContextMenu from "./components/MapContextMenu.svelte";
    import MapMobileNoteModal from "./components/MapMobileNoteModal.svelte";
    import MapLoadingOverlay from "./components/MapLoadingOverlay.svelte";

    import { t } from "../../js/i18n.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import GlobalState from "../../js/GlobalState.js";
    import TileCache from "../../js/TileCache.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import { mapViewStateKey } from "../../js/mapStateKeys.js";
    import { formatCoordinate } from "../../js/mapGeoCoords.js";

    import {
        createDrawingStyle,
        createMeasureStyle,
        createOnlineTileSource,
        createOfflineMBTilesSource,
    } from "./lib/mapOpenLayers.js";
    import { resolveMyLocationWgs84, calculateAzimuth } from "./lib/mapActions.js";
    import {
        fetchTelemetryMarkers,
        fetchPeers,
        fetchDiscoveredNodes,
        loadMBTilesList,
        setActiveMBTiles,
        deleteMBTiles,
        restoreStarterTiles,
        saveMBTilesDir,
        loadDrawings,
        saveDrawing,
        deleteDrawing,
        startExport,
        getExportStatus,
        sendMapPing,
    } from "./lib/mapService.js";
    import {
        createPeerFeatures,
        createDiscoveredFeatures,
        getContextMenuCoordRows,
        extractDrawFeaturePayload,
    } from "./lib/mapPageHelpers.js";
    import type { DrawingTool, DrawingEntry, MBTilesEntry, MapExportStatus, SearchResult } from "./lib/types.js";

    interface Props {
        embedded?: boolean;
        tabStorageId?: string;
        tabTitle?: string;
        isActiveTab?: boolean;
        onupdatetitle?: (title: string) => void;
        onUpdateTitle?: (title: string) => void;
    }

    let {
        embedded = false,
        tabStorageId = "",
        tabTitle = "",
        isActiveTab: _isActiveTab = true,
        onupdatetitle,
        onUpdateTitle,
    }: Props = $props();

    let mapContainer = $state<HTMLDivElement | null>(null);
    let map = $state<Map | null>(null);
    let isMapLoaded = $state(false);

    let offlineEnabled = $state(false);
    let cachingEnabled = $state(true);
    let discoveredVisible = $state(false);
    let clusterMarkersEnabled = $state(false);
    let tileServerUrl = $state("https://tile.openstreetmap.org/{z}/{x}/{y}.png");
    let nominatimApiUrl = $state("https://nominatim.openstreetmap.org/search");
    let coordinateFormat = $state("wgs84");
    let currentZoom = $state(2);
    let centerCoords = $state<[number, number]>([0, 0]);
    let _rotation = $state(0);

    let drawSource = $state<VectorSource | null>(null);
    let drawLayer = $state<VectorLayer<VectorSource> | null>(null);
    let markersSource = $state<VectorSource | null>(null);
    let markersLayer = $state<VectorLayer<VectorSource> | null>(null);
    let discoveredSource = $state<VectorSource | null>(null);
    let discoveredLayer = $state<VectorLayer<VectorSource> | null>(null);
    let measureSource = $state<VectorSource | null>(null);
    let measureLayer = $state<VectorLayer<VectorSource> | null>(null);
    let tileLayer = $state<TileLayer<any> | null>(null);

    let drawInteraction = $state<Draw | null>(null);
    let modifyInteraction = $state<Modify | null>(null);
    let snapInteraction = $state<Snap | null>(null);
    let drawType = $state<string | null>(null);

    let isMeasuring = $state(false);
    let isBearingMode = $state(false);
    let bearingFromGps = $state(false);
    let bearingFirstMapCoord = $state<number[] | null>(null);
    let isExportMode = $state(false);
    let exportMinZoom = $state(0);
    let exportMaxZoom = $state(15);
    let exportBbox = $state<number[] | null>(null);
    let exportStatus = $state<MapExportStatus | null>(null);
    let activeExportId = $state<string | number | null>(null);
    let exportPollTimer: ReturnType<typeof setInterval> | null = null;

    let searchQuery = $state("");
    let searchResults = $state<SearchResult[]>([]);
    let isSearching = $state(false);
    let isSearchFocused = $state(false);
    let searchError = $state<string | null>(null);
    let isMobileScreen = $state(false);

    let isMapToolsOpen = $state(false);
    let isSettingsOpen = $state(false);
    let settingsPanelPos = $state<{ left: number; top: number } | null>(null);
    let showSaveDrawingModal = $state(false);
    let showLoadDrawingModal = $state(false);
    let hasOfflineMap = $state(false);

    let showContextMenu = $state(false);
    let contextMenuPos = $state({ x: 0, y: 0 });
    let contextMenuFeature = $state<any>(null);
    let contextMenuMapCoord = $state<number[] | null>(null);

    let selectedMarker = $state<any>(null);
    let selectedCluster = $state<any>(null);
    let selectedFeature = $state<any>(null);
    let editingFeature = $state<any>(null);
    let noteDraft = $state("");
    let drawFeatureInfoPayload = $state<any>(null);

    let peers = $state<Record<string, any>>({});
    let telemetryList = $state<any[]>([]);
    let trackedHashes = $state<string[]>([]);
    let mbtilesList = $state<MBTilesEntry[]>([]);
    let mbtilesDir = $state("");
    let drawingsList = $state<DrawingEntry[]>([]);
    let saveDrawingNameDraft = $state("");
    let pingDestinationHash = $state("");

    let saveStateTimer: ReturnType<typeof setTimeout> | null = null;
    let telemetryPollTimer: ReturnType<typeof setInterval> | null = null;

    const drawingTools: DrawingTool[] = [
        { type: "Point", icon: "map-marker" },
        { type: "LineString", icon: "vector-line" },
        { type: "Polygon", icon: "vector-polygon" },
        { type: "Circle", icon: "vector-circle" },
        { type: "Text", icon: "format-text" },
    ];

    let formattedDisplayCoords = $derived(formatCoordinate(centerCoords[1], centerCoords[0], coordinateFormat));
    let hasVectorDrawFeatures = $derived(Boolean(drawSource && drawSource.getFeatures().length > 0));
    let trackedPeersList = $derived(trackedHashes.map((h) => ({ destination_hash: h })));
    let contextMenuCoordRows = $derived(getContextMenuCoordRows(contextMenuMapCoord));

    function getStorageKey(): string {
        const idHash = (GlobalState.config as any)?.identity_hash || null;
        return mapViewStateKey(idHash, tabStorageId || null);
    }

    async function loadSavedState() {
        try {
            const key = getStorageKey();
            const saved = await TileCache.getMapState(key);
            if (saved) {
                if (saved.center && saved.zoom !== undefined && map) {
                    map.getView().setCenter(fromLonLat(saved.center));
                    map.getView().setZoom(saved.zoom);
                }
                if (saved.offlineEnabled !== undefined) offlineEnabled = saved.offlineEnabled;
                if (saved.cachingEnabled !== undefined) cachingEnabled = saved.cachingEnabled;
                if (saved.tileServerUrl) tileServerUrl = saved.tileServerUrl;
                if (saved.coordinateFormat) coordinateFormat = saved.coordinateFormat;
                if (saved.clusterMarkersEnabled !== undefined) clusterMarkersEnabled = saved.clusterMarkersEnabled;
            }
        } catch {
            // state load best effort
        }
    }

    function saveState() {
        if (saveStateTimer) clearTimeout(saveStateTimer);
        saveStateTimer = setTimeout(async () => {
            if (!map) return;
            const view = map.getView();
            const center = toLonLat(view.getCenter() || [0, 0]);
            const zoom = view.getZoom() || 2;
            const key = getStorageKey();
            await TileCache.setMapState(key, {
                center,
                zoom,
                offlineEnabled,
                cachingEnabled,
                tileServerUrl,
                coordinateFormat,
                clusterMarkersEnabled,
            });
        }, 500);
    }

    function initOpenLayers() {
        if (!mapContainer) return;
        drawSource = new VectorSource();
        drawLayer = new VectorLayer({ source: drawSource, style: createDrawingStyle(), zIndex: 10 });

        markersSource = new VectorSource();
        markersLayer = new VectorLayer({ source: markersSource, zIndex: 15 });

        discoveredSource = new VectorSource();
        discoveredLayer = new VectorLayer({ source: discoveredSource, zIndex: 14 });

        measureSource = new VectorSource();
        measureLayer = new VectorLayer({ source: measureSource, style: createMeasureStyle(), zIndex: 12 });

        tileLayer = new TileLayer({
            source: offlineEnabled
                ? createOfflineMBTilesSource()
                : createOnlineTileSource(tileServerUrl, cachingEnabled),
            zIndex: 1,
        });

        const view = new View({
            center: fromLonLat([0, 20]),
            zoom: 2,
            maxZoom: 19,
        });

        map = new Map({
            target: mapContainer,
            layers: [tileLayer, drawLayer, discoveredLayer, markersLayer, measureLayer],
            view,
            controls: [],
        });

        view.on("change:resolution", () => {
            currentZoom = view.getZoom() || 2;
            saveState();
        });
        view.on("change:center", () => {
            const c = view.getCenter();
            if (c) {
                const lonLat = toLonLat(c);
                centerCoords = [lonLat[0], lonLat[1]];
            }
            saveState();
        });
        view.on("change:rotation", () => {
            _rotation = view.getRotation() || 0;
        });

        (map as any).on("click", handleMapClick);
        (map as any).on("contextmenu", handleMapContextMenu);

        modifyInteraction = new Modify({ source: drawSource });
        snapInteraction = new Snap({ source: drawSource });
        map.addInteraction(modifyInteraction);
        map.addInteraction(snapInteraction);

        isMapLoaded = true;
    }

    function handleMapClick(evt: any) {
        if (showContextMenu) showContextMenu = false;
        if (!map) return;
        if (isBearingMode) {
            handleBearingClick(evt.coordinate);
            return;
        }
        let clickedFeature: any = null;
        map.forEachFeatureAtPixel(evt.pixel, (f) => {
            clickedFeature = f;
            return true;
        });
        if (clickedFeature) {
            const peer = clickedFeature.get("peer");
            const cluster = clickedFeature.get("cluster");
            if (cluster) {
                selectedCluster = cluster;
                selectedMarker = null;
                selectedFeature = null;
                return;
            }
            if (peer) {
                selectedMarker = peer;
                selectedCluster = null;
                selectedFeature = null;
                return;
            }
            selectedFeature = clickedFeature;
            drawFeatureInfoPayload = extractDrawFeaturePayload(clickedFeature);
        } else {
            selectedMarker = null;
            selectedCluster = null;
            selectedFeature = null;
            drawFeatureInfoPayload = null;
        }
    }

    function handleMapContextMenu(evt: any) {
        evt.preventDefault();
        if (!map) return;
        const pixel = map.getEventPixel(evt.originalEvent);
        contextMenuPos = { x: evt.originalEvent.clientX, y: evt.originalEvent.clientY };
        contextMenuMapCoord = map.getCoordinateFromPixel(pixel);
        let feat: any = null;
        map.forEachFeatureAtPixel(pixel, (f) => {
            feat = f;
            return true;
        });
        contextMenuFeature = feat;
        showContextMenu = true;
    }

    function startDraw(type: string) {
        if (!map || !drawSource) return;
        stopDrawing();
        drawType = type;
        const olType = type === "Text" ? "Point" : type;
        drawInteraction = new Draw({
            source: drawSource,
            type: olType as any,
        });
        drawInteraction.on("drawend", (e: any) => {
            if (type === "Text") {
                const text = prompt(t("map.text_prompt")) || "";
                e.feature.set("text", text);
            }
            stopDrawing();
        });
        map.addInteraction(drawInteraction);
    }

    function stopDrawing() {
        if (drawInteraction && map) {
            map.removeInteraction(drawInteraction);
            drawInteraction = null;
        }
        drawType = null;
    }

    function toggleMeasure() {
        if (!map || !measureSource) return;
        if (isMeasuring) {
            isMeasuring = false;
            measureSource.clear();
            stopDrawing();
            return;
        }
        isMeasuring = true;
        stopDrawing();
        drawInteraction = new Draw({
            source: measureSource,
            type: "LineString",
            style: createMeasureStyle(),
        });
        map.addInteraction(drawInteraction);
    }

    function handleBearingClick(coord: number[]) {
        if (!bearingFirstMapCoord) {
            bearingFirstMapCoord = coord;
            ToastUtils.info(t("map.bearing_second_click_prompt"));
        } else {
            const lonLat1 = toLonLat(bearingFirstMapCoord);
            const lonLat2 = toLonLat(coord);
            const az = calculateAzimuth(lonLat1[0], lonLat1[1], lonLat2[0], lonLat2[1]);
            ToastUtils.success(`Bearing: ${az.deg}° (${az.cardinal})`);
            bearingFirstMapCoord = null;
            isBearingMode = false;
        }
    }

    async function toggleOffline(enabled: boolean) {
        offlineEnabled = enabled;
        if (tileLayer) {
            tileLayer.setSource(
                enabled ? createOfflineMBTilesSource() : createOnlineTileSource(tileServerUrl, cachingEnabled)
            );
        }
        saveState();
    }

    async function toggleCaching(enabled: boolean) {
        cachingEnabled = enabled;
        if (tileLayer && !offlineEnabled) {
            tileLayer.setSource(createOnlineTileSource(tileServerUrl, cachingEnabled));
        }
        saveState();
    }

    async function reloadTelemetry() {
        telemetryList = await fetchTelemetryMarkers();
        peers = await fetchPeers();
        updatePeerMarkers();
    }

    function updatePeerMarkers() {
        if (!markersSource) return;
        markersSource.clear();
        markersSource.addFeatures(createPeerFeatures(telemetryList));
    }

    async function toggleDiscovered() {
        discoveredVisible = !discoveredVisible;
        if (!discoveredSource) return;
        discoveredSource.clear();
        if (!discoveredVisible) return;
        const nodes = await fetchDiscoveredNodes();
        discoveredSource.addFeatures(createDiscoveredFeatures(nodes));
    }

    async function goToMyLocation() {
        const loc = await resolveMyLocationWgs84({ config: GlobalState.config as any, telemetryList });
        if (loc && map) {
            map.getView().animate({ center: fromLonLat([loc.lon, loc.lat]), zoom: 14, duration: 800 });
        } else {
            ToastUtils.warning(t("map.location_unavailable"));
        }
    }

    async function handleSearch(q: string) {
        if (!q.trim()) {
            searchResults = [];
            return;
        }
        isSearching = true;
        searchError = null;
        try {
            const res = await fetch(`${nominatimApiUrl}?format=json&q=${encodeURIComponent(q)}&limit=5`);
            if (res.ok) {
                searchResults = await res.json();
            }
        } catch (e: any) {
            searchError = e.message || "Search failed";
        } finally {
            isSearching = false;
        }
    }

    function selectSearchResult(res: SearchResult) {
        if (!map || res.lon == null || res.lat == null) return;
        const lon = Number(res.lon);
        const lat = Number(res.lat);
        map.getView().animate({ center: fromLonLat([lon, lat]), zoom: 12, duration: 600 });
        searchResults = [];
        isSearchFocused = false;
        (onupdatetitle || onUpdateTitle)?.(res.display_name?.split(",")?.[0] || "");
    }

    function handleStartExport() {
        if (!map || !exportBbox) return;
        startExport({
            min_zoom: exportMinZoom,
            max_zoom: exportMaxZoom,
            bbox: exportBbox,
        })
            .then((res: any) => {
                activeExportId = res?.export_id || res?.data?.export_id;
                isExportMode = false;
                if (activeExportId) pollExport();
            })
            .catch(() => {
                ToastUtils.error(t("map.export_failed"));
            });
    }

    function pollExport() {
        if (exportPollTimer) clearInterval(exportPollTimer);
        exportPollTimer = setInterval(async () => {
            if (!activeExportId) return;
            exportStatus = await getExportStatus(activeExportId);
            if (exportStatus?.status === "completed" || exportStatus?.status === "failed") {
                if (exportPollTimer) clearInterval(exportPollTimer);
                exportPollTimer = null;
                await loadMBTiles();
            }
        }, 1500);
    }

    async function loadMBTiles() {
        mbtilesList = await loadMBTilesList();
        hasOfflineMap = mbtilesList.some((f) => f.is_active);
    }

    onMount(async () => {
        initOpenLayers();
        await loadSavedState();
        await reloadTelemetry();
        await loadMBTiles();

        telemetryPollTimer = setInterval(() => reloadTelemetry(), 10000);
        onWsEvent("telemetry", reloadTelemetry);
        onWsEvent("announce", reloadTelemetry);
    });

    onDestroy(() => {
        if (exportPollTimer) clearInterval(exportPollTimer);
        if (telemetryPollTimer) clearInterval(telemetryPollTimer);
        if (saveStateTimer) clearTimeout(saveStateTimer);
        offWsEvent("telemetry", reloadTelemetry);
        offWsEvent("announce", reloadTelemetry);
        if (map) {
            map.setTarget(undefined);
            map = null;
        }
    });
</script>

<div class="flex flex-col h-full w-full bg-sem-surface overflow-hidden">
    <MapHeaderBar
        {embedded}
        {tabTitle}
        {discoveredVisible}
        {offlineEnabled}
        ontogglediscovered={toggleDiscovered}
        ontoggleoffline={toggleOffline}
        ontogglemotools={() => (isMapToolsOpen = !isMapToolsOpen)}
        ontogglesettings={() => (isSettingsOpen = !isSettingsOpen)}
    />

    <div class="relative flex-1 min-h-0 h-full">
        <MapDrawingToolbar
            tools={drawingTools}
            {drawType}
            measuring={isMeasuring}
            bearingMode={isBearingMode}
            {bearingFromGps}
            exportMode={isExportMode}
            {selectedFeature}
            ontoggledraw={(type) => (drawType === type ? stopDrawing() : startDraw(type))}
            ontogglemeasure={toggleMeasure}
            ontogglebearing={() => (isBearingMode = !isBearingMode)}
            onclear={() => drawSource?.clear()}
            onlocate={goToMyLocation}
            onsave={() => (showSaveDrawingModal = true)}
            onload={() => (showLoadDrawingModal = true)}
        />

        {#if isBearingMode}
            <MapBearingInstructions
                fromGpsActive={bearingFromGps}
                awaitingSecondTap={Boolean(bearingFirstMapCoord)}
                onusemylocation={goToMyLocation}
            />
        {/if}

        <div
            class="absolute left-4 right-4 top-[calc(0.5rem+2.75rem+0.5rem)] z-30 sm:top-2 sm:left-auto sm:right-4 sm:w-80 md:max-lg:w-72 lg:w-80"
        >
            <MapSearchBar
                bind:modelValue={searchQuery}
                results={searchResults}
                error={searchError}
                searching={isSearching}
                showResults={isSearchFocused}
                placeholder={offlineEnabled ? t("map.search_placeholder_offline") : t("map.search_placeholder")}
                oninput={() => handleSearch(searchQuery)}
                onsearch={() => handleSearch(searchQuery)}
                onclear={() => (searchResults = [])}
                onfocus={() => (isSearchFocused = true)}
                onselect={selectSearchResult}
            />
        </div>

        <div bind:this={mapContainer} class="absolute inset-0"></div>

        {#if selectedMarker}
            <MapMarkerPanel
                marker={selectedMarker}
                {coordinateFormat}
                onclose={() => (selectedMarker = null)}
                ontoggletracking={(hash) => {
                    if (trackedHashes.includes(hash)) {
                        trackedHashes = trackedHashes.filter((h) => h !== hash);
                    } else {
                        trackedHashes = [...trackedHashes, hash];
                    }
                }}
            />
        {/if}

        {#if selectedCluster}
            <MapClusterPanel cluster={selectedCluster} onclose={() => (selectedCluster = null)} />
        {/if}

        <MapSettingsPanel
            show={isSettingsOpen}
            {offlineEnabled}
            bind:clusterMarkersEnabled
            bind:tileServerUrl
            bind:nominatimApiUrl
            trackedPeers={trackedPeersList}
            {peers}
            {currentZoom}
            displayCoords={centerCoords}
            {formattedDisplayCoords}
            {coordinateFormat}
            {settingsPanelPos}
            {isMobileScreen}
            onclose={() => (isSettingsOpen = false)}
            onsetasdefaultview={saveState}
            ontoggletracking={(hash) => (trackedHashes = trackedHashes.filter((h) => h !== hash))}
        />

        <MapToolsDrawer
            isOpen={isMapToolsOpen}
            {drawSource}
            {hasVectorDrawFeatures}
            {offlineEnabled}
            {cachingEnabled}
            {mbtilesList}
            {mbtilesDir}
            {hasOfflineMap}
            mapReady={isMapLoaded}
            ontoggleoffline={toggleOffline}
            ontogglecaching={toggleCaching}
            onsetactivembtiles={(name) => setActiveMBTiles(name).then(loadMBTiles)}
            ondeletembtiles={(name) => deleteMBTiles(name).then(loadMBTiles)}
            onsavembtilesdir={(dir) => saveMBTilesDir(dir)}
            onclearcache={() => TileCache.clear()}
            onexportregion={() => (isExportMode = true)}
            onstartexport={handleStartExport}
            onrestorestarter={() => restoreStarterTiles().then(loadMBTiles)}
            onclose={() => (isMapToolsOpen = false)}
        />

        <MapContextMenu
            show={showContextMenu}
            x={contextMenuPos.x}
            y={contextMenuPos.y}
            {contextMenuFeature}
            isEditable={Boolean(contextMenuFeature)}
            {contextMenuCoordRows}
            onselectfeature={() => {}}
            oneditfeature={() => (drawFeatureInfoPayload = extractDrawFeaturePayload(contextMenuFeature))}
            onaddnote={() => {
                editingFeature = contextMenuFeature;
                noteDraft = contextMenuFeature?.get("note") || "";
            }}
            ondeletefeature={() => {
                if (contextMenuFeature && drawSource) drawSource.removeFeature(contextMenuFeature);
            }}
            oncopycoords={() => {
                if (contextMenuMapCoord) {
                    const lonLat = toLonLat(contextMenuMapCoord);
                    navigator.clipboard?.writeText(`${lonLat[1].toFixed(5)}, ${lonLat[0].toFixed(5)}`);
                    ToastUtils.success(t("map.coords_copied"));
                }
            }}
            onpinghere={() => {
                if (contextMenuMapCoord) {
                    const lonLat = toLonLat(contextMenuMapCoord);
                    sendMapPing(pingDestinationHash, lonLat[1], lonLat[0], currentZoom);
                }
            }}
            onclearmap={() => drawSource?.clear()}
            onclose={() => (showContextMenu = false)}
        />

        <MapSaveDrawingModal
            show={showSaveDrawingModal}
            bind:name={saveDrawingNameDraft}
            onclose={() => (showSaveDrawingModal = false)}
            onsave={() => {
                if (!drawSource) return;
                const features = new GeoJSON().writeFeaturesObject(drawSource.getFeatures());
                saveDrawing(saveDrawingNameDraft, features as any).then(() => {
                    ToastUtils.success(t("map.drawing_saved"));
                    showSaveDrawingModal = false;
                });
            }}
        />

        <MapLoadDrawingModal
            show={showLoadDrawingModal}
            drawings={drawingsList}
            onclose={() => (showLoadDrawingModal = false)}
            onload={(d) => {
                if (!drawSource || !d.features) return;
                const feats = new GeoJSON().readFeatures(d.features);
                drawSource.clear();
                drawSource.addFeatures(feats);
                showLoadDrawingModal = false;
            }}
            ondelete={(d) => deleteDrawing(d.id).then(() => loadDrawings().then((l) => (drawingsList = l)))}
        />

        {#if drawFeatureInfoPayload}
            <MapDrawFeatureInfoPanel payload={drawFeatureInfoPayload} onclose={() => (drawFeatureInfoPayload = null)} />
        {/if}

        {#if editingFeature}
            <MapMobileNoteModal
                show={Boolean(editingFeature)}
                bind:text={noteDraft}
                onclose={() => (editingFeature = null)}
                onsave={() => {
                    editingFeature?.set("note", noteDraft);
                    editingFeature = null;
                }}
                ondelete={() => {
                    editingFeature?.set("note", "");
                    editingFeature = null;
                }}
            />
        {/if}

        {#if exportStatus && exportStatus.status === "running"}
            <MapLoadingOverlay message={exportStatus.message || t("map.exporting")} />
        {/if}
    </div>
</div>
