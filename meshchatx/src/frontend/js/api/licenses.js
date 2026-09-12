// @ts-check

/**
 * Endpoint wrappers for /api/v1/licenses.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listLicenses(...rest) {
    return window.api.get(apiPath("/licenses"), ...rest);
}
