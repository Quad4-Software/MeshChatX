import { reactive } from "vue";

// global state
const globalState = reactive({
    unreadConversationsCount: 0,
    activeCallTab: "phone",
    blockedDestinations: [],
    modifiedInterfaceNames: new Set(),
    hasPendingInterfaceChanges: false,
    config: {
        banished_effect_enabled: true,
        banished_text: "BANISHED",
        banished_color: "#dc2626",
        message_outbound_bubble_color: "#4f46e5",
        message_inbound_bubble_color: null,
        message_failed_bubble_color: "#ef4444",
    },
});

export default globalState;
