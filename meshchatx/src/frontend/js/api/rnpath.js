// @ts-check

/**
 * Endpoint wrappers for /api/v1/rnpath.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function listRates(...rest) {
    return window.api.get(apiPath("/rnpath/rates"), ...rest);
}
export function getTable(...rest) {
    return window.api.get(apiPath("/rnpath/table"), ...rest);
}
export function getTrace(destinationHash, ...rest) {
    return window.api.get(apiPath(`/rnpath/trace/${destinationHash}`), ...rest);
}
export function dropRnpath(data, ...rest) {
    return window.api.post(apiPath("/rnpath/drop"), data, ...rest);
}
export function dropQueuesRnpath(data, ...rest) {
    return window.api.post(apiPath("/rnpath/drop-queues"), data, ...rest);
}
export function dropViaRnpath(data, ...rest) {
    return window.api.post(apiPath("/rnpath/drop-via"), data, ...rest);
}
export function requestRnpath(data, ...rest) {
    return window.api.post(apiPath("/rnpath/request"), data, ...rest);
}
