<template>
    <div class="flex flex-1 min-w-0 h-full overflow-hidden">
        <MessagesSidebar
            v-if="!isPopoutMode"
            :class="{ 'hidden sm:flex': destinationHash }"
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
        />

        <div
            class="flex-col flex-1 overflow-hidden min-w-0 bg-gradient-to-br from-white via-slate-50 to-slate-100 dark:from-zinc-950 dark:via-zinc-900 dark:to-zinc-900/80"
            :class="destinationHash ? 'flex' : 'hidden sm:flex'"
        >
            <!-- messages tab -->
            <ConversationViewer
                ref="conversation-viewer"
                :config="config"
                :my-lxmf-address-hash="config?.lxmf_address_hash"
                :selected-peer="selectedPeer"
                :conversations="conversations"
                @update:selected-peer="onPeerClick"
                @update-peer-tracking="onUpdatePeerTracking"
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

            config: null,
            hasLoadedConversations: false,
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
        GlobalEmitter.off("refresh-conversations", this.requestConversationsRefresh);
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);
        GlobalEmitter.on("compose-new-message", this.onComposeNewMessage);

        this.getConfig();
        this.getConversations();
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
                const offset = append ? Object.keys(this.peers).length : 0;
                const response = await window.axios.get(`/api/v1/announces`, {
                    params: {
                        aspect: "lxmf.delivery",
                        limit: this.pageSize,
                        offset: offset,
                        search: this.peersSearchTerm,
                    },
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
        async getConversations(append = false) {
            try {
                const shouldShowInitialLoading =
                    !append && !this.hasLoadedConversations && this.conversations.length === 0;
                if (shouldShowInitialLoading) {
                    this.isLoadingConversations = true;
                }

                const offset = append ? this.conversations.length : 0;
                const response = await window.axios.get(`/api/v1/lxmf/conversations`, {
                    params: {
                        ...this.buildConversationQueryParams(),
                        limit: this.pageSize,
                        offset: offset,
                    },
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
                    this.peers[conversation.destination_hash] = {
                        ...existingPeer,
                        destination_hash: conversation.destination_hash,
                        display_name: conversation.display_name ?? existingPeer.display_name,
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
                console.log(e);
            } finally {
                this.isLoadingConversations = false;
                this.isLoadingMore = false;
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
                const response = await window.axios.get(`/api/v1/lxmf/conversations`, {
                    params: { search: peerHash, limit: 1 },
                });
                const results = response.data.conversations;
                if (!results || results.length === 0) return;

                const fresh = results[0];
                if (fresh.destination_hash !== peerHash) return;

                const conv = this.conversations.find((c) => c.destination_hash === peerHash);
                if (conv) {
                    if (fresh.display_name) conv.display_name = fresh.display_name;
                    if (fresh.custom_display_name) conv.custom_display_name = fresh.custom_display_name;
                    if (fresh.contact_image) conv.contact_image = fresh.contact_image;
                    if (fresh.lxmf_user_icon) conv.lxmf_user_icon = fresh.lxmf_user_icon;
                    if (fresh.is_contact) conv.is_contact = fresh.is_contact;
                }

                if (this.selectedPeer && this.selectedPeer.destination_hash === peerHash) {
                    if (fresh.display_name && fresh.display_name !== this.selectedPeer.display_name) {
                        this.selectedPeer = {
                            ...this.selectedPeer,
                            display_name: fresh.display_name,
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
                const response = await window.axios.get("/api/v1/lxmf/folders");
                this.folders = response.data;
            } catch (e) {
                console.error("Failed to load folders", e);
            }
        },
        async onCreateFolder(name) {
            try {
                await window.axios.post("/api/v1/lxmf/folders", { name });
                await this.getFolders();
                ToastUtils.success(this.$t("messages.folder_created"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_create_folder"));
            }
        },
        async onRenameFolder({ id, name }) {
            try {
                await window.axios.patch(`/api/v1/lxmf/folders/${id}`, { name });
                await this.getFolders();
                ToastUtils.success(this.$t("messages.folder_renamed"));
            } catch {
                ToastUtils.error(this.$t("messages.failed_rename_folder"));
            }
        },
        async onDeleteFolder(id) {
            try {
                await window.axios.delete(`/api/v1/lxmf/folders/${id}`);
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
                await window.axios.post("/api/v1/lxmf/conversations/move-to-folder", {
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
                await window.axios.post("/api/v1/lxmf/conversations/bulk-mark-as-read", {
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

                await window.axios.post("/api/v1/lxmf/conversations/bulk-delete", {
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
                const response = await window.axios.get("/api/v1/lxmf/folders/export");
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
                        await window.axios.post("/api/v1/lxmf/folders/import", data);
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
            this.peers[announce.destination_hash] = { ...existing, ...announce };
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
    },
};
</script>
