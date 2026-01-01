<template>
    <div
        :class="{ dark: config?.theme === 'dark' }"
        class="h-screen w-full flex flex-col bg-slate-50 dark:bg-zinc-950 transition-colors"
    >
        <div
            v-if="appInfo?.is_demo"
            class="relative z-[100] bg-blue-600/90 backdrop-blur-sm text-white text-[10px] font-bold uppercase tracking-[0.2em] py-1 text-center select-none border-b border-white/10 shadow-sm"
        >
            Demo Mode &bull; Read Only
        </div>

        <RouterView v-if="$route.name === 'auth'" />

        <template v-else>
            <div v-if="isPopoutMode" class="flex flex-1 h-full w-full overflow-hidden bg-slate-50/90 dark:bg-zinc-950">
                <RouterView class="flex-1" />
            </div>

            <template v-else>
                <!-- header -->
                <div
                    class="relative z-[60] flex bg-white/80 dark:bg-zinc-900/70 backdrop-blur border-gray-200 dark:border-zinc-800 border-b min-h-16 shadow-sm transition-colors"
                >
                    <div class="flex w-full px-4">
                        <button
                            type="button"
                            class="sm:hidden my-auto mr-4 text-gray-500 hover:text-gray-600 dark:text-gray-400 dark:hover:text-gray-300"
                            @click="isSidebarOpen = !isSidebarOpen"
                        >
                            <MaterialDesignIcon :icon-name="isSidebarOpen ? 'close' : 'menu'" class="size-6" />
                        </button>
                        <div
                            class="hidden sm:flex my-auto w-12 h-12 mr-2 rounded-xl overflow-hidden bg-white/70 dark:bg-white/10 border border-gray-200 dark:border-zinc-700 shadow-inner"
                        >
                            <img class="w-12 h-12 object-contain p-1.5" src="/assets/images/logo.png" />
                        </div>
                        <div class="my-auto">
                            <div
                                class="font-semibold cursor-pointer text-gray-900 dark:text-zinc-100 tracking-tight text-lg"
                                @click="onAppNameClick"
                            >
                                {{ $t("app.name") }}
                            </div>
                            <div class="hidden sm:block text-sm text-gray-600 dark:text-zinc-300">
                                {{ $t("app.custom_fork_by") }}
                                <a
                                    target="_blank"
                                    href="https://github.com/Sudo-Ivan"
                                    class="text-blue-500 dark:text-blue-300 hover:underline"
                                    >Sudo-Ivan</a
                                >
                            </div>
                        </div>
                        <div class="flex my-auto ml-auto mr-0 sm:mr-2 space-x-2">
                            <button
                                type="button"
                                class="relative rounded-full p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
                                :title="config?.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
                                @click="toggleTheme"
                            >
                                <MaterialDesignIcon
                                    :icon-name="config?.theme === 'dark' ? 'brightness-6' : 'brightness-4'"
                                    class="w-6 h-6"
                                />
                            </button>
                            <LanguageSelector @language-change="onLanguageChange" />
                            <NotificationBell />
                            <button type="button" class="rounded-full" @click="syncPropagationNode">
                                <span
                                    class="flex text-gray-800 dark:text-zinc-100 bg-white dark:bg-zinc-800/80 border border-gray-200 dark:border-zinc-700 hover:border-blue-400 dark:hover:border-blue-400/60 px-3 py-1.5 rounded-full shadow-sm transition"
                                >
                                    <span :class="{ 'animate-spin': isSyncingPropagationNode }">
                                        <MaterialDesignIcon icon-name="refresh" class="size-6" />
                                    </span>
                                    <span class="hidden sm:inline-block my-auto mx-1 text-sm font-medium">{{
                                        $t("app.sync_messages")
                                    }}</span>
                                </span>
                            </button>
                            <button type="button" class="rounded-full" @click="composeNewMessage">
                                <span
                                    class="flex text-white bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 hover:from-blue-500/90 hover:to-purple-500/90 px-3 py-1.5 rounded-full shadow-md transition"
                                >
                                    <span>
                                        <MaterialDesignIcon icon-name="email" class="w-6 h-6" />
                                    </span>
                                    <span class="hidden sm:inline-block my-auto mx-1 text-sm font-semibold">{{
                                        $t("app.compose")
                                    }}</span>
                                </span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- middle -->
                <div
                    ref="middle"
                    class="flex flex-1 w-full overflow-hidden bg-slate-50/80 dark:bg-zinc-950 transition-colors"
                >
                    <!-- sidebar backdrop for mobile -->
                    <div
                        v-if="isSidebarOpen"
                        class="fixed inset-0 z-[65] bg-black/20 backdrop-blur-sm sm:hidden"
                        @click="isSidebarOpen = false"
                    ></div>

                    <!-- sidebar -->
                    <div
                        class="fixed inset-y-0 left-0 z-[70] w-72 transform transition-transform duration-300 ease-in-out sm:relative sm:z-0 sm:flex sm:translate-x-0"
                        :class="isSidebarOpen ? 'translate-x-0' : '-translate-x-full'"
                    >
                        <div
                            class="flex h-full w-full flex-col overflow-y-auto border-r border-gray-200/70 bg-white dark:border-zinc-800 dark:bg-zinc-900 backdrop-blur"
                        >
                            <!-- navigation -->
                            <div class="flex-1">
                                <ul class="py-3 pr-2 space-y-1">
                                    <!-- messages -->
                                    <li>
                                        <SidebarLink :to="{ name: 'messages' }">
                                            <template #icon>
                                                <MaterialDesignIcon
                                                    icon-name="message-text"
                                                    class="w-6 h-6 dark:text-white"
                                                />
                                            </template>
                                            <template #text>
                                                <span>{{ $t("app.messages") }}</span>
                                                <span v-if="unreadConversationsCount > 0" class="ml-auto mr-2">{{
                                                    unreadConversationsCount
                                                }}</span>
                                            </template>
                                        </SidebarLink>
                                    </li>

                                    <!-- nomad network -->
                                    <li>
                                        <SidebarLink :to="{ name: 'nomadnetwork' }">
                                            <template #icon>
                                                <MaterialDesignIcon icon-name="earth" class="w-6 h-6" />
                                            </template>
                                            <template #text>{{ $t("app.nomad_network") }}</template>
                                        </SidebarLink>
                                    </li>

                                    <!-- map -->
                                    <li>
                                        <SidebarLink :to="{ name: 'map' }">
                                            <template #icon>
                                                <MaterialDesignIcon icon-name="map" class="w-6 h-6" />
                                            </template>
                                            <template #text>{{ $t("app.map") }}</template>
                                        </SidebarLink>
                                    </li>

                                    <!-- archives -->
                                    <li>
                                        <SidebarLink :to="{ name: 'archives' }">
                                            <template #icon>
                                                <MaterialDesignIcon icon-name="archive" class="w-6 h-6" />
                                            </template>
                                            <template #text>{{ $t("app.archives") }}</template>
                                        </SidebarLink>
                                    </li>

                                    <!-- interfaces -->
                                    <li>
                                        <SidebarLink :to="{ name: 'interfaces' }">
                                            <template #icon>
                                                <MaterialDesignIcon icon-name="router" class="w-6 h-6" />
                                            </template>
                                            <template #text>{{ $t("app.interfaces") }}</template>
                                        </SidebarLink>
                                    </li>

                                    <!-- network visualiser -->
                                    <li>
                                        <SidebarLink :to="{ name: 'network-visualiser' }">
                                            <template #icon>
                                                <MaterialDesignIcon icon-name="diagram-projector" class="w-6 h-6" />
                                            </template>
                                            <template #text>{{ $t("app.network_visualiser") }}</template>
                                        </SidebarLink>
                                    </li>

                                    <!-- tools -->
                                    <li>
                                        <SidebarLink :to="{ name: 'tools' }">
                                            <template #icon>
                                                <MaterialDesignIcon icon-name="wrench" class="size-6" />
                                            </template>
                                            <template #text>{{ $t("app.tools") }}</template>
                                        </SidebarLink>
                                    </li>

                                    <!-- settings -->
                                    <li>
                                        <SidebarLink :to="{ name: 'settings' }">
                                            <template #icon>
                                                <MaterialDesignIcon icon-name="cog" class="size-6" />
                                            </template>
                                            <template #text>{{ $t("app.settings") }}</template>
                                        </SidebarLink>
                                    </li>

                                    <!-- info -->
                                    <li>
                                        <SidebarLink :to="{ name: 'about' }">
                                            <template #icon>
                                                <MaterialDesignIcon icon-name="information" class="size-6" />
                                            </template>
                                            <template #text>{{ $t("app.about") }}</template>
                                        </SidebarLink>
                                    </li>
                                </ul>
                            </div>

                            <div>
                                <!-- my identity -->
                                <div
                                    v-if="config"
                                    class="bg-white/80 border-t dark:border-zinc-800 dark:bg-zinc-900/70 backdrop-blur"
                                >
                                    <div
                                        class="flex text-gray-700 p-3 cursor-pointer"
                                        @click="isShowingMyIdentitySection = !isShowingMyIdentitySection"
                                    >
                                        <div class="my-auto mr-2">
                                            <RouterLink :to="{ name: 'profile.icon' }" @click.stop>
                                                <LxmfUserIcon
                                                    :icon-name="config?.lxmf_user_icon_name"
                                                    :icon-foreground-colour="config?.lxmf_user_icon_foreground_colour"
                                                    :icon-background-colour="config?.lxmf_user_icon_background_colour"
                                                />
                                            </RouterLink>
                                        </div>
                                        <div class="my-auto dark:text-white">{{ $t("app.my_identity") }}</div>
                                        <div class="my-auto ml-auto">
                                            <button
                                                type="button"
                                                class="my-auto inline-flex items-center gap-x-1 rounded-md bg-gray-500 px-2 py-1 text-sm font-semibold text-white shadow-sm hover:bg-gray-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-500 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700 dark:focus-visible:outline-zinc-500"
                                                @click.stop="saveIdentitySettings"
                                            >
                                                {{ $t("common.save") }}
                                            </button>
                                        </div>
                                    </div>
                                    <div
                                        v-if="isShowingMyIdentitySection"
                                        class="divide-y text-gray-900 border-t border-gray-200 dark:text-zinc-200 dark:border-zinc-800"
                                    >
                                        <div class="p-2">
                                            <input
                                                v-model="displayName"
                                                type="text"
                                                :placeholder="$t('app.display_name_placeholder')"
                                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-800 dark:border-zinc-600 dark:text-zinc-200 dark:focus:ring-blue-400 dark:focus:border-blue-400"
                                            />
                                        </div>
                                        <div class="p-2 dark:border-zinc-900">
                                            <div>{{ $t("app.identity_hash") }}</div>
                                            <div class="text-sm text-gray-700 dark:text-zinc-400">
                                                {{ config.identity_hash }}
                                            </div>
                                        </div>
                                        <div class="p-2 dark:border-zinc-900">
                                            <div>{{ $t("app.lxmf_address") }}</div>
                                            <div class="text-sm text-gray-700 dark:text-zinc-400">
                                                {{ config.lxmf_address_hash }}
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- auto announce -->
                                <div
                                    v-if="config"
                                    class="bg-white/80 border-t dark:bg-zinc-900/70 dark:border-zinc-800"
                                >
                                    <div
                                        class="flex text-gray-700 p-3 cursor-pointer dark:text-white"
                                        @click="isShowingAnnounceSection = !isShowingAnnounceSection"
                                    >
                                        <div class="my-auto mr-2">
                                            <MaterialDesignIcon icon-name="radio" class="size-6" />
                                        </div>
                                        <div class="my-auto">{{ $t("app.announce") }}</div>
                                        <div class="ml-auto">
                                            <button
                                                type="button"
                                                class="my-auto inline-flex items-center gap-x-1 rounded-md bg-gray-500 px-2 py-1 text-sm font-semibold text-white shadow-sm hover:bg-gray-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-500 dark:bg-zinc-800 dark:text-white dark:hover:bg-zinc-700 dark:focus-visible:outline-zinc-500"
                                                @click.stop="sendAnnounce"
                                            >
                                                {{ $t("app.announce_now") }}
                                            </button>
                                        </div>
                                    </div>
                                    <div
                                        v-if="isShowingAnnounceSection"
                                        class="divide-y text-gray-900 border-t border-gray-200 dark:text-zinc-200 dark:border-zinc-800"
                                    >
                                        <div class="p-2 dark:border-zinc-800">
                                            <select
                                                v-model="config.auto_announce_interval_seconds"
                                                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-zinc-800 dark:border-zinc-600 dark:text-zinc-200 dark:focus:ring-blue-400 dark:focus:border-blue-400"
                                                @change="onAnnounceIntervalSecondsChange"
                                            >
                                                <option value="0">{{ $t("app.disabled") }}</option>
                                                <option value="900">Every 15 Minutes</option>
                                                <option value="1800">Every 30 Minutes</option>
                                                <option value="3600">Every 1 Hour</option>
                                                <option value="10800">Every 3 Hours</option>
                                                <option value="21600">Every 6 Hours</option>
                                                <option value="43200">Every 12 Hours</option>
                                                <option value="86400">Every 24 Hours</option>
                                            </select>
                                            <div class="text-sm text-gray-700 dark:text-zinc-100">
                                                <span v-if="config.last_announced_at">{{
                                                    $t("app.last_announced", {
                                                        time: formatSecondsAgo(config.last_announced_at),
                                                    })
                                                }}</span>
                                                <span v-else>{{ $t("app.last_announced_never") }}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- audio calls -->
                                <div
                                    v-if="config"
                                    class="bg-white/80 border-t dark:bg-zinc-900/70 dark:border-zinc-800 pb-3"
                                >
                                    <div
                                        class="flex text-gray-700 p-3 cursor-pointer"
                                        @click="isShowingCallsSection = !isShowingCallsSection"
                                    >
                                        <div class="my-auto mr-2">
                                            <MaterialDesignIcon icon-name="phone" class="dark:text-white w-6 h-6" />
                                        </div>
                                        <div class="my-auto dark:text-white">{{ $t("app.calls") }}</div>
                                        <div class="ml-auto">
                                            <RouterLink
                                                :to="{ name: 'call' }"
                                                class="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-gray-100 dark:bg-zinc-800 hover:bg-gray-200 dark:hover:bg-zinc-700 text-gray-700 dark:text-zinc-300 transition-colors"
                                            >
                                                <MaterialDesignIcon
                                                    icon-name="phone"
                                                    class="w-3.5 h-3.5 flex-shrink-0"
                                                />
                                            </RouterLink>
                                        </div>
                                    </div>
                                    <div
                                        v-if="isShowingCallsSection"
                                        class="divide-y text-gray-900 border-t border-gray-200 dark:border-zinc-800"
                                    >
                                        <div class="p-2 flex dark:border-zinc-800 dark:text-white">
                                            <div>
                                                <div>{{ $t("app.status") }}</div>
                                                <div class="text-sm text-gray-700 dark:text-white">
                                                    <div v-if="isTelephoneCallActive" class="flex space-x-2">
                                                        <span>{{ $t("app.active_call") }}</span>
                                                    </div>
                                                    <div v-else>{{ $t("app.hung_up_waiting") }}</div>
                                                </div>
                                            </div>
                                            <div v-if="isTelephoneCallActive" class="ml-auto my-auto mr-1 space-x-2">
                                                <!-- hangup all calls -->
                                                <button
                                                    :title="$t('app.hangup_all_calls')"
                                                    type="button"
                                                    class="my-auto inline-flex items-center gap-x-1 rounded-full bg-red-500 p-2 text-sm font-semibold text-white shadow-sm hover:bg-red-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
                                                    @click="hangupTelephoneCall"
                                                >
                                                    <MaterialDesignIcon
                                                        icon-name="phone-hangup"
                                                        class="w-5 h-5 rotate-[135deg] translate-y-0.5"
                                                    />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-if="!isPopoutMode" class="flex flex-1 min-w-0 overflow-hidden">
                        <RouterView class="flex-1 min-w-0 h-full" />
                    </div>
                </div>
            </template>
        </template>
        <CallOverlay v-if="activeCall || isCallEnded" :active-call="activeCall || lastCall" :is-ended="isCallEnded" />
        <Toast />
    </div>
</template>

<script>
import SidebarLink from "./SidebarLink.vue";
import DialogUtils from "../js/DialogUtils";
import WebSocketConnection from "../js/WebSocketConnection";
import GlobalState from "../js/GlobalState";
import Utils from "../js/Utils";
import GlobalEmitter from "../js/GlobalEmitter";
import NotificationUtils from "../js/NotificationUtils";
import LxmfUserIcon from "./LxmfUserIcon.vue";
import Toast from "./Toast.vue";
import ToastUtils from "../js/ToastUtils";
import MaterialDesignIcon from "./MaterialDesignIcon.vue";
import NotificationBell from "./NotificationBell.vue";
import LanguageSelector from "./LanguageSelector.vue";
import CallOverlay from "./call/CallOverlay.vue";

export default {
    name: "App",
    components: {
        LxmfUserIcon,
        SidebarLink,
        Toast,
        MaterialDesignIcon,
        NotificationBell,
        LanguageSelector,
        CallOverlay,
    },
    data() {
        return {
            reloadInterval: null,
            appInfoInterval: null,

            isShowingMyIdentitySection: true,
            isShowingAnnounceSection: true,
            isShowingCallsSection: true,

            isSidebarOpen: false,

            displayName: "Anonymous Peer",
            config: null,
            appInfo: null,

            isTelephoneCallActive: false,
            activeCall: null,
            propagationNodeStatus: null,
            isCallEnded: false,
            lastCall: null,
            endedTimeout: null,
        };
    },
    computed: {
        currentPopoutType() {
            if (this.$route?.meta?.popoutType) {
                return this.$route.meta.popoutType;
            }
            return this.$route?.query?.popout ?? this.getHashPopoutValue();
        },
        isPopoutMode() {
            return this.currentPopoutType != null;
        },
        unreadConversationsCount() {
            return GlobalState.unreadConversationsCount;
        },
        isSyncingPropagationNode() {
            return [
                "path_requested",
                "link_establishing",
                "link_established",
                "request_sent",
                "receiving",
                "response_received",
                "complete",
            ].includes(this.propagationNodeStatus?.state);
        },
    },
    watch: {
        $route() {
            this.isSidebarOpen = false;
        },
        config: {
            handler(newConfig) {
                if (newConfig && newConfig.language) {
                    this.$i18n.locale = newConfig.language;
                }
            },
            deep: true,
        },
    },
    beforeUnmount() {
        clearInterval(this.reloadInterval);
        clearInterval(this.appInfoInterval);
        if (this.endedTimeout) clearTimeout(this.endedTimeout);

        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        this.getAppInfo();
        this.getConfig();
        this.updateTelephoneStatus();
        this.updatePropagationNodeStatus();

        // update info every few seconds
        this.reloadInterval = setInterval(() => {
            this.updateTelephoneStatus();
            this.updatePropagationNodeStatus();
        }, 1000);
        this.appInfoInterval = setInterval(() => {
            this.getAppInfo();
        }, 15000);
    },
    methods: {
        getHashPopoutValue() {
            const hash = window.location.hash || "";
            const match = hash.match(/popout=([^&]+)/);
            return match ? decodeURIComponent(match[1]) : null;
        },
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            switch (json.type) {
                case "config": {
                    this.config = json.config;
                    this.displayName = json.config.display_name;
                    break;
                }
                case "announced": {
                    // we just announced, update config so we can show the new last updated at
                    this.getConfig();
                    break;
                }
                case "telephone_ringing": {
                    NotificationUtils.showIncomingCallNotification();
                    this.updateTelephoneStatus();
                    break;
                }
            }
        },
        async getAppInfo() {
            try {
                const response = await window.axios.get(`/api/v1/app/info`);
                this.appInfo = response.data.app_info;
            } catch (e) {
                // do nothing if failed to load app info
                console.log(e);
            }
        },
        async getConfig() {
            try {
                const response = await window.axios.get(`/api/v1/config`);
                this.config = response.data.config;
            } catch (e) {
                // do nothing if failed to load config
                console.log(e);
            }
        },
        async sendAnnounce() {
            try {
                await window.axios.get(`/api/v1/announce`);
            } catch (e) {
                ToastUtils.error("failed to announce");
                console.log(e);
            }

            // fetch config so it updates last announced timestamp
            await this.getConfig();
        },
        async updateConfig(config) {
            // update local state immediately if in demo mode, as websocket is not available
            if (this.appInfo?.is_demo) {
                this.config = {
                    ...this.config,
                    ...config,
                };
                return;
            }

            try {
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "config.set",
                        config: config,
                    })
                );
            } catch (e) {
                console.error(e);
            }
        },
        async saveIdentitySettings() {
            await this.updateConfig({
                display_name: this.displayName,
            });
        },
        async onAnnounceIntervalSecondsChange() {
            await this.updateConfig({
                auto_announce_interval_seconds: this.config.auto_announce_interval_seconds,
            });
        },
        async toggleTheme() {
            if (!this.config) {
                return;
            }
            const newTheme = this.config.theme === "dark" ? "light" : "dark";
            await this.updateConfig({
                theme: newTheme,
            });
        },
        async onLanguageChange(langCode) {
            await this.updateConfig({
                language: langCode,
            });
            this.$i18n.locale = langCode;
        },
        async composeNewMessage() {
            // go to messages route
            await this.$router.push({ name: "messages" });

            // emit global event handled by MessagesPage
            GlobalEmitter.emit("compose-new-message");
        },
        async syncPropagationNode() {
            // ask to stop syncing if already syncing
            if (this.isSyncingPropagationNode) {
                if (await DialogUtils.confirm("Are you sure you want to stop syncing?")) {
                    await this.stopSyncingPropagationNode();
                }
                return;
            }

            // request sync
            try {
                await axios.get("/api/v1/lxmf/propagation-node/sync");
            } catch (e) {
                const errorMessage = e.response?.data?.message ?? "Something went wrong. Try again later.";
                ToastUtils.error(errorMessage);
                return;
            }

            // update propagation status
            await this.updatePropagationNodeStatus();

            // wait until sync has finished
            const syncFinishedInterval = setInterval(() => {
                // do nothing if still syncing
                if (this.isSyncingPropagationNode) {
                    return;
                }

                // finished syncing, stop checking
                clearInterval(syncFinishedInterval);

                // show result
                const status = this.propagationNodeStatus?.state;
                const messagesReceived = this.propagationNodeStatus?.messages_received ?? 0;
                if (status === "complete" || status === "idle") {
                    ToastUtils.success(`Sync complete. ${messagesReceived} messages received.`);
                } else {
                    ToastUtils.error(`Sync error: ${status}`);
                }
            }, 500);
        },
        async stopSyncingPropagationNode() {
            // stop sync
            try {
                await axios.get("/api/v1/lxmf/propagation-node/stop-sync");
            } catch {
                // do nothing on error
            }

            // update propagation status
            await this.updatePropagationNodeStatus();
        },
        async updatePropagationNodeStatus() {
            try {
                const response = await axios.get("/api/v1/lxmf/propagation-node/status");
                this.propagationNodeStatus = response.data.propagation_node_status;
            } catch {
                // do nothing on error
            }
        },
        formatSecondsAgo: function (seconds) {
            return Utils.formatSecondsAgo(seconds);
        },
        async updateTelephoneStatus() {
            try {
                // fetch status
                const response = await axios.get("/api/v1/telephone/status");
                const oldCall = this.activeCall;

                // update ui
                this.activeCall = response.data.active_call;
                this.isTelephoneCallActive = this.activeCall != null;

                // If call just ended, show ended state for a few seconds
                if (oldCall != null && this.activeCall == null) {
                    this.lastCall = oldCall;
                    this.isCallEnded = true;

                    if (this.endedTimeout) clearTimeout(this.endedTimeout);
                    this.endedTimeout = setTimeout(() => {
                        this.isCallEnded = false;
                        this.lastCall = null;
                    }, 5000);
                } else if (this.activeCall != null) {
                    // if a new call starts, clear ended state
                    this.isCallEnded = false;
                    this.lastCall = null;
                    if (this.endedTimeout) clearTimeout(this.endedTimeout);
                }
            } catch {
                // do nothing on error
            }
        },
        async hangupTelephoneCall() {
            // confirm user wants to hang up call
            if (!(await DialogUtils.confirm("Are you sure you want to hang up the current telephone call?"))) {
                return;
            }

            try {
                // hangup call
                await axios.get(`/api/v1/telephone/hangup`);

                // reload status
                await this.updateTelephoneStatus();
            } catch {
                // ignore error hanging up call
            }
        },
        onAppNameClick() {
            // user may be on mobile, and is unable to scroll back to sidebar, so let them tap app name to do it
            this.$refs["middle"].scrollTo({
                top: 0,
                left: 0,
                behavior: "smooth",
            });
        },
    },
};
</script>
