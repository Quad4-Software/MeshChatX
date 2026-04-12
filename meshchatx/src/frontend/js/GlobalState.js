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
