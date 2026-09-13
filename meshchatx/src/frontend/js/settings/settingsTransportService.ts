import { apiPath } from "../constants.js";

/**
 * Reticulum transport mode enable/disable (separate from config PATCH).
 */

import type { ApiClient } from "../apiClient.js";

export async function applyTransportMode(enabled: boolean, api: Pick<ApiClient, "post">): Promise<unknown> {
    if (enabled) {
        return api.post(apiPath("/reticulum/enable-transport"));
    }
    return api.post(apiPath("/reticulum/disable-transport"));
}

export { applyReticulumInstanceSettings, fetchReticulumInstanceSettings } from "./settingsReticulumInstanceService.js";
