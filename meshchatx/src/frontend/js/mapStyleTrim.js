// SPDX-License-Identifier: 0BSD
/**
 * Protomaps light style trimming for render cost.
 *
 * The stock style has 73 layers and OpenLayers replays every active layer
 * on every frame. Two changes cut that cost without changing what the map
 * shows at rest:
 *
 *  1. minzoom overrides hide detail layers below the zoom where they are
 *     readable anyway (buildings, minor roads, tunnels, POIs, landuse
 *     detail classes), so low-zoom tiles evaluate fewer layers.
 *  2. partitionBasemapLayers splits symbol (text/icon) layers from the
 *     geometry layers. Symbols go on a separate VectorTileLayer sharing
 *     the same source, which the app hides while the map is being
 *     dragged or zoomed and shows again on moveend.
 */

// Layers that only carry visual detail at close zooms. Values are the
// minimum zoom at which the layer stays active; the stock default is 0.
const MINZOOM_OVERRIDES = {
    landuse_hospital: 12,
    landuse_industrial: 12,
    landuse_school: 12,
    landuse_beach: 12,
    landuse_zoo: 12,
    landuse_aerodrome: 12,
    landuse_pedestrian: 12,
    landuse_pier: 12,
    landuse_urban_green: 11,
    landuse_park: 9,
    buildings: 13,
    roads_taxiway: 14,
    roads_pier: 13,
    roads_tunnels_other_casing: 12,
    roads_tunnels_minor_casing: 12,
    roads_tunnels_link_casing: 12,
    roads_tunnels_major_casing: 12,
    roads_tunnels_highway_casing: 12,
    roads_tunnels_other: 12,
    roads_tunnels_minor: 12,
    roads_tunnels_link: 12,
    roads_tunnels_major: 12,
    roads_tunnels_highway: 12,
    roads_minor_service_casing: 14,
    roads_minor_service: 14,
    roads_minor_casing: 13,
    roads_minor: 13,
    roads_link_casing: 14,
    roads_link: 14,
    roads_other: 14,
    roads_rail: 9,
    pois: 14,
    places_subplace: 8,
    water_stream: 13,
};

// Layers dropped outright: value is too low or duplicates another layer.
const DROPPED_LAYERS = new Set([
    // One-way arrows: 16+ zoom only and rarely used offline.
    "roads_oneway",
]);

// Layers that must survive trimming at every zoom. Unit tests pin these
// so a future override cannot remove orientation-critical content.
export const REQUIRED_LAYER_IDS = [
    "earth",
    "water",
    "boundaries",
    "boundaries_country",
    "roads_highway",
    "roads_major",
    "places_country",
    "places_locality",
    "water_label_ocean",
];

/**
 * Return a new layer list with dropped layers removed and minzoom
 * overrides applied. Input layers are cloned shallowly; paint/layout
 * objects are shared with the source style on purpose.
 */
export function trimBasemapLayers(layers) {
    return layers
        .filter((l) => !DROPPED_LAYERS.has(l.id))
        .map((l) => {
            const min = MINZOOM_OVERRIDES[l.id];
            if (min === undefined) return l;
            const existing = l.minzoom ?? 0;
            if (existing >= min) return l;
            return { ...l, minzoom: min };
        });
}

/**
 * Split a (already trimmed) layer list into geometry and symbol groups.
 * Symbol layers render text and icons and are the expensive part to draw
 * every frame; the app puts them on a layer it can hide mid-interaction.
 */
export function partitionBasemapLayers(layers) {
    const geometry = [];
    const symbols = [];
    for (const l of layers) {
        if (l.type === "symbol") symbols.push(l);
        else geometry.push(l);
    }
    return { geometry, symbols };
}
