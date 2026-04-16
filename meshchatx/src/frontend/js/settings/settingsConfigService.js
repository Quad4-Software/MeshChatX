/**
 * Pure helpers and HTTP-backed config load/patch for settings UI.
 *
 * @param {unknown} v
 * @returns {number|null}
 */
export function numOrNull(v) {
    if (v === null || v === undefined || v === "") {
        return null;
    }
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}

/**
 * Normalizes hex color fields on a config object in place.
 *
 * @param {Record<string, unknown>} config
 */
export function sanitizeColorConfigFields(config) {
    if (!config) return;
    const hex6 = (value, fallback) => {
        if (value == null || value === "") {
            return fallback;
        }
        if (typeof value === "string" && /^#[0-9A-Fa-f]{6}$/.test(value.trim())) {
            return value.trim();
        }
        return fallback;
    };
    config.banished_color = hex6(config.banished_color, "#dc2626");
    config.message_outbound_bubble_color = hex6(config.message_outbound_bubble_color, "#4f46e5");
    config.message_failed_bubble_color = hex6(config.message_failed_bubble_color, "#ef4444");
    config.message_waiting_bubble_color = hex6(config.message_waiting_bubble_color, "#e5e7eb");
    const inbound = config.message_inbound_bubble_color;
    if (inbound == null || inbound === "") {
        config.message_inbound_bubble_color = null;
    } else if (typeof inbound === "string" && /^#[0-9A-Fa-f]{6}$/.test(inbound.trim())) {
        config.message_inbound_bubble_color = inbound.trim();
    } else {
        config.message_inbound_bubble_color = null;
    }
}

/**
 * @param {{ get: (path: string) => Promise<{ data?: { config?: object } }> }} api
 * @returns {Promise<object|null>}
 */
export async function fetchMergedConfig(api, baseConfig) {
    const response = await api.get("/api/v1/config");
    if (response?.data?.config) {
        return { ...baseConfig, ...response.data.config };
    }
    return null;
}

/**
 * @param {object} partial
 * @param {{ patch: (path: string, data: object) => Promise<{ data: { config: object } }> }} api
 * @returns {Promise<object>}
 */
export async function patchServerConfig(partial, api) {
    const response = await api.patch("/api/v1/config", partial);
    return response.data.config;
}
