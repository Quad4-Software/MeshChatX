// @ts-check

/**
 * Endpoint wrappers for /api/v1/map.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function getDataHeard(...rest) {
    return window.api.get(apiPath("/map/data/heard"), ...rest);
}
