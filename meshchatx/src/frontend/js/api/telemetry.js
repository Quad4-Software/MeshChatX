// @ts-check

/**
 * Endpoint wrappers for /api/v1/telemetry.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getHistoryX(hash, ...rest) {
    return window.api.get(apiPath(`/telemetry/history/${hash}?limit=50`), ...rest);
}
export function listPeers(...rest) {
    return window.api.get(apiPath("/telemetry/peers"), ...rest);
}
export function listTrustedPeers(...rest) {
    return window.api.get(apiPath("/telemetry/trusted-peers"), ...rest);
}
export function toggleTracking(hash, data, ...rest) {
    return window.api.post(apiPath(`/telemetry/tracking/${hash}/toggle`), data, ...rest);
}
