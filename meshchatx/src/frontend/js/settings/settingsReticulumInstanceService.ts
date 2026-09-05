// SPDX-License-Identifier: 0BSD

/**
 * Reticulum shared-instance / RPC / hop-obfuscation settings (Sideband parity).
 *
 * @param {{ get: (path: string) => Promise<{ data?: { instance?: object } }> }} api
 * @returns {Promise<object>}
 */
export async function fetchReticulumInstanceSettings(api) {
    const response = await api.get("/api/v1/reticulum/instance");
    return response?.data?.instance ?? {};
}

/**
 * @param {Record<string, unknown>} patch
 * @param {{ patch: (path: string, body: object) => Promise<{ data?: { instance?: object, message?: string } }> }} api
 * @returns {Promise<{ data?: { instance?: object, message?: string } }>}
 */
export async function applyReticulumInstanceSettings(patch, api) {
    return api.patch("/api/v1/reticulum/instance", patch);
}
