// @ts-check

/**
 * Endpoint wrappers for /api/v1/identities.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function remove(hash, ...rest) {
    return window.api.delete(apiPath(`/identities/${hash}`), ...rest);
}
export function delete2(originalIdentityHash, ...rest) {
    return window.api.delete(apiPath(`/identities/${originalIdentityHash}`), ...rest);
}
export function listIdentities(...rest) {
    return window.api.get(apiPath("/identities"), ...rest);
}
export function postCreate(data, ...rest) {
    return window.api.post(apiPath("/identities/create"), data, ...rest);
}
export function postExportAll(data, ...rest) {
    return window.api.post(apiPath("/identities/export-all"), data, ...rest);
}
export function postSwitch(data, ...rest) {
    return window.api.post(apiPath("/identities/switch"), data, ...rest);
}
