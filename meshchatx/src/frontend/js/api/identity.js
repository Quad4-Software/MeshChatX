// @ts-check

/**
 * Endpoint wrappers for /api/v1/identity.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getLxmfAddress(hash, ...rest) {
    return window.api.get(apiPath(`/identity/${hash}/lxmf-address`), ...rest);
}
export function backupBase32(data, ...rest) {
    return window.api.post(apiPath("/identity/backup/base32"), data, ...rest);
}
export function downloadBackup(data, ...rest) {
    return window.api.post(apiPath("/identity/backup/download"), data, ...rest);
}
export function restoreIdentity(data, ...rest) {
    return window.api.post(apiPath("/identity/restore"), data, ...rest);
}
