// @ts-check

/**
 * Endpoint wrappers for /api/v1/rncp.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getStatus(...rest) {
    return window.api.get(apiPath("/rncp/status"), ...rest);
}
export function cancelRncp(data, ...rest) {
    return window.api.post(apiPath("/rncp/cancel"), data, ...rest);
}
export function fetchRncp(data, ...rest) {
    return window.api.post(apiPath("/rncp/fetch"), data, ...rest);
}
export function listenRncp(data, ...rest) {
    return window.api.post(apiPath("/rncp/listen"), data, ...rest);
}
export function sendRncp(data, ...rest) {
    return window.api.post(apiPath("/rncp/send"), data, ...rest);
}
export function stopRncp(data, ...rest) {
    return window.api.post(apiPath("/rncp/stop"), data, ...rest);
}
