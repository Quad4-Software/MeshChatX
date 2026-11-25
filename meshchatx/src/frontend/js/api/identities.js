// @ts-check

/**
 * Endpoint wrappers for /api/v1/identities.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function postExportAll(data, ...rest) {
    return window.api.post(apiPath("/identities/export-all"), data, ...rest);
}
