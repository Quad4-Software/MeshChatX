// @ts-check

/**
 * Endpoint wrappers for /api/v1/blocked-destinations.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function remove(hash, ...rest) {
    return window.api.delete(apiPath(`/blocked-destinations/${hash}`), ...rest);
}
export function delete2(identityHash, ...rest) {
    return window.api.delete(apiPath(`/blocked-destinations/${identityHash}`), ...rest);
}
export function delete3(targetHash, ...rest) {
    return window.api.delete(apiPath(`/blocked-destinations/${targetHash}`), ...rest);
}
export function delete4(destinationHash, ...rest) {
    return window.api.delete(apiPath(`/blocked-destinations/${destinationHash}`), ...rest);
}
export function delete5(destinationHash, ...rest) {
    return window.api.delete(apiPath(`/blocked-destinations/${destinationHash}`), ...rest);
}
export function listBlockedDestinations(...rest) {
    return window.api.get(apiPath("/blocked-destinations"), ...rest);
}
export function createBlockedDestinations(data, ...rest) {
    return window.api.post(apiPath("/blocked-destinations"), data, ...rest);
}
