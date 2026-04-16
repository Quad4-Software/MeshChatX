import { reactive } from "vue";

// global state
const globalState = reactive({
    authSessionResolved: true,
    authEnabled: false,
    authenticated: false,
    detailedOutboundSendStatus: false,
    unreadConversationsCount: 0,
    activeCallTab: "phone",
    blockedDestinations: [],
    modifiedInterfaceNames: new Set(),
    hasPendingInterfaceChanges: false,
    config: {
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
        nomad_default_page_path: "/page/index.mu",
        ui_transparency: 0,
        ui_glass_enabled: true,
        message_list_virtualization: true,
    },
});

export function mergeGlobalConfig(next) {
    if (!next || typeof next !== "object") {
        return;
    }
    const prev = globalState.config && typeof globalState.config === "object" ? globalState.config : {};
    globalState.config = { ...prev, ...next };
}

export default globalState;
