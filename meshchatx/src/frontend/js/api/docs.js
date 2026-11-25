// @ts-check

/**
 * Endpoint wrappers for /api/v1/docs.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function getSearch(...rest) {
    return window.api.get(apiPath("/docs/search"), ...rest);
}
export function postUpload(trim, data, ...rest) {
    return window.api.post(apiPath(`/docs/upload?version=${trim}`), data, ...rest);
}
