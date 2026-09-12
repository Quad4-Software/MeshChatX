// @ts-check

/**
 * Endpoint wrappers for /api/v1/destination.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getCustomDisplayName(destinationHash, ...rest) {
    return window.api.get(apiPath(`/destination/${destinationHash}/custom-display-name`), ...rest);
}
export function getLxmfStampInfo(destinationHash, ...rest) {
    return window.api.get(apiPath(`/destination/${destinationHash}/lxmf-stamp-info`), ...rest);
}
export function getSignalMetrics(destinationHash, ...rest) {
    return window.api.get(apiPath(`/destination/${destinationHash}/signal-metrics`), ...rest);
}
export function postCustomDisplayNameUpdate(destHash, data, ...rest) {
    return window.api.post(apiPath(`/destination/${destHash}/custom-display-name/update`), data, ...rest);
}
export function postPath(lxmf, data, ...rest) {
    return window.api.post(apiPath(`/destination/${lxmf}/path`), data, ...rest);
}
export function dropPathDestination(destinationHash, data, ...rest) {
    return window.api.post(apiPath(`/destination/${destinationHash}/drop-path`), data, ...rest);
}
export function postCustomDisplayNameUpdate2(destinationHash, data, ...rest) {
    return window.api.post(apiPath(`/destination/${destinationHash}/custom-display-name/update`), data, ...rest);
}
