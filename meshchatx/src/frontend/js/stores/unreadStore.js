// @ts-check

import { defineStore } from "pinia";

/**
 * Badge counters shown across the app shell (sidebar, tab bar).
 *
 * Read via useUnreadStore() in new code.
 */
export const useUnreadStore = defineStore("unread", {
    state: () => ({
        unreadConversationsCount: 0,
        relayChatUnreadCount: 0,
        missedCallsCount: 0,
    }),
    actions: {
        reset() {
            this.unreadConversationsCount = 0;
            this.relayChatUnreadCount = 0;
            this.missedCallsCount = 0;
        },
    },
});
