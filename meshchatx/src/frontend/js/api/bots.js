// @ts-check

/**
 * Endpoint wrappers for /api/v1/bots.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function getSubprocessLog(...rest) {
    return window.api.get(apiPath("/bots/subprocess-log"), ...rest);
}
export function exportBots(data, ...rest) {
    return window.api.post(apiPath("/bots/export"), data, ...rest);
}
