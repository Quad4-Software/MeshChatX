// @ts-check

/**
 * Endpoint wrappers for /api/v1/system.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listNetworkInterfaces(...rest) {
    return window.api.get(apiPath("/system/network-interfaces"), ...rest);
}
