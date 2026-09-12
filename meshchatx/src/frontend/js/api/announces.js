// @ts-check

/**
 * Endpoint wrappers for /api/v1/announces.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listAnnounces(...rest) {
    return window.api.get(apiPath("/announces"), ...rest);
}
export function postQuery(data, ...rest) {
    return window.api.post(apiPath("/announces/query"), data, ...rest);
}
