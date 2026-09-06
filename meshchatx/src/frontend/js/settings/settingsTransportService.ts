/**
 * Reticulum transport mode enable/disable (separate from config PATCH).
 */

import type { ApiClient } from "../apiClient.js";

export async function applyTransportMode(enabled: boolean, api: Pick<ApiClient, "post">): Promise<unknown> {
    if (enabled) {
        return api.post("/api/v1/reticulum/enable-transport");
    }
    return api.post("/api/v1/reticulum/disable-transport");
}

export { applyReticulumInstanceSettings, fetchReticulumInstanceSettings } from "./settingsReticulumInstanceService.js";
