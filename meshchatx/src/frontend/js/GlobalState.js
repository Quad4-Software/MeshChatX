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
    },
});

export default globalState;
