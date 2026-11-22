// SPDX-License-Identifier: 0BSD

/**
 * Bridge between plugin workers and the live map instances.
 *
 * MapPage registers one provider per mounted map (browser tabs and pop-outs).
 * Providers supply the map-library primitives (layer factory, GeoJSON parser,
 * projection helpers) so this module stays free of map-renderer imports and
 * can live in the main bundle.
 *
 * Plugin layer data is kept per plugin so it survives map page navigation and
 * is replayed onto every map instance, including ones created later.
 */

const MAX_GEOJSON_CHARS = 2_000_000;
const MAX_GEOJSON_FEATURES = 20000;
const MAX_PLUGIN_LAYERS = 64;
const HIT_TOLERANCE_PX = 5;
const PROVIDER_WAIT_TIMEOUT_MS = 15000;
const PROVIDER_WAIT_POLL_MS = 100;

export const PLUGIN_MAP_EVENTS = Object.freeze(["click", "moveend", "featureclick"]);
const PLUGIN_MAP_EVENT_SET = new Set(PLUGIN_MAP_EVENTS);

/**
 * @typedef {Object} PluginMapProvider
 * @property {string} id
 * @property {object} map
 * @property {() => boolean} [isActive]
 * @property {(coord: number[]) => [number, number]} toLonLat
 * @property {(lonLat: [number, number]) => number[]} fromLonLat
 * @property {() => { layer: object, source: { clear: () => void, addFeatures: (features: object[]) => void } }} createPluginLayer
 * @property {(geojsonText: string) => object[]} parsePluginGeoJson
 */

/** @type {Map<string, { id: string, provider: PluginMapProvider, isActive: () => boolean, entries: Map<string, { source: object, layer: object }>, layerMeta: Map<object, { pluginId: string, layerId: string }>, listeners: Array<[string, Function]> }>} */
const providers = new Map();
/** @type {Map<string, Map<string, { name: string, geojson: string | null }>>} */
const pluginLayers = new Map();
/** @type {Map<string, Set<string>>} */
const pluginEvents = new Map();
/** @type {Map<string, (message: object) => void>} */
const notifiers = new Map();
let layerSeq = 0;

function layerKey(pluginId, layerId) {
    return `${pluginId}\n${layerId}`;
}

function isProviderActive(rec) {
    try {
        return Boolean(rec.isActive());
    } catch {
        return false;
    }
}

function activeProvider() {
    for (const rec of providers.values()) {
        if (isProviderActive(rec)) {
            return rec;
        }
    }
    return null;
}

function attachProviderListeners(rec) {
    const map = rec.provider.map;
    const onClick = (evt) => handleProviderClick(rec, evt);
    const onMoveEnd = () => handleProviderMoveEnd(rec);
    map.on("click", onClick);
    map.on("moveend", onMoveEnd);
    rec.listeners.push(["click", onClick], ["moveend", onMoveEnd]);
}

/**
 * @param {PluginMapProvider} provider
 */
export function registerMapProvider(provider) {
    const id = String(provider?.id || "");
    if (!id || !provider?.map || typeof provider.map.addLayer !== "function") {
        return;
    }
    if (providers.has(id)) {
        unregisterMapProvider(id);
    }
    const rec = {
        id,
        provider,
        isActive: typeof provider.isActive === "function" ? provider.isActive : () => true,
        entries: new Map(),
        layerMeta: new Map(),
        listeners: [],
    };
    providers.set(id, rec);
    attachProviderListeners(rec);
    for (const [pluginId, store] of pluginLayers) {
        for (const [layerId, entry] of store) {
            try {
                attachPluginLayer(rec, pluginId, layerId, entry);
            } catch (err) {
                console.warn(`Plugin map layer attach failed for ${pluginId}/${layerId}:`, err);
            }
        }
    }
}

/**
 * @param {string} id
 */
export function unregisterMapProvider(id) {
    const rec = providers.get(String(id || ""));
    if (!rec) {
        return;
    }
    const map = rec.provider.map;
    for (const [type, fn] of rec.listeners) {
        try {
            map.un(type, fn);
        } catch {
            // Map may already be torn down.
        }
    }
    for (const { layer } of rec.entries.values()) {
        try {
            map.removeLayer(layer);
        } catch {
            // Map may already be torn down.
        }
    }
    providers.delete(rec.id);
}

function dispatchMapEvent(event, payload) {
    for (const [pluginId, events] of pluginEvents) {
        if (!events.has(event)) {
            continue;
        }
        const notify = notifiers.get(pluginId);
        if (!notify) {
            continue;
        }
        try {
            notify({ type: "map-event", event, payload });
        } catch {
            // A broken plugin channel must not break the map.
        }
    }
}

function sanitizeFeatureProperties(properties) {
    const out = {};
    for (const [key, value] of Object.entries(properties || {})) {
        if (key === "geometry") {
            continue;
        }
        const t = typeof value;
        if (value == null || t === "string" || t === "number" || t === "boolean") {
            out[key] = value;
        } else if (
            Array.isArray(value) &&
            value.every((v) => v == null || ["string", "number", "boolean"].includes(typeof v))
        ) {
            out[key] = value;
        }
    }
    return out;
}

function featureIdOf(feature) {
    try {
        const id = feature.getId?.();
        return id == null ? null : String(id);
    } catch {
        return null;
    }
}

function findPluginFeatureAtPixel(rec, pixel) {
    let found = null;
    try {
        rec.provider.map.forEachFeatureAtPixel(
            pixel,
            (feature, layer) => {
                const meta = rec.layerMeta.get(layer);
                if (meta && feature) {
                    found = { feature, meta };
                    return true;
                }
                return undefined;
            },
            {
                hitTolerance: HIT_TOLERANCE_PX,
                layerFilter: (layer) => rec.layerMeta.has(layer),
            }
        );
    } catch {
        return null;
    }
    return found;
}

function handleProviderClick(rec, evt) {
    try {
        if (!isProviderActive(rec) || !evt || !evt.pixel) {
            return;
        }
        const map = rec.provider.map;
        const coord = map.getCoordinateFromPixel(evt.pixel);
        if (!coord) {
            return;
        }
        const [lon, lat] = rec.provider.toLonLat(coord);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
            return;
        }
        const pixelPayload = { x: evt.pixel[0], y: evt.pixel[1] };
        dispatchMapEvent("click", { lat, lon, pixel: pixelPayload });
        const hit = findPluginFeatureAtPixel(rec, evt.pixel);
        if (!hit) {
            return;
        }
        dispatchMapEvent("featureclick", {
            lat,
            lon,
            layerId: hit.meta.layerId,
            featureId: featureIdOf(hit.feature),
            properties: sanitizeFeatureProperties(hit.feature.getProperties?.() || {}),
        });
    } catch {
        // Plugin event delivery must never break map interaction.
    }
}

function getMapState(rec) {
    const map = rec.provider.map;
    const view = map.getView();
    const centerCoord = view.getCenter();
    const [lon, lat] = centerCoord ? rec.provider.toLonLat(centerCoord) : [null, null];
    const zoom = view.getZoom();
    const hasCenter = Number.isFinite(lon) && Number.isFinite(lat);
    const rotation = view.getRotation();
    const size = map.getSize();
    let bounds = null;
    try {
        const extent = view.calculateExtent();
        const sw = rec.provider.toLonLat([extent[0], extent[1]]);
        const ne = rec.provider.toLonLat([extent[2], extent[3]]);
        bounds = [
            [sw[0], sw[1]],
            [ne[0], ne[1]],
        ];
    } catch {
        // View extent unavailable; bounds stay null.
    }
    return {
        available: true,
        center: hasCenter ? [lon, lat] : null,
        zoom: Number.isFinite(zoom) ? zoom : null,
        bearing: Number.isFinite(rotation) ? (rotation * 180) / Math.PI : 0,
        bounds,
        size: Array.isArray(size) ? { width: size[0], height: size[1] } : null,
    };
}

function handleProviderMoveEnd(rec) {
    if (!isProviderActive(rec)) {
        return;
    }
    try {
        dispatchMapEvent("moveend", getMapState(rec));
    } catch {
        // Plugin event delivery must never break map interaction.
    }
}

function pluginLayerStore(pluginId) {
    let store = pluginLayers.get(pluginId);
    if (!store) {
        store = new Map();
        pluginLayers.set(pluginId, store);
    }
    return store;
}

function loadFeaturesIntoSource(rec, source, geojsonText) {
    if (!geojsonText) {
        return;
    }
    source.addFeatures(rec.provider.parsePluginGeoJson(geojsonText));
}

/**
 * Structural validation cannot catch everything the map parser rejects.
 * When a provider exists, parse once at write time so plugins get a real
 * error instead of a silently empty layer.
 * @param {string} geojsonText
 */
function assertGeoJsonParseable(geojsonText) {
    const rec = providers.values().next().value;
    if (!rec || !geojsonText) {
        return;
    }
    try {
        rec.provider.parsePluginGeoJson(geojsonText);
    } catch {
        throw new Error("invalid_geojson");
    }
}

function attachPluginLayer(rec, pluginId, layerId, entry) {
    const key = layerKey(pluginId, layerId);
    if (rec.entries.has(key)) {
        return;
    }
    const { layer, source } = rec.provider.createPluginLayer();
    rec.provider.map.addLayer(layer);
    rec.entries.set(key, { source, layer });
    rec.layerMeta.set(layer, { pluginId, layerId });
    try {
        loadFeaturesIntoSource(rec, source, entry?.geojson || null);
    } catch (err) {
        try {
            rec.provider.map.removeLayer(layer);
        } catch {
            // ignore
        }
        rec.entries.delete(key);
        rec.layerMeta.delete(layer);
        throw err;
    }
}

function refreshPluginLayer(rec, pluginId, layerId) {
    const key = layerKey(pluginId, layerId);
    const attached = rec.entries.get(key);
    const entry = pluginLayers.get(pluginId)?.get(layerId);
    if (!attached) {
        if (entry) {
            try {
                attachPluginLayer(rec, pluginId, layerId, entry);
            } catch (err) {
                console.warn(`Plugin map layer attach failed for ${pluginId}/${layerId}:`, err);
            }
        }
        return;
    }
    attached.source.clear();
    try {
        loadFeaturesIntoSource(rec, attached.source, entry?.geojson || null);
    } catch (err) {
        console.warn(`Plugin map layer refresh failed for ${pluginId}/${layerId}:`, err);
    }
}

function detachPluginLayer(rec, pluginId, layerId) {
    const key = layerKey(pluginId, layerId);
    const attached = rec.entries.get(key);
    if (!attached) {
        return;
    }
    try {
        rec.provider.map.removeLayer(attached.layer);
    } catch {
        // Map may already be torn down.
    }
    rec.entries.delete(key);
    rec.layerMeta.delete(attached.layer);
}

/**
 * Permission id a map request action requires, or null when none is needed.
 * @param {string} action
 * @returns {string | null}
 */
export function requiredMapPermission(action) {
    switch (action) {
        case "getState":
            return "map:read";
        case "setView":
        case "addLayer":
        case "setLayerData":
        case "removeLayer":
        case "clearLayers":
            return "map:write";
        default:
            return null;
    }
}

function normalizeGeoJsonPayload(data) {
    let parsed = data;
    if (typeof data === "string") {
        if (data.length > MAX_GEOJSON_CHARS) {
            throw new Error("geojson_too_large");
        }
        try {
            parsed = JSON.parse(data);
        } catch {
            throw new Error("invalid_geojson");
        }
    }
    if (!parsed || typeof parsed !== "object") {
        throw new Error("invalid_geojson");
    }
    let fc = parsed;
    if (parsed.type === "Feature") {
        fc = { type: "FeatureCollection", features: [parsed] };
    } else if (parsed.type !== "FeatureCollection") {
        throw new Error("invalid_geojson");
    }
    if (!Array.isArray(fc.features)) {
        throw new Error("invalid_geojson");
    }
    if (fc.features.length > MAX_GEOJSON_FEATURES) {
        throw new Error("too_many_features");
    }
    for (const feature of fc.features) {
        if (!feature || feature.type !== "Feature") {
            throw new Error("invalid_geojson");
        }
        const geom = feature.geometry;
        if (geom != null && (typeof geom !== "object" || typeof geom.type !== "string")) {
            throw new Error("invalid_geojson");
        }
    }
    const text = JSON.stringify(fc);
    if (text.length > MAX_GEOJSON_CHARS) {
        throw new Error("geojson_too_large");
    }
    return { text, count: fc.features.length };
}

function parseLonLatPair(value, label) {
    if (!Array.isArray(value) || value.length < 2) {
        throw new Error(`invalid_${label}`);
    }
    const lon = Number(value[0]);
    const lat = Number(value[1]);
    if (!Number.isFinite(lon) || !Number.isFinite(lat) || lon < -180 || lon > 180 || lat < -90 || lat > 90) {
        throw new Error(`invalid_${label}`);
    }
    return [lon, lat];
}

async function ensureActiveProvider(navigate, router) {
    const existing = activeProvider();
    if (existing) {
        return existing;
    }
    if (!navigate) {
        return null;
    }
    if (router && typeof router.push === "function") {
        try {
            await router.push({ name: "map" });
        } catch {
            // Navigation failure still gets a chance via polling below.
        }
    }
    const deadline = Date.now() + PROVIDER_WAIT_TIMEOUT_MS;
    while (Date.now() < deadline) {
        const rec = activeProvider();
        if (rec) {
            return rec;
        }
        await new Promise((resolve) => setTimeout(resolve, PROVIDER_WAIT_POLL_MS));
    }
    return null;
}

async function setMapView(req, ctx) {
    const params = req?.view && typeof req.view === "object" ? req.view : req || {};
    const target = {};
    let centerLonLat = null;
    if (params.center != null) {
        centerLonLat = parseLonLatPair(params.center, "center");
    }
    if (params.zoom != null) {
        const zoom = Number(params.zoom);
        if (!Number.isFinite(zoom) || zoom < 0 || zoom > 22) {
            throw new Error("invalid_zoom");
        }
        target.zoom = zoom;
    }
    if (params.bearing != null) {
        const bearing = Number(params.bearing);
        if (!Number.isFinite(bearing)) {
            throw new Error("invalid_bearing");
        }
        target.rotation = (bearing * Math.PI) / 180;
    }
    const durationMs = params.durationMs != null ? Number(params.durationMs) : 400;
    if (!Number.isFinite(durationMs) || durationMs < 0 || durationMs > 60000) {
        throw new Error("invalid_duration");
    }
    const rec = await ensureActiveProvider(Boolean(params.navigate), ctx?.router);
    if (!rec) {
        throw new Error("map_not_open");
    }
    if (centerLonLat) {
        target.center = rec.provider.fromLonLat(centerLonLat);
    }
    if (Object.keys(target).length === 0) {
        return getMapState(rec);
    }
    const view = rec.provider.map.getView();
    if (durationMs > 0) {
        // OL animate accepts a trailing completion callback; fall back to a
        // timer so a missing callback cannot hang the request.
        await new Promise((resolve) => {
            const timer = setTimeout(resolve, durationMs + 1000);
            try {
                view.animate({ ...target, duration: durationMs }, () => {
                    clearTimeout(timer);
                    resolve();
                });
            } catch {
                clearTimeout(timer);
                resolve();
            }
        });
    } else {
        view.animate({ ...target, duration: durationMs });
    }
    return getMapState(rec);
}

function addPluginLayer(pluginId, req) {
    const opts = req || {};
    const rawId = opts.id ?? opts.layerId;
    const layerId = String(rawId || `layer-${++layerSeq}`).trim();
    if (!/^[A-Za-z0-9._:-]{1,128}$/.test(layerId)) {
        throw new Error("invalid_layer_id");
    }
    const store = pluginLayerStore(pluginId);
    if (store.has(layerId)) {
        throw new Error("layer_exists");
    }
    if (store.size >= MAX_PLUGIN_LAYERS) {
        throw new Error("too_many_layers");
    }
    const entry = {
        name: typeof opts.name === "string" ? opts.name.slice(0, 200) : "",
        geojson: null,
    };
    if (opts.data != null) {
        const normalized = normalizeGeoJsonPayload(opts.data);
        assertGeoJsonParseable(normalized.text);
        entry.geojson = normalized.text;
    }
    store.set(layerId, entry);
    for (const rec of providers.values()) {
        try {
            attachPluginLayer(rec, pluginId, layerId, entry);
        } catch (err) {
            console.warn(`Plugin map layer attach failed for ${pluginId}/${layerId}:`, err);
        }
    }
    return { layerId };
}

function setPluginLayerData(pluginId, req) {
    const layerId = String(req?.layerId || "");
    const entry = pluginLayers.get(pluginId)?.get(layerId);
    if (!entry) {
        throw new Error("layer_not_found");
    }
    const normalized = normalizeGeoJsonPayload(req?.data ?? req?.geojson);
    assertGeoJsonParseable(normalized.text);
    entry.geojson = normalized.text;
    for (const rec of providers.values()) {
        refreshPluginLayer(rec, pluginId, layerId);
    }
    return { layerId, featureCount: normalized.count };
}

function removePluginLayer(pluginId, req) {
    const layerId = String(req?.layerId || "");
    const store = pluginLayers.get(pluginId);
    if (!store?.has(layerId)) {
        throw new Error("layer_not_found");
    }
    store.delete(layerId);
    if (!store.size) {
        pluginLayers.delete(pluginId);
    }
    for (const rec of providers.values()) {
        detachPluginLayer(rec, pluginId, layerId);
    }
    return { layerId, removed: true };
}

function clearPluginLayers(pluginId) {
    const store = pluginLayers.get(pluginId);
    const count = store ? store.size : 0;
    if (store) {
        for (const layerId of [...store.keys()]) {
            for (const rec of providers.values()) {
                detachPluginLayer(rec, pluginId, layerId);
            }
        }
        pluginLayers.delete(pluginId);
    }
    return { cleared: count };
}

/**
 * @param {string} pluginId
 * @param {Record<string, unknown>} req
 * @param {{ router?: { push: Function } | null }} [ctx]
 */
export async function handlePluginMapRequest(pluginId, req, ctx = {}) {
    const action = String(req?.action || "");
    switch (action) {
        case "isAvailable": {
            return {
                available: providers.size > 0,
                active: Boolean(activeProvider()),
            };
        }
        case "getState": {
            const rec = activeProvider();
            if (!rec) {
                return {
                    available: providers.size > 0,
                    active: false,
                    center: null,
                    zoom: null,
                    bearing: null,
                    bounds: null,
                    size: null,
                };
            }
            return { ...getMapState(rec), active: true };
        }
        case "setView":
            return setMapView(req, ctx);
        case "addLayer":
            return addPluginLayer(pluginId, req);
        case "setLayerData":
            return setPluginLayerData(pluginId, req);
        case "removeLayer":
            return removePluginLayer(pluginId, req);
        case "clearLayers":
            return clearPluginLayers(pluginId);
        default:
            throw new Error(`unknown_map_action:${action || "?"}`);
    }
}

/**
 * @param {string} pluginId
 * @param {string[]} events
 * @param {boolean} subscribe
 */
export function updatePluginMapEvents(pluginId, events, subscribe) {
    if (!Array.isArray(events)) {
        return;
    }
    const valid = events.filter((e) => typeof e === "string" && PLUGIN_MAP_EVENT_SET.has(e));
    if (!valid.length) {
        return;
    }
    let set = pluginEvents.get(pluginId);
    if (subscribe) {
        if (!set) {
            set = new Set();
            pluginEvents.set(pluginId, set);
        }
        for (const event of valid) {
            set.add(event);
        }
    } else if (set) {
        for (const event of valid) {
            set.delete(event);
        }
        if (!set.size) {
            pluginEvents.delete(pluginId);
        }
    }
}

/**
 * @param {string} pluginId
 * @param {((message: object) => void) | null} notify
 */
export function setPluginMapNotifier(pluginId, notify) {
    if (typeof notify === "function") {
        notifiers.set(pluginId, notify);
    } else {
        notifiers.delete(pluginId);
    }
}

/**
 * Drop all layers, subscriptions, and the notifier for a plugin.
 * @param {string} pluginId
 */
export function removePluginMapState(pluginId) {
    clearPluginLayers(pluginId);
    pluginEvents.delete(pluginId);
    notifiers.delete(pluginId);
}

/** Test hook: clears all bridge state. */
export function resetPluginMapBridgeForTests() {
    for (const id of [...providers.keys()]) {
        unregisterMapProvider(id);
    }
    pluginLayers.clear();
    pluginEvents.clear();
    notifiers.clear();
}
