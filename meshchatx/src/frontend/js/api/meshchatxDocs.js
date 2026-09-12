// @ts-check

/**
 * Endpoint wrappers for /api/v1/meshchatx-docs.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getContent(...rest) {
    return window.api.get(apiPath("/meshchatx-docs/content"), ...rest);
}
export function getList(...rest) {
    return window.api.get(apiPath("/meshchatx-docs/list"), ...rest);
}
