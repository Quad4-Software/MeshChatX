// @ts-check

/**
 * Endpoint wrappers for /api/v1/notification-sounds.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function remove(id, ...rest) {
    return window.api.delete(apiPath(`/notification-sounds/${id}`), ...rest);
}
export function listNotificationSounds(...rest) {
    return window.api.get(apiPath("/notification-sounds"), ...rest);
}
export function getStatus(...rest) {
    return window.api.get(apiPath("/notification-sounds/status"), ...rest);
}
export function update(id, data, ...rest) {
    return window.api.patch(apiPath(`/notification-sounds/${id}`), data, ...rest);
}
export function uploadNotificationSounds(data, ...rest) {
    return window.api.post(apiPath("/notification-sounds/upload"), data, ...rest);
}
