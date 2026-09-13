// SPDX-License-Identifier: 0BSD

/**
 * Reticulum shared-instance / RPC / hop-obfuscation settings (Sideband parity).
 */

import type { ApiClient, ApiResponse } from "../apiClient.js";

export type ReticulumInstanceSettings = Record<string, unknown>;

export type ReticulumInstancePatchData = {
    instance?: ReticulumInstanceSettings;
    message?: string;
};

export async function fetchReticulumInstanceSettings(api: Pick<ApiClient, "get">): Promise<ReticulumInstanceSettings> {
    const response = await api.get<{ instance?: ReticulumInstanceSettings }>("/api/v1/reticulum/instance");
    return response?.data?.instance ?? {};
}

export async function applyReticulumInstanceSettings(
    api: Pick<ApiClient, "patch">,
    patch: Record<string, unknown>
): Promise<ApiResponse<ReticulumInstancePatchData>> {
    return api.patch<ReticulumInstancePatchData>("/api/v1/reticulum/instance", patch);
}
