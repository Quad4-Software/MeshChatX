// @ts-check

/**
 * Endpoint wrappers for /api/v1/rnpath.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function listRates(...rest) {
    return window.api.get(apiPath("/rnpath/rates"), ...rest);
}
export function getTable(...rest) {
    return window.api.get(apiPath("/rnpath/table"), ...rest);
}
