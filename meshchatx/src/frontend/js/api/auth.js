// @ts-check

/**
 * Endpoint wrappers for /api/v1/auth.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getStatus(...rest) {
    return window.api.get(apiPath("/auth/status"), ...rest);
}
