// @ts-check

/**
 * Endpoint wrappers for /api/v1/rnx.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteSessions(sessionId, ...rest) {
    return window.api.delete(apiPath(`/rnx/sessions/${sessionId}`), ...rest);
}
export function listSessions(...rest) {
    return window.api.get(apiPath("/rnx/sessions"), ...rest);
}
export function createSessions(data, ...rest) {
    return window.api.post(apiPath("/rnx/sessions"), data, ...rest);
}
export function postSessionsClear(id, data, ...rest) {
    return window.api.post(apiPath(`/rnx/sessions/${id}/clear`), data, ...rest);
}
export function postSessionsInput(id, data, ...rest) {
    return window.api.post(apiPath(`/rnx/sessions/${id}/input`), data, ...rest);
}
export function startSessions(id, data, ...rest) {
    return window.api.post(apiPath(`/rnx/sessions/${id}/start`), data, ...rest);
}
export function stopSessions(id, data, ...rest) {
    return window.api.post(apiPath(`/rnx/sessions/${id}/stop`), data, ...rest);
}
