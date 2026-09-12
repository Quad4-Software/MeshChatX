// @ts-check

/**
 * Endpoint wrappers for /api/v1/docs.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteVersion(version, ...rest) {
    return window.api.delete(apiPath(`/docs/version/${version}`), ...rest);
}
export function getSearch(...rest) {
    return window.api.get(apiPath("/docs/search"), ...rest);
}
export function getStatus(...rest) {
    return window.api.get(apiPath("/docs/status"), ...rest);
}
export function postSwitch(data, ...rest) {
    return window.api.post(apiPath("/docs/switch"), data, ...rest);
}
export function postUpload(trim, data, ...rest) {
    return window.api.post(apiPath(`/docs/upload?version=${trim}`), data, ...rest);
}
