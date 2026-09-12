import { apiPath } from "../constants.js";

/**
 * Reticulum transport mode enable/disable (separate from config PATCH).
 *
 * @param {boolean} enabled
 * @param {{ post: (path: string) => Promise<unknown> }} api
 */
export async function applyTransportMode(enabled, api) {
    if (enabled) {
        return api.post(apiPath("/reticulum/enable-transport"));
    }
    return api.post(apiPath("/reticulum/disable-transport"));
}

export { applyReticulumInstanceSettings, fetchReticulumInstanceSettings } from "./settingsReticulumInstanceService.js";
