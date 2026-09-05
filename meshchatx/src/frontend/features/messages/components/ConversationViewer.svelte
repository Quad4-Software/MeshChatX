<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import "../lib/conversationViewerGlobals.js";
    import { onMount, tick, untrack } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import DialogUtils from "../../../js/DialogUtils.js";
    import DownloadUtils from "../../../js/DownloadUtils.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import GlobalState from "../../../js/GlobalState.js";
    import MicrophoneRecorder from "../../../js/MicrophoneRecorder.js";
    import NotificationUtils from "../../../js/NotificationUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import WebSocketConnection from "../../../js/WebSocketConnection.js";
    import { copyTextToClipboard } from "../../../js/clipboardUtils.js";
    import { LXMF_REACTION_EMOJIS } from "../../../js/lxmfReactions.js";
    import { createOutboundQueue } from "../../../js/outboundSendQueue.js";
    import { offWsEvent, onWsEvent } from "../../../js/registries/wsEventRegistry.js";
    import { t } from "../../../js/i18n.js";
    import { fromNow } from "../../../libs/datetime.js";
    import ConversationComposer from "./ConversationComposer.svelte";
    import ConversationEmptyState from "./ConversationEmptyState.svelte";
    import ConversationImageLightbox from "./ConversationImageLightbox.svelte";
    import ConversationMessageContextMenu from "./ConversationMessageContextMenu.svelte";
    import ConversationMessageEntry, { type MessageDisplayEntry } from "./ConversationMessageEntry.svelte";
    import ConversationMessageListVirtual from "./ConversationMessageListVirtual.svelte";
    import ConversationPeerHeader from "./ConversationPeerHeader.svelte";
    import ConversationRawMessageModal from "./ConversationRawMessageModal.svelte";
    import ConversationStrangerBanner from "./ConversationStrangerBanner.svelte";
    import PaperMessageModal from "./modals/PaperMessageModal.svelte";
    import ShareContactModal from "./modals/ShareContactModal.svelte";
    import TelemetryHistoryModal from "./telemetry/TelemetryHistoryModal.svelte";
    import {
        lxmfContactResolvedIcon,
        lxmfDeliveryDestinationHexFromContact,
    } from "../lib/lxmf/contactDisplay.js";
    import { isTelemetryOnly } from "../lib/conversationMessageHelpers.js";
    import {
        deleteWsMessage,
        fetchConversationPage,
        oldestMessageId,
        applyWsMessage,
        prependConversationPage,
        updateWsMessage,
        visibleConversationItems,
    } from "../lib/conversationViewerMessages.js";
    import { loadPeerNetworkInfo, peerPathNeedsRefresh, runPeerPathAction } from "../lib/conversationViewerPath.js";
    import {
        buildOutboundJob,
        cancelOutbound,
        executeOutboundJob,
        optimisticMessage,
        type ComposeAudio,
        type OutboundJob,
    } from "../lib/conversationViewerSend.js";
    import { loadDraft, saveDraft } from "../lib/conversationDrafts.js";
    import { buildDisplayGroupsNewestFirst } from "../lib/conversationDisplayGroups.js";
    import { isNearBottom, scrollContainerToBottom, shouldLoadPreviousMessages } from "../lib/conversationScroll.js";
    import { createConversationViewerActions } from "../lib/conversationViewerActions.js";
    import type { LxmfMessage, ViewerChatItem, ViewerPathSnapshot } from "../lib/conversationViewerCtx.js";
    import { sameHash } from "../lib/conversationViewerCtx.js";
    import { displayGroupsOldestFirst, MIN_VIRTUAL_DISPLAY_GROUPS } from "../lib/messageListVirtual.js";
    import { MESSAGE_BODY_MAX_DISPLAY_CHARS } from "../lib/constants.js";
    import type { Conversation, MessagesConfig, Peer } from "../lib/types.js";
    import type { MessageChatItem } from "../lib/viewerActions.js";

    export type ConversationViewerApi = {
        markConversationAsRead: (conversation: Conversation | Peer, opts?: { force?: boolean }) => void | Promise<void>;
    };

    type Props = {
        config?: MessagesConfig | null;
        myLxmfAddressHash?: string;
        selectedPeer?: Peer | null;
        conversations?: Conversation[];
        isPopout?: boolean;
        onupdateSelectedPeer?: (peer: Peer | null) => void;
        onupdatePeerTracking?: (payload: { destination_hash: string; is_tracking: boolean }) => void;
        onclose?: () => void;
        onreloadConversations?: () => void;
        onoutboundComposeEnqueued?: (payload: Record<string, unknown>) => void;
        onviewerReady?: (api: ConversationViewerApi | null) => void;
    };

    let {
        config = null,
        myLxmfAddressHash = "",
        selectedPeer = null,
        conversations = [],
        isPopout = false,
        onupdateSelectedPeer,
        onupdatePeerTracking: _onupdatePeerTracking,
        onclose,
        onreloadConversations,
        onoutboundComposeEnqueued,
        onviewerReady,
    }: Props = $props();

    let messagesScroll: HTMLDivElement | undefined = $state();
    let fileInput: HTMLInputElement | undefined = $state();
    let chatItems = $state.raw<ViewerChatItem[]>([]);
    let isLoadingPrevious = $state(false);
    let hasMorePrevious = $state(true);
    let autoScrollOnNewMessage = $state(true);
    let messagesViewportReady = $state(true);
    let newMessageText = $state("");
    let newMessageDeliveryMethod = $state<string | null>(null);
    let newMessageImages = $state.raw<File[]>([]);
    let newMessageImageUrls = $state.raw<string[]>([]);
    let newMessageFiles = $state.raw<File[]>([]);
    let newMessageAudio = $state<ComposeAudio | null>(null);
    let replyingTo = $state<ViewerChatItem | null>(null);
    let peerPathSnapshot = $state<ViewerPathSnapshot | null>(null);
    let peerPathLoading = $state(false);
    let peerPathWarming = $state(false);
    let selectedPeerLxmfStampInfo = $state<Record<string, unknown> | null>(null);
    let selectedPeerSignalMetrics = $state<Record<string, unknown> | null>(null);
    let pathfinderInProgress = $state(false);
    let composeAddress = $state("");
    let isComposeInputFocused = $state(false);
    let selectedComposeSuggestionIndex = $state(-1);
    let contacts = $state.raw<Array<Record<string, unknown>>>([]);
    let isStrangerPeer = $state(false);
    let strangerBannerDismissed = $state(false);
    let isRawMessageModalOpen = $state(false);
    let rawMessageData = $state<LxmfMessage>({});
    let messageListVirtual: ConversationMessageListVirtual | undefined = $state();
    let imageLightboxUrl = $state("");
    let imageLightboxGallery = $state.raw<string[] | null>(null);
    let imageLightboxItems = $state.raw<MessageChatItem[] | null>(null);
    let imageLightboxIndex = $state(0);
    let contextMenu = $state({
        show: false,
        x: 0,
        y: 0,
        chatItem: null as ViewerChatItem | null,
        justOpened: false,
    });
    let isRecordingAudioAttachment = $state(false);
    let audioAttachmentRecordingDuration = $state("0:00");
    let audioRecorder: {
        start: () => Promise<boolean>;
        stop: () => Promise<Blob | ArrayBuffer>;
        codec2Mode?: string;
    } | null = null;
    let audioRecorderCodec: "opus" | "codec2" | null = null;
    let audioRecordingStartedAt = 0;
    let audioRecordingTimer: ReturnType<typeof setInterval> | null = null;
    let generatedPaperMessageUri = $state<string | null>(null);
    let isPaperMessageResultModalOpen = $state(false);
    let isShareContactModalOpen = $state(false);
    let contactsSearch = $state("");
    let isTelemetryHistoryModalOpen = $state(false);
    let showTelemetryInChat = $state(false);
    let requestSequence = 0;
    let openedPeerHash = "";
    let openedIdentityKey = "";
    let loadPreviousPromise: Promise<void> | null = null;

    const selectedHash = $derived(String(selectedPeer?.destination_hash || ""));
    const identityKey = $derived(String(config?.identity_hash || myLxmfAddressHash || "_"));
    const selectedMessages = $derived(
        visibleConversationItems(chatItems, selectedHash, showTelemetryInChat)
    );
    const filteredContacts = $derived.by(() => {
        const q = contactsSearch.trim().toLowerCase();
        if (!q) return contacts;
        return contacts.filter((contact) => {
            const name = String(contact.name || "").toLowerCase();
            const hash = String(contact.remote_identity_hash || "").toLowerCase();
            const lxmf = String(contact.lxmf_address || "").toLowerCase();
            return name.includes(q) || hash.includes(q) || lxmf.includes(q);
        });
    });
    const selectedPeerTelemetryItems = $derived.by(() => {
        if (!selectedHash) return [];
        const peer = selectedHash.toLowerCase();
        return chatItems
            .filter((chatItem) => {
                if (chatItem.type !== "lxmf_message") return false;
                const src = String(chatItem.lxmf_message.source_hash || "").toLowerCase();
                const dst = String(chatItem.lxmf_message.destination_hash || "").toLowerCase();
                if (src !== peer && dst !== peer) return false;
                return isTelemetryOnly(chatItem.lxmf_message);
            })
            .slice()
            .reverse();
    });
    const actions = $derived(
        createConversationViewerActions({
            chatItems: selectedMessages as unknown as MessageChatItem[],
            selectedPeer,
            conversations,
            myLxmfAddressHash,
            messageFontSize: Number(config?.message_font_size) || 14,
            audioAttachmentUrls: Object.fromEntries(
                selectedMessages
                    .filter((item) => item.lxmf_message.hash && item.lxmf_message.fields?.audio)
                    .map((item) => [
                        String(item.lxmf_message.hash),
                        `/api/v1/lxmf-messages/attachment/${item.lxmf_message.hash}/audio`,
                    ])
            ),
            openImage,
            onMessageContextMenu: (event, item, suppressToggle) =>
                openContextMenu(event, item as ViewerChatItem, suppressToggle),
            onChatItemClick: toggleChatItemActions,
            openReactionPicker,
            replyToMessage,
            retrySendingMessage: (item) => {
                contextMenu.chatItem = item as ViewerChatItem;
                void retryMessage();
            },
            cancelSendingMessage: (item) => {
                contextMenu.chatItem = item as ViewerChatItem;
                void cancelSending();
            },
            deleteChatItem: (item) => {
                contextMenu.chatItem = item as ViewerChatItem;
                void deleteMessage();
            },
            showRawMessage,
            scrollToMessage,
            copyText: copyTextToClipboard,
            downloadMessageImage,
            downloadLxmfFileAttachment: (item, index, name) => downloadFile(item as ViewerChatItem, index, name),
            addContact: addSharedContact,
        })
    );
    const groupsNewestFirst = $derived(
        buildDisplayGroupsNewestFirst(selectedMessages, (item) =>
            actions.canMergeImageIntoImageStrip(item as MessageChatItem)
        )
    );
    const groups = $derived(displayGroupsOldestFirst(groupsNewestFirst) as MessageDisplayEntry[]);
    const useVirtualMessageList = $derived(groups.length >= MIN_VIRTUAL_DISPLAY_GROUPS);
    const canSendMessage = $derived(
        Boolean(
            selectedPeer &&
            (newMessageText.trim() || newMessageImages.length || newMessageFiles.length || newMessageAudio)
        )
    );
    const hasFailedOrCancelledMessages = $derived(
        selectedMessages.some(
            (item) => item.is_outbound && ["failed", "cancelled"].includes(String(item.lxmf_message.state || ""))
        )
    );
    const composePlaceholder = $derived(
        newMessageDeliveryMethod === "direct"
            ? t("messages.compose_hint_direct")
            : newMessageDeliveryMethod === "propagated"
              ? t("messages.compose_hint_propagated")
              : newMessageDeliveryMethod === "opportunistic"
                ? t("messages.compose_hint_opportunistic")
                : t("messages.compose_hint_automatic")
    );
    const latestConversations = $derived(
        conversations
            .filter((conversation) => Boolean(conversation.destination_hash))
            .slice(0, 4)
            .map((conversation) => {
                const icon = (conversation as Record<string, unknown>).lxmf_user_icon;
                return {
                    ...conversation,
                    destination_hash: String(conversation.destination_hash),
                    lxmf_user_icon: icon && typeof icon === "object" ? icon : null,
                };
            })
    );
    const composeSuggestions = $derived.by(() => {
        if (!isComposeInputFocused) return [];
        const search = composeAddress.trim().toLowerCase();
        const seen: string[] = [];
        const suggestions: Array<{ hash: string; name: string; icon: string; type: string }> = [];
        for (const contact of contacts) {
            const hash = String(contact.remote_identity_hash || "");
            const name = String(contact.name || hash);
            if (
                hash &&
                !seen.includes(hash) &&
                (!search || name.toLowerCase().includes(search) || hash.includes(search))
            ) {
                suggestions.push({ hash, name, icon: "account", type: "contact" });
                seen.push(hash);
            }
        }
        for (const conversation of conversations) {
            const hash = String(conversation.destination_hash || "");
            const name = String(conversation.custom_display_name || conversation.display_name || hash);
            if (
                hash &&
                !seen.includes(hash) &&
                (!search || name.toLowerCase().includes(search) || hash.includes(search))
            ) {
                suggestions.push({ hash, name, icon: "history", type: "recent" });
                seen.push(hash);
            }
        }
        return suggestions.slice(0, 10);
    });
    const isSelectedPeerBlocked = $derived(
        Array.isArray(GlobalState.blockedDestinations) &&
            GlobalState.blockedDestinations.some((entry: unknown) => {
                const hash =
                    typeof entry === "string"
                        ? entry
                        : String((entry as Record<string, unknown>)?.destination_hash || "");
                return sameHash(hash, selectedHash);
            })
    );
    const outboundQueue = createOutboundQueue((job: OutboundJob) => executeSendJob(job));
    const viewerApi: ConversationViewerApi = { markConversationAsRead };

    $effect(() => {
        const peerHash = selectedHash;
        const nextIdentity = identityKey;
        untrack(() => void openConversation(peerHash, nextIdentity));
    });

    $effect(() => {
        if (selectedHash) {
            saveDraft(selectedHash, identityKey, newMessageText);
        }
    });

    onMount(() => {
        onviewerReady?.(viewerApi);
        const wsHandlers: Array<[string, (payload: Record<string, unknown>) => void | Promise<void>]> = [
            ["announce", onAnnounce],
            ["lxmf.delivery", onDelivery],
            ["lxmf_message_created", onCreated],
            ["lxmf_message_state_updated", onStateUpdated],
            ["lxmf_message_deleted", onDeleted],
            ["lxm.generate_paper_uri.result", onPaperResult],
        ];
        for (const [type, handler] of wsHandlers) onWsEvent(type, handler);
        GlobalEmitter.on("websocket-reconnected", softResync);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        void fetchContacts();
        return () => {
            onviewerReady?.(null);
            for (const [type, handler] of wsHandlers) offWsEvent(type, handler);
            GlobalEmitter.off("websocket-reconnected", softResync);
            GlobalEmitter.off("identity-switched", onIdentitySwitched);
            if (openedPeerHash) saveDraft(openedPeerHash, openedIdentityKey, newMessageText);
            releaseImageUrls();
            if (newMessageAudio?.audio_preview_url) URL.revokeObjectURL(newMessageAudio.audio_preview_url);
            if (audioRecordingTimer) clearInterval(audioRecordingTimer);
        };
    });

    async function openConversation(peerHash: string, nextIdentity: string) {
        if (openedPeerHash) saveDraft(openedPeerHash, openedIdentityKey, newMessageText);
        openedPeerHash = peerHash;
        openedIdentityKey = nextIdentity;
        requestSequence += 1;
        loadPreviousPromise = null;
        isLoadingPrevious = false;
        chatItems = [];
        hasMorePrevious = true;
        autoScrollOnNewMessage = true;
        messagesViewportReady = !peerHash;
        peerPathSnapshot = null;
        selectedPeerLxmfStampInfo = null;
        selectedPeerSignalMetrics = null;
        strangerBannerDismissed = false;
        newMessageText = peerHash ? loadDraft(peerHash, nextIdentity) : "";
        isStrangerPeer = Boolean(peerHash) && !contacts.some((c) => sameHash(c.remote_identity_hash, peerHash));
        if (!peerHash) return;
        void refreshPeerNetwork(true);
        void markConversationAsRead(selectedPeer || { destination_hash: peerHash }, { force: true });
        await loadPrevious();
        await tick();
        scrollMessagesToBottom();
        messagesViewportReady = true;
    }

    async function loadPrevious() {
        if (!selectedHash || !hasMorePrevious || loadPreviousPromise) return;
        const peerHash = selectedHash;
        const seq = requestSequence;
        const anchorHeight = messagesScroll?.scrollHeight || 0;
        const anchorTop = messagesScroll?.scrollTop || 0;
        isLoadingPrevious = true;
        const pending = (async () => {
            try {
                const page = await fetchConversationPage(
                    window.api,
                    peerHash,
                    myLxmfAddressHash,
                    oldestMessageId(chatItems, peerHash)
                );
                if (seq !== requestSequence || !sameHash(peerHash, selectedHash)) return;
                const merged = prependConversationPage(chatItems, page.items);
                chatItems = merged.items;
                hasMorePrevious = page.hasMore && merged.added > 0;
                await tick();
                if (messagesScroll && anchorHeight > 0) {
                    messagesScroll.scrollTop = anchorTop + messagesScroll.scrollHeight - anchorHeight;
                }
            } catch {
                hasMorePrevious = false;
            } finally {
                if (loadPreviousPromise === pending) {
                    isLoadingPrevious = false;
                    loadPreviousPromise = null;
                }
            }
        })();
        loadPreviousPromise = pending;
        await pending;
    }

    function onMessagesScroll() {
        autoScrollOnNewMessage = isNearBottom(messagesScroll);
        if (shouldLoadPreviousMessages(messagesScroll)) void loadPrevious();
    }

    async function scrollMessagesToBottom() {
        autoScrollOnNewMessage = true;
        await tick();
        requestAnimationFrame(() => scrollContainerToBottom(messagesScroll));
    }

    async function softResync() {
        if (!selectedHash) return;
        try {
            const page = await fetchConversationPage(window.api, selectedHash, myLxmfAddressHash, null);
            let next = chatItems;
            for (const item of page.items) {
                next = applyWsMessage(next, item.lxmf_message, selectedHash, myLxmfAddressHash).items;
            }
            chatItems = next;
            await refreshPeerNetwork(false);
        } catch {
            return;
        }
    }

    async function applyLiveMessage(message: LxmfMessage) {
        const result = applyWsMessage(chatItems, message, selectedHash, myLxmfAddressHash);
        if (!result.changed) return;
        chatItems = result.items;
        if (result.incoming) {
            const conversation = conversations.find((candidate) => sameHash(candidate.destination_hash, selectedHash));
            await markConversationAsRead(conversation || selectedPeer || { destination_hash: selectedHash }, {
                force: true,
            });
        }
        if (autoScrollOnNewMessage) void scrollMessagesToBottom();
    }

    async function onDelivery(payload: Record<string, unknown>) {
        await applyLiveMessage((payload.lxmf_message || {}) as LxmfMessage);
        void refreshPeerNetwork(false);
    }

    async function onCreated(payload: Record<string, unknown>) {
        await applyLiveMessage((payload.lxmf_message || {}) as LxmfMessage);
        void refreshPeerNetwork(false);
    }

    function onStateUpdated(payload: Record<string, unknown>) {
        chatItems = updateWsMessage(chatItems, (payload.lxmf_message || {}) as LxmfMessage);
    }

    function onDeleted(payload: Record<string, unknown>) {
        chatItems = deleteWsMessage(chatItems, payload.hash);
    }

    async function onAnnounce(payload: Record<string, unknown>) {
        const announce = payload.announce as Record<string, unknown> | undefined;
        if (sameHash(announce?.destination_hash, selectedHash)) await refreshPeerNetwork(true);
    }

    function onIdentitySwitched(payload: Record<string, unknown>) {
        const nextIdentity = String(payload.identity_hash || identityKey);
        void openConversation(selectedHash, nextIdentity);
    }

    async function refreshPeerNetwork(warm: boolean) {
        if (!selectedHash) return;
        const hash = selectedHash;
        peerPathLoading = true;
        peerPathWarming = warm;
        try {
            const info = await loadPeerNetworkInfo(window.api, hash, warm);
            if (!sameHash(hash, selectedHash)) return;
            peerPathSnapshot = info.path;
            selectedPeerLxmfStampInfo = info.stampInfo;
            selectedPeerSignalMetrics = info.signalMetrics;
        } catch {
            peerPathSnapshot = null;
        } finally {
            if (sameHash(hash, selectedHash)) {
                peerPathLoading = false;
                peerPathWarming = false;
            }
        }
    }

    async function runPathAction(action: "quick" | "force" | "drop_then_request") {
        if (!selectedHash || pathfinderInProgress) return;
        pathfinderInProgress = true;
        try {
            peerPathSnapshot = await runPeerPathAction(window.api, selectedHash, action);
            ToastUtils.success(
                action === "force" && peerPathSnapshot?.path
                    ? t("nomadnet.path_finder_found")
                    : t("nomadnet.path_finder_request_sent")
            );
        } catch {
            ToastUtils.error(t("nomadnet.path_finder_failed"));
        } finally {
            pathfinderInProgress = false;
        }
    }

    let pingInFlight = false;

    async function pingSelectedPeer() {
        if (!selectedHash || pingInFlight) return;
        if (selectedHash.length !== 32 || !/^[0-9a-fA-F]+$/.test(selectedHash)) {
            await DialogUtils.alert(t("messages.invalid_destination_hash_format"));
            return;
        }
        pingInFlight = true;
        const pingToastKey = "conversation-ping";
        ToastUtils.loading(t("messages.ping_in_progress"), 0, pingToastKey);
        try {
            const response = await window.api.post(
                `/api/v1/ping/${selectedHash}/lxmf.delivery`,
                {},
                { params: { timeout: 30 } }
            );
            const pingResult = response.data.ping_result || {};
            const rttMilliseconds = ((Number(pingResult.rtt) || 0) * 1000).toFixed(3);
            const info = [
                t("messages.ping_reply_from", { hash: selectedHash }),
                t("messages.duration", { duration: `${rttMilliseconds} ms` }),
                t("messages.hops_there", { count: pingResult.hops_there }),
                t("messages.hops_back", { count: pingResult.hops_back }),
            ];
            if (pingResult.quality != null) {
                info.push(t("messages.signal_quality", { quality: pingResult.quality }));
            }
            if (pingResult.rssi != null) {
                info.push(t("messages.rssi_val", { rssi: pingResult.rssi }));
            }
            if (pingResult.snr != null) {
                info.push(t("messages.snr_val", { snr: pingResult.snr }));
            }
            await DialogUtils.alert(info.join("\n"));
        } catch (error) {
            const message =
                (error as { response?: { data?: { message?: string } } })?.response?.data?.message ||
                t("messages.ping_failed");
            await DialogUtils.alert(message);
        } finally {
            ToastUtils.dismiss(pingToastKey);
            pingInFlight = false;
        }
    }

    async function banishSelectedPeer() {
        if (!selectedHash) return;
        if (!(await DialogUtils.confirm(t("messages.banish_confirm")))) return;
        try {
            await window.api.post("/api/v1/blocked-destinations", { destination_hash: selectedHash });
            GlobalEmitter.emit("block-status-changed");
            await DialogUtils.alert(t("messages.user_banished"));
        } catch {
            await DialogUtils.alert(t("messages.failed_banish_user"));
        }
    }

    async function unbanishSelectedPeer() {
        if (!selectedHash) return;
        try {
            await window.api.delete(`/api/v1/blocked-destinations/${selectedHash}`);
            GlobalEmitter.emit("block-status-changed");
            await DialogUtils.alert(t("banishment.banishment_lifted"));
        } catch {
            await DialogUtils.alert(t("banishment.failed_lift_banishment"));
        }
    }

    async function deleteMessageHistory() {
        if (!selectedHash) return;
        if (!(await DialogUtils.confirm(t("messages.delete_history_confirm")))) return;
        try {
            await window.api.delete(`/api/v1/lxmf-messages/conversation/${selectedHash}`);
            onreloadConversations?.();
            onclose?.();
        } catch {
            await DialogUtils.alert(t("messages.failed_delete_history"));
        }
    }

    async function openShareContactModal() {
        try {
            const response = await window.api.get("/api/v1/telephone/contacts");
            contacts = response.data?.contacts ?? (Array.isArray(response.data) ? response.data : []);
            if (contacts.length === 0) {
                ToastUtils.info(t("messages.no_contacts_telephone"));
                return;
            }
            contactsSearch = "";
            isShareContactModalOpen = true;
        } catch {
            ToastUtils.error(t("messages.failed_load_contacts"));
        }
    }

    function shareContact(contact: Record<string, unknown>) {
        let sharedString = `Contact: ${contact.name} <${contact.remote_identity_hash}>`;
        if (contact.lxmf_address) sharedString += ` [LXMF: ${contact.lxmf_address}]`;
        if (contact.lxst_address) sharedString += ` [LXST: ${contact.lxst_address}]`;
        newMessageText = sharedString;
        isShareContactModalOpen = false;
        void sendMessage();
    }

    function viewLocationOnMap(coords: { latitude: number; longitude: number }) {
        const params = new URLSearchParams({
            lat: String(coords.latitude),
            lon: String(coords.longitude),
            zoom: "15",
        });
        window.location.hash = `#/map?${params.toString()}`;
    }

    async function sendMessage() {
        if (!canSendMessage || !selectedHash) return;
        try {
            const job = await buildOutboundJob({
                destinationHash: selectedHash,
                deliveryMethod: newMessageDeliveryMethod,
                text: newMessageText,
                files: newMessageFiles,
                images: newMessageImages,
                audio: newMessageAudio,
                replyToHash: replyingTo?.lxmf_message.hash || null,
                replyQuotedContent: replyingTo?.lxmf_message.content || null,
                myLxmfAddressHash,
                confirmOversized: (size) =>
                    DialogUtils.confirm(t("messages.send_oversized_confirm", { size: formatBytes(size) })),
            });
            if (!job) return;
            const pending = optimisticMessage(job, peerPathNeedsRefresh(peerPathSnapshot));
            chatItems = chatItems.concat({
                type: "lxmf_message",
                is_outbound: true,
                lxmf_message: pending,
            });
            onoutboundComposeEnqueued?.({
                peerHash: job.destinationHash,
                previewText: job.text,
                title: "",
                fields: job.fields,
                pendingHash: job.pendingHash,
            });
            clearCompose();
            outboundQueue.enqueue(job);
            void scrollMessagesToBottom();
        } catch (error) {
            const message = (error as Error)?.message || t("messages.failed_to_send");
            await DialogUtils.alert(message);
        }
    }

    async function executeSendJob(job: OutboundJob) {
        try {
            const sent = await executeOutboundJob({
                api: window.api,
                job,
                pathSnapshot: peerPathSnapshot,
                propagationHash: (GlobalState.config as Record<string, unknown> | undefined)
                    ?.lxmf_preferred_propagation_node_destination_hash,
            });
            let next = chatItems.filter((item) => item.lxmf_message.hash !== job.pendingHash);
            for (const message of sent) {
                next = applyWsMessage(next, message, job.destinationHash, job.myLxmfAddressHash).items;
            }
            chatItems = next;
            void refreshPeerNetwork(false);
        } catch (error) {
            chatItems = chatItems.map((item) =>
                item.lxmf_message.hash === job.pendingHash
                    ? {
                          ...item,
                          lxmf_message: {
                              ...item.lxmf_message,
                              state: "failed",
                              _pendingPathfinding: false,
                          },
                      }
                    : item
            );
            await DialogUtils.alert(
                (error as { response?: { data?: { message?: string } } }).response?.data?.message ||
                    t("messages.failed_to_send")
            );
        }
    }

    function clearCompose() {
        newMessageText = "";
        releaseImageUrls();
        newMessageImages = [];
        newMessageImageUrls = [];
        newMessageFiles = [];
        if (newMessageAudio?.audio_preview_url) URL.revokeObjectURL(newMessageAudio.audio_preview_url);
        newMessageAudio = null;
        replyingTo = null;
        if (fileInput) fileInput.value = "";
    }

    function releaseImageUrls() {
        for (const url of newMessageImageUrls) URL.revokeObjectURL(url);
    }

    function addImage(file: File) {
        if (!file.type.startsWith("image/")) return;
        newMessageImages = newMessageImages.concat(file);
        newMessageImageUrls = newMessageImageUrls.concat(URL.createObjectURL(file));
    }

    function removeImage(index: number) {
        const url = newMessageImageUrls[index];
        if (url) URL.revokeObjectURL(url);
        newMessageImages = newMessageImages.filter((_, candidate) => candidate !== index);
        newMessageImageUrls = newMessageImageUrls.filter((_, candidate) => candidate !== index);
    }

    function onPaste(event: ClipboardEvent) {
        const files = Array.from(event.clipboardData?.files || []).filter((file) => file.type.startsWith("image/"));
        if (files.length > 0) {
            event.preventDefault();
            for (const file of files) addImage(file);
        }
    }

    async function startAudioRecording(args: { codec: string; mode?: string }) {
        if (isRecordingAudioAttachment) return;
        if (
            newMessageAudio &&
            !(await DialogUtils.confirm("An audio recording is already attached. A new recording will replace it."))
        )
            return;
        try {
            if (args.codec === "codec2") {
                const Recorder = (
                    globalThis as typeof globalThis & {
                        Codec2MicrophoneRecorder: new () => {
                            codec2Mode: string;
                            start: () => Promise<boolean>;
                            stop: () => Promise<ArrayBuffer>;
                        };
                    }
                ).Codec2MicrophoneRecorder;
                const recorder = new Recorder();
                recorder.codec2Mode = args.mode || "1200";
                audioRecorder = recorder;
                audioRecorderCodec = "codec2";
            } else {
                audioRecorder = new MicrophoneRecorder();
                audioRecorderCodec = "opus";
            }
            isRecordingAudioAttachment = await audioRecorder.start();
            if (!isRecordingAudioAttachment) throw new Error(t("messages.failed_start_recording"));
            audioRecordingStartedAt = Date.now();
            audioAttachmentRecordingDuration = "0:00";
            audioRecordingTimer = setInterval(() => {
                audioAttachmentRecordingDuration = formatDuration(Date.now() - audioRecordingStartedAt);
            }, 1000);
        } catch (error) {
            audioRecorder = null;
            audioRecorderCodec = null;
            await DialogUtils.alert((error as Error).message);
        }
    }

    async function stopAudioRecording() {
        if (audioRecordingTimer) clearInterval(audioRecordingTimer);
        audioRecordingTimer = null;
        if (!isRecordingAudioAttachment || !audioRecorder) return;
        isRecordingAudioAttachment = false;
        try {
            const audio = await audioRecorder.stop();
            if (audioRecorderCodec === "codec2") {
                const encoded = new Uint8Array(audio as ArrayBuffer);
                const mode = audioRecorder.codec2Mode || "1200";
                const Codec2Lib = (
                    globalThis as typeof globalThis & {
                        Codec2Lib: {
                            runDecode: (mode: string, bytes: Uint8Array) => Promise<ArrayBuffer>;
                            rawToWav: (bytes: ArrayBuffer) => Promise<ArrayBuffer>;
                        };
                    }
                ).Codec2Lib;
                const decoded = await Codec2Lib.runDecode(mode, encoded);
                const wav = await Codec2Lib.rawToWav(decoded);
                const preview = new Blob([wav], { type: "audio/wav" });
                newMessageAudio = {
                    audio_mode: mode === "3200" ? 0x09 : 0x04,
                    audio_blob: new Blob([encoded]),
                    audio_preview_url: URL.createObjectURL(preview),
                };
            } else {
                const blob = audio as Blob;
                if (blob.size > 0) {
                    newMessageAudio = {
                        audio_mode: 0x10,
                        audio_blob: blob,
                        audio_preview_url: URL.createObjectURL(blob),
                    };
                }
            }
        } catch (error) {
            await DialogUtils.alert((error as Error).message);
        } finally {
            audioRecorder = null;
            audioRecorderCodec = null;
        }
    }

    async function markConversationAsRead(
        conversation: Conversation | Peer,
        { force = false }: { force?: boolean } = {}
    ) {
        if (!conversation?.destination_hash) return;
        const wasUnread = conversation.is_unread === true;
        if (!wasUnread && !force) return;
        conversation.is_unread = false;
        try {
            await window.api.post(`/api/v1/lxmf/conversations/${conversation.destination_hash}/mark-as-read`);
            GlobalEmitter.emit("notifications-changed");
            NotificationUtils.clearMessageNotifications(conversation.destination_hash);
            if (wasUnread && GlobalState.unreadConversationsCount > 0) GlobalState.unreadConversationsCount -= 1;
        } catch {
            conversation.is_unread = wasUnread;
        }
    }

    async function fetchContacts() {
        try {
            const response = await window.api.get("/api/v1/telephone/contacts");
            contacts = response.data?.contacts ?? (Array.isArray(response.data) ? response.data : []);
            isStrangerPeer =
                Boolean(selectedHash) &&
                !contacts.some((contact) => sameHash(contact.remote_identity_hash, selectedHash));
        } catch {
            contacts = [];
        }
    }

    async function addStrangerAsContact() {
        if (!selectedHash) return;
        try {
            await window.api.post("/api/v1/telephone/contacts", {
                name: selectedPeer?.display_name || selectedHash,
                remote_identity_hash: String(selectedPeer?.identity_hash || selectedHash),
                lxmf_address: selectedHash,
            });
            isStrangerPeer = false;
            onreloadConversations?.();
            ToastUtils.success(t("contacts.contact_added"));
        } catch {
            ToastUtils.error(t("messages.failed_add_contact"));
        }
    }

    async function addSharedContact(name?: string, hash?: string, lxmfAddress?: string, lxstAddress?: string) {
        const remoteHash = String(hash || "");
        if (!remoteHash) return;
        try {
            await window.api.post("/api/v1/telephone/contacts", {
                name: name || remoteHash,
                remote_identity_hash: remoteHash,
                lxmf_address: lxmfAddress || remoteHash,
                lxst_address: lxstAddress || undefined,
            });
            onreloadConversations?.();
            ToastUtils.success(t("contacts.contact_added"));
        } catch {
            ToastUtils.error(t("messages.failed_add_contact"));
        }
    }

    async function updateCustomDisplayName() {
        if (!selectedHash) return;
        const displayName = await DialogUtils.prompt(t("messages.enter_display_name"));
        if (displayName == null) return;
        try {
            await window.api.post(`/api/v1/destination/${selectedHash}/custom-display-name/update`, {
                display_name: displayName,
            });
            onupdateSelectedPeer?.({ ...selectedPeer, custom_display_name: displayName });
            onreloadConversations?.();
        } catch {
            await DialogUtils.alert(t("messages.failed_update_display_name"));
        }
    }

    function openContextMenu(event: MouseEvent, item: ViewerChatItem, suppressToggle = false) {
        event.preventDefault();
        event.stopPropagation();
        if (!suppressToggle) {
            toggleChatItemActions(item as unknown as MessageChatItem);
        }
        contextMenu = {
            show: true,
            x: event.clientX,
            y: event.clientY,
            chatItem: item,
            justOpened: true,
        };
        queueMicrotask(() => {
            contextMenu.justOpened = false;
        });
    }

    function toggleChatItemActions(item: MessageChatItem) {
        const hash = item.lxmf_message.hash;
        chatItems = chatItems.map((candidate) =>
            candidate.lxmf_message.hash === hash
                ? ({
                      ...candidate,
                      is_actions_expanded: !item.is_actions_expanded,
                  } as ViewerChatItem)
                : candidate
        );
    }

    function replyToMessage(item: MessageChatItem) {
        replyingTo = item as ViewerChatItem;
        contextMenu.show = false;
        requestAnimationFrame(() => document.getElementById("message-input")?.focus());
    }

    function showRawMessage(item: MessageChatItem) {
        rawMessageData = item.lxmf_message as LxmfMessage;
        isRawMessageModalOpen = true;
        contextMenu.show = false;
    }

    function openReactionPicker(item: MessageChatItem) {
        const hash = item.lxmf_message.hash;
        const bubble = hash ? document.getElementById(`message-${hash}`) : null;
        const bounds = bubble?.getBoundingClientRect();
        contextMenu = {
            show: true,
            x: bounds?.right ?? window.innerWidth / 2,
            y: bounds?.bottom ?? window.innerHeight / 2,
            chatItem: item as ViewerChatItem,
            justOpened: false,
        };
    }

    function scrollToMessage(hash: string) {
        const item = chatItems.find((candidate) => sameHash(candidate.lxmf_message.hash, hash));
        if (!item) {
            void DialogUtils.alert(t("messages.message_not_found_in_cache"));
            return;
        }
        const element = document.getElementById(`message-${hash}`);
        if (element) {
            element.scrollIntoView({ behavior: "smooth", block: "center" });
            return;
        }
        if (useVirtualMessageList) {
            messageListVirtual?.scrollToMessageHash(hash);
        }
    }

    function openImage(src: string, gallery: string[] = [], items: MessageChatItem[] = []) {
        const nextGallery = gallery.length > 1 ? gallery.slice() : null;
        imageLightboxGallery = nextGallery;
        imageLightboxItems = items.length ? items.slice() : null;
        imageLightboxIndex = nextGallery ? Math.max(0, nextGallery.indexOf(src)) : 0;
        imageLightboxUrl = nextGallery?.[imageLightboxIndex] || src;
    }

    function navigateImageLightbox(delta: number) {
        if (!imageLightboxGallery?.length) return;
        imageLightboxIndex = (imageLightboxIndex + delta + imageLightboxGallery.length) % imageLightboxGallery.length;
        imageLightboxUrl = imageLightboxGallery[imageLightboxIndex];
    }

    function closeImageLightbox() {
        imageLightboxUrl = "";
        imageLightboxGallery = null;
        imageLightboxItems = null;
        imageLightboxIndex = 0;
    }

    async function downloadMessageImage(item: MessageChatItem) {
        const hash = item.lxmf_message.hash;
        if (!hash) return;
        const response = await window.api.get(`/api/v1/lxmf-messages/attachment/${hash}/image`, {
            responseType: "arraybuffer",
        });
        const type = String(item.lxmf_message.fields?.image?.image_type || "png").replace(/^image\//, "");
        await DownloadUtils.downloadFromApiResponse(response, `image-${hash.slice(0, 8)}.${type}`);
    }

    async function sendReaction(emoji: string) {
        const item = contextMenu.chatItem;
        contextMenu.show = false;
        if (!item?.lxmf_message.hash || !selectedHash) return;
        try {
            const response = await window.api.post("/api/v1/lxmf-messages/reactions", {
                destination_hash: selectedHash,
                target_message_hash: item.lxmf_message.hash,
                emoji,
            });
            const reaction = response.data?.lxmf_message as LxmfMessage | undefined;
            if (reaction) chatItems = applyWsMessage(chatItems, reaction, selectedHash, myLxmfAddressHash).items;
        } catch {
            ToastUtils.error(t("messages.reaction_send_failed"));
        }
    }

    async function deleteMessage() {
        const item = contextMenu.chatItem;
        contextMenu.show = false;
        if (!item?.lxmf_message.hash) return;
        if (!(await DialogUtils.confirm(t("messages.delete_message_confirm")))) return;
        if (!item.lxmf_message.hash.startsWith("pending-")) {
            await window.api.delete(`/api/v1/lxmf-messages/${item.lxmf_message.hash}`);
        }
        chatItems = deleteWsMessage(chatItems, item.lxmf_message.hash);
    }

    async function retryMessage() {
        const item = contextMenu.chatItem;
        contextMenu.show = false;
        if (!item) return;
        newMessageText = String(item.lxmf_message.content || "");
        replyingTo = item.lxmf_message.reply_to_hash
            ? chatItems.find((candidate) => sameHash(candidate.lxmf_message.hash, item.lxmf_message.reply_to_hash)) ||
              null
            : null;
        await deleteMessage();
        await sendMessage();
    }

    async function cancelSending() {
        const item = contextMenu.chatItem;
        contextMenu.show = false;
        const hash = String(item?.lxmf_message.hash || "");
        if (!hash) return;
        if (hash.startsWith("pending-")) {
            outboundQueue.cancelJob({ pendingHash: hash });
            chatItems = deleteWsMessage(chatItems, hash);
            return;
        }
        const updated = await cancelOutbound(window.api, hash);
        if (updated) chatItems = updateWsMessage(chatItems, updated);
    }

    async function downloadFile(item: ViewerChatItem, index: number, name: string) {
        const hash = item.lxmf_message.hash;
        if (!hash) return;
        const response = await window.api.get(`/api/v1/lxmf-messages/attachment/${hash}/file`, {
            params: { file_index: index },
            responseType: "arraybuffer",
        });
        await DownloadUtils.downloadFromApiResponse(response, name || "download");
    }

    function formatBytes(bytes: number): string {
        if (!bytes) return "0 B";
        const units = ["B", "KB", "MB"];
        const index = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
        return `${(bytes / 1024 ** index).toFixed(index ? 1 : 0)} ${units[index]}`;
    }

    function formatDuration(milliseconds: number): string {
        const seconds = Math.max(0, Math.floor(milliseconds / 1000));
        return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
    }

    function formatConversationTime(value: unknown): string {
        return value ? fromNow(value as string) : "";
    }

    function composeEnter() {
        if (navigator.userAgent.match(/Android|iPhone|iPad|iPod/i)) {
            newMessageText += "\n";
        } else {
            void sendMessage();
        }
    }

    function handleComposeAddress() {
        const suggestion = composeSuggestions[selectedComposeSuggestionIndex];
        const hash = suggestion?.hash || composeAddress.trim().replace(/[^a-fA-F0-9]/g, "");
        if (hash.length !== 32) {
            void DialogUtils.alert(t("common.invalid_address"));
            return;
        }
        composeAddress = "";
        GlobalEmitter.emit("compose-new-message", hash.toLowerCase());
    }

    function onPaperResult(payload: Record<string, unknown>) {
        if (payload.status === "success" && typeof payload.uri === "string") {
            generatedPaperMessageUri = payload.uri;
            isPaperMessageResultModalOpen = true;
        } else if (payload.message) {
            ToastUtils.error(String(payload.message));
        }
    }

    function generatePaperMessage() {
        if (!selectedHash || !canSendMessage) return;
        WebSocketConnection.send(
            JSON.stringify({
                type: "lxm.generate_paper_uri",
                destination_hash: selectedHash,
                content: newMessageText,
            })
        );
    }
</script>

{#if selectedPeer}
    <div class="relative flex h-full min-h-0 flex-col overflow-hidden bg-sem-canvas">
        <ConversationPeerHeader
            selectedPeer={selectedPeer as never}
            compactPeerActions={false}
            {hasFailedOrCancelledMessages}
            selectedPeerPath={(peerPathSnapshot?.path || null) as never}
            {peerPathSnapshot}
            {peerPathLoading}
            {peerPathWarming}
            selectedPeerSignalMetrics={selectedPeerSignalMetrics as never}
            selectedPeerLxmfStampInfo={selectedPeerLxmfStampInfo as never}
            {pathfinderInProgress}
            oneditdisplayname={updateCustomDisplayName}
            oncopyhash={(hash) => void copyTextToClipboard(hash)}
            ondestinationpathclick={(path) => {
                const hops = Number(path?.hops);
                const hopsText =
                    hops === 0 || hops === 1
                        ? `1 ${t("app.hop")}`
                        : `${Number.isFinite(hops) ? hops : "?"} ${t("app.hops_plural")}`;
                const iface =
                    String(path?.next_hop_interface || "").trim() || t("messages.path_hops_unknown_iface");
                let message = t("messages.path_hops_via", { hops: hopsText, iface });
                if (peerPathSnapshot?.path_stale) {
                    message = `${message}\n${t("messages.path_stale_hint")}`;
                }
                if (peerPathSnapshot?.path_unresponsive) {
                    message = `${message}\n${t("messages.path_unresponsive_hint")}`;
                }
                ToastUtils.info(message);
            }}
            onsignalmetricsclick={(metrics) => {
                const detail = metrics as Record<string, unknown> | null;
                void DialogUtils.alert(`RSSI: ${detail?.rssi ?? "?"}dBm\nSNR: ${detail?.snr ?? "?"}dB`);
            }}
            onstampinfoclick={(info) => void DialogUtils.alert(`Stamp cost: ${info?.stamp_cost ?? "?"}`)}
            onconversationdeleted={() => void deleteMessageHistory()}
            onpopout={() => {
                if (!isPopout) location.hash = `#/popout/messages/${selectedHash}`;
            }}
            onretryfailed={() => {
                const failed = selectedMessages.filter((item) =>
                    ["failed", "cancelled"].includes(String(item.lxmf_message.state || ""))
                );
                for (const item of failed) {
                    contextMenu.chatItem = item;
                    void retryMessage();
                }
            }}
            onopentelemetryhistory={() => {
                isTelemetryHistoryModalOpen = true;
            }}
            onstartcall={() => void window.api.post(`/api/v1/telephone/call/${selectedHash}`)}
            onsharecontact={() => void openShareContactModal()}
            onping={() => void pingSelectedPeer()}
            onbanish={() => void banishSelectedPeer()}
            onunbanish={() => void unbanishSelectedPeer()}
            isPeerBlocked={isSelectedPeerBlocked}
            onclose={() => onclose?.()}
            onpathfinderquick={() => void runPathAction("quick")}
            onpathfinderforce={() => void runPathAction("force")}
            onpathfinderdrop={() => void runPathAction("drop_then_request")}
        />

        {#if isStrangerPeer && !strangerBannerDismissed && config?.show_unknown_contact_banner !== false}
            <ConversationStrangerBanner
                onadd={() => void addStrangerAsContact()}
                ondismiss={() => {
                    strangerBannerDismissed = true;
                }}
            />
        {/if}

        <div class="relative flex min-h-0 flex-1 flex-col">
            <div
                id="messages"
                bind:this={messagesScroll}
                class="min-h-0 flex-1 overflow-y-auto bg-sem-canvas"
                data-message-list-mode={useVirtualMessageList ? "virtual" : "flow"}
                aria-busy={!messagesViewportReady}
                onscroll={onMessagesScroll}
            >
                <div class="relative flex min-w-0 flex-col px-3 sm:px-4 {useVirtualMessageList ? '' : 'py-5'}">
                    {#if hasMorePrevious}
                        <button
                            id="load-previous"
                            type="button"
                            class="mx-auto rounded-full border border-sem-border bg-sem-surface px-4 py-2 text-sm text-sem-fg-muted shadow-xs hover:bg-sem-surface-muted {useVirtualMessageList
                                ? 'absolute top-2 left-1/2 z-20 -translate-x-1/2'
                                : 'mb-2'}"
                            disabled={isLoadingPrevious}
                            onclick={() => void loadPrevious()}
                        >
                            {isLoadingPrevious ? t("common.loading") : t("messages.load_previous")}
                        </button>
                    {/if}
                    {#if useVirtualMessageList}
                        <ConversationMessageListVirtual
                            bind:this={messageListVirtual}
                            {groups}
                            getScrollElement={() => messagesScroll}
                            {actions}
                        />
                    {:else}
                        <div class="flex min-w-0 flex-col [overflow-anchor:none]">
                            {#each groups as entry (entry.key)}
                                <ConversationMessageEntry {entry} {actions} />
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>

            {#if !autoScrollOnNewMessage && messagesViewportReady}
                <button
                    type="button"
                    class="absolute bottom-3 left-1/2 z-20 flex size-11 -translate-x-1/2 items-center justify-center rounded-full border border-sem-border bg-sem-surface shadow-md"
                    title={t("messages.scroll_to_bottom")}
                    onclick={() => void scrollMessagesToBottom()}
                >
                    <MaterialDesignIcon iconName="chevron-down" class="size-5" />
                </button>
            {/if}
        </div>

        <ConversationComposer
            bind:text={newMessageText}
            bind:deliveryMethod={newMessageDeliveryMethod}
            imageUrls={newMessageImageUrls}
            files={newMessageFiles}
            audio={newMessageAudio}
            {replyingTo}
            {canSendMessage}
            compactSendLayout={false}
            {isRecordingAudioAttachment}
            {audioAttachmentRecordingDuration}
            isPeerBlocked={isSelectedPeerBlocked}
            {composePlaceholder}
            sendingTooltip={t("messages.send_pathfinding_tooltip")}
            onsend={() => void sendMessage()}
            onaddfiles={() => fileInput?.click()}
            onaddimage={addImage}
            onstartrecording={(args) => void startAudioRecording(args)}
            onstoprecording={() => void stopAudioRecording()}
            onremovefile={(file) => {
                newMessageFiles = newMessageFiles.filter((candidate) => candidate !== file);
            }}
            onremoveimage={removeImage}
            onremoveaudio={() => {
                if (newMessageAudio?.audio_preview_url) URL.revokeObjectURL(newMessageAudio.audio_preview_url);
                newMessageAudio = null;
            }}
            oncancelreply={() => {
                replyingTo = null;
            }}
            onpaste={onPaste}
            onenter={composeEnter}
            onshiftenter={() => {
                newMessageText += "\n";
            }}
            onsendpapercompose={generatePaperMessage}
        />

        <input
            bind:this={fileInput}
            type="file"
            multiple
            class="hidden"
            onchange={(event) => {
                newMessageFiles = newMessageFiles.concat(Array.from(event.currentTarget.files || []));
            }}
        />
    </div>
{:else}
    <ConversationEmptyState
        {latestConversations}
        bind:composeAddress
        bind:isComposeInputFocused
        {composeSuggestions}
        {selectedComposeSuggestionIndex}
        formatTimeAgo={formatConversationTime}
        oncompose={() => document.getElementById("compose-input")?.focus()}
        onsync={() => GlobalEmitter.emit("sync-propagation-node")}
        oncopyaddress={() => void copyTextToClipboard(myLxmfAddressHash)}
        onidentities={() => {
            location.hash = "#/identities";
        }}
        onselectpeer={(peer) => onupdateSelectedPeer?.(peer as Peer)}
        oncomposeenter={handleComposeAddress}
        oncomposeup={() => {
            selectedComposeSuggestionIndex =
                selectedComposeSuggestionIndex > 0 ? selectedComposeSuggestionIndex - 1 : composeSuggestions.length - 1;
        }}
        oncomposedown={() => {
            selectedComposeSuggestionIndex =
                selectedComposeSuggestionIndex < composeSuggestions.length - 1 ? selectedComposeSuggestionIndex + 1 : 0;
        }}
        oncomposebblur={() =>
            setTimeout(() => {
                isComposeInputFocused = false;
                selectedComposeSuggestionIndex = -1;
            }, 200)}
        onselectsuggestion={(suggestion) => {
            composeAddress = suggestion.hash;
            isComposeInputFocused = false;
            selectedComposeSuggestionIndex = -1;
            handleComposeAddress();
        }}
    />
{/if}

<ConversationImageLightbox
    url={imageLightboxUrl}
    gallery={imageLightboxGallery}
    index={imageLightboxIndex}
    onclose={closeImageLightbox}
    onnavigate={navigateImageLightbox}
    ondownload={() => {
        const item = imageLightboxItems?.[imageLightboxIndex] || imageLightboxItems?.[0];
        if (item) void downloadMessageImage(item);
    }}
/>

<ConversationMessageContextMenu
    show={contextMenu.show}
    x={contextMenu.x}
    y={contextMenu.y}
    justOpened={contextMenu.justOpened}
    openedFromBubble
    canCopy={Boolean(contextMenu.chatItem?.lxmf_message.content)}
    canReact={!contextMenu.chatItem?.lxmf_message.is_reaction}
    hasImage={Boolean(contextMenu.chatItem?.lxmf_message.fields?.image)}
    canCancelSend={Boolean(
        contextMenu.chatItem?.is_outbound &&
        ["sending", "generating", "outbound"].includes(String(contextMenu.chatItem?.lxmf_message.state || ""))
    )}
    canRetry={Boolean(
        contextMenu.chatItem?.is_outbound &&
        ["failed", "cancelled"].includes(String(contextMenu.chatItem?.lxmf_message.state || ""))
    )}
    reactionEmojis={LXMF_REACTION_EMOJIS}
    onreply={() => {
        replyingTo = contextMenu.chatItem;
        contextMenu.show = false;
    }}
    oncopy={() => {
        void copyTextToClipboard(String(contextMenu.chatItem?.lxmf_message.content || ""));
        contextMenu.show = false;
    }}
    onreact={(emoji) => void sendReaction(emoji)}
    onviewraw={() => {
        rawMessageData = contextMenu.chatItem?.lxmf_message || {};
        isRawMessageModalOpen = true;
        contextMenu.show = false;
    }}
    oncancelsend={() => void cancelSending()}
    onretry={() => void retryMessage()}
    ondelete={() => void deleteMessage()}
    onclose={() => {
        contextMenu.show = false;
    }}
/>

<ConversationRawMessageModal
    open={isRawMessageModalOpen}
    {rawMessageData}
    rawMessageJsonPreview={JSON.stringify(rawMessageData, null, 2)}
    isBodyOversized={String(rawMessageData.content || "").length > MESSAGE_BODY_MAX_DISPLAY_CHARS}
    bodyCharCount={String(rawMessageData.content || "").length}
    hasStoredPath={rawMessageData.path_hops_at_send != null || Boolean(rawMessageData.path_interface_at_send)}
    onclose={() => {
        isRawMessageModalOpen = false;
    }}
    oncopyhash={(hash) => void copyTextToClipboard(hash)}
    oncopycontent={() => void copyTextToClipboard(String(rawMessageData.content || ""))}
/>

{#if isPaperMessageResultModalOpen}
    <PaperMessageModal
        initialUri={generatedPaperMessageUri}
        recipientHash={selectedHash}
        onclose={() => {
            isPaperMessageResultModalOpen = false;
            generatedPaperMessageUri = null;
        }}
    />
{/if}

<ShareContactModal
    show={isShareContactModalOpen}
    bind:search={contactsSearch}
    contacts={filteredContacts as never}
    resolveIcon={(contact) => lxmfContactResolvedIcon(contact, conversations)}
    destinationHex={lxmfDeliveryDestinationHexFromContact}
    onclose={() => {
        isShareContactModalOpen = false;
    }}
    onshare={(contact) => shareContact(contact as Record<string, unknown>)}
/>

<TelemetryHistoryModal
    open={isTelemetryHistoryModalOpen}
    telemetryItems={selectedPeerTelemetryItems as never}
    {showTelemetryInChat}
    formatTimeAgo={(value) => fromNow(value as never)}
    gradientIdSuffix={selectedHash || "peer"}
    onopenchange={(open) => {
        isTelemetryHistoryModalOpen = open;
    }}
    onclose={() => {
        isTelemetryHistoryModalOpen = false;
    }}
    onshowtelemetrychange={(show) => {
        showTelemetryInChat = show;
    }}
    onlocationclick={viewLocationOnMap}
/>
