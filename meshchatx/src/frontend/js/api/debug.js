// @ts-check

/**
 * Endpoint wrappers for /api/v1/debug.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listAccessAttempts(...rest) {
    return window.api.get(apiPath("/debug/access-attempts"), ...rest);
}
export function listLogs(...rest) {
    return window.api.get(apiPath("/debug/logs"), ...rest);
}
