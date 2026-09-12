// @ts-check

/**
 * Endpoint wrappers for /api/v1/self-test.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getSelfTest(...rest) {
    return window.api.get(apiPath("/self-test"), ...rest);
}
