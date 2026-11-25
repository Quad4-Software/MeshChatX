// @ts-check

/**
 * Endpoint wrappers for /api/v1/page-nodes.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function createFiles(nodeId, data, ...rest) {
    return window.api.post(apiPath(`/page-nodes/${nodeId}/files`), data, ...rest);
}
