// @ts-check

/**
 * Endpoint wrappers for /api/v1/setup.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function postStorageMigration(data, ...rest) {
    return window.api.post(apiPath("/setup/storage-migration"), data, ...rest);
}
