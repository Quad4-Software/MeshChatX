// @ts-check

/**
 * Endpoint wrappers for /api/v1/rnsh.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteSessions(sessionId, ...rest) {
    return window.api.delete(apiPath(`/rnsh/sessions/${sessionId}`), ...rest);
}
export function listSessions(...rest) {
    return window.api.get(apiPath("/rnsh/sessions"), ...rest);
}
export function createSessions(data, ...rest) {
    return window.api.post(apiPath("/rnsh/sessions"), data, ...rest);
}
export function postSessionsClear(id, data, ...rest) {
    return window.api.post(apiPath(`/rnsh/sessions/${id}/clear`), data, ...rest);
}
export function postSessionsInput(id, data, ...rest) {
    return window.api.post(apiPath(`/rnsh/sessions/${id}/input`), data, ...rest);
}
export function startSessions(id, data, ...rest) {
    return window.api.post(apiPath(`/rnsh/sessions/${id}/start`), data, ...rest);
}
export function stopSessions(id, data, ...rest) {
    return window.api.post(apiPath(`/rnsh/sessions/${id}/stop`), data, ...rest);
}
