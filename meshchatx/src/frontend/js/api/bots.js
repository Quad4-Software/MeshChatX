// @ts-check

/**
 * Endpoint wrappers for /api/v1/bots.
 * Each function maps one HTTP call through window.api; add new
 * endpoints here rather than inlining paths in components.
 */

import { apiPath } from "../constants.js";

export function getStatus(...rest) {
    return window.api.get(apiPath("/bots/status"), ...rest);
}
export function getSubprocessLog(...rest) {
    return window.api.get(apiPath("/bots/subprocess-log"), ...rest);
}
export function updateLxmfConfig(data, ...rest) {
    return window.api.patch(apiPath("/bots/lxmf-config"), data, ...rest);
}
export function updateUpdate(data, ...rest) {
    return window.api.patch(apiPath("/bots/update"), data, ...rest);
}
export function announceBots(data, ...rest) {
    return window.api.post(apiPath("/bots/announce"), data, ...rest);
}
export function deleteBots(data, ...rest) {
    return window.api.post(apiPath("/bots/delete"), data, ...rest);
}
export function exportBots(data, ...rest) {
    return window.api.post(apiPath("/bots/export"), data, ...rest);
}
export function restartBots(data, ...rest) {
    return window.api.post(apiPath("/bots/restart"), data, ...rest);
}
export function startBots(data, ...rest) {
    return window.api.post(apiPath("/bots/start"), data, ...rest);
}
export function stopBots(data, ...rest) {
    return window.api.post(apiPath("/bots/stop"), data, ...rest);
}
