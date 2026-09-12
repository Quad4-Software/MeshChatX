// @ts-check

/**
 * Endpoint wrappers for /api/v1/maintenance.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function importMessages(data, ...rest) {
    return window.api.post(apiPath("/maintenance/messages/import"), data, ...rest);
}
export function postMessagesImportFile(data, ...rest) {
    return window.api.post(apiPath("/maintenance/messages/import-file"), data, ...rest);
}
