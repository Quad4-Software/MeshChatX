<template>
    <div class="flex flex-1 min-w-0 h-full overflow-hidden">
        <MessagesSidebar
            v-if="!isPopoutMode"
            :class="{ 'hidden sm:flex': destinationHash }"
            :conversations="conversations"
            :peers="peers"
            :selected-destination-hash="selectedPeer?.destination_hash"
            :conversation-search-term="conversationSearchTerm"
            :filter-unread-only="filterUnreadOnly"
            :filter-failed-only="filterFailedOnly"
            :filter-has-attachments-only="filterHasAttachmentsOnly"
            :is-loading="isLoadingConversations"
            @conversation-click="onConversationClick"
            @peer-click="onPeerClick"
            @conversation-search-changed="onConversationSearchChanged"
            @conversation-filter-changed="onConversationFilterChanged"
            @ingest-paper-message="openIngestPaperMessageModal"
        />

        <div
            class="flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-white via-slate-50 to-slate-100 dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900/80"
            :class="destinationHash ? 'flex' : 'hidden sm:flex'"
        >
            <!-- messages tab -->
            <ConversationViewer
                ref="conversation-viewer"
                :my-lxmf-address-hash="config?.lxmf_address_hash"
                :selected-peer="selectedPeer"
                :conversations="conversations"
                @close="onCloseConversationViewer"
                @reload-conversations="getConversations"
            />
        </div>

        <!-- Ingest Paper Message Modal -->
        <div
            v-if="isIngestModalOpen"
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            @click.self="isIngestModalOpen = false"
        >
            <div class="w-full max-w-md bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl overflow-hidden">
                <div class="px-6 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">Ingest Paper Message</h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors"
                        @click="isIngestModalOpen = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                </div>
                <div class="p-6">
                    <p class="text-sm text-gray-600 dark:text-zinc-400 mb-4">
                        You can read LXMF paper messages by scanning a QR code or pasting an <strong>lxmf://</strong> or
                        <strong>lxm://</strong> link.
                    </p>
                    <div class="space-y-4">
                        <div>
                            <label
                                class="block text-xs font-medium text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-1"
                            >
                                LXMF URI
                            </label>
                            <div class="flex gap-2">
                                <input
                                    v-model="ingestUri"
                                    type="text"
                                    placeholder="lxmf://..."
                                    class="block w-full rounded-lg border-0 py-2 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                                    @keydown.enter="ingestPaperMessage"
                                />
                                <button
                                    type="button"
                                    class="px-3 py-2 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 rounded-lg hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
                                    title="Paste from Clipboard"
                                    @click="pasteFromClipboard"
                                >
                                    <MaterialDesignIcon icon-name="clipboard-text-outline" class="size-5" />
                                </button>
                            </div>
                        </div>
                        <button
                            type="button"
                            class="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all"
                            :disabled="!ingestUri"
                            @click="ingestPaperMessage"
                        >
                            Read LXM
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import WebSocketConnection from "../../js/WebSocketConnection";
import MessagesSidebar from "./MessagesSidebar.vue";
import ConversationViewer from "./ConversationViewer.vue";
import GlobalState from "../../js/GlobalState";
import DialogUtils from "../../js/DialogUtils";
import GlobalEmitter from "../../js/GlobalEmitter";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "MessagesPage",
    components: {
        ConversationViewer,
        MessagesSidebar,
    },
    props: {
        destinationHash: {
            type: String,
            required: false,
            default: null,
        },
    },
    data() {
        return {
            reloadInterval: null,
            conversationRefreshTimeout: null,

            config: null,
            peers: {},
            selectedPeer: null,

            conversations: [],
            lxmfDeliveryAnnounces: [],

            conversationSearchTerm: "",
            filterUnreadOnly: false,
            filterFailedOnly: false,
            filterHasAttachmentsOnly: false,
            isLoadingConversations: false,

            isIngestModalOpen: false,
            ingestUri: "",
        };
    },
    computed: {
        popoutRouteType() {
            if (this.$route?.meta?.popoutType) {
                return this.$route.meta.popoutType;
            }
            return this.$route?.query?.popout ?? this.getHashPopoutValue();
        },
        isPopoutMode() {
            return this.popoutRouteType === "conversation";
        },
    },
    watch: {
        conversations() {
            // update global state
            GlobalState.unreadConversationsCount = this.conversations.filter((conversation) => {
                return conversation.is_unread;
            }).length;
        },
        destinationHash(newHash) {
            if (newHash) {
                this.onComposeNewMessage(newHash);
            }
        },
    },
    beforeUnmount() {
        clearInterval(this.reloadInterval);
        clearTimeout(this.conversationRefreshTimeout);

        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
        GlobalEmitter.off("compose-new-message", this.onComposeNewMessage);
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);
        GlobalEmitter.on("compose-new-message", this.onComposeNewMessage);

        this.getConfig();
        this.getConversations();
        this.getLxmfDeliveryAnnounces();

        // update info every few seconds
        this.reloadInterval = setInterval(() => {
            this.getConversations();
        }, 5000);

        // compose message if a destination hash was provided on page load
        if (this.destinationHash) {
            this.onComposeNewMessage(this.destinationHash);
        }
    },
    methods: {
        async onComposeNewMessage(destinationHash) {
            if (destinationHash == null) {
                if (this.selectedPeer) {
                    return;
                }
                this.$nextTick(() => {
                    const composeInput = document.getElementById("compose-input");
                    if (composeInput) {
                        composeInput.focus();
                    }
                });
                return;
            }

            if (destinationHash.startsWith("lxmf@")) {
                destinationHash = destinationHash.replace("lxmf@", "");
            }

            await this.getLxmfDeliveryAnnounce(destinationHash);

            const existingPeer = this.peers[destinationHash];
            if (existingPeer) {
                this.onPeerClick(existingPeer);
                return;
            }

            if (destinationHash.length !== 32) {
                DialogUtils.alert("Invalid Address");
                return;
            }

            this.onPeerClick({
                display_name: "Unknown Peer",
                destination_hash: destinationHash,
            });
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
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            switch (json.type) {
                case "config": {
                    this.config = json.config;
                    break;
                }
                case "announce": {
                    const aspect = json.announce.aspect;
                    if (aspect === "lxmf.delivery") {
                        this.updatePeerFromAnnounce(json.announce);
                    }
                    break;
                }
                case "lxmf.delivery": {
                    // reload conversations when a new message is received
                    await this.getConversations();
                    break;
                }
                case "lxm.ingest_uri.result": {
                    if (json.status === "success") {
                        ToastUtils.success(json.message);
                        await this.getConversations();
                    } else if (json.status === "error") {
                        ToastUtils.error(json.message);
                    } else if (json.status === "warning") {
                        ToastUtils.warning(json.message);
                    } else {
                        ToastUtils.info(json.message);
                    }
                    break;
                }
            }
        },
        async getLxmfDeliveryAnnounces() {
            try {
                // fetch announces for "lxmf.delivery" aspect
                const response = await window.axios.get(`/api/v1/announces`, {
                    params: {
                        aspect: "lxmf.delivery",
                        limit: 500, // limit ui to showing 500 latest announces
                    },
                });

                // update ui
                const lxmfDeliveryAnnounces = response.data.announces;
                for (const lxmfDeliveryAnnounce of lxmfDeliveryAnnounces) {
                    this.updatePeerFromAnnounce(lxmfDeliveryAnnounce);
                }
            } catch (e) {
                // do nothing if failed to load announces
                console.log(e);
            }
        },
        async getLxmfDeliveryAnnounce(destinationHash) {
            try {
                // fetch announce for destination hash
                const response = await window.axios.get(`/api/v1/announces`, {
                    params: {
                        destination_hash: destinationHash,
                        limit: 1,
                    },
                });

                // update ui
                const lxmfDeliveryAnnounces = response.data.announces;
                for (const lxmfDeliveryAnnounce of lxmfDeliveryAnnounces) {
                    this.updatePeerFromAnnounce(lxmfDeliveryAnnounce);
                }
            } catch (e) {
                // do nothing if failed to load announce
                console.log(e);
            }
        },
        async getConversations() {
            try {
                this.isLoadingConversations = true;
                const response = await window.axios.get(`/api/v1/lxmf/conversations`, {
                    params: this.buildConversationQueryParams(),
                });
                this.conversations = response.data.conversations;
            } catch (e) {
                // do nothing if failed to load conversations
                console.log(e);
            } finally {
                this.isLoadingConversations = false;
            }
        },
        buildConversationQueryParams() {
            const params = {};
            if (this.conversationSearchTerm && this.conversationSearchTerm.trim() !== "") {
                params.search = this.conversationSearchTerm.trim();
            }
            if (this.filterUnreadOnly) {
                params.filter_unread = true;
            }
            if (this.filterFailedOnly) {
                params.filter_failed = true;
            }
            if (this.filterHasAttachmentsOnly) {
                params.filter_has_attachments = true;
            }
            return params;
        },
        updatePeerFromAnnounce: function (announce) {
            this.peers[announce.destination_hash] = announce;
        },
        onPeerClick: function (peer) {
            // update selected peer
            this.selectedPeer = peer;

            // update current route
            const routeName = this.isPopoutMode ? "messages-popout" : "messages";
            const routeOptions = {
                name: routeName,
                params: {
                    destinationHash: peer.destination_hash,
                },
            };
            if (!this.isPopoutMode && this.$route?.query) {
                routeOptions.query = { ...this.$route.query };
            }
            this.$router.replace(routeOptions);
        },
        onConversationClick: function (conversation) {
            // object must stay compatible with format of peers
            this.onPeerClick(conversation);

            // mark conversation as read
            this.$refs["conversation-viewer"].markConversationAsRead(conversation);
        },
        onCloseConversationViewer: function () {
            // clear selected peer
            this.selectedPeer = null;

            if (this.isPopoutMode) {
                window.close();
                return;
            }

            // update current route
            const routeName = this.isPopoutMode ? "messages-popout" : "messages";
            const routeOptions = { name: routeName };
            if (!this.isPopoutMode && this.$route?.query) {
                routeOptions.query = { ...this.$route.query };
            }
            this.$router.replace(routeOptions);
        },
        requestConversationsRefresh() {
            if (this.conversationRefreshTimeout) {
                clearTimeout(this.conversationRefreshTimeout);
            }
            this.conversationRefreshTimeout = setTimeout(() => {
                this.getConversations();
            }, 250);
        },
        onConversationSearchChanged(term) {
            this.conversationSearchTerm = term;
            this.requestConversationsRefresh();
        },
        onConversationFilterChanged(filterKey) {
            if (filterKey === "unread") {
                this.filterUnreadOnly = !this.filterUnreadOnly;
            } else if (filterKey === "failed") {
                this.filterFailedOnly = !this.filterFailedOnly;
            } else if (filterKey === "attachments") {
                this.filterHasAttachmentsOnly = !this.filterHasAttachmentsOnly;
            }
            this.requestConversationsRefresh();
        },
        openIngestPaperMessageModal() {
            this.ingestUri = "";
            this.isIngestModalOpen = true;
        },
        async pasteFromClipboard() {
            try {
                this.ingestUri = await navigator.clipboard.readText();
            } catch {
                ToastUtils.error("Failed to read from clipboard");
            }
        },
        async ingestPaperMessage() {
            if (!this.ingestUri) return;

            try {
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "lxm.ingest_uri",
                        uri: this.ingestUri,
                    })
                );
                this.isIngestModalOpen = false;
            } catch {
                ToastUtils.error("Failed to send ingest request");
            }
        },
        getHashPopoutValue() {
            const hash = window.location.hash || "";
            const match = hash.match(/popout=([^&]+)/);
            return match ? decodeURIComponent(match[1]) : null;
        },
    },
};
</script>
