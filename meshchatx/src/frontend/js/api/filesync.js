// @ts-check

/**
 * Endpoint wrappers for /api/v1/filesync.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function deleteEntry(...rest) {
    return window.api.delete(apiPath("/filesync/entry"), ...rest);
}
export function getContent(...rest) {
    return window.api.get(apiPath("/filesync/content"), ...rest);
}
export function getTree(...rest) {
    return window.api.get(apiPath("/filesync/tree"), ...rest);
}
