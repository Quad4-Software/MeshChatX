import { defineStore } from "pinia";

/**
 * Server-provided app config. All keys are optional — the server may send
 * any subset, and mergeConfig overlays onto the defaults.
 */
export interface Config {
    show_unknown_contact_banner?: boolean;
    banished_effect_enabled?: boolean;
    banished_text?: string;
    banished_color?: string;
    message_outbound_bubble_color?: string | null;
    message_inbound_bubble_color?: string | null;
    message_failed_bubble_color?: string;
    message_waiting_bubble_color?: string;
    nomad_render_markdown_enabled?: boolean;
    nomad_render_html_enabled?: boolean;
    nomad_render_plaintext_enabled?: boolean;
    nomad_micron_wasm_enabled?: boolean;
    nomad_micron_default_engine?: string;
    nomad_default_page_path?: string;
    ui_transparency?: number;
    ui_glass_enabled?: boolean;
    ui_font_family?: string;
    ui_custom_font_name?: string;
    ui_custom_font_data?: string;
    message_list_virtualization?: boolean;
    warn_on_stranger_links?: boolean;
    messages_sidebar_position?: string;
    messages_multi_pane_enabled?: boolean;
    delivery_helptips_enabled?: boolean;
    nomad_tabs_enabled?: boolean;
    nomad_private_tabs_enabled?: boolean;
    nomad_history_enabled?: boolean;
    rrc_enabled?: boolean;
    rrc_unread_badges_enabled?: boolean;
    live_transport_mode?: string;
    webtransport_sidecar_enabled?: boolean;
    // Allow arbitrary server-provided keys beyond the defaults.
    [key: string]: unknown;
}

/** Capability flags the backend may advertise via app_info. */
export type CapabilityName = string;

/**
 * Default server-provided config. mergeConfig overlays onto this object;
 * resetConfig restores it so a new identity never inherits stale keys.
 */
function defaultConfig(): Config {
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
        ui_font_family: "system",
        ui_custom_font_name: "",
        ui_custom_font_data: "",
        message_list_virtualization: true,
        warn_on_stranger_links: true,
        messages_sidebar_position: "left",
        messages_multi_pane_enabled: true,
        delivery_helptips_enabled: true,
        nomad_tabs_enabled: true,
        nomad_private_tabs_enabled: true,
        nomad_history_enabled: true,
        rrc_enabled: true,
        rrc_unread_badges_enabled: true,
        live_transport_mode: "auto",
        webtransport_sidecar_enabled: false,
    };
}

export interface ConfigState {
    detailedOutboundSendStatus: boolean;
    outboundTransferProgressEnabled: boolean;
    messageTimestampGroupingEnabled: boolean;
    activeCallTab: string;
    config: Config;
    backendCapabilities: Record<CapabilityName, boolean>;
    backendApiVersion: number | null;
}

/**
 * Server-provided app config and UI preference flags shared across pages.
 *
 * Read via useConfigStore() in new code.
 */
export const useConfigStore = defineStore("config", {
    state: (): ConfigState => ({
        detailedOutboundSendStatus: false,
        outboundTransferProgressEnabled: true,
        messageTimestampGroupingEnabled: true,
        activeCallTab: "phone",
        config: defaultConfig(),
        backendCapabilities: {},
        backendApiVersion: null,
    }),
    getters: {
        /**
         * Check if the backend supports a named feature.
         * Returns true when capabilities haven't loaded yet (assume modern).
         */
        hasCapability:
            (state) =>
            (name: CapabilityName): boolean => {
                if (state.backendApiVersion == null) {
                    return true;
                }
                return Boolean(state.backendCapabilities?.[name]);
            },
        /**
         * Check if the backend API version is at least the given version.
         * Returns true when version hasn't loaded yet (assume modern).
         */
        backendSupports:
            (state) =>
            (min: number): boolean => {
                if (state.backendApiVersion == null) {
                    return true;
                }
                return state.backendApiVersion >= min;
            },
    },
    actions: {
        mergeConfig(next: Partial<Config> | null | undefined) {
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
