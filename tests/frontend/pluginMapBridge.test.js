// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it } from "vitest";

import {
    handlePluginMapRequest,
    registerMapProvider,
    removePluginMapState,
    requiredMapPermission,
    resetPluginMapBridgeForTests,
    setPluginMapNotifier,
    unregisterMapProvider,
    updatePluginMapEvents,
} from "../../meshchatx/src/frontend/js/plugins/pluginMapBridge.js";

const PLUGIN = "com.example.test";

function makeStubView() {
    const view = {
        animations: [],
        _center: [100, 200],
        _zoom: 11,
        _rotation: 0,
        getCenter: () => view._center,
        getZoom: () => view._zoom,
        getRotation: () => view._rotation,
        calculateExtent: () => [90, 190, 110, 210],
        animate(opts, done) {
            this.animations.push(opts);
            if (opts.center) {
                view._center = opts.center;
            }
            if (opts.zoom != null) {
                view._zoom = opts.zoom;
            }
            if (opts.rotation != null) {
                view._rotation = opts.rotation;
            }
            if (typeof done === "function") {
                done(true);
            }
        },
    };
    return view;
}

function makeStubMap() {
    const listeners = new Map();
    const view = makeStubView();
    return {
        view,
        layers: [],
        addedFeatures: [],
        hitResult: null,
        on(type, fn) {
            if (!listeners.has(type)) {
                listeners.set(type, []);
            }
            listeners.get(type).push(fn);
        },
        un(type, fn) {
            listeners.set(
                type,
                (listeners.get(type) || []).filter((f) => f !== fn)
            );
        },
        emit(type, evt) {
            for (const fn of listeners.get(type) || []) {
                fn(evt);
            }
        },
        addLayer(layer) {
            this.layers.push(layer);
        },
        removeLayer(layer) {
            const idx = this.layers.indexOf(layer);
            if (idx >= 0) {
                this.layers.splice(idx, 1);
            }
        },
        getView: () => view,
        getCoordinateFromPixel: () => [50, 60],
        forEachFeatureAtPixel(pixel, callback) {
            if (this.hitResult) {
                callback(this.hitResult.feature, this.hitResult.layer);
            }
        },
        getSize: () => [800, 600],
    };
}

function makeProvider(id, { active = true } = {}) {
    const map = makeStubMap();
    return {
        id,
        map,
        isActive: () => active,
        toLonLat: (coord) => [coord[0], coord[1]],
        fromLonLat: (lonLat) => [lonLat[0], lonLat[1]],
        createPluginLayer: () => {
            const source = {
                features: [],
                clear() {
                    this.features = [];
                },
                addFeatures(features) {
                    this.features.push(...features);
                    map.addedFeatures.push(...features);
                },
            };
            const layer = { source };
            return { layer, source };
        },
        parsePluginGeoJson: (text) => {
            const fc = JSON.parse(text);
            const list = fc.type === "FeatureCollection" ? fc.features : [fc];
            return list.map((f, i) => ({
                geojson: f,
                getId: () => f.id ?? null,
                getProperties: () => ({ ...(f.properties || {}) }),
            }));
        },
    };
}

const SAMPLE_FC = {
    type: "FeatureCollection",
    features: [
        {
            type: "Feature",
            id: "f1",
            geometry: { type: "Point", coordinates: [1, 2] },
            properties: { name: "Alpha" },
        },
    ],
};

describe("pluginMapBridge", () => {
    beforeEach(() => {
        resetPluginMapBridgeForTests();
    });

    it("maps actions to permission ids", () => {
        expect(requiredMapPermission("isAvailable")).toBeNull();
        expect(requiredMapPermission("getState")).toBe("map:read");
        expect(requiredMapPermission("setView")).toBe("map:write");
        expect(requiredMapPermission("addLayer")).toBe("map:write");
        expect(requiredMapPermission("clearLayers")).toBe("map:write");
        expect(requiredMapPermission("bogus")).toBeNull();
    });

    it("reports availability and state", async () => {
        expect(await handlePluginMapRequest(PLUGIN, { action: "isAvailable" })).toEqual({
            available: false,
            active: false,
        });
        const provider = makeProvider("p1");
        registerMapProvider(provider);
        const avail = await handlePluginMapRequest(PLUGIN, { action: "isAvailable" });
        expect(avail).toEqual({ available: true, active: true });
        const state = await handlePluginMapRequest(PLUGIN, { action: "getState" });
        expect(state.available).toBe(true);
        expect(state.center).toEqual([100, 200]);
        expect(state.zoom).toBe(11);
        expect(state.bounds).toEqual([
            [90, 190],
            [110, 210],
        ]);
    });

    it("stores layer data and replays it onto later providers", async () => {
        await handlePluginMapRequest(PLUGIN, {
            action: "addLayer",
            id: "zones",
            name: "Zones",
            data: SAMPLE_FC,
        });
        const provider = makeProvider("p1");
        registerMapProvider(provider);
        expect(provider.map.layers.length).toBe(1);
        expect(provider.map.addedFeatures.length).toBe(1);

        const provider2 = makeProvider("p2");
        registerMapProvider(provider2);
        expect(provider2.map.layers.length).toBe(1);
        expect(provider2.map.addedFeatures.length).toBe(1);
    });

    it("updates and removes layers", async () => {
        await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "a" });
        const provider = makeProvider("p1");
        registerMapProvider(provider);
        await handlePluginMapRequest(PLUGIN, {
            action: "setLayerData",
            layerId: "a",
            data: SAMPLE_FC,
        });
        expect(provider.map.addedFeatures.length).toBe(1);
        await handlePluginMapRequest(PLUGIN, { action: "removeLayer", layerId: "a" });
        expect(provider.map.layers.length).toBe(0);
        await expect(handlePluginMapRequest(PLUGIN, { action: "removeLayer", layerId: "a" })).rejects.toThrow(
            "layer_not_found"
        );
    });

    it("rejects duplicate layers and bad geojson", async () => {
        await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "a" });
        await expect(handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "a" })).rejects.toThrow("layer_exists");
        await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "b" });
        await expect(
            handlePluginMapRequest(PLUGIN, { action: "setLayerData", layerId: "b", data: { nope: true } })
        ).rejects.toThrow("invalid_geojson");
        await expect(
            handlePluginMapRequest(PLUGIN, { action: "setLayerData", layerId: "missing", data: SAMPLE_FC })
        ).rejects.toThrow("layer_not_found");
    });

    it("moves the camera on the active provider only", async () => {
        const active = makeProvider("active");
        const inactive = makeProvider("inactive", { active: false });
        registerMapProvider(inactive);
        registerMapProvider(active);
        const result = await handlePluginMapRequest(PLUGIN, {
            action: "setView",
            view: { center: [10, 20], zoom: 9, bearing: 90, durationMs: 0 },
        });
        expect(active.map.view.animations.length).toBe(1);
        expect(inactive.map.view.animations.length).toBe(0);
        expect(active.map.view.animations[0].center).toEqual([10, 20]);
        expect(active.map.view.animations[0].zoom).toBe(9);
        // setView resolves after the animation so the returned state is the
        // destination, not the pre-animation view.
        expect(result.center).toEqual([10, 20]);
        expect(result.zoom).toBe(9);
        expect(result.bearing).toBeCloseTo(90);
    });

    it("returns post-animation state for animated setView", async () => {
        const provider = makeProvider("p1");
        registerMapProvider(provider);
        const result = await handlePluginMapRequest(PLUGIN, {
            action: "setView",
            view: { center: [30, 40], zoom: 12, durationMs: 100 },
        });
        expect(result.center).toEqual([30, 40]);
        expect(result.zoom).toBe(12);
    });

    it("reports available but inactive state when no provider is active", async () => {
        registerMapProvider(makeProvider("p1", { active: false }));
        const state = await handlePluginMapRequest(PLUGIN, { action: "getState" });
        expect(state).toEqual({
            available: true,
            active: false,
            center: null,
            zoom: null,
            bearing: null,
            bounds: null,
            size: null,
        });
    });

    it("fails setView when no map is active", async () => {
        await expect(handlePluginMapRequest(PLUGIN, { action: "setView", view: { center: [1, 2] } })).rejects.toThrow(
            "map_not_open"
        );
    });

    it("dispatches click and featureclick events to subscribed plugins", async () => {
        const messages = [];
        setPluginMapNotifier(PLUGIN, (msg) => messages.push(msg));
        updatePluginMapEvents(PLUGIN, ["click", "featureclick"], true);

        const provider = makeProvider("p1");
        const feature = {
            getId: () => "f1",
            getProperties: () => ({ name: "Alpha", geometry: {} }),
        };
        // layerMeta is populated by attachPluginLayer; register a layer first.
        await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "a", data: SAMPLE_FC });
        registerMapProvider(provider);
        // Point the hit test at the registered plugin layer.
        const registeredLayer = provider.map.layers[0];
        provider.map.hitResult = { feature, layer: registeredLayer };

        provider.map.emit("click", { pixel: [5, 6] });
        const clickEvent = messages.find((m) => m.event === "click");
        expect(clickEvent).toBeTruthy();
        expect(clickEvent.payload.lat).toBe(60);
        expect(clickEvent.payload.lon).toBe(50);

        const featureEvent = messages.find((m) => m.event === "featureclick");
        expect(featureEvent).toBeTruthy();
        expect(featureEvent.payload.properties.name).toBe("Alpha");
        expect(featureEvent.payload.properties.geometry).toBeUndefined();
        expect(featureEvent.payload.layerId).toBe("a");
    });

    it("does not dispatch events from inactive providers", async () => {
        const messages = [];
        setPluginMapNotifier(PLUGIN, (msg) => messages.push(msg));
        updatePluginMapEvents(PLUGIN, ["click"], true);
        const provider = makeProvider("p1", { active: false });
        registerMapProvider(provider);
        provider.map.emit("click", { pixel: [1, 2] });
        expect(messages.length).toBe(0);
    });

    it("removePluginMapState drops layers and subscriptions", async () => {
        const messages = [];
        setPluginMapNotifier(PLUGIN, (msg) => messages.push(msg));
        updatePluginMapEvents(PLUGIN, ["click"], true);
        await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "a", data: SAMPLE_FC });
        const provider = makeProvider("p1");
        registerMapProvider(provider);
        expect(provider.map.layers.length).toBe(1);

        removePluginMapState(PLUGIN);
        expect(provider.map.layers.length).toBe(0);
        provider.map.emit("click", { pixel: [1, 2] });
        expect(messages.length).toBe(0);
        await expect(
            handlePluginMapRequest(PLUGIN, { action: "setLayerData", layerId: "a", data: SAMPLE_FC })
        ).rejects.toThrow("layer_not_found");
    });

    it("rejects oversized geojson objects, not just strings", async () => {
        await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "big" });
        const huge = "x".repeat(2_000_001);
        const fc = {
            type: "FeatureCollection",
            features: [
                {
                    type: "Feature",
                    geometry: { type: "Point", coordinates: [1, 2] },
                    properties: { blob: huge },
                },
            ],
        };
        await expect(
            handlePluginMapRequest(PLUGIN, { action: "setLayerData", layerId: "big", data: fc })
        ).rejects.toThrow("geojson_too_large");
    });

    it("caps the number of layers per plugin", async () => {
        for (let i = 0; i < 64; i += 1) {
            await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: `l${i}` });
        }
        await expect(handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "one-more" })).rejects.toThrow(
            "too_many_layers"
        );
    });

    it("rejects geojson the map parser cannot read when a provider exists", async () => {
        const provider = makeProvider("p1");
        provider.parsePluginGeoJson = () => {
            throw new Error("parse failed");
        };
        registerMapProvider(provider);
        await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "a" });
        await expect(
            handlePluginMapRequest(PLUGIN, { action: "setLayerData", layerId: "a", data: SAMPLE_FC })
        ).rejects.toThrow("invalid_geojson");
    });

    it("unregisterMapProvider removes plugin layers from that map only", async () => {
        await handlePluginMapRequest(PLUGIN, { action: "addLayer", id: "a", data: SAMPLE_FC });
        const p1 = makeProvider("p1");
        const p2 = makeProvider("p2");
        registerMapProvider(p1);
        registerMapProvider(p2);
        expect(p1.map.layers.length).toBe(1);
        expect(p2.map.layers.length).toBe(1);
        unregisterMapProvider("p1");
        expect(p1.map.layers.length).toBe(0);
        expect(p2.map.layers.length).toBe(1);
    });
});
