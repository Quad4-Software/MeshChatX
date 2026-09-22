import { apiPath } from "../constants.js";

/**
 * Reticulum transport mode enable/disable (separate from config PATCH).
 */

import type { ApiClient, ApiResponse } from "../apiClient.js";

export type TransportModeResult = {
    transport_enabled?: boolean;
    message?: string;
};

export async function applyTransportMode(
    enabled: boolean,
    api: Pick<ApiClient, "post">
): Promise<ApiResponse<TransportModeResult>> {
    if (enabled) {
        return api.post<TransportModeResult>(apiPath("/reticulum/enable-transport"));
    }
    return api.post<TransportModeResult>(apiPath("/reticulum/disable-transport"));
}

export { applyReticulumInstanceSettings, fetchReticulumInstanceSettings } from "./settingsReticulumInstanceService.js";
