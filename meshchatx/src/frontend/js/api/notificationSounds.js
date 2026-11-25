// @ts-check

/**
 * Endpoint wrappers for /api/v1/notification-sounds.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function uploadNotificationSounds(data, ...rest) {
    return window.api.post(apiPath("/notification-sounds/upload"), data, ...rest);
}
