// @ts-check

/**
 * Endpoint wrappers for /api/v1/ping.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function postLxmfDelivery(destinationHash, data, ...rest) {
    return window.api.post(apiPath(`/ping/${destinationHash}/lxmf.delivery`), data, ...rest);
}
export function postLxmfDelivery2(destinationHash, data, ...rest) {
    return window.api.post(apiPath(`/ping/${destinationHash}/lxmf.delivery`), data, ...rest);
}
