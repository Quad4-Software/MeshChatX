<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div class="flex flex-1 min-w-0 h-full overflow-hidden" :class="{ 'flex-row-reverse': messagesSidebarOnRight }">
        <MessagesSidebar
            v-if="!isPopoutMode"
            :class="{ 'hidden sm:flex': destinationHash }"
            :sidebar-position="messagesSidebarPosition"
            :collapsed="messagesListSidebarCollapsed"
            :conversations="conversations"
            :peers="peers"
            :folders="folders"
            :selected-folder-id="selectedFolderId"
            :selected-destination-hash="selectedPeer?.destination_hash"
            :conversation-search-term="conversationSearchTerm"
            :filter-unread-only="filterUnreadOnly"
            :filter-failed-only="filterFailedOnly"
            :filter-has-attachments-only="filterHasAttachmentsOnly"
            :is-loading="isLoadingConversations"
            :is-loading-more="isLoadingMore"
            :has-more-conversations="hasMoreConversations"
            :is-loading-more-announces="isLoadingMoreAnnounces"
            :has-more-announces="hasMoreAnnounces"
            :peers-search-term="peersSearchTerm"
            :total-peers-count="totalPeersCount"
            :pinned-peer-hashes="pinnedPeerHashes"
            @conversation-click="onConversationClick"
            @peer-click="onPeerClick"
            @conversation-search-changed="onConversationSearchChanged"
            @conversation-filter-changed="onConversationFilterChanged"
            @peers-search-changed="onPeersSearchChanged"
            @ingest-paper-message="openIngestPaperMessageModal"
            @load-more="loadMoreConversations"
            @load-more-announces="loadMoreAnnounces"
            @folder-click="onFolderClick"
            @create-folder="onCreateFolder"
            @rename-folder="onRenameFolder"
            @delete-folder="onDeleteFolder"
            @move-to-folder="onMoveToFolder"
            @bulk-mark-as-read="onBulkMarkAsRead"
            @bulk-delete="onBulkDelete"
            @export-folders="onExportFolders"
            @import-folders="onImportFolders"
            @toggle-conversation-pin="onToggleConversationPin"
            @toggle-collapse="messagesListSidebarCollapsed = !messagesListSidebarCollapsed"
        />

        <div
            class="flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950"
            :class="destinationHash ? 'flex' : 'hidden sm:flex'"
        >
            <!-- messages tab -->
            <ConversationViewer
                ref="conversation-viewer"
                :config="config"
                :my-lxmf-address-hash="config?.lxmf_address_hash || ''"
                :selected-peer="selectedPeer"
                :conversations="conversations"
                @update:selected-peer="onPeerClick"
                @update-peer-tracking="onUpdatePeerTracking"
                @close="onCloseConversationViewer"
                @reload-conversations="getConversations"
            />
        </div>

        <button
            v-if="!isPopoutMode && !destinationHash"
            type="button"
            class="sm:hidden fixed bottom-5 right-4 z-[65] flex h-14 w-14 items-center justify-center rounded-full bg-zinc-900 text-white shadow-lg ring-1 ring-white/10 transition active:scale-95 dark:bg-zinc-100 dark:text-zinc-900 dark:ring-zinc-800"
            :title="$t('app.compose')"
            @click="openMobileCompose"
        >
            <MaterialDesignIcon icon-name="plus" class="size-7" />
        </button>

        <div
            v-if="isMobileComposeModalOpen"
            class="fixed inset-0 z-[95] flex items-end justify-center sm:items-center p-0 sm:p-4 bg-black/50 backdrop-blur-sm sm:bg-black/50"
            @click.self="isMobileComposeModalOpen = false"
        >
            <div
                class="w-full sm:max-w-md bg-white dark:bg-zinc-900 rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col"
                @click.stop
            >
                <div
                    class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between shrink-0"
                >
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">
                        {{ $t("messages.mobile_compose_title") }}
                    </h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center -mr-2"
                        @click="isMobileComposeModalOpen = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                </div>
                <div class="p-5 overflow-y-auto space-y-4">
                    <p class="text-sm text-gray-600 dark:text-zinc-400">
                        {{ $t("messages.select_peer_or_enter_address") }}
                    </p>
                    <div>
                        <label
                            class="block text-xs font-medium text-gray-500 dark:text-zinc-500 uppercase tracking-wider mb-1"
                            for="mobile-compose-destination"
                        >
                            {{ $t("app.lxmf_address_hash") }}
                        </label>
                        <input
                            id="mobile-compose-destination"
                            v-model="mobileComposeAddress"
                            type="text"
                            autocomplete="off"
                            autocorrect="off"
                            spellcheck="false"
                            :placeholder="$t('messages.mobile_compose_destination_placeholder')"
                            class="block w-full rounded-xl border-0 py-2.5 px-3 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                            @keydown.enter="submitMobileCompose"
                        />
                    </div>
                    <div class="flex flex-col gap-2">
                        <button
                            type="button"
                            class="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all disabled:opacity-50 disabled:pointer-events-none"
                            :disabled="!mobileComposeAddress.trim()"
                            @click="submitMobileCompose"
                        >
                            {{ $t("app.compose") }}
                        </button>
                        <button
                            type="button"
                            class="w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-xl border border-gray-200 dark:border-zinc-700 text-sm font-semibold text-gray-800 dark:text-zinc-200 bg-gray-50 dark:bg-zinc-800 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                            @click="openIngestFromMobileCompose"
                        >
                            <MaterialDesignIcon icon-name="qrcode" class="size-5 shrink-0" />
                            {{ $t("messages.ingest_paper_message") }}
                        </button>
                    </div>
                </div>
            </div>
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
                        <strong>lxm://</strong> link. Contact-sharing links using <strong>lxma://</strong> are also
                        supported.
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
                                    placeholder="lxmf://... or lxma://..."
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
                                <button
                                    v-if="cameraSupported"
                                    type="button"
                                    class="px-3 py-2 bg-gray-100 dark:bg-zinc-800 text-gray-700 dark:text-zinc-300 rounded-lg hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
                                    :title="$t('messages.scan_qr')"
                                    @click="openIngestScannerModal"
                                >
                                    <MaterialDesignIcon icon-name="qrcode-scan" class="size-5" />
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
                        <p v-if="!cameraSupported" class="text-xs text-gray-500 dark:text-zinc-400">
                            {{ $t("messages.camera_not_supported") }}
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <div
            v-if="isIngestScannerModalOpen"
            class="fixed inset-0 z-[120] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
            @click.self="closeIngestScannerModal"
        >
            <div class="w-full max-w-xl rounded-2xl bg-white dark:bg-zinc-900 shadow-2xl overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-zinc-100">{{ $t("messages.scan_qr") }}</h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300"
                        @click="closeIngestScannerModal"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-5" />
                    </button>
                </div>
                <div class="p-5 space-y-3">
                    <video
                        ref="ingestScannerVideo"
                        class="w-full rounded-xl bg-black max-h-[60vh]"
                        autoplay
                        playsinline
                        muted
                    ></video>
                    <div class="text-sm text-gray-500 dark:text-zinc-400">
                        {{ ingestScannerError || $t("messages.scanner_hint") }}
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
import GlobalState, { mergeGlobalConfig } from "../../js/GlobalState";

function snapshotGlobalConfig() {
    return GlobalState.config && typeof GlobalState.config === "object" ? { ...GlobalState.config } : {};
}
import DialogUtils from "../../js/DialogUtils";
import GlobalEmitter from "../../js/GlobalEmitter";
import ToastUtils from "../../js/ToastUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";

export default {
    name: "MessagesPage",
    components: {
        ConversationViewer,
        MessagesSidebar,
        MaterialDesignIcon,
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
            peersRefreshTimeout: null,
            conversationsAbortController: null,
            announcesAbortController: null,

            config: snapshotGlobalConfig(),
            hasLoadedConversations: false,
            messagesListSidebarCollapsed: false,
            peers: {},
            selectedPeer: null,

            conversations: [],
            folders: [],
            selectedFolderId: null,
            pageSize: 50,
            hasMoreConversations: true,
            isLoadingMore: false,

            hasMoreAnnounces: true,
            isLoadingMoreAnnounces: false,
            totalPeersCount: 0,
            peersSearchTerm: "",
            lxmfDeliveryAnnounces: [],

            conversationSearchTerm: "",
            filterUnreadOnly: false,
            filterFailedOnly: false,
            filterHasAttachmentsOnly: false,
            isLoadingConversations: false,

            pinnedPeerHashes: [],

            isIngestModalOpen: false,
            ingestUri: "",
            isIngestScannerModalOpen: false,
            ingestScannerError: null,
            ingestScannerStream: null,
            ingestScannerAnimationFrame: null,
            isMobileComposeModalOpen: false,
            mobileComposeAddress: "",
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
        messagesSidebarPosition() {
            const p = this.config?.messages_sidebar_position;
            return p === "right" ? "right" : "left";
        },
        messagesSidebarOnRight() {
            return this.messagesSidebarPosition === "right";
        },
        cameraSupported() {
            return (
                typeof window !== "undefined" &&
                typeof window.BarcodeDetector !== "undefined" &&
                navigator?.mediaDevices?.getUserMedia
            );
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
                this.isMobileComposeModalOpen = false;
                this.onComposeNewMessage(newHash);
            }
        },
    },
    beforeUnmount() {
        clearInterval(this.reloadInterval);
        clearTimeout(this.conversationRefreshTimeout);
        clearTimeout(this.peersRefreshTimeout);
        this.conversationsAbortController?.abort();
        this.announcesAbortController?.abort();
        this.stopIngestScanner();

        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
        GlobalEmitter.off("compose-new-message", this.onComposeNewMessage);
        GlobalEmitter.off("refresh-conversations", this.requestConversationsRefresh);
        GlobalEmitter.off("websocket-reconnected", this.requestConversationsRefresh);
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);
        GlobalEmitter.on("compose-new-message", this.onComposeNewMessage);
        GlobalEmitter.on("websocket-reconnected", this.requestConversationsRefresh);

        this.getConfig();
        this.getConversations();
        this.loadConversationPins();
        this.getFolders();
        this.getLxmfDeliveryAnnounces();

        // update info every few seconds
        this.reloadInterval = setInterval(() => {
            this.getConversations();
            this.getFolders();
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
                DialogUtils.alert(this.$t("common.invalid_address"));
                return;
            }

            const existingConversation = this.conversations.find((c) => c.destination_hash === destinationHash);
            this.onPeerClick({
                display_name: existingConversation?.display_name ?? "Anonymous Peer",
                custom_display_name: existingConversation?.custom_display_name ?? null,
                destination_hash: destinationHash,
            });
        },
        async getConfig() {
            try {
                const response = await window.api.get(`/api/v1/config`);
                const next = response.data?.config;
                if (next && typeof next === "object") {
                    mergeGlobalConfig(next);
                    this.config = next;
                }
            } catch (e) {
                console.log(e);
                this.config = snapshotGlobalConfig();
            }
        },
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            switch (json.type) {
                case "config": {
                    const next = json?.config;
                    if (next && typeof next === "object") {
                        mergeGlobalConfig(next);
                        this.config = next;
                    }
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
                    await this.getConversations();
                    break;
                }
                case "lxmf_message_created": {
                    this.onOutboundMessageCreated(json.lxmf_message);
                    break;
                }
                case "lxmf_message_state_updated": {
                    this.onOutboundMessageStateUpdated(json.lxmf_message);
                    break;
                }
                case "lxmf.telemetry": {
                    // update tracking status if peer matches
                    const destHash = json.destination_hash;
                    if (this.peers[destHash]) {
                        this.peers[destHash].is_tracking = json.is_tracking;
                    }
                    if (this.selectedPeer && this.selectedPeer.destination_hash === destHash) {
                        this.selectedPeer.is_tracking = json.is_tracking;
                    }
                    break;
                }
                case "lxm.ingest_uri.result": {
                    if (json.status === "success") {
                        this.ingestUri = "";
                        if (json.ingest_type === "lxma_contact" && json.destination_hash) {
                            await this.onComposeNewMessage(json.destination_hash);
                        } else {
                            await this.getConversations();
                        }
                    }
                    break;
                }
            }
        },
        async getLxmfDeliveryAnnounces(append = false) {
            try {
                if (!append) {
                    if (this.announcesAbortController) {
                        this.announcesAbortController.abort();
                    }
                    this.announcesAbortController = new AbortController();
                } else if (!this.announcesAbortController) {
                    this.announcesAbortController = new AbortController();
                }
                const offset = append ? Object.keys(this.peers).length : 0;
                const response = await window.api.get(`/api/v1/announces`, {
                    params: {
                        aspect: "lxmf.delivery",
                        limit: this.pageSize,
                        offset: offset,
                        search: this.peersSearchTerm,
                    },
                    signal: this.announcesAbortController.signal,
                });

                const newAnnounces = response.data.announces;
                if (!append) {
                    this.peers = {};
                }

                this.totalPeersCount = response.data.total_count || 0;

                for (const ann of newAnnounces) {
                    this.updatePeerFromAnnounce(ann);
                }

                this.hasMoreAnnounces = newAnnounces.length === this.pageSize;
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
                console.log(e);
            } finally {
                this.isLoadingMoreAnnounces = false;
            }
        },
        async loadMoreAnnounces() {
            if (this.isLoadingMoreAnnounces || !this.hasMoreAnnounces) return;
            this.isLoadingMoreAnnounces = true;
            await this.getLxmfDeliveryAnnounces(true);
        },
        async getLxmfDeliveryAnnounce(destinationHash) {
            try {
                // fetch announce for destination hash
                const response = await window.api.get(`/api/v1/announces`, {
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
        async getConversations(append = false) {
            try {
                if (!append) {
                    if (this.conversationsAbortController) {
                        this.conversationsAbortController.abort();
                    }
                    this.conversationsAbortController = new AbortController();
                } else if (!this.conversationsAbortController) {
                    this.conversationsAbortController = new AbortController();
                }
                const shouldShowInitialLoading =
                    !append && !this.hasLoadedConversations && this.conversations.length === 0;
                if (shouldShowInitialLoading) {
                    this.isLoadingConversations = true;
                }

                const offset = append ? this.conversations.length : 0;
                const response = await window.api.get(`/api/v1/lxmf/conversations`, {
                    params: {
                        ...this.buildConversationQueryParams(),
                        limit: this.pageSize,
                        offset: offset,
                    },
                    signal: this.conversationsAbortController.signal,
                });

                const newConversations = response.data.conversations;
                if (append) {
                    this.conversations = [...this.conversations, ...newConversations];
                } else {
                    this.conversations = newConversations;
                }

                for (const conversation of newConversations) {
                    if (!conversation?.destination_hash) continue;
                    const existingPeer = this.peers[conversation.destination_hash] || {};
                    let displayName = conversation.display_name ?? existingPeer.display_name;
                    if (
                        displayName === "Anonymous Peer" &&
                        existingPeer.display_name &&
                        existingPeer.display_name !== "Anonymous Peer"
                    ) {
                        displayName = existingPeer.display_name;
                    }
                    this.peers[conversation.destination_hash] = {
                        ...existingPeer,
                        destination_hash: conversation.destination_hash,
                        display_name: displayName,
                        custom_display_name: conversation.custom_display_name ?? existingPeer.custom_display_name,
                        contact_image: conversation.contact_image ?? existingPeer.contact_image,
                        lxmf_user_icon: conversation.lxmf_user_icon ?? existingPeer.lxmf_user_icon,
                        updated_at: conversation.updated_at ?? existingPeer.updated_at,
                        is_tracking: conversation.is_tracking ?? existingPeer.is_tracking,
                    };
                }

                this.hasLoadedConversations = true;
                this.hasMoreConversations = newConversations.length === this.pageSize;
            } catch (e) {
                if (window.api.isCancel?.(e)) return;
                console.log(e);
            } finally {
                this.isLoadingConversations = false;
                this.isLoadingMore = false;
            }
        },
        async loadConversationPins() {
            try {
                const response = await window.api.get("/api/v1/lxmf/conversation-pins");
                this.pinnedPeerHashes = response.data.peer_hashes || [];
            } catch (e) {
                console.log(e);
            }
        },
        async onToggleConversationPin(destinationHash) {
            try {
                const response = await window.api.post("/api/v1/lxmf/conversation-pins/toggle", {
                    destination_hash: destinationHash,
                });
                this.pinnedPeerHashes = response.data.peer_hashes || [];
            } catch (e) {
                ToastUtils.error(this.$t("messages.failed_toggle_pin"));
                console.log(e);
            }
        },
        peerHashFromMessage(msg) {
            return msg.is_incoming ? msg.source_hash : msg.destination_hash;
        },
        onOutboundMessageCreated(msg) {
            const peerHash = this.peerHashFromMessage(msg);
            const idx = this.conversations.findIndex((c) => c.destination_hash === peerHash);
            if (idx !== -1) {
                const conv = this.conversations[idx];
                conv.latest_message_preview = msg.content;
                conv.latest_message_title = msg.title;
                conv.latest_message_created_at = msg.timestamp;
                conv.updated_at = new Date(msg.timestamp * 1000).toISOString();
            } else {
                const peer = this.peers[peerHash];
                this.conversations.unshift({
                    destination_hash: peerHash,
                    display_name: peer?.display_name ?? this.selectedPeer?.display_name ?? "Anonymous Peer",
                    custom_display_name: peer?.custom_display_name ?? this.selectedPeer?.custom_display_name ?? null,
                    contact_image: peer?.contact_image ?? null,
                    lxmf_user_icon: peer?.lxmf_user_icon ?? null,
                    is_unread: false,
                    is_tracking: peer?.is_tracking ?? false,
                    failed_messages_count: 0,
                    has_attachments: false,
                    latest_message_preview: msg.content,
                    latest_message_title: msg.title,
                    latest_message_created_at: msg.timestamp,
                    updated_at: new Date(msg.timestamp * 1000).toISOString(),
                    is_contact: false,
                });
                this.resolvePeerDisplayName(peerHash);
            }
        },
        onOutboundMessageStateUpdated(msg) {
            const peerHash = this.peerHashFromMessage(msg);
            const conv = this.conversations.find((c) => c.destination_hash === peerHash);
            if (!conv) return;

            const oldState = conv._lastKnownState;
            const newState = msg.state;
            conv._lastKnownState = newState;

            if (newState === "failed" && oldState !== "failed") {
                conv.failed_messages_count = (conv.failed_messages_count || 0) + 1;
            } else if (oldState === "failed" && newState !== "failed") {
                conv.failed_messages_count = Math.max(0, (conv.failed_messages_count || 1) - 1);
            }
        },
        async resolvePeerDisplayName(peerHash) {
            try {
                const response = await window.api.get(`/api/v1/lxmf/conversations`, {
                    params: { search: peerHash, limit: 1 },
                });
                const results = response.data.conversations;
                if (!results || results.length === 0) return;

                const fresh = results[0];
                if (fresh.destination_hash !== peerHash) return;

                const conv = this.conversations.find((c) => c.destination_hash === peerHash);
                if (conv) {
                    if (fresh.display_name && fresh.display_name !== "Anonymous Peer") {
                        conv.display_name = fresh.display_name;
                    }
                    if (fresh.custom_display_name) conv.custom_display_name = fresh.custom_display_name;
                    if (fresh.contact_image) conv.contact_image = fresh.contact_image;
                    if (fresh.lxmf_user_icon) conv.lxmf_user_icon = fresh.lxmf_user_icon;
                    if (fresh.is_contact) conv.is_contact = fresh.is_contact;
                }

                if (this.selectedPeer && this.selectedPeer.destination_hash === peerHash) {
                    const incomingName = fresh.display_name;
                    const shouldUpdate =
                        incomingName &&
                        incomingName !== "Anonymous Peer" &&
                        incomingName !== this.selectedPeer.display_name;
                    if (shouldUpdate) {
                        this.selectedPeer = {
                            ...this.selectedPeer,
                            display_name: incomingName,
                            custom_display_name: fresh.custom_display_name ?? this.selectedPeer.custom_display_name,
                        };
                    }
                }
            } catch {
                // non-critical
            }
        },
        async getFolders() {
            try {
                const response = await window.api.get("/api/v1/lxmf/folders");
                this.folders = response.data;
            } catch (e) {
                console.error("Failed to load folders", e);
            }
        },
        async onCreateFolder(name) {
            try {
                await window.api.post("/api/v1/lxmf/folders", { name });
                await this.getFolders();
                ToastUtils.success(this.$t("messages.folder_created"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_create_folder"));
            }
        },
        async onRenameFolder({ id, name }) {
            try {
                await window.api.patch(`/api/v1/lxmf/folders/${id}`, { name });
                await this.getFolders();
                ToastUtils.success(this.$t("messages.folder_renamed"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_rename_folder"));
            }
        },
        async onDeleteFolder(id) {
            try {
                await window.api.delete(`/api/v1/lxmf/folders/${id}`);
                if (this.selectedFolderId === id) {
                    this.selectedFolderId = null;
                }
                await this.getFolders();
                await this.getConversations();
                ToastUtils.success(this.$t("messages.folder_deleted"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_delete_folder"));
            }
        },
        async onMoveToFolder({ peer_hashes, folder_id }) {
            try {
                // Treat 0 as null (Uncategorized) for the backend
                const targetFolderId = folder_id === 0 ? null : folder_id;
                await window.api.post("/api/v1/lxmf/conversations/move-to-folder", {
                    peer_hashes,
                    folder_id: targetFolderId,
                });
                await this.getConversations();
                ToastUtils.success(this.$t("messages.moved_to_folder"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_move_folder"));
            }
        },
        async onBulkMarkAsRead(destination_hashes) {
            try {
                await window.api.post("/api/v1/lxmf/conversations/bulk-mark-as-read", {
                    destination_hashes,
                });
                await this.getConversations();
                ToastUtils.success(this.$t("messages.marked_read"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_mark_read"));
            }
        },
        async onBulkDelete(destination_hashes) {
            try {
                const confirmed = await DialogUtils.confirm(
                    "Are you sure you want to delete these conversations? All messages will be lost.",
                    "Delete Conversations"
                );
                if (!confirmed) return;

                await window.api.post("/api/v1/lxmf/conversations/bulk-delete", {
                    destination_hashes,
                });
                await this.getConversations();
                ToastUtils.success(this.$t("messages.conversations_deleted"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_delete_conversations"));
            }
        },
        async onExportFolders() {
            try {
                const response = await window.api.get("/api/v1/lxmf/folders/export");
                const data = JSON.stringify(response.data, null, 2);
                const blob = new Blob([data], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `meshchatx-folders-${new Date().toISOString().slice(0, 10)}.json`;
                a.click();
                URL.revokeObjectURL(url);
            } catch {
                ToastUtils.error(this.$t("messages.failed_export_folders"));
            }
        },
        async onImportFolders() {
            const input = document.createElement("input");
            input.type = "file";
            input.accept = ".json";
            input.onchange = async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = async (re) => {
                    try {
                        const data = JSON.parse(re.target.result);
                        await window.api.post("/api/v1/lxmf/folders/import", data);
                        await this.getFolders();
                        await this.getConversations();
                        ToastUtils.success(this.$t("messages.folders_imported"));
                    } catch {
                        ToastUtils.error(this.$t("messages.failed_import_folders"));
                    }
                };
                reader.readAsText(file);
            };
            input.click();
        },
        onFolderClick(folderId) {
            this.selectedFolderId = folderId;
            this.requestConversationsRefresh();
        },
        async loadMoreConversations() {
            if (this.isLoadingMore || !this.hasMoreConversations) return;
            this.isLoadingMore = true;
            await this.getConversations(true);
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
            if (this.selectedFolderId !== null) {
                params.folder_id = this.selectedFolderId;
            }
            return params;
        },
        updatePeerFromAnnounce: function (announce) {
            const existing = this.peers[announce.destination_hash] || {};
            const merged = { ...existing, ...announce };
            if (
                announce.display_name === "Anonymous Peer" &&
                existing.display_name &&
                existing.display_name !== "Anonymous Peer"
            ) {
                merged.display_name = existing.display_name;
            }
            this.peers[announce.destination_hash] = merged;
        },
        onUpdatePeerTracking({ destination_hash, is_tracking }) {
            if (this.peers[destination_hash]) {
                this.peers[destination_hash].is_tracking = is_tracking;
            }
            if (this.selectedPeer && this.selectedPeer.destination_hash === destination_hash) {
                this.selectedPeer.is_tracking = is_tracking;
            }
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
        onPeersSearchChanged(term) {
            this.peersSearchTerm = term;
            if (this.peersRefreshTimeout) {
                clearTimeout(this.peersRefreshTimeout);
            }
            this.peersRefreshTimeout = setTimeout(() => {
                this.getLxmfDeliveryAnnounces();
            }, 500);
        },
        openIngestPaperMessageModal() {
            this.ingestUri = "";
            this.isIngestModalOpen = true;
        },
        async openIngestScannerModal() {
            this.ingestScannerError = null;
            this.isIngestScannerModalOpen = true;
            await this.$nextTick();
            await this.startIngestScanner();
        },
        closeIngestScannerModal() {
            this.isIngestScannerModalOpen = false;
            this.stopIngestScanner();
        },
        async startIngestScanner() {
            if (!this.cameraSupported) {
                this.ingestScannerError = this.$t("messages.camera_not_supported");
                return;
            }
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "environment" },
                    audio: false,
                });
                this.ingestScannerStream = stream;
                const video = this.$refs.ingestScannerVideo;
                if (!video) {
                    this.ingestScannerError = this.$t("messages.camera_failed");
                    this.stopIngestScanner();
                    return;
                }
                video.srcObject = stream;
                await video.play();
                this.detectIngestQrLoop();
            } catch (e) {
                this.ingestScannerError = this.describeCameraError(e);
            }
        },
        detectIngestQrLoop() {
            if (!this.isIngestScannerModalOpen) return;
            const video = this.$refs.ingestScannerVideo;
            if (!video || video.readyState < 2) {
                this.ingestScannerAnimationFrame = requestAnimationFrame(() => this.detectIngestQrLoop());
                return;
            }
            const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
            detector
                .detect(video)
                .then((barcodes) => {
                    const qr = barcodes?.[0]?.rawValue?.trim();
                    if (!qr) {
                        this.ingestScannerAnimationFrame = requestAnimationFrame(() => this.detectIngestQrLoop());
                        return;
                    }
                    if (!/^lxm(a|f)?:\/\//i.test(qr)) {
                        ToastUtils.error(this.$t("messages.invalid_qr_uri"));
                        this.ingestScannerAnimationFrame = requestAnimationFrame(() => this.detectIngestQrLoop());
                        return;
                    }
                    this.ingestUri = qr;
                    this.closeIngestScannerModal();
                    this.ingestPaperMessage();
                })
                .catch(() => {
                    this.ingestScannerAnimationFrame = requestAnimationFrame(() => this.detectIngestQrLoop());
                });
        },
        stopIngestScanner() {
            if (this.ingestScannerAnimationFrame) {
                cancelAnimationFrame(this.ingestScannerAnimationFrame);
                this.ingestScannerAnimationFrame = null;
            }
            if (this.ingestScannerStream) {
                this.ingestScannerStream.getTracks().forEach((track) => track.stop());
                this.ingestScannerStream = null;
            }
        },
        describeCameraError(error) {
            const name = error?.name || "";
            if (name === "NotAllowedError" || name === "SecurityError") {
                return this.$t("messages.camera_permission_denied");
            }
            if (name === "NotFoundError" || name === "DevicesNotFoundError") {
                return this.$t("messages.camera_not_found");
            }
            return this.$t("messages.camera_failed");
        },
        async pasteFromClipboard() {
            try {
                this.ingestUri = await navigator.clipboard.readText();
            } catch {
                ToastUtils.error(this.$t("messages.failed_read_clipboard"));
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
                ToastUtils.error(this.$t("messages.failed_send_ingest"));
            }
        },
        getHashPopoutValue() {
            const hash = window.location.hash || "";
            const match = hash.match(/popout=([^&]+)/);
            return match ? decodeURIComponent(match[1]) : null;
        },
        openMobileCompose() {
            this.mobileComposeAddress = "";
            this.isMobileComposeModalOpen = true;
        },
        openIngestFromMobileCompose() {
            this.isMobileComposeModalOpen = false;
            this.openIngestPaperMessageModal();
        },
        async submitMobileCompose() {
            const raw = this.mobileComposeAddress.trim();
            if (!raw) {
                return;
            }
            this.isMobileComposeModalOpen = false;
            this.mobileComposeAddress = "";
            await this.onComposeNewMessage(raw.replace(/^lxmf@/, ""));
        },
    },
};
</script>
