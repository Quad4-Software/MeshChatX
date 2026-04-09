<template>
    <div class="relative">
        <button
            type="button"
            class="relative rounded-full p-1.5 sm:p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
            @click.stop="toggleDropdown"
        >
            <MaterialDesignIcon icon-name="bell" class="w-5 h-5 sm:w-6 sm:h-6" />
            <span
                v-if="unreadCount > 0"
                class="absolute top-0 right-0 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-semibold text-white"
            >
                {{ unreadCount > 9 ? "9+" : unreadCount }}
            </span>
        </button>

        <Teleport to="body">
            <div
                v-if="isDropdownOpen"
                v-click-outside="closeDropdown"
                class="fixed w-80 sm:w-96 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-xl z-[9999] max-h-[500px] overflow-hidden flex flex-col"
                :style="dropdownStyle"
            >
                <div class="p-4 border-b border-gray-200 dark:border-zinc-800">
                    <div class="flex items-center justify-between">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Notifications</h3>
                        <div class="flex items-center gap-2">
                            <button
                                v-if="notifications.length > 0 && !showHistory"
                                type="button"
                                class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                                @click.stop="clearAllNotifications"
                            >
                                Clear
                            </button>
                            <button
                                type="button"
                                class="rounded-md p-1 transition-colors"
                                :class="
                                    showHistory
                                        ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40'
                                        : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800'
                                "
                                :title="$t('app.notifications_history_title')"
                                :aria-label="$t('app.notifications_history_title')"
                                @click.stop="toggleHistory"
                            >
                                <MaterialDesignIcon icon-name="history" class="w-5 h-5" />
                            </button>
                            <button
                                type="button"
                                class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                                @click="closeDropdown"
                            >
                                <MaterialDesignIcon icon-name="close" class="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>

                <div class="overflow-y-auto flex-1">
                    <div v-if="isLoading" class="p-8 text-center">
                        <div class="inline-block animate-spin text-gray-400">
                            <MaterialDesignIcon icon-name="refresh" class="w-6 h-6" />
                        </div>
                        <div class="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading notifications...</div>
                    </div>

                    <div v-else-if="notifications.length === 0" class="p-8 text-center">
                        <MaterialDesignIcon
                            icon-name="bell-off"
                            class="w-12 h-12 mx-auto text-gray-400 dark:text-gray-500"
                        />
                        <div class="mt-2 text-sm text-gray-500 dark:text-gray-400">
                            {{
                                showHistory
                                    ? $t("app.notifications_empty_history")
                                    : $t("app.notifications_no_new")
                            }}
                        </div>
                    </div>

                    <div v-else class="divide-y divide-gray-200 dark:divide-zinc-800">
                        <button
                            v-for="notification in notifications"
                            :key="notification.destination_hash"
                            type="button"
                            class="w-full p-4 hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors text-left"
                            @click="onNotificationClick(notification)"
                        >
                            <div class="flex gap-3">
                                <div class="flex-shrink-0">
                                    <div
                                        v-if="notification.lxmf_user_icon"
                                        class="p-2 rounded-lg"
                                        :style="{
                                            color: notification.lxmf_user_icon.foreground_colour,
                                            'background-color': notification.lxmf_user_icon.background_colour,
                                        }"
                                    >
                                        <MaterialDesignIcon
                                            :icon-name="notification.lxmf_user_icon.icon_name"
                                            class="w-6 h-6"
                                        />
                                    </div>
                                    <div
                                        v-else
                                        class="bg-gray-200 dark:bg-zinc-700 text-gray-500 dark:text-gray-400 p-2 rounded-lg"
                                    >
                                        <MaterialDesignIcon icon-name="account-outline" class="w-6 h-6" />
                                    </div>
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-start justify-between gap-2 mb-1">
                                        <div
                                            class="font-semibold text-gray-900 dark:text-white truncate"
                                            :title="notification.custom_display_name ?? notification.display_name"
                                        >
                                            {{ notification.custom_display_name ?? notification.display_name }}
                                        </div>
                                        <div
                                            class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex-shrink-0"
                                        >
                                            {{ formatTimeAgo(notification.updated_at) }}
                                        </div>
                                    </div>
                                    <div
                                        class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2"
                                        :title="
                                            notification.latest_message_preview ?? notification.content ?? 'No preview'
                                        "
                                    >
                                        {{
                                            notification.latest_message_preview ?? notification.content ?? "No preview"
                                        }}
                                    </div>
                                </div>
                            </div>
                        </button>
                    </div>
                </div>
            </div>
        </Teleport>
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import Utils from "../js/Utils";
import WebSocketConnection from "../js/WebSocketConnection";
import GlobalState from "../js/GlobalState";

export default {
    name: "NotificationBell",
    components: {
        MaterialDesignIcon,
    },
    directives: {
        "click-outside": {
            mounted(el, binding) {
                el.clickOutsideEvent = function (event) {
                    if (!(el === event.target || el.contains(event.target))) {
                        binding.value();
                    }
                };
                document.addEventListener("click", el.clickOutsideEvent);
            },
            unmounted(el) {
                document.removeEventListener("click", el.clickOutsideEvent);
            },
        },
    },
    emits: ["notifications-cleared"],
    data() {
        return {
            isDropdownOpen: false,
            isLoading: false,
            notifications: [],
            unreadCount: 0,
            reloadInterval: null,
            dropdownPosition: { top: 0, left: 0 },
            showHistory: false,
        };
    },
    computed: {
        dropdownStyle() {
            return {
                top: `${this.dropdownPosition.top}px`,
                left: `${this.dropdownPosition.left}px`,
            };
        },
    },
    beforeUnmount() {
        if (this.reloadInterval) {
            clearInterval(this.reloadInterval);
        }
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    mounted() {
        this.loadNotifications();
        WebSocketConnection.on("message", this.onWebsocketMessage);
        this.reloadInterval = setInterval(() => {
            if (this.isDropdownOpen) {
                this.loadNotifications({ updateList: false });
            }
        }, 5000);
    },
    methods: {
        shouldFetchNotifications() {
            if (!GlobalState.authSessionResolved) {
                return false;
            }
            if (!GlobalState.authEnabled) {
                return true;
            }
            return GlobalState.authenticated;
        },
        async toggleDropdown(event) {
            this.isDropdownOpen = !this.isDropdownOpen;
            if (this.isDropdownOpen) {
                this.showHistory = false;
                this.updateDropdownPosition(event);
                await this.loadNotifications();
                const hadNotifications = this.notifications.length > 0;
                await this.markNotificationsAsViewed();
                if (hadNotifications) {
                    await this.loadNotifications({ updateList: false });
                }
            }
        },
        updateDropdownPosition(event) {
            const button = event.currentTarget;
            const rect = button.getBoundingClientRect();
            const isMobile = window.innerWidth < 640;
            const dropdownWidth = isMobile ? 320 : 384; // 80 (320px) or 96 (384px)

            this.dropdownPosition = {
                top: rect.bottom + 8,
                left: Math.max(16, rect.right - dropdownWidth),
            };
        },
        closeDropdown() {
            this.isDropdownOpen = false;
            this.showHistory = false;
        },
        async toggleHistory() {
            this.showHistory = !this.showHistory;
            await this.loadNotifications();
            if (!this.showHistory) {
                const hadNotifications = this.notifications.length > 0;
                await this.markNotificationsAsViewed();
                if (hadNotifications) {
                    await this.loadNotifications({ updateList: false });
                }
            }
        },
        async loadNotifications(options = {}) {
            const updateList = options.updateList !== false;
            if (!this.shouldFetchNotifications()) {
                this.notifications = [];
                this.unreadCount = 0;
                this.isLoading = false;
                return;
            }
            if (updateList) {
                this.isLoading = true;
            }
            try {
                const response = await window.api.get(`/api/v1/notifications`, {
                    params: {
                        unread: !this.showHistory,
                        limit: 10,
                    },
                });
                const newNotifications = response.data.notifications || [];
                if (updateList) {
                    this.notifications = newNotifications;
                }
                this.unreadCount = response.data.unread_count || 0;
            } catch (e) {
                console.error("Failed to load notifications", e);
                if (updateList) {
                    this.notifications = [];
                }
            } finally {
                if (updateList) {
                    this.isLoading = false;
                }
            }
        },
        async markNotificationsAsViewed() {
            if (!this.shouldFetchNotifications()) {
                return;
            }
            if (this.notifications.length === 0) {
                return;
            }
            try {
                const destination_hashes = this.notifications
                    .filter((n) => n.type === "lxmf_message")
                    .map((n) => n.destination_hash);
                const notification_ids = this.notifications.filter((n) => n.type !== "lxmf_message").map((n) => n.id);

                await window.api.post("/api/v1/notifications/mark-as-viewed", {
                    destination_hashes: destination_hashes,
                    notification_ids: notification_ids,
                });
            } catch (e) {
                console.error("Failed to mark notifications as viewed", e);
            }
        },
        async clearAllNotifications() {
            if (!this.shouldFetchNotifications()) {
                return;
            }
            try {
                await window.api.post("/api/v1/notifications/mark-as-viewed", {
                    destination_hashes: [],
                    notification_ids: [],
                });

                const response = await window.api.get("/api/v1/lxmf/conversations");
                const conversations = response.data.conversations || [];

                for (const conversation of conversations) {
                    if (conversation.is_unread) {
                        try {
                            await window.api.get(
                                `/api/v1/lxmf/conversations/${conversation.destination_hash}/mark-as-read`
                            );
                        } catch (e) {
                            console.error(`Failed to mark conversation as read: ${conversation.destination_hash}`, e);
                        }
                    }
                }

                GlobalState.unreadConversationsCount = 0;

                this.showHistory = false;
                await this.loadNotifications();
                this.$emit("notifications-cleared");
            } catch (e) {
                console.error("Failed to clear notifications", e);
            }
        },
        async onNotificationClick(notification) {
            this.closeDropdown();

            if (!this.shouldFetchNotifications()) {
                return;
            }

            // Mark this specific notification as viewed
            try {
                const destination_hashes = notification.type === "lxmf_message" ? [notification.destination_hash] : [];
                const notification_ids = notification.type !== "lxmf_message" ? [notification.id] : [];

                await window.api.post("/api/v1/notifications/mark-as-viewed", {
                    destination_hashes: destination_hashes,
                    notification_ids: notification_ids,
                });

                // reload to update unread count
                await this.loadNotifications();
            } catch (e) {
                console.error("Failed to mark notification as viewed", e);
            }

            if (notification.type === "lxmf_message") {
                this.$router.push({
                    name: "messages",
                    params: { destinationHash: notification.destination_hash },
                });
            } else if (notification.type === "telephone_missed_call") {
                this.$router.push({
                    name: "call",
                    query: { tab: "history" },
                });
            } else if (notification.type === "telephone_voicemail") {
                this.$router.push({
                    name: "call",
                    query: { tab: "voicemail" },
                });
            }
        },
        formatTimeAgo(datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        async onWebsocketMessage(message) {
            if (!this.shouldFetchNotifications()) {
                return;
            }
            const json = JSON.parse(message.data);
            if (json.type === "lxmf.delivery") {
                if (json.lxmf_message?.is_incoming !== true) {
                    return;
                }
                await this.loadNotifications();
                if (this.isDropdownOpen) {
                    const hadNotifications = this.notifications.length > 0;
                    await this.markNotificationsAsViewed();
                    if (hadNotifications) {
                        await this.loadNotifications({ updateList: false });
                    }
                }
                return;
            }
            if (json.type === "telephone_missed_call" || json.type === "new_voicemail") {
                await this.loadNotifications();
                if (this.isDropdownOpen) {
                    const hadNotifications = this.notifications.length > 0;
                    await this.markNotificationsAsViewed();
                    if (hadNotifications) {
                        await this.loadNotifications({ updateList: false });
                    }
                }
            }
        },
    },
};
</script>

<style scoped>
.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
