// @ts-check

/**
 * Endpoint wrappers for /api/v1/database.
 * Each function maps one HTTP call through window.api. Add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants";

export function listBackups(...rest) {
    return window.api.get(apiPath("/database/backups"), ...rest);
}
export function listSnapshots(...rest) {
    return window.api.get(apiPath("/database/snapshots"), ...rest);
}
export function downloadBackup(data, ...rest) {
    return window.api.post(apiPath("/database/backup/download"), data, ...rest);
}
export function downloadBackups(filename, data, ...rest) {
    return window.api.post(apiPath(`/database/backups/${filename}/download`), data, ...rest);
}
export function restoreDatabase(data, ...rest) {
    return window.api.post(apiPath("/database/restore"), data, ...rest);
}
export function downloadSnapshots(filename, data, ...rest) {
    return window.api.post(apiPath(`/database/snapshots/${filename}/download`), data, ...rest);
}
