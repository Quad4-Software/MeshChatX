/**
 * Reticulum transport mode enable/disable (separate from config PATCH).
 *
 * @param {boolean} enabled
 * @param {{ post: (path: string) => Promise<unknown> }} api
 */
export async function applyTransportMode(enabled, api) {
    if (enabled) {
        return api.post("/api/v1/reticulum/enable-transport");
    }
    return api.post("/api/v1/reticulum/disable-transport");
}
