// @ts-check

/**
 * Endpoint wrappers for /api/v1/lxmf.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function listConversations(...rest) {
    return window.api.get(apiPath("/lxmf/conversations"), ...rest);
}
export function listPropagationNodes(...rest) {
    return window.api.get(apiPath("/lxmf/propagation-nodes"), ...rest);
}
