// @ts-check

/**
 * Endpoint wrappers for /api/v1/rnstatus.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listRnstatus(...rest) {
    return window.api.get(apiPath("/rnstatus"), ...rest);
}
