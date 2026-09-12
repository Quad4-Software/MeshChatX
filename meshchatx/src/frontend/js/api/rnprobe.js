// @ts-check

/**
 * Endpoint wrappers for /api/v1/rnprobe.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function postRnprobe(data, ...rest) {
    return window.api.post(apiPath("/rnprobe"), data, ...rest);
}
