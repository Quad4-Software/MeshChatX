<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, onDestroy, tick } from "svelte";
    import Map from "ol/Map";
    import View from "ol/View";
    import { fromLonLat, toLonLat } from "ol/proj";
    import VectorLayer from "ol/layer/Vector";
    import VectorSource from "ol/source/Vector";
    import TileLayer from "ol/layer/Tile";
    import { Draw, Modify, Snap } from "ol/interaction";
    import DragBox from "ol/interaction/DragBox";
    import GeoJSON from "ol/format/GeoJSON";
    import LineString from "ol/geom/LineString";
    import Feature from "ol/Feature";

    import MapHeaderBar from "./components/MapHeaderBar.svelte";
    import MapToolbarControls from "./components/MapToolbarControls.svelte";
    import MapPortal from "./components/MapPortal.svelte";
    import MapTileBanner from "./components/MapTileBanner.svelte";
    import MapOnboardingTooltip from "./components/MapOnboardingTooltip.svelte";
    import MapExportInstructions from "./components/MapExportInstructions.svelte";
    import MapExportConfigPanel from "./components/MapExportConfigPanel.svelte";
    import MapExportProgressPanel from "./components/MapExportProgressPanel.svelte";
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
    import MapPingModal from "./components/MapPingModal.svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import Point from "ol/geom/Point";

    import { t } from "../../js/i18n.js";
    import ToastUtils from "../../js/ToastUtils.js";
    import GlobalState from "../../js/GlobalState.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import TileCache from "../../js/TileCache.js";
    import { publishPatchedConfig } from "../../js/settings/settingsConfigService.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import { mapViewStateKey } from "../../js/mapStateKeys.js";
    import { formatCoordinate, ensureGeoCoordsReady, parseCoordinateQuery } from "../../js/mapGeoCoords.js";
    import { computeSegmentMetrics, buildBearingLiveTooltipHtml } from "../../js/mapGeodesy.js";
    import { buildMeshchatMapUri, buildWebHashMapUrl } from "../../js/mapLinkUtils.js";
    import { buildNominatimSearchUrl } from "../../js/mapTileNetwork.js";
    import { getCurrentRoute, subscribe as subscribeRoute } from "../../shell/hashRouter.js";

    import {
        createDrawingStyle,
        createMeasureStyle,
        createOnlineTileSource,
        createOfflineMBTilesSource,
    } from "./lib/mapOpenLayers.js";
    import { resolveMyLocationWgs84, calculateAzimuth, handleRemoteOverlaysChanged } from "./lib/mapActions.js";
    import { MapMeasureTooltipManager } from "./lib/mapMeasureTooltips.js";
    import {
        exportDrawFeaturesGeoJson,
        exportDrawFeaturesKml,
        exportDrawFeaturesKmz,
        exportDrawFeaturesGpx,
        downloadTextFile,
        downloadBlobFile,
        exportFilename,
    } from "./lib/mapVectorExchange.js";
    import {
        ensureRemoteOverlayLayer,
        removeRemoteOverlayLayer,
        exportRemoteOverlay,
        copyRemoteOverlayToDrawings,
        type RemoteOverlayEntry,
    } from "./lib/mapRemoteOverlays.js";
    import { MAX_EXPORT_TILES, EXPORT_REGION_PRESETS } from "./lib/constants.js";
    import { lonToTile, latToTile } from "./lib/mapTileUtils.js";
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
        cancelExport,
        getExportStatus,
        sendMapPing,
        uploadMbtilesFile,
        toggleTelemetryTracking,
        fetchTelemetryHistory,
        patchAnnounceStoreMapData,
    } from "./lib/mapService.js";
    import {
        createPeerFeatures,
        createDiscoveredFeatures,
        getContextMenuCoordRows,
        extractDrawFeaturePayload,
        markerPanelPayloadFromFeature,
    } from "./lib/mapPageHelpers.js";
    import { classifyMapDropFiles, isMbtilesFile, readDroppedGeoFileToFeatures } from "./lib/mapDropImport.js";
    import { buildTelemetryHistoryTrailFeature, createTelemetryHistoryStyle } from "./lib/mapTelemetryHistory.js";
    import { getPeerMarkerStyle } from "./lib/markerStyles.js";
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

    let offlineEnabled = $state(true);
    let cachingEnabled = $state(true);
    let discoveredVisible = $state(false);
    let clusterMarkersEnabled = $state(false);
    let tileServerUrl = $state("https://tile.openstreetmap.org/{z}/{x}/{y}.png");
    let nominatimApiUrl = $state("https://nominatim.openstreetmap.org");
    let coordinateFormat = $state("wgs84");
    let currentZoom = $state(2);
    let centerCoords = $state<[number, number]>([0, 0]);
    let _rotation = $state(0);
    let showMapPingModal = $state(false);
    let mapPingLat = $state(0);
    let mapPingLon = $state(0);
    let mapPingZoom = $state(10);
    let remoteOverlayLayers: Record<string, RemoteOverlayEntry> = {};
    let remoteOverlayLoadGeneration = 0;
    let queryMarker: Feature | null = null;
    let unsubscribeRoute: (() => void) | null = null;

    let drawSource = $state<VectorSource | null>(null);
    let drawLayer = $state<VectorLayer<VectorSource> | null>(null);
    let markersSource = $state<VectorSource | null>(null);
    let markersLayer = $state<VectorLayer<VectorSource> | null>(null);
    let discoveredSource = $state<VectorSource | null>(null);
    let discoveredLayer = $state<VectorLayer<VectorSource> | null>(null);
    let measureSource = $state<VectorSource | null>(null);
    let measureLayer = $state<VectorLayer<VectorSource> | null>(null);
    let historySource = $state<VectorSource | null>(null);
    let historyLayer = $state<VectorLayer<VectorSource> | null>(null);
    let tileLayer = $state<TileLayer<any> | null>(null);

    let drawInteraction = $state<Draw | null>(null);
    let modifyInteraction = $state<Modify | null>(null);
    let snapInteraction = $state<Snap | null>(null);
    let drawType = $state<string | null>(null);

    let isMeasuring = $state(false);
    let isBearingMode = $state(false);
    let bearingFromGps = $state(false);
    let bearingGpsMapCoord = $state<number[] | null>(null);
    let bearingFirstMapCoord = $state<number[] | null>(null);
    let bearingPreviewFeature = $state<any>(null);
    let isExportMode = $state(false);
    let isExporting = $state(false);
    let isUploading = $state(false);
    let exportMinZoom = $state(0);
    let exportMaxZoom = $state(15);
    let exportBbox = $state<number[] | null>(null);
    let exportStatus = $state<MapExportStatus | null>(null);
    let activeExportId = $state<string | number | null>(null);
    let exportPollTimer: ReturnType<typeof setInterval> | null = null;
    let tileConnectivityBannerTimer: ReturnType<typeof setTimeout> | null = null;
    let tileErrorCount = $state(0);
    let showTileConnectivityBanner = $state(false);
    let showOnboardingTooltip = $state(false);
    let onboardingTooltipStyle = $state("");
    let onboardingArrowPath = $state<string | null>(null);
    let tabToolbarHostReady = $state(false);
    let isWideViewport = $state(false);
    let mbtilesFileInput = $state<HTMLInputElement | null>(null);

    let dragBox = $state<DragBox | null>(null);
    let measureTooltipManager: MapMeasureTooltipManager | null = null;
    let measureSketch = $state<any>(null);
    let tabToolbarMq: MediaQueryList | null = null;
    let tabToolbarMqListener: ((event: MediaQueryListEvent) => void) | null = null;

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
    let isMiniChatOpen = $state(false);
    let isMapDropTarget = $state(false);
    let announceListenEnabled = $state(false);
    let announceListenBusy = $state(false);
    let geoWasmEpoch = $state(0);

    let peers = $state<Record<string, any>>({});
    let telemetryList = $state<any[]>([]);
    let trackedHashes = $state<string[]>([]);

    let conversationOptions = $derived(
        Object.values(peers)
            .filter((p: any) => p?.destination_hash)
            .map((p: any) => ({
                hash: p.destination_hash,
                label: p.display_name || p.destination_hash.substring(0, 8),
            }))
    );

    let mapPingSummary = $derived(`${mapPingLat.toFixed(5)}, ${mapPingLon.toFixed(5)} @ z${Math.round(mapPingZoom)}`);
    let mbtilesList = $state<MBTilesEntry[]>([]);
    let mbtilesDir = $state("");
    let drawingsList = $state<DrawingEntry[]>([]);
    let saveDrawingNameDraft = $state("");

    let saveStateTimer: ReturnType<typeof setTimeout> | null = null;
    let telemetryPollTimer: ReturnType<typeof setInterval> | null = null;

    const drawingTools: DrawingTool[] = [
        { type: "Point", icon: "map-marker" },
        { type: "LineString", icon: "vector-line" },
        { type: "Polygon", icon: "vector-polygon" },
        { type: "Circle", icon: "vector-circle" },
        { type: "Text", icon: "format-text" },
    ];

    let formattedDisplayCoords = $derived(
        formatCoordinate(centerCoords[0], centerCoords[1], coordinateFormat)?.text ||
            `${Number(centerCoords[1]).toFixed(6)}, ${Number(centerCoords[0]).toFixed(6)}`
    );
    let hasVectorDrawFeatures = $derived(Boolean(drawSource && drawSource.getFeatures().length > 0));
    let trackedPeersList = $derived(trackedHashes.map((h) => ({ destination_hash: h })));
    let contextMenuCoordRows = $derived(getContextMenuCoordRows(contextMenuMapCoord));
    let useTabToolbar = $derived(embedded && _isActiveTab && tabToolbarHostReady && isWideViewport);
    let estimatedTiles = $derived.by(() => {
        if (!exportBbox) return 0;
        const [minLon, minLat, maxLon, maxLat] = exportBbox;
        let total = 0;
        for (let z = exportMinZoom; z <= exportMaxZoom; z++) {
            const x1 = lonToTile(minLon, z);
            const x2 = lonToTile(maxLon, z);
            const y1 = latToTile(maxLat, z);
            const y2 = latToTile(minLat, z);
            total += (Math.abs(x2 - x1) + 1) * (Math.abs(y2 - y1) + 1);
        }
        return total;
    });
    let exportTileLimitExceeded = $derived(estimatedTiles > MAX_EXPORT_TILES);

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

        historySource = new VectorSource();
        historyLayer = new VectorLayer({
            source: historySource,
            style: createTelemetryHistoryStyle(),
            zIndex: 40,
        });

        tileLayer = new TileLayer({
            source: offlineEnabled
                ? createOfflineMBTilesSource()
                : createOnlineTileSource(tileServerUrl, cachingEnabled, onOnlineTileLoadFailure),
            zIndex: 1,
        });

        const view = new View({
            center: fromLonLat([0, 20]),
            zoom: 2,
            maxZoom: 19,
        });

        map = new Map({
            target: mapContainer,
            layers: [tileLayer, drawLayer, discoveredLayer, markersLayer, measureLayer, historyLayer],
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
        measureTooltipManager = new MapMeasureTooltipManager(map);

        dragBox = new DragBox({
            condition: () => isExportMode,
        });
        dragBox.on("boxend", () => {
            if (!dragBox || !map) return;
            const extent = dragBox.getGeometry().getExtent();
            const min = toLonLat([extent[0], extent[1]]);
            const max = toLonLat([extent[2], extent[3]]);
            exportBbox = [min[0], min[1], max[0], max[1]];
            exportMinZoom = Math.floor(map.getView().getZoom() || 0);
            exportMaxZoom = Math.min(exportMinZoom + 3, 18);
        });
        map.addInteraction(dragBox);
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
            const cluster = clickedFeature.get("cluster");
            if (cluster) {
                selectedCluster = cluster;
                selectedMarker = null;
                selectedFeature = null;
                isMiniChatOpen = false;
                clearTelemetryPath();
                return;
            }
            const markerPayload = markerPanelPayloadFromFeature(clickedFeature);
            if (markerPayload) {
                const prevHash = selectedMarker?.telemetry?.destination_hash;
                const nextHash = markerPayload?.telemetry?.destination_hash;
                if (!nextHash || prevHash !== nextHash) {
                    isMiniChatOpen = false;
                }
                selectedMarker = markerPayload;
                selectedCluster = null;
                selectedFeature = null;
                if (markerPayload.telemetry?.destination_hash) {
                    void drawTelemetryPath(markerPayload.telemetry.destination_hash);
                } else {
                    clearTelemetryPath();
                }
                return;
            }
            selectedFeature = clickedFeature;
            drawFeatureInfoPayload = extractDrawFeaturePayload(clickedFeature);
            selectedMarker = null;
            isMiniChatOpen = false;
            clearTelemetryPath();
        } else {
            selectedMarker = null;
            selectedCluster = null;
            selectedFeature = null;
            drawFeatureInfoPayload = null;
            isMiniChatOpen = false;
            clearTelemetryPath();
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
        if (!map || !drawSource || !measureTooltipManager) return;
        stopDrawing();
        stopMeasuring();
        drawType = type;
        const olType = type === "Text" ? "Point" : type;
        drawInteraction = new Draw({
            source: drawSource,
            type: olType as any,
        });
        drawInteraction.on("drawstart", (evt: any) => {
            measureSketch = evt.feature;
            if (type === "LineString" || type === "Polygon" || type === "Circle") {
                measureTooltipManager?.attachDrawMeasureListener(evt.feature);
            }
        });
        drawInteraction.on("drawend", (e: any) => {
            if (type === "Text") {
                const text = prompt(t("map.text_prompt")) || "";
                e.feature.set("text", text);
            }
            measureTooltipManager?.cleanupDrawListener();
            measureTooltipManager?.cleanupMeasureTooltip();
            measureSketch = null;
            stopDrawing();
        });
        map.addInteraction(drawInteraction);
    }

    function stopDrawing() {
        if (drawInteraction && map) {
            map.removeInteraction(drawInteraction);
            drawInteraction = null;
        }
        measureTooltipManager?.cleanupDrawListener();
        measureSketch = null;
        drawType = null;
    }

    function stopMeasuring() {
        isMeasuring = false;
        measureSource?.clear();
        measureTooltipManager?.disablePointerHelp();
        measureTooltipManager?.cleanupDrawListener();
        measureTooltipManager?.cleanupMeasureTooltip();
        if (drawInteraction && map) {
            map.removeInteraction(drawInteraction);
            drawInteraction = null;
        }
        measureSketch = null;
    }

    function toggleMeasure() {
        if (!map || !measureSource || !measureTooltipManager) return;
        if (isMeasuring) {
            stopMeasuring();
            return;
        }
        stopDrawing();
        isMeasuring = true;
        measureTooltipManager.createMeasureTooltip();
        measureTooltipManager.createHelpTooltip();
        measureTooltipManager.enablePointerHelp(() => Boolean(measureSketch));
        drawInteraction = new Draw({
            source: measureSource,
            type: "LineString",
            style: createMeasureStyle(),
        });
        drawInteraction.on("drawstart", (evt: any) => {
            measureSketch = evt.feature;
            measureTooltipManager?.attachDrawMeasureListener(evt.feature);
        });
        drawInteraction.on("drawend", () => {
            measureTooltipManager?.finalizeStaticTooltip();
            measureSketch = null;
        });
        map.addInteraction(drawInteraction);
    }

    function handleBearingClick(coord: number[]) {
        if (bearingFromGps && bearingGpsMapCoord) {
            finishBearingSegment(bearingGpsMapCoord, coord);
            return;
        }
        if (!bearingFirstMapCoord) {
            bearingFirstMapCoord = coord;
            ToastUtils.info(t("map.bearing_second_click_prompt"));
            return;
        }
        finishBearingSegment(bearingFirstMapCoord, coord);
    }

    function finishBearingSegment(startMapCoord: number[], endMapCoord: number[]) {
        if (!map || !drawSource) return;
        const lonLat1 = toLonLat(startMapCoord);
        const lonLat2 = toLonLat(endMapCoord);
        const az = calculateAzimuth(lonLat1[0], lonLat1[1], lonLat2[0], lonLat2[1]);
        ToastUtils.success(`Bearing: ${az.deg}° (${az.cardinal})`);
        removeBearingPreview();
        stopBearingMode();
    }

    function removeBearingPreview() {
        if (bearingPreviewFeature && drawSource) {
            drawSource.removeFeature(bearingPreviewFeature);
        }
        bearingPreviewFeature = null;
    }

    function stopBearingMode() {
        isBearingMode = false;
        bearingFromGps = false;
        bearingGpsMapCoord = null;
        bearingFirstMapCoord = null;
        removeBearingPreview();
        measureTooltipManager?.cleanupDrawListener();
        measureTooltipManager?.cleanupMeasureTooltip();
        measureTooltipManager?.disablePointerHelp();
    }

    async function startBearingFromMyLocation() {
        if (!map) return;
        const loc = await resolveMyLocationWgs84({ config: GlobalState.config as any, telemetryList });
        if (!loc) {
            ToastUtils.warning(t("map.location_not_determined"));
            return;
        }
        stopDrawing();
        stopMeasuring();
        bearingFirstMapCoord = null;
        removeBearingPreview();
        isBearingMode = true;
        bearingFromGps = true;
        bearingGpsMapCoord = fromLonLat([loc.lon, loc.lat]) as number[];
        measureTooltipManager?.createHelpTooltip();
        measureTooltipManager?.createMeasureTooltip();
        map.getView().animate({ center: bearingGpsMapCoord, zoom: Math.max(currentZoom, 12), duration: 600 });
    }

    function toggleBearingMode() {
        if (isBearingMode) {
            stopBearingMode();
            return;
        }
        stopDrawing();
        stopMeasuring();
        bearingFromGps = false;
        bearingGpsMapCoord = null;
        bearingFirstMapCoord = null;
        isBearingMode = true;
        measureTooltipManager?.createHelpTooltip();
        measureTooltipManager?.createMeasureTooltip();
    }

    async function toggleOffline(enabled: boolean) {
        offlineEnabled = enabled;
        if (tileLayer) {
            tileLayer.setSource(
                enabled
                    ? createOfflineMBTilesSource()
                    : createOnlineTileSource(tileServerUrl, cachingEnabled, onOnlineTileLoadFailure)
            );
        }
        saveState();
    }

    async function toggleCaching(enabled: boolean) {
        cachingEnabled = enabled;
        if (tileLayer && !offlineEnabled) {
            tileLayer.setSource(createOnlineTileSource(tileServerUrl, cachingEnabled, onOnlineTileLoadFailure));
        }
        saveState();
    }

    async function reloadTelemetry() {
        telemetryList = await fetchTelemetryMarkers();
        peers = await fetchPeers();
        updatePeerMarkers();
        const selectedHash = selectedMarker?.telemetry?.destination_hash;
        if (selectedHash) {
            void drawTelemetryPath(selectedHash);
        }
    }

    function updatePeerMarkers() {
        if (!markersSource) return;
        markersSource.clear();
        if (queryMarker) {
            markersSource.addFeature(queryMarker);
        }
        markersSource.addFeatures(createPeerFeatures(telemetryList, peers));
    }

    function clearTelemetryPath() {
        historySource?.clear();
    }

    async function drawTelemetryPath(hash: string) {
        clearTelemetryPath();
        if (!hash || !historySource) return;
        try {
            const history = await fetchTelemetryHistory(hash, 50);
            const feature = buildTelemetryHistoryTrailFeature(history);
            if (feature) {
                historySource.addFeature(feature);
            }
        } catch (e) {
            console.error("Failed to draw telemetry path", e);
        }
    }

    function onMapDragOver(ev: DragEvent) {
        ev.preventDefault();
        if (ev.dataTransfer && Array.from(ev.dataTransfer.types || []).includes("Files")) {
            isMapDropTarget = true;
        }
    }

    function onMapDragLeave() {
        isMapDropTarget = false;
    }

    async function onMapDrop(ev: DragEvent) {
        ev.preventDefault();
        isMapDropTarget = false;
        const files = Array.from(ev.dataTransfer?.files || []);
        if (!files.length) return;

        const { mbtilesFiles, geoFiles } = classifyMapDropFiles(files);
        if (!mbtilesFiles.length && !geoFiles.length) {
            ToastUtils.warning(t("map.drop_no_supported_files"));
            return;
        }

        for (const file of mbtilesFiles) {
            if (file instanceof File) {
                await uploadDroppedMbtiles(file);
            }
        }

        for (const file of geoFiles) {
            if (!(file instanceof File)) continue;
            try {
                const features = await readDroppedGeoFileToFeatures(file, "EPSG:3857");
                if (!features) {
                    ToastUtils.warning(t("map.drop_no_supported_files"));
                    continue;
                }
                onVectorExchangeImport({ features, merge: true });
            } catch (e) {
                console.error("Map drop import failed:", e);
                ToastUtils.error(`${t("map.vector_import_failed")} - ${file.name}`);
            }
        }
    }

    async function uploadDroppedMbtiles(file: File) {
        if (!isMbtilesFile(file)) {
            ToastUtils.error(t("map.select_mbtiles_error"));
            return;
        }
        isUploading = true;
        try {
            const response: any = await uploadMbtilesFile(file);
            const metadata = response?.metadata || response?.data?.metadata;
            hasOfflineMap = true;
            offlineEnabled = true;
            await loadMBTiles();
            if (tileLayer) {
                tileLayer.setSource(createOfflineMBTilesSource());
            }
            ToastUtils.success(t("map.upload_success"));
            if (metadata?.bounds && map) {
                const bounds = String(metadata.bounds).split(",").map(parseFloat);
                if (bounds.length === 4) {
                    const extent = [...fromLonLat([bounds[0], bounds[1]]), ...fromLonLat([bounds[2], bounds[3]])];
                    map.getView().fit(extent, { padding: [20, 20, 20, 20] });
                }
            }
        } catch (e: any) {
            ToastUtils.error(`${t("map.upload_failed")}: ${e?.response?.data?.error || e?.message || ""}`);
        } finally {
            isUploading = false;
        }
    }

    async function onToggleAnnounceListen(enabled: boolean) {
        if (announceListenBusy) return;
        announceListenBusy = true;
        const next = Boolean(enabled);
        try {
            const response: any = await patchAnnounceStoreMapData(next);
            const cfg = response?.config || response?.data?.config;
            if (cfg) {
                publishPatchedConfig(cfg);
            } else {
                publishPatchedConfig({ announce_store_map_data: next });
            }
            announceListenEnabled = next;
            ToastUtils.success(next ? t("map.data_listen_enabled_toast") : t("map.data_listen_disabled_toast"));
        } catch (e) {
            console.error(e);
            ToastUtils.error(t("common.save_failed"));
        } finally {
            announceListenBusy = false;
        }
    }

    function onConfigUpdatedExternally(cfg: any) {
        if (!cfg || typeof cfg !== "object") return;
        if (Object.prototype.hasOwnProperty.call(cfg, "announce_store_map_data")) {
            announceListenEnabled = Boolean(cfg.announce_store_map_data);
        }
    }

    function layersTagForShare() {
        return discoveredVisible ? "discovered" : "";
    }

    async function shareMapView() {
        if (!map) return;
        const view = map.getView();
        const c = toLonLat(view.getCenter() || [0, 0]);
        const z = view.getZoom() || currentZoom;
        const layers = layersTagForShare();
        const mesh = buildMeshchatMapUri({ lat: c[1], lon: c[0], zoom: z, layers });
        const web = buildWebHashMapUrl({ lat: c[1], lon: c[0], zoom: z, layers });
        const text = `${t("map.share_message_prefix")} ${mesh}\n${web}`;
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
                ToastUtils.success(t("map.share_copied"));
            } else {
                ToastUtils.info(text);
            }
        } catch {
            ToastUtils.warning(web);
        }
    }

    function openPingModalAt(lat: number, lon: number, zoom: number) {
        mapPingLat = lat;
        mapPingLon = lon;
        mapPingZoom = zoom;
        showMapPingModal = true;
    }

    async function handleSendMapPing(destinationHash: string) {
        try {
            await sendMapPing({
                destinationHash,
                lat: mapPingLat,
                lon: mapPingLon,
                zoom: mapPingZoom,
                layers: layersTagForShare(),
                contentPrefix: t("map.ping_message_prefix"),
            });
            ToastUtils.success(t("map.ping_sent"));
            showMapPingModal = false;
        } catch (e: any) {
            if (e?.message === "invalid_destination") {
                ToastUtils.error(t("map.ping_invalid_destination"));
                return;
            }
            ToastUtils.error(t("map.ping_failed"));
        }
    }

    async function handleToggleTracking(hash: string) {
        const entry = telemetryList.find((tEntry) => tEntry.destination_hash === hash);
        const currentlyTracking = Boolean(entry?.is_tracking || selectedMarker?.telemetry?.is_tracking);
        const next = await toggleTelemetryTracking(hash, !currentlyTracking);
        if (next == null) {
            ToastUtils.error(t("map.failed_update_tracking"));
            return;
        }
        if (entry) entry.is_tracking = next;
        const selectedHash = selectedMarker?.telemetry?.destination_hash;
        if (selectedHash && selectedHash === hash) {
            selectedMarker = {
                ...selectedMarker,
                telemetry: { ...selectedMarker.telemetry, is_tracking: next },
            };
        }
        if (next) {
            if (!trackedHashes.includes(hash)) trackedHashes = [...trackedHashes, hash];
        } else {
            trackedHashes = trackedHashes.filter((h) => h !== hash);
        }
        updatePeerMarkers();
        ToastUtils.success(next ? t("map.tracking_enabled") : t("map.tracking_disabled"));
    }

    async function onRemoteOverlaysChanged(overlays?: any[]) {
        if (!map) return;
        const ctx = {
            map,
            remoteOverlayLoadGeneration,
            remoteOverlayLayers,
            removeRemoteOverlayLayer(id: string) {
                removeRemoteOverlayLayer(map, remoteOverlayLayers, id);
            },
            async ensureRemoteOverlayLayer(overlay: any) {
                await ensureRemoteOverlayLayer(map, remoteOverlayLayers, overlay);
            },
        };
        await handleRemoteOverlaysChanged(ctx, overlays || []);
        remoteOverlayLoadGeneration = ctx.remoteOverlayLoadGeneration;
    }

    async function onRemoteOverlayExport(detail: { id: string | number; format: string }) {
        try {
            await exportRemoteOverlay(detail.id, detail.format);
            ToastUtils.success(t("map.remote_overlays_export_ok"));
        } catch {
            ToastUtils.error(t("map.remote_overlays_export_failed"));
        }
    }

    async function onRemoteOverlayCopyToDrawings(overlay: any) {
        try {
            const count = await copyRemoteOverlayToDrawings(drawSource, overlay);
            if (count > 0) {
                ToastUtils.success(t("map.remote_overlays_copied"));
            }
        } catch {
            ToastUtils.error(t("map.remote_overlays_error"));
        }
    }

    function applyLayersFromRouteString(layersStr: string) {
        if (!layersStr) return;
        const parts = layersStr
            .split(",")
            .map((s) => s.trim().toLowerCase())
            .filter(Boolean);
        if (parts.includes("discovered") && !discoveredVisible) {
            void toggleDiscovered();
        }
    }

    function applyMapViewFromRoute() {
        if (!map || !markersSource) return;
        const route = getCurrentRoute();
        const q = route?.query || {};
        const latRaw = q.lat;
        const lonRaw = q.lon;
        if (latRaw == null || lonRaw == null || latRaw === "" || lonRaw === "") {
            if (q.layers) applyLayersFromRouteString(String(q.layers));
            return;
        }
        const lat = parseFloat(latRaw);
        const lon = parseFloat(lonRaw);
        const zRaw = q.zoom != null && q.zoom !== "" ? q.zoom : q.z;
        let zoom = parseFloat(zRaw != null && zRaw !== "" ? zRaw : "15");
        if (!Number.isFinite(zoom)) zoom = 15;
        zoom = Math.max(0, Math.min(22, zoom));
        const label = (q.label != null && String(q.label)) || "Target";
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

        if (queryMarker) {
            markersSource.removeFeature(queryMarker);
            queryMarker = null;
        }

        map.getView().setCenter(fromLonLat([lon, lat]));
        map.getView().setZoom(zoom);
        currentZoom = zoom;
        centerCoords = [lon, lat];

        const coord = fromLonLat([lon, lat]);
        const feature = new Feature({
            geometry: new Point(coord),
            originalCoord: coord,
        });
        feature.setStyle(
            getPeerMarkerStyle(
                {
                    display_name: String(label),
                    background_colour: "#2563eb",
                    foreground_colour: "#ffffff",
                },
                true
            )
        );
        queryMarker = feature;
        markersSource.addFeature(feature);

        if (q.layers) applyLayersFromRouteString(String(q.layers));
        if (q.view === "discovered" && !discoveredVisible) {
            void toggleDiscovered();
        }
    }

    async function toggleDiscovered() {
        if (discoveredVisible) {
            discoveredVisible = false;
            discoveredSource?.clear();
            return;
        }
        if (!discoveredSource) return;
        try {
            const nodes = await fetchDiscoveredNodes();
            const withLoc = nodes.filter((n) => n.latitude != null && n.longitude != null);
            if (withLoc.length === 0) {
                ToastUtils.info(t("map.no_nodes_location"));
                return;
            }
            discoveredSource.clear();
            discoveredSource.addFeatures(createDiscoveredFeatures(withLoc));
            discoveredVisible = true;
            ToastUtils.success(`Mapped ${withLoc.length} discovered nodes`);
        } catch {
            ToastUtils.error(t("map.failed_fetch_nodes"));
        }
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
            await ensureGeoCoordsReady();
            const parsed = parseCoordinateQuery(q.trim());
            if (parsed?.ok && parsed.lat != null && parsed.lon != null) {
                const label = `${parsed.kind || "coord"}: ${parsed.lat.toFixed(6)}, ${parsed.lon.toFixed(6)}`;
                searchResults = [
                    {
                        display_name: label,
                        lat: parsed.lat,
                        lon: parsed.lon,
                        type: parsed.kind || "coordinate",
                    },
                ];
                if (map) {
                    map.getView().animate({
                        center: fromLonLat([parsed.lon, parsed.lat]),
                        zoom: 12,
                        duration: 600,
                    });
                }
                return;
            }
            if (offlineEnabled) {
                searchResults = [];
                searchError = t("map.search_offline_coordinates_only");
                return;
            }
            const res = await fetch(buildNominatimSearchUrl(nominatimApiUrl, q, 5));
            if (res.ok) {
                searchResults = await res.json();
            }
        } catch (e: any) {
            searchError = e.message || t("map.search_error");
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

    function toggleExportMode() {
        isExportMode = !isExportMode;
        if (isExportMode) {
            stopBearingMode();
        } else {
            exportBbox = null;
        }
    }

    function cancelExportSelection() {
        exportBbox = null;
        isExportMode = false;
    }

    function applyExportRegionPreset(preset: (typeof EXPORT_REGION_PRESETS)[number]) {
        exportBbox = preset.bbox.slice();
        exportMinZoom = preset.minZoom;
        exportMaxZoom = preset.maxZoom;
    }

    async function handleStartExport() {
        if (!map || !exportBbox || exportTileLimitExceeded) return;
        isExporting = true;
        try {
            const res: any = await startExport({
                min_zoom: exportMinZoom,
                max_zoom: exportMaxZoom,
                bbox: exportBbox,
                name: `Map Export ${new Date().toLocaleString()}`,
            });
            activeExportId = res?.export_id || res?.data?.export_id;
            isExportMode = false;
            exportBbox = null;
            if (activeExportId) pollExport();
        } catch (e: any) {
            ToastUtils.error(e?.response?.data?.error || t("map.export_failed"));
        } finally {
            isExporting = false;
        }
    }

    async function cancelActiveExport() {
        if (!activeExportId) {
            exportStatus = null;
            return;
        }
        try {
            await cancelExport(activeExportId);
            exportStatus = null;
            activeExportId = null;
            ToastUtils.success(t("map.export_cancelled"));
        } catch {
            ToastUtils.error(t("map.failed_cancel_export"));
        }
    }

    function onVectorExchangeImport({ features, merge }: { features: any[]; merge: boolean }) {
        if (!drawSource || !features?.length) {
            ToastUtils.warning(t("map.vector_import_empty"));
            return;
        }
        if (!merge) {
            drawSource.clear();
            selectedFeature = null;
            drawFeatureInfoPayload = null;
        }
        for (const f of features) {
            if (f.get("type") == null || f.get("type") === "") {
                f.set("type", "draw");
            }
        }
        drawSource.addFeatures(features);
        ToastUtils.success(t("map.vector_import_ok", { count: features.length }));
    }

    function onVectorExchangeImportError() {
        ToastUtils.error(t("map.vector_import_failed"));
    }

    function exportVectorGeoJson() {
        if (!drawSource || !hasVectorDrawFeatures) return;
        downloadTextFile(
            exportFilename("geojson"),
            exportDrawFeaturesGeoJson(drawSource.getFeatures()),
            "application/geo+json"
        );
        ToastUtils.success(t("map.vector_export_ok"));
    }

    function exportVectorKml() {
        if (!drawSource || !hasVectorDrawFeatures) return;
        downloadTextFile(
            exportFilename("kml"),
            exportDrawFeaturesKml(drawSource.getFeatures()),
            "application/vnd.google-earth.kml+xml"
        );
        ToastUtils.success(t("map.vector_export_ok"));
    }

    async function exportVectorKmz() {
        if (!drawSource || !hasVectorDrawFeatures) return;
        try {
            const blob = await exportDrawFeaturesKmz(drawSource.getFeatures());
            downloadBlobFile(exportFilename("kmz"), blob, "application/vnd.google-earth.kmz");
            ToastUtils.success(t("map.vector_export_ok"));
        } catch {
            ToastUtils.error(t("map.vector_import_failed"));
        }
    }

    function exportVectorGpx() {
        if (!drawSource || !hasVectorDrawFeatures) return;
        downloadTextFile(exportFilename("gpx"), exportDrawFeaturesGpx(drawSource.getFeatures()), "application/gpx+xml");
        ToastUtils.success(t("map.vector_export_ok"));
    }

    function triggerMbtilesUpload() {
        mbtilesFileInput?.click();
    }

    async function onMbtilesFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0];
        input.value = "";
        if (!file) return;
        await uploadDroppedMbtiles(file);
    }

    function dismissTileConnectivityBanner() {
        showTileConnectivityBanner = false;
        if (tileConnectivityBannerTimer) {
            clearTimeout(tileConnectivityBannerTimer);
            tileConnectivityBannerTimer = null;
        }
    }

    function onOnlineTileLoadFailure() {
        if (offlineEnabled) return;
        tileErrorCount++;
        if (tileErrorCount > 10) {
            tileErrorCount = 0;
            if (hasOfflineMap) {
                void toggleOffline(true);
                ToastUtils.info(t("map.tile_failover_offline"));
                return;
            }
            showTileConnectivityBanner = true;
            if (tileConnectivityBannerTimer) clearTimeout(tileConnectivityBannerTimer);
            tileConnectivityBannerTimer = setTimeout(() => {
                showTileConnectivityBanner = false;
                tileConnectivityBannerTimer = null;
            }, 45000);
        }
    }

    function retryMapTiles() {
        tileErrorCount = 0;
        dismissTileConnectivityBanner();
        tileLayer?.getSource()?.refresh?.();
    }

    function checkOnboardingTooltip() {
        try {
            const hasSeen = localStorage.getItem("map_onboarding_seen");
            if (!hasSeen && !offlineEnabled) {
                showOnboardingTooltip = true;
            }
        } catch {
            // ignore storage errors
        }
    }

    function dismissOnboardingTooltip() {
        showOnboardingTooltip = false;
        try {
            localStorage.setItem("map_onboarding_seen", "true");
        } catch {
            // ignore storage errors
        }
    }

    function refreshTabToolbarHost() {
        tabToolbarHostReady = Boolean(
            typeof document !== "undefined" && document.getElementById("map-browser-toolbar-host")
        );
    }

    function setupTabToolbarHostWatcher() {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            isWideViewport = false;
            return;
        }
        tabToolbarMq = window.matchMedia("(min-width: 768px)");
        isWideViewport = tabToolbarMq.matches;
        tabToolbarMqListener = () => {
            isWideViewport = tabToolbarMq?.matches ?? false;
            refreshTabToolbarHost();
        };
        if (typeof tabToolbarMq.addEventListener === "function") {
            tabToolbarMq.addEventListener("change", tabToolbarMqListener);
        } else if (typeof (tabToolbarMq as any).addListener === "function") {
            (tabToolbarMq as any).addListener(tabToolbarMqListener);
        }
        refreshTabToolbarHost();
    }

    function teardownTabToolbarHostWatcher() {
        if (tabToolbarMq && tabToolbarMqListener) {
            if (typeof tabToolbarMq.removeEventListener === "function") {
                tabToolbarMq.removeEventListener("change", tabToolbarMqListener);
            } else if (typeof (tabToolbarMq as any).removeListener === "function") {
                (tabToolbarMq as any).removeListener(tabToolbarMqListener);
            }
        }
        tabToolbarMq = null;
        tabToolbarMqListener = null;
        tabToolbarHostReady = false;
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
        setupTabToolbarHostWatcher();
        initOpenLayers();
        void ensureGeoCoordsReady().then(() => {
            geoWasmEpoch += 1;
        });
        announceListenEnabled = Boolean((GlobalState.config as any)?.announce_store_map_data);
        GlobalEmitter.on("config-updated", onConfigUpdatedExternally);
        await loadSavedState();
        await reloadTelemetry();
        await loadMBTiles();
        checkOnboardingTooltip();
        await tick();
        refreshTabToolbarHost();
        setTimeout(refreshTabToolbarHost, 100);

        telemetryPollTimer = setInterval(() => reloadTelemetry(), 10000);
        onWsEvent("lxmf.telemetry", reloadTelemetry);
        onWsEvent("announce", reloadTelemetry);
        applyMapViewFromRoute();
        unsubscribeRoute = subscribeRoute(() => {
            applyMapViewFromRoute();
        });

        if (map) {
            map.on("pointermove", (evt: any) => {
                if (!isBearingMode || evt.dragging) return;
                const origin = bearingFromGps ? bearingGpsMapCoord : bearingFirstMapCoord;
                if (!origin || !drawSource) return;
                if (!bearingPreviewFeature) {
                    const f = new Feature({
                        geometry: new LineString([origin, evt.coordinate]),
                        type: "draw",
                        bearingPreview: true,
                    });
                    drawSource.addFeature(f);
                    bearingPreviewFeature = f;
                } else {
                    (bearingPreviewFeature.getGeometry() as LineString).setCoordinates([origin, evt.coordinate]);
                }
                const ll0 = toLonLat(origin);
                const ll1 = toLonLat(evt.coordinate);
                const metrics = computeSegmentMetrics(ll0[0], ll0[1], ll1[0], ll1[1]);
                measureTooltipManager?.setMeasureHtml(
                    buildBearingLiveTooltipHtml(metrics, (key) => t(key)),
                    evt.coordinate
                );
            });
        }
    });

    onDestroy(() => {
        teardownTabToolbarHostWatcher();
        if (exportPollTimer) clearInterval(exportPollTimer);
        if (telemetryPollTimer) clearInterval(telemetryPollTimer);
        if (saveStateTimer) clearTimeout(saveStateTimer);
        if (tileConnectivityBannerTimer) clearTimeout(tileConnectivityBannerTimer);
        measureTooltipManager?.destroy();
        GlobalEmitter.off("config-updated", onConfigUpdatedExternally);
        offWsEvent("lxmf.telemetry", reloadTelemetry);
        offWsEvent("announce", reloadTelemetry);
        unsubscribeRoute?.();
        unsubscribeRoute = null;
        for (const id of Object.keys(remoteOverlayLayers)) {
            removeRemoteOverlayLayer(map, remoteOverlayLayers, id);
        }
        if (map) {
            map.setTarget(undefined);
            map = null;
        }
    });
</script>

<div class="flex flex-col h-full w-full bg-sem-surface overflow-hidden">
    {#if useTabToolbar}
        <MapPortal targetId="map-browser-toolbar-host" enabled={useTabToolbar}>
            <MapToolbarControls
                {discoveredVisible}
                {offlineEnabled}
                compact={true}
                ontogglediscovered={toggleDiscovered}
                ontoggleoffline={toggleOffline}
                ontogglemotools={() => (isMapToolsOpen = !isMapToolsOpen)}
                ontogglesettings={() => (isSettingsOpen = !isSettingsOpen)}
                onshare={shareMapView}
            />
        </MapPortal>
    {:else}
        <MapHeaderBar
            {embedded}
            {tabTitle}
            {discoveredVisible}
            {offlineEnabled}
            ontogglediscovered={toggleDiscovered}
            ontoggleoffline={toggleOffline}
            ontogglemotools={() => (isMapToolsOpen = !isMapToolsOpen)}
            ontogglesettings={() => (isSettingsOpen = !isSettingsOpen)}
            onshare={shareMapView}
        />
    {/if}

    <input bind:this={mbtilesFileInput} type="file" accept=".mbtiles" class="hidden" onchange={onMbtilesFileSelected} />

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
            ontogglebearing={toggleBearingMode}
            onclear={() => drawSource?.clear()}
            onlocate={goToMyLocation}
            onsave={() => (showSaveDrawingModal = true)}
            onload={() => (showLoadDrawingModal = true)}
        />

        {#if isBearingMode}
            <MapBearingInstructions
                fromGpsActive={bearingFromGps}
                awaitingSecondTap={Boolean(bearingFirstMapCoord)}
                onusemylocation={startBearingFromMyLocation}
            />
        {/if}

        {#if isExportMode && !exportBbox}
            <MapExportInstructions presets={EXPORT_REGION_PRESETS} onselectpreset={applyExportRegionPreset} />
        {/if}

        {#if isExportMode && exportBbox}
            <MapExportConfigPanel
                minZoom={exportMinZoom}
                maxZoom={exportMaxZoom}
                {estimatedTiles}
                exporting={isExporting}
                tileLimitExceeded={exportTileLimitExceeded}
                onCancel={cancelExportSelection}
                onStart={handleStartExport}
                onUpdateMinZoom={(val) => (exportMinZoom = val)}
                onUpdateMaxZoom={(val) => (exportMaxZoom = val)}
            />
        {/if}

        {#if exportStatus}
            <MapExportProgressPanel
                status={exportStatus}
                exportId={activeExportId}
                onDismiss={() => (exportStatus = null)}
                onCancel={cancelActiveExport}
                onShowOfflineMaps={() => (isMapToolsOpen = true)}
            />
        {/if}

        <MapTileBanner
            show={!offlineEnabled && showTileConnectivityBanner}
            {hasOfflineMap}
            onretry={retryMapTiles}
            onswitchoffline={() => toggleOffline(true)}
            ondismiss={dismissTileConnectivityBanner}
            onopensettings={() => (isSettingsOpen = true)}
        />

        <MapOnboardingTooltip
            show={showOnboardingTooltip}
            style={onboardingTooltipStyle}
            arrowPath={onboardingArrowPath}
            {isMobileScreen}
            ondismiss={dismissOnboardingTooltip}
        />

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

        <div
            bind:this={mapContainer}
            class="absolute inset-0 {isExportMode ? 'cursor-crosshair' : ''}"
            ondragover={onMapDragOver}
            ondragleave={onMapDragLeave}
            ondrop={onMapDrop}
            role="presentation"
        ></div>

        {#if isMapDropTarget}
            <div
                class="absolute inset-0 z-40 flex flex-col items-center justify-center bg-blue-500/20 backdrop-blur-sm border-4 border-blue-500 border-dashed m-4 rounded-2xl pointer-events-none transition-opacity"
            >
                <MaterialDesignIcon iconName="map-plus" class="w-16 h-16 text-sem-accent mb-4" />
                <h3 class="text-lg font-bold text-blue-700 dark:text-blue-300">{t("map.drop_geo_files")}</h3>
                <p class="text-sm text-sem-accent mt-1">{t("map.drop_map_files_hint")}</p>
            </div>
        {/if}

        {#if selectedMarker}
            <MapMarkerPanel
                marker={selectedMarker}
                {coordinateFormat}
                {geoWasmEpoch}
                refLon={centerCoords[0]}
                refLat={centerCoords[1]}
                miniChatOpen={isMiniChatOpen}
                onclose={() => {
                    selectedMarker = null;
                    isMiniChatOpen = false;
                    clearTelemetryPath();
                }}
                ontoggletracking={handleToggleTracking}
                ontoggleminichat={() => (isMiniChatOpen = !isMiniChatOpen)}
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
            oncoordinateformatchange={(fmt) => {
                coordinateFormat = fmt;
                saveState();
            }}
            {settingsPanelPos}
            {isMobileScreen}
            onclose={() => (isSettingsOpen = false)}
            onsetasdefaultview={saveState}
            ontoggletracking={handleToggleTracking}
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
            {announceListenEnabled}
            {announceListenBusy}
            ontoggleoffline={toggleOffline}
            ontogglecaching={toggleCaching}
            onsetactivembtiles={(name) => setActiveMBTiles(name).then(loadMBTiles)}
            ondeletembtiles={(name) => deleteMBTiles(name).then(loadMBTiles)}
            onsavembtilesdir={(dir) => saveMBTilesDir(dir)}
            onclearcache={() => TileCache.clear()}
            onexportregion={toggleExportMode}
            onstartexport={handleStartExport}
            onrestorestarter={() => restoreStarterTiles().then(loadMBTiles)}
            onuploadmbtiles={triggerMbtilesUpload}
            onimportfeatures={onVectorExchangeImport}
            onimporterror={onVectorExchangeImportError}
            onexportgeojson={exportVectorGeoJson}
            onexportkml={exportVectorKml}
            onexportkmz={exportVectorKmz}
            onexportgpx={exportVectorGpx}
            onoverlayschanged={onRemoteOverlaysChanged}
            onexportoverlay={onRemoteOverlayExport}
            oncopyoverlaytodrawings={onRemoteOverlayCopyToDrawings}
            onoverlayerror={() => ToastUtils.error(t("map.remote_overlays_error"))}
            ontoggleannouncelisten={onToggleAnnounceListen}
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
                if (contextMenuMapCoord && map) {
                    const lonLat = toLonLat(contextMenuMapCoord);
                    openPingModalAt(lonLat[1], lonLat[0], map.getView().getZoom() || currentZoom);
                }
            }}
            onclearmap={() => drawSource?.clear()}
            onclose={() => (showContextMenu = false)}
        />

        <MapPingModal
            show={showMapPingModal}
            summary={mapPingSummary}
            {conversationOptions}
            onclose={() => (showMapPingModal = false)}
            onsend={handleSendMapPing}
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

        {#if isUploading}
            <MapLoadingOverlay message={t("map.uploading")} />
        {/if}
    </div>
</div>

<style>
    :global(.cursor-crosshair) {
        cursor: crosshair !important;
    }

    :global(.ol-tooltip) {
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

    :global(.ol-tooltip-measure) {
        opacity: 1;
        font-weight: bold;
    }

    :global(.ol-tooltip-static) {
        background-color: #3b82f6;
        color: white;
        border: 1px solid white;
    }

    :global(.ol-tooltip-measure:before),
    :global(.ol-tooltip-static:before) {
        border-top: 6px solid rgba(0, 0, 0, 0.7);
        border-right: 6px solid transparent;
        border-left: 6px solid transparent;
        content: "";
        position: absolute;
        bottom: -6px;
        margin-left: -7px;
        left: 50%;
    }

    :global(.ol-tooltip-static:before) {
        border-top-color: #3b82f6;
    }
</style>
