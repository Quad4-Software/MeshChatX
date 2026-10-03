import { defineStore } from "pinia";

export interface UnreadState {
    unreadConversationsCount: number;
    relayChatUnreadCount: number;
    missedCallsCount: number;
}

/**
 * Badge counters shown across the app shell (sidebar, tab bar).
 */
export const useUnreadStore = defineStore("unread", {
    state: (): UnreadState => ({
        unreadConversationsCount: 0,
        relayChatUnreadCount: 0,
        missedCallsCount: 0,
    }),
    actions: {
        reset(): void {
            this.unreadConversationsCount = 0;
            this.relayChatUnreadCount = 0;
            this.missedCallsCount = 0;
        },
    },
});
