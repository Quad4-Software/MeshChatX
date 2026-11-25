// @ts-check

/**
 * Endpoint wrappers for /api/v1/identity.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function downloadBackup(data, ...rest) {
    return window.api.post(apiPath("/identity/backup/download"), data, ...rest);
}
export function restoreIdentity(data, ...rest) {
    return window.api.post(apiPath("/identity/restore"), data, ...rest);
}
