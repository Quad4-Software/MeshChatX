// @ts-check

/**
 * Endpoint wrappers for /api/v1/database.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function deleteBackups(filename, ...rest) {
    return window.api.delete(apiPath(`/database/backups/${filename}`), ...rest);
}
export function deleteSnapshots(filename, ...rest) {
    return window.api.delete(apiPath(`/database/snapshots/${filename}`), ...rest);
}
export function listBackups(...rest) {
    return window.api.get(apiPath("/database/backups"), ...rest);
}
export function getHealth(...rest) {
    return window.api.get(apiPath("/database/health"), ...rest);
}
export function listSnapshots(...rest) {
    return window.api.get(apiPath("/database/snapshots"), ...rest);
}
export function postAutoRecover(data, ...rest) {
    return window.api.post(apiPath("/database/auto-recover"), data, ...rest);
}
export function downloadBackup(data, ...rest) {
    return window.api.post(apiPath("/database/backup/download"), data, ...rest);
}
export function downloadBackups(filename, data, ...rest) {
    return window.api.post(apiPath(`/database/backups/${filename}/download`), data, ...rest);
}
export function recoverDatabase(data, ...rest) {
    return window.api.post(apiPath("/database/recover"), data, ...rest);
}
export function restoreDatabase(data, ...rest) {
    return window.api.post(apiPath("/database/restore"), data, ...rest);
}
export function postSnapshot(data, ...rest) {
    return window.api.post(apiPath("/database/snapshot"), data, ...rest);
}
export function downloadSnapshots(filename, data, ...rest) {
    return window.api.post(apiPath(`/database/snapshots/${filename}/download`), data, ...rest);
}
export function vacuumDatabase(data, ...rest) {
    return window.api.post(apiPath("/database/vacuum"), data, ...rest);
}
