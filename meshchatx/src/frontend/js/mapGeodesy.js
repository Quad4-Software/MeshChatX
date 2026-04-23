// SPDX-License-Identifier: 0BSD

import { DEFAULT_RADIUS, getDistance } from "ol/sphere";

/**
 * @param {number} lon1
 * @param {number} lat1
 * @param {number} lon2
 * @param {number} lat2
 * @returns {number} Initial (forward) azimuth in degrees [0, 360), spherical model.
 */
export function sphericalInitialBearingDeg(lon1, lat1, lon2, lat2) {
    const φ1 = (lat1 * Math.PI) / 180;
    const φ2 = (lat2 * Math.PI) / 180;
    const Δλ = ((lon2 - lon1) * Math.PI) / 180;
    const y = Math.sin(Δλ) * Math.cos(φ2);
    const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
    const θ = Math.atan2(y, x);
    return ((((θ * 180) / Math.PI) % 360) + 360) % 360;
}

/**
 * Rhumb-line distance and constant bearing on the sphere (mean Earth radius).
 * @param {number} lon1
 * @param {number} lat1
 * @param {number} lon2
 * @param {number} lat2
 * @param {number} [radius]
 * @returns {{ distanceMeters: number, bearingDeg: number }}
 */
export function rhumbLineMetrics(lon1, lat1, lon2, lat2, radius = DEFAULT_RADIUS) {
    const R = radius;
    const φ1 = (lat1 * Math.PI) / 180;
    const φ2 = (lat2 * Math.PI) / 180;
    let Δλ = ((lon2 - lon1) * Math.PI) / 180;
    if (Δλ > Math.PI) {
        Δλ -= 2 * Math.PI;
    }
    if (Δλ < -Math.PI) {
        Δλ += 2 * Math.PI;
    }
    const Δφ = φ2 - φ1;
    const Δψ = Math.log(Math.tan(Math.PI / 4 + φ2 / 2) / Math.tan(Math.PI / 4 + φ1 / 2));
    const q = Math.abs(Δψ) > 1e-12 ? Δφ / Δψ : Math.cos(φ1);
    const dist = Math.sqrt(Δφ * Δφ + q * q * Δλ * Δλ) * R;
    const bearingDeg = ((((Math.atan2(Δλ, Δψ) * 180) / Math.PI) % 360) + 360) % 360;
    return { distanceMeters: dist, bearingDeg };
}

/**
 * Great-circle (geodesic on sphere) distance matches OpenLayers {@link import("ol/sphere").getLength}
 * for a two-point line in WGS84.
 *
 * @param {number} lon1
 * @param {number} lat1
 * @param {number} lon2
 * @param {number} lat2
 * @returns {{
 *   geodesicMeters: number,
 *   forwardAzimuthDeg: number,
 *   backAzimuthDeg: number,
 *   rhumbMeters: number,
 *   rhumbBearingDeg: number,
 *   rhumbBackBearingDeg: number,
 * }}
 */
export function computeSegmentMetrics(lon1, lat1, lon2, lat2) {
    const a = [lon1, lat1];
    const b = [lon2, lat2];
    const geodesicMeters = getDistance(a, b);
    const forwardAzimuthDeg = sphericalInitialBearingDeg(lon1, lat1, lon2, lat2);
    const backAzimuthDeg = sphericalInitialBearingDeg(lon2, lat2, lon1, lat1);
    const rh = rhumbLineMetrics(lon1, lat1, lon2, lat2);
    const rhumbBackBearingDeg = (rh.bearingDeg + 180) % 360;
    return {
        geodesicMeters,
        forwardAzimuthDeg,
        backAzimuthDeg,
        rhumbMeters: rh.distanceMeters,
        rhumbBearingDeg: rh.bearingDeg,
        rhumbBackBearingDeg,
    };
}

/**
 * @param {number} meters
 * @returns {{ metric: string, imperial: string }}
 */
export function formatLengthPairMeters(meters) {
    let metric;
    let imperial;
    if (meters > 100) {
        metric = `${Math.round((meters / 1000) * 100) / 100} km`;
    } else {
        metric = `${Math.round(meters * 100) / 100} m`;
    }
    const feet = meters * 3.28084;
    if (feet > 5280) {
        imperial = `${Math.round(meters * 0.000621371 * 100) / 100} mi`;
    } else {
        imperial = `${Math.round(feet * 100) / 100} ft`;
    }
    return { metric, imperial };
}

/**
 * @param {ReturnType<typeof computeSegmentMetrics>} metrics
 * @param {(key: string) => string} t i18n
 * @returns {string}
 */
export function buildBearingOverlayHtml(metrics, t) {
    const geo = formatLengthPairMeters(metrics.geodesicMeters);
    const rh = formatLengthPairMeters(metrics.rhumbMeters);
    const fd = metrics.forwardAzimuthDeg.toFixed(1);
    const bd = metrics.backAzimuthDeg.toFixed(1);
    const rfd = metrics.rhumbBearingDeg.toFixed(1);
    const rbd = metrics.rhumbBackBearingDeg.toFixed(1);
    return (
        `<div class="text-left space-y-0.5">` +
        `<div class="font-semibold text-gray-900 dark:text-zinc-100">${escapeHtml(t("map.bearing_geodesic"))}</div>` +
        `<div>${escapeHtml(geo.metric)} <span class="text-[10px] opacity-80">(${escapeHtml(geo.imperial)})</span></div>` +
        `<div>${escapeHtml(t("map.bearing_forward"))}: ${escapeHtml(fd)}°</div>` +
        `<div>${escapeHtml(t("map.bearing_back"))}: ${escapeHtml(bd)}°</div>` +
        `<div class="mt-1 font-semibold text-gray-900 dark:text-zinc-100">${escapeHtml(t("map.bearing_rhumb"))}</div>` +
        `<div>${escapeHtml(rh.metric)} <span class="text-[10px] opacity-80">(${escapeHtml(rh.imperial)})</span></div>` +
        `<div>${escapeHtml(t("map.bearing_rhumb_line"))}: ${escapeHtml(rfd)}° / ${escapeHtml(rbd)}°</div>` +
        `</div>`
    );
}

/**
 * @param {ReturnType<typeof computeSegmentMetrics>} metrics
 * @param {(key: string) => string} t
 * @returns {string}
 */
export function buildBearingLiveTooltipHtml(metrics, t) {
    const geo = formatLengthPairMeters(metrics.geodesicMeters);
    const fd = metrics.forwardAzimuthDeg.toFixed(1);
    const rd = metrics.rhumbBearingDeg.toFixed(1);
    return (
        `<span class="font-semibold">${escapeHtml(t("map.bearing_geodesic"))}</span> ` +
        `${escapeHtml(geo.metric)}<br/>` +
        `<span class="text-[10px] opacity-90">${escapeHtml(t("map.bearing_forward"))}: ${escapeHtml(fd)}° · ` +
        `${escapeHtml(t("map.bearing_rhumb_line"))}: ${escapeHtml(rd)}°</span>`
    );
}

function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
