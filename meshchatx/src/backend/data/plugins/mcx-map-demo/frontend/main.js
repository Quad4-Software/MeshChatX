// SPDX-License-Identifier: 0BSD

/**
 * Map Demo - reference plugin for the map capability.
 *
 * Demonstrates api.map: GeoJSON layers with simplestyle properties,
 * camera moves, and click / featureclick / moveend events.
 */

const DEMO_LAYER_ID = "demo";
const PICKED_LAYER_ID = "picked";
const SAMPLE_CENTER = [16.3738, 48.2082]; // [lon, lat]

/**
 * @param {any} api
 * @param {string} key
 * @param {Record<string, string | number>} [params]
 */
function label(api, key, params = {}) {
    let text = api.t(key);
    for (const [name, value] of Object.entries(params)) {
        text = text.replace(`{${name}}`, String(value));
    }
    return text;
}

function toast(api, key, params = {}, type = "info") {
    if (typeof api.toast === "function") {
        api.toast(label(api, key, params), type);
    }
}

function pointFeature(lon, lat, name, color) {
    return {
        type: "Feature",
        geometry: { type: "Point", coordinates: [lon, lat] },
        properties: {
            name,
            "marker-color": color,
            "marker-size": "medium",
        },
    };
}

function sampleLayerData() {
    return {
        type: "FeatureCollection",
        features: [
            {
                type: "Feature",
                geometry: {
                    type: "Polygon",
                    coordinates: [
                        [
                            [16.3, 48.15],
                            [16.45, 48.15],
                            [16.45, 48.27],
                            [16.3, 48.27],
                            [16.3, 48.15],
                        ],
                    ],
                },
                properties: {
                    name: "Demo zone",
                    stroke: "#0284c7",
                    "stroke-width": 2,
                    fill: "#0284c7",
                    "fill-opacity": 0.18,
                },
            },
            {
                type: "Feature",
                geometry: {
                    type: "LineString",
                    coordinates: [
                        [16.3, 48.16],
                        [16.36, 48.2],
                        [16.42, 48.24],
                    ],
                },
                properties: {
                    name: "Demo route",
                    stroke: "#d97706",
                    "stroke-width": 3,
                },
            },
            pointFeature(SAMPLE_CENTER[0], SAMPLE_CENTER[1], "Demo marker", "#dc2626"),
        ],
    };
}

/**
 * @param {{ t: (key: string) => string, setUi: Function, onAction: Function, onRefresh: Function, onInput?: Function, map: any, toast?: Function, hasPermission: Function }} api
 */
export async function activate(api) {
    const state = {
        pickMode: false,
        mapState: null,
        mapError: "",
        layerIds: new Set(),
        subscriptions: [],
    };

    function mapDenied() {
        return !api.hasPermission("map:read") && !api.hasPermission("map:write");
    }

    async function ensureLayer(layerId) {
        if (!state.layerIds.has(layerId)) {
            const result = await api.map.addLayer({ id: layerId, name: layerId });
            state.layerIds.add(result?.layerId || layerId);
        }
        return state.layerIds.has(layerId) ? layerId : null;
    }

    async function refreshMapState() {
        try {
            const current = await api.map.getState();
            state.mapState = current && current.available ? current : null;
            state.mapError = "";
        } catch (err) {
            state.mapState = null;
            state.mapError = err?.message || String(err);
        }
        render();
    }

    function stateText() {
        if (state.mapError) {
            return label(api, "map_error", { message: state.mapError });
        }
        if (!state.mapState || !state.mapState.available) {
            return label(api, "state_unavailable");
        }
        const [lon, lat] = state.mapState.center || [null, null];
        return label(api, "state_value", {
            lon: Number(lon).toFixed(5),
            lat: Number(lat).toFixed(5),
            zoom: state.mapState.zoom == null ? "-" : Number(state.mapState.zoom).toFixed(1),
        });
    }

    function render() {
        api.setUi({
            type: "column",
            children: [
                {
                    type: "text",
                    variant: "title",
                    value: label(api, "title"),
                },
                {
                    type: "text",
                    variant: "body",
                    value: label(api, "description"),
                },
                mapDenied()
                    ? {
                          type: "text",
                          variant: "caption",
                          value: "map:read / map:write permission not granted",
                      }
                    : null,
                {
                    type: "section",
                    title: label(api, "state_title"),
                    children: [
                        {
                            type: "text",
                            variant: "stat",
                            value: stateText(),
                        },
                    ],
                },
                {
                    type: "section",
                    title: label(api, "demo_title"),
                    children: [
                        {
                            type: "row",
                            children: [
                                {
                                    type: "button",
                                    id: "show-sample",
                                    label: label(api, "show_sample"),
                                    variant: "primary",
                                },
                                {
                                    type: "button",
                                    id: "fly-sample",
                                    label: label(api, "fly_sample"),
                                    variant: "secondary",
                                },
                                {
                                    type: "button",
                                    id: "clear-layers",
                                    label: label(api, "clear_layers"),
                                    variant: "danger",
                                },
                            ],
                        },
                    ],
                },
                {
                    type: "section",
                    title: label(api, "pick_title"),
                    children: [
                        {
                            type: "text",
                            variant: "caption",
                            value: label(api, "pick_hint"),
                        },
                        {
                            type: "checkbox",
                            id: "pick-mode",
                            label: label(api, state.pickMode ? "pick_stop" : "pick_start"),
                            checked: state.pickMode,
                        },
                    ],
                },
            ].filter(Boolean),
        });
    }

    async function showSample() {
        try {
            const layerId = await ensureLayer(DEMO_LAYER_ID);
            if (!layerId) {
                return;
            }
            await api.map.setLayerData(layerId, sampleLayerData());
            await api.map.setView({
                center: SAMPLE_CENTER,
                zoom: 13,
                durationMs: 800,
                navigate: true,
            });
        } catch (err) {
            toast(api, "map_error", { message: err?.message || String(err) }, "error");
        }
    }

    async function flyToSample() {
        try {
            await api.map.setView({
                center: SAMPLE_CENTER,
                zoom: 15,
                durationMs: 800,
                navigate: true,
            });
        } catch (err) {
            toast(api, "map_error", { message: err?.message || String(err) }, "error");
        }
    }

    async function clearAll() {
        try {
            await api.map.clearLayers();
            state.layerIds.clear();
            toast(api, "layers_cleared", {}, "success");
        } catch (err) {
            toast(api, "map_error", { message: err?.message || String(err) }, "error");
        }
    }

    async function dropPickedMarker(lat, lon) {
        try {
            const layerId = await ensureLayer(PICKED_LAYER_ID);
            if (!layerId) {
                return;
            }
            await api.map.setLayerData(layerId, {
                type: "FeatureCollection",
                features: [pointFeature(lon, lat, "Picked point", "#16a34a")],
            });
            toast(api, "picked_toast", {
                lat: Number(lat).toFixed(5),
                lon: Number(lon).toFixed(5),
            });
        } catch (err) {
            toast(api, "map_error", { message: err?.message || String(err) }, "error");
        }
    }

    try {
        state.subscriptions.push(
            api.map.on("click", (payload) => {
                if (state.pickMode && Number.isFinite(payload?.lat) && Number.isFinite(payload?.lon)) {
                    void dropPickedMarker(payload.lat, payload.lon);
                }
            })
        );
        state.subscriptions.push(
            api.map.on("featureclick", (payload) => {
                const name = payload?.properties?.name || payload?.featureId || "feature";
                toast(api, "feature_click_toast", { name: String(name) });
            })
        );
        state.subscriptions.push(
            api.map.on("moveend", () => {
                void refreshMapState();
            })
        );
    } catch {
        // Map permissions may be denied; the UI still renders.
    }

    api.onAction((actionId) => {
        if (actionId === "show-sample") {
            void showSample();
        } else if (actionId === "fly-sample") {
            void flyToSample();
        } else if (actionId === "clear-layers") {
            void clearAll();
        }
    });

    api.onInput((id, value) => {
        if (id === "pick-mode") {
            state.pickMode = value === "1" || value === true || value === "true";
            render();
        }
    });

    api.onRefresh(() => {
        render();
    });

    await refreshMapState();
}
