// @ts-check

/**
 * Endpoint wrappers for /api/v1/community-interfaces.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listCommunityInterfaces(...rest) {
    return window.api.get(apiPath("/community-interfaces"), ...rest);
}
