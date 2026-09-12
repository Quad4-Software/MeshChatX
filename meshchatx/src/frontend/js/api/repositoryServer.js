// @ts-check

/**
 * Endpoint wrappers for /api/v1/repository-server.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteUpload(enc, ...rest) {
    return window.api.delete(apiPath(`/repository-server/upload/${enc}`), ...rest);
}
export function getList(...rest) {
    return window.api.get(apiPath("/repository-server/list"), ...rest);
}
export function getStatus(...rest) {
    return window.api.get(apiPath("/repository-server/status"), ...rest);
}
export function restartHttp(data, ...rest) {
    return window.api.post(apiPath("/repository-server/http/restart"), data, ...rest);
}
export function startHttp(data, ...rest) {
    return window.api.post(apiPath("/repository-server/http/start"), data, ...rest);
}
export function stopHttp(data, ...rest) {
    return window.api.post(apiPath("/repository-server/http/stop"), data, ...rest);
}
export function uploadRepositoryServer(data, ...rest) {
    return window.api.post(apiPath("/repository-server/upload"), data, ...rest);
}
