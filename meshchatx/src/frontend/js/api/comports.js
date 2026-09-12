// @ts-check

/**
 * Endpoint wrappers for /api/v1/comports.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listComports(...rest) {
    return window.api.get(apiPath("/comports"), ...rest);
}
