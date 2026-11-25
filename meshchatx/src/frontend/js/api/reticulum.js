// @ts-check

/**
 * Endpoint wrappers for /api/v1/reticulum.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function listDiscoveredInterfaces(...rest) {
    return window.api.get(apiPath("/reticulum/discovered-interfaces"), ...rest);
}
