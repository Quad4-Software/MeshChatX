// @ts-check

/**
 * Endpoint wrappers for /api/v1/notifications.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listNotifications(...rest) {
    return window.api.get(apiPath("/notifications"), ...rest);
}
