<template>
    <div class="relative">
        <button
            type="button"
            class="relative rounded-full p-1.5 sm:p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
            @click="toggleDropdown"
        >
            <MaterialDesignIcon icon-name="bell" class="w-5 h-5 sm:w-6 sm:h-6" />
            <span
                v-if="unreadCount > 0"
                class="absolute top-0 right-0 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-semibold text-white"
            >
                {{ unreadCount > 9 ? "9+" : unreadCount }}
            </span>
        </button>

        <div
            v-if="isDropdownOpen"
            v-click-outside="closeDropdown"
            class="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-xl z-[9999] max-h-[500px] overflow-hidden flex flex-col"
        >
            <div class="p-4 border-b border-gray-200 dark:border-zinc-800">
                <div class="flex items-center justify-between">
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Notifications</h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                        @click="closeDropdown"
                    >
                        <MaterialDesignIcon icon-name="close" class="w-5 h-5" />
                    </button>
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
                    <div class="mt-2 text-sm text-gray-500 dark:text-gray-400">No new notifications</div>
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
                                    :title="notification.latest_message_preview ?? notification.content ?? 'No preview'"
                                >
                                    {{ notification.latest_message_preview ?? notification.content ?? "No preview" }}
                                </div>
                            </div>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import Utils from "../js/Utils";
import WebSocketConnection from "../js/WebSocketConnection";

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
    data() {
        return {
            isDropdownOpen: false,
            isLoading: false,
            notifications: [],
            unreadCount: 0,
            reloadInterval: null,
        };
    },
    computed: {},
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
                this.loadNotifications();
            }
        }, 5000);
    },
    methods: {
        async toggleDropdown() {
            this.isDropdownOpen = !this.isDropdownOpen;
            if (this.isDropdownOpen) {
                await this.loadNotifications();
                await this.markNotificationsAsViewed();
            }
        },
        closeDropdown() {
            this.isDropdownOpen = false;
        },
        async loadNotifications() {
            this.isLoading = true;
            try {
                const response = await window.axios.get(`/api/v1/notifications`, {
                    params: {
                        unread: true,
                        limit: 10,
                    },
                });
                const newNotifications = response.data.notifications || [];

                this.notifications = newNotifications;
                this.unreadCount = response.data.unread_count || 0;
            } catch (e) {
                console.error("Failed to load notifications", e);
                this.notifications = [];
            } finally {
                this.isLoading = false;
            }
        },
        async markNotificationsAsViewed() {
            if (this.notifications.length === 0) {
                return;
            }
            try {
                const destination_hashes = this.notifications
                    .filter((n) => n.type === "lxmf_message")
                    .map((n) => n.destination_hash);
                const notification_ids = this.notifications.filter((n) => n.type !== "lxmf_message").map((n) => n.id);

                await window.axios.post("/api/v1/notifications/mark-as-viewed", {
                    destination_hashes: destination_hashes,
                    notification_ids: notification_ids,
                });
            } catch (e) {
                console.error("Failed to mark notifications as viewed", e);
            }
        },
        onNotificationClick(notification) {
            this.closeDropdown();
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
            }
        },
        formatTimeAgo(datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            if (json.type === "lxmf.delivery") {
                await this.loadNotifications();
                // If dropdown is open, mark new notifications as viewed
                if (this.isDropdownOpen) {
                    await this.markNotificationsAsViewed();
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
