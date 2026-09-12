// @ts-check

/**
 * Endpoint wrappers for /api/v1/bug-reports.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function postLocal(data, ...rest) {
    return window.api.post(apiPath("/bug-reports/local"), data, ...rest);
}
