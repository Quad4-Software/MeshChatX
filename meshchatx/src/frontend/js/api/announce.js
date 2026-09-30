// @ts-check

/**
 * Endpoint wrappers for /api/v1/announce.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function triggerAnnounce(...rest) {
    return window.api.post(apiPath("/announce"), ...rest);
}
