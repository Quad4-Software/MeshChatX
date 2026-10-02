// @ts-check

import { defineStore } from "pinia";

/**
 * Default server-provided config. mergeConfig overlays onto this object;
 * resetConfig restores it so a new identity never inherits stale keys.
 */
function defaultConfig() {
    return {
        show_unknown_contact_banner: true,
        banished_effect_enabled: true,
        banished_text: "BANISHED",
        banished_color: "#dc2626",
        message_outbound_bubble_color: "#4f46e5",
        message_inbound_bubble_color: null,
        message_failed_bubble_color: "#ef4444",
        message_waiting_bubble_color: "#e5e7eb",
        nomad_render_markdown_enabled: true,
        nomad_render_html_enabled: true,
        nomad_render_plaintext_enabled: true,
        nomad_micron_wasm_enabled: true,
        nomad_micron_default_engine: "js",
        nomad_default_page_path: "/page/index.mu",
        ui_transparency: 0,
        ui_glass_enabled: true,
        message_list_virtualization: true,
        warn_on_stranger_links: true,
        messages_sidebar_position: "left",
        messages_multi_pane_enabled: true,
        delivery_helptips_enabled: true,
        nomad_tabs_enabled: true,
        rrc_enabled: true,
        rrc_unread_badges_enabled: true,
        live_transport_mode: "auto",
        webtransport_sidecar_enabled: false,
    };
}

/**
 * Server-provided app config and UI preference flags shared across pages.
 *
 * Read via useConfigStore() in new code.
 */
export const useConfigStore = defineStore("config", {
    state: () => ({
        detailedOutboundSendStatus: false,
        outboundTransferProgressEnabled: true,
        messageTimestampGroupingEnabled: true,
        activeCallTab: "phone",
        // Server sends arbitrary keys beyond the defaults.
        /** @type {Record<string, any>} */
        config: defaultConfig(),
        // Backend capability flags from app_info. Populated once appInfo loads.
        /** @type {Record<string, boolean>} */
        backendCapabilities: {},
        /** @type {number|null} */
        backendApiVersion: null,
    }),
    getters: {
        /**
         * Check if the backend supports a named feature.
         * Returns true when capabilities haven't loaded yet (assume modern).
         * @param {string} name
         * @returns {boolean}
         */
        hasCapability:
            (state) =>
            (name) => {
                if (state.backendApiVersion == null) {
                    return true;
                }
                return Boolean(state.backendCapabilities?.[name]);
            },
        /**
         * Check if the backend API version is at least the given version.
         * Returns true when version hasn't loaded yet (assume modern).
         * @param {number} min
         * @returns {boolean}
         */
        backendSupports:
            (state) =>
            (min) => {
                if (state.backendApiVersion == null) {
                    return true;
                }
                return state.backendApiVersion >= min;
            },
    },
    actions: {
        mergeConfig(next) {
            if (!next || typeof next !== "object") {
                return;
            }
            const prev = this.config && typeof this.config === "object" ? this.config : {};
            this.config = { ...prev, ...next };
        },
        resetConfig() {
            this.config = defaultConfig();
        },
    },
});
