// @ts-check

/**
 * Endpoint wrappers for /api/v1/path-table.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getPathTable(...rest) {
    return window.api.get(apiPath("/path-table"), ...rest);
}
export function postPathTable(data, ...rest) {
    return window.api.post(apiPath("/path-table"), data, ...rest);
}
