// @ts-check

/**
 * Endpoint wrappers for /api/v1/interface-stats.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listInterfaceStats(...rest) {
    return window.api.get(apiPath("/interface-stats"), ...rest);
}
