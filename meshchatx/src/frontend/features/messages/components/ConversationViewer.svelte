<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import "../lib/conversationViewerGlobals.js";
    import { onMount, tick, untrack } from "svelte";
    import DialogUtils from "../../../js/DialogUtils.js";
    import DownloadUtils from "../../../js/DownloadUtils.js";
    import GlobalEmitter from "../../../js/GlobalEmitter.js";
    import GlobalState from "../../../js/GlobalState.js";
    import NotificationUtils from "../../../js/NotificationUtils.js";
    import ToastUtils from "../../../js/ToastUtils.js";
    import WebSocketConnection from "../../../js/WebSocketConnection.js";
    import { copyTextToClipboard } from "../../../js/clipboardUtils.js";
    import { createOutboundQueue } from "../../../js/outboundSendQueue.js";
    import { offWsEvent, onWsEvent } from "../../../js/registries/wsEventRegistry.js";
    import { t } from "../../../js/i18n.js";
    import ConversationViewerEmptyHost from "./ConversationViewerEmptyHost.svelte";
    import ConversationViewerHeaderHost from "./ConversationViewerHeaderHost.svelte";
    import type { MessageDisplayEntry } from "./ConversationMessageEntry.svelte";
    import ConversationViewerListPane from "./ConversationViewerListPane.svelte";
    import ConversationViewerComposerHost from "./ConversationViewerComposerHost.svelte";
    import ConversationViewerModalsBridge from "./ConversationViewerModalsBridge.svelte";
    import { loadTranslatorLanguages, translateText, type LangOption } from "../lib/conversationTranslate.js";
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
        banishPeerDestination,
        deletePeerConversationHistory,
        pingPeerDestination,
        unbanishPeerDestination,
    } from "../lib/conversationViewerPeerOps.js";
    import {
        cancelOutbound,
        executeOutboundJob,
        optimisticMessage,
        type OutboundJob,
    } from "../lib/conversationViewerSend.js";
    import { loadDraft, saveDraft } from "../lib/conversationDrafts.js";
    import { buildDisplayGroupsNewestFirst } from "../lib/conversationDisplayGroups.js";
    import { isNearBottom, scrollContainerToBottom, shouldLoadPreviousMessages } from "../lib/conversationScroll.js";
    import { createConversationViewerActions } from "../lib/conversationViewerActions.js";
    import { latestConversationCards, buildAudioAttachmentUrlMap } from "../lib/conversationViewerUi.js";
    import {
        openContextMenu as openContextMenuFn,
        toggleChatItemActions as toggleChatItemActionsFn,
        replyToMessage as replyToMessageFn,
        showRawMessage as showRawMessageFn,
        openReactionPicker as openReactionPickerFn,
        scrollToMessage as scrollToMessageFn,
    } from "../lib/conversationViewerShellHandlers.js";
    import {
        sendReactionToMessage,
        deleteMessageItem,
        cancelOutboundMessageItem,
        downloadMessageImageAttachment,
        downloadMessageFileAttachment,
        updatePeerCustomDisplayName,
        addStrangerContact,
        addSharedContactEntry,
        generatePaperMessagePayload,
        formatSharedContactString,
        buildMapLocationHash,
        executeOutboundSendJob,
    } from "../lib/conversationViewerMutations.js";
    import {
        markConversationAsRead as markConversationAsReadSession,
        fetchTelephoneContacts,
        filterContactsList,
        filterSelectedPeerTelemetry,
        buildComposeAddressSuggestions,
        formatTimeAgo,
        isPeerBlockedInState,
        prepareOpenConversationState,
        runLoadPreviousPage,
    } from "../lib/conversationViewerSession.js";
    import {
        initialImageLightboxState,
        openImageLightbox as openImageLightboxState,
        navigateImageLightbox as navigateImageLightboxState,
        type ImageLightboxState,
    } from "../lib/conversationViewerLightbox.js";
    import type { LxmfMessage, ViewerChatItem, ViewerPathSnapshot } from "../lib/conversationViewerCtx.js";
    import { sameHash } from "../lib/conversationViewerCtx.js";
    import { displayGroupsOldestFirst, MIN_VIRTUAL_DISPLAY_GROUPS } from "../lib/messageListVirtual.js";
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
        onupdatePeerTracking,
        onclose,
        onreloadConversations,
        onoutboundComposeEnqueued,
        onviewerReady,
    }: Props = $props();

    let messagesScroll: HTMLDivElement | undefined = $state();
    let chatItems = $state.raw<ViewerChatItem[]>([]);
    let isLoadingPrevious = $state(false);
    let hasMorePrevious = $state(true);
    let autoScrollOnNewMessage = $state(true);
    let messagesViewportReady = $state(true);
    let newMessageText = $state("");
    let replyingTo = $state<ViewerChatItem | null>(null);

    let listPane: ConversationViewerListPane | undefined = $state();
    let composerHost: ConversationViewerComposerHost | undefined = $state();
    let translateOptions = $state.raw<LangOption[]>([]);
    let hasTranslator = $state(false);
    let bubbleTranslate = $state({
        open: false,
        targetLang: "en",
        chatItem: null as ViewerChatItem | null,
        working: false,
    });
    let reactionPicker = $state({
        open: false,
        style: "",
        chatItem: null as ViewerChatItem | null,
    });
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
    let imageLightbox = $state(initialImageLightboxState());
    let contextMenu = $state({
        show: false,
        x: 0,
        y: 0,
        chatItem: null as ViewerChatItem | null,
        justOpened: false,
    });
    let audioRecorder: {
        start: () => Promise<boolean>;
        stop: () => Promise<Blob | ArrayBuffer>;
        codec2Mode?: string;
    } | null = null;
    let audioRecorderCodec: "opus" | "codec2" | null = null;
    let audioRecordingStartedAt = 0;
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
    const filteredContacts = $derived(filterContactsList(contacts, contactsSearch));
    const selectedPeerTelemetryItems = $derived(filterSelectedPeerTelemetry(chatItems, selectedHash));
    const actions = $derived(
        createConversationViewerActions({
            chatItems: selectedMessages as unknown as MessageChatItem[],
            selectedPeer,
            conversations,
            myLxmfAddressHash,
            messageFontSize: Number(config?.message_font_size) || 14,
            audioAttachmentUrls: buildAudioAttachmentUrlMap(selectedMessages),
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
            onupdatePeerTracking,
            onSetBubbleMessageShowOriginal: (hash, showOriginal) => {
                chatItems = chatItems.map((candidate) =>
                    candidate.lxmf_message.hash === hash
                        ? {
                              ...candidate,
                              lxmf_message: {
                                  ...candidate.lxmf_message,
                                  _translation: {
                                      ...(candidate.lxmf_message as { _translation?: Record<string, unknown> })
                                          ._translation,
                                      showOriginal,
                                  },
                              },
                          }
                        : candidate
                );
            },
        })
    );
    const groupsNewestFirst = $derived(
        buildDisplayGroupsNewestFirst(selectedMessages, (item) =>
            actions.canMergeImageIntoImageStrip(item as MessageChatItem)
        )
    );
    const groups = $derived(displayGroupsOldestFirst(groupsNewestFirst) as MessageDisplayEntry[]);
    const useVirtualMessageList = $derived(groups.length >= MIN_VIRTUAL_DISPLAY_GROUPS);
    const hasFailedOrCancelledMessages = $derived(
        selectedMessages.some(
            (item) => item.is_outbound && ["failed", "cancelled"].includes(String(item.lxmf_message.state || ""))
        )
    );
    const latestConversations = $derived(latestConversationCards(conversations));
    const composeSuggestions = $derived(
        buildComposeAddressSuggestions(contacts, conversations, composeAddress, isComposeInputFocused)
    );
    const isSelectedPeerBlocked = $derived(isPeerBlockedInState(GlobalState.blockedDestinations, selectedHash));
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
        void loadTranslateOptions();
        return () => {
            onviewerReady?.(null);
            for (const [type, handler] of wsHandlers) offWsEvent(type, handler);
            GlobalEmitter.off("websocket-reconnected", softResync);
            GlobalEmitter.off("identity-switched", onIdentitySwitched);
            if (openedPeerHash) saveDraft(openedPeerHash, openedIdentityKey, newMessageText);
        };
    });

    async function openConversation(peerHash: string, nextIdentity: string) {
        if (openedPeerHash) saveDraft(openedPeerHash, openedIdentityKey, newMessageText);
        openedPeerHash = peerHash;
        openedIdentityKey = nextIdentity;
        requestSequence += 1;
        loadPreviousPromise = null;
        isLoadingPrevious = false;
        const seed = prepareOpenConversationState({
            peerHash,
            nextIdentity,
            contacts,
            loadDraft,
        });
        chatItems = seed.chatItems;
        hasMorePrevious = seed.hasMorePrevious;
        autoScrollOnNewMessage = seed.autoScrollOnNewMessage;
        messagesViewportReady = seed.messagesViewportReady;
        peerPathSnapshot = seed.peerPathSnapshot;
        selectedPeerLxmfStampInfo = seed.selectedPeerLxmfStampInfo;
        selectedPeerSignalMetrics = seed.selectedPeerSignalMetrics;
        strangerBannerDismissed = seed.strangerBannerDismissed;
        newMessageText = seed.newMessageText;
        isStrangerPeer = seed.isStrangerPeer;
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
        isLoadingPrevious = true;
        let pending: Promise<void> | null = null;
        pending = (async () => {
            try {
                const result = await runLoadPreviousPage({
                    api: window.api,
                    peerHash,
                    myLxmfAddressHash,
                    chatItems,
                    requestSequence: seq,
                    currentSelectedHash: selectedHash,
                    messagesScroll,
                    tick,
                });
                if (!result || seq !== requestSequence) return;
                chatItems = result.items;
                hasMorePrevious = result.hasMorePrevious;
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
            /* ignore soft resync errors */
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
        pingInFlight = true;
        try {
            await pingPeerDestination({
                api: window.api,
                destinationHash: selectedHash,
                t,
                DialogUtils,
                ToastUtils,
            });
        } finally {
            pingInFlight = false;
        }
    }

    async function banishSelectedPeer() {
        if (!selectedHash) return;
        await banishPeerDestination({
            api: window.api,
            destinationHash: selectedHash,
            t,
            DialogUtils,
            emitBlockChanged: () => GlobalEmitter.emit("block-status-changed"),
        });
    }

    async function unbanishSelectedPeer() {
        if (!selectedHash) return;
        await unbanishPeerDestination({
            api: window.api,
            destinationHash: selectedHash,
            t,
            DialogUtils,
            emitBlockChanged: () => GlobalEmitter.emit("block-status-changed"),
        });
    }

    async function deleteMessageHistory() {
        if (!selectedHash) return;
        await deletePeerConversationHistory({
            api: window.api,
            destinationHash: selectedHash,
            t,
            DialogUtils,
            onDone: () => {
                onreloadConversations?.();
                onclose?.();
            },
        });
    }

    async function openShareContactModal() {
        contacts = await fetchTelephoneContacts(window.api);
        if (contacts.length === 0) {
            ToastUtils.info(t("messages.no_contacts_telephone"));
            return;
        }
        contactsSearch = "";
        isShareContactModalOpen = true;
    }

    function shareContact(contact) {
        newMessageText = formatSharedContactString(contact);
        isShareContactModalOpen = false;
        void tick().then(() => composerHost?.sendNow?.());
    }

    function viewLocationOnMap(coords) {
        window.location.hash = buildMapLocationHash(coords);
    }

    async function executeSendJob(job: OutboundJob) {
        chatItems = await executeOutboundSendJob({
            api: window.api,
            job,
            peerPathSnapshot,
            chatItems,
            myLxmfAddressHash,
            refreshPeerNetwork,
            DialogUtils,
            t,
            applyWsMessage,
            getPropagationHash: () =>
                (GlobalState.config as Record<string, unknown> | undefined)
                    ?.lxmf_preferred_propagation_node_destination_hash,
        });
    }

    async function markConversationAsRead(
        conversation: Conversation | Peer | { destination_hash?: string; is_unread?: boolean } | null | undefined,
        opts: { force?: boolean } = {}
    ) {
        await markConversationAsReadSession(window.api, conversation, opts);
    }

    async function fetchContacts() {
        contacts = await fetchTelephoneContacts(window.api);
        isStrangerPeer =
            Boolean(selectedHash) &&
            !contacts.some((contact) => sameHash(contact.remote_identity_hash, selectedHash));
    }

    async function addStrangerAsContact() {
        const ok = await addStrangerContact({
            api: window.api,
            destinationHash: selectedHash,
            displayName: selectedPeer?.display_name ? String(selectedPeer.display_name) : null,
            identityHash: selectedPeer?.identity_hash ? String(selectedPeer.identity_hash) : null,
            onSuccess: () => {
                isStrangerPeer = false;
                onreloadConversations?.();
            },
        });
        void ok;
    }

    async function addSharedContact(
        name?: string,
        hash?: string,
        lxmfAddress?: string,
        lxstAddress?: string
    ) {
        await addSharedContactEntry({
            api: window.api,
            name,
            hash,
            lxmfAddress,
            lxstAddress,
            onSuccess: () => onreloadConversations?.(),
        });
    }

    async function updateCustomDisplayName() {
        await updatePeerCustomDisplayName(window.api, selectedHash, (displayName) => {
            onupdateSelectedPeer?.({ ...selectedPeer, custom_display_name: displayName });
            onreloadConversations?.();
        });
    }

    function shellBag() {
        return {
            chatItems,
            setChatItems: (items) => {
                chatItems = items;
            },
            contextMenu,
            setContextMenu: (value) => {
                contextMenu = value;
            },
            reactionPicker,
            setReactionPicker: (value) => {
                reactionPicker = value;
            },
            setReplyingTo: (item) => {
                replyingTo = item;
            },
            setRawMessageData: (data) => {
                rawMessageData = data;
            },
            setIsRawMessageModalOpen: (open) => {
                isRawMessageModalOpen = open;
            },
            useVirtualMessageList,
            listPane,
        };
    }

    function openContextMenu(event: MouseEvent, item: ViewerChatItem, suppressToggle = false) {
        openContextMenuFn(shellBag(), event, item, suppressToggle, toggleChatItemActions);
    }

    function toggleChatItemActions(item: MessageChatItem) {
        toggleChatItemActionsFn(shellBag(), item);
    }

    function replyToMessage(item: MessageChatItem) {
        replyToMessageFn(shellBag(), item);
    }

    function showRawMessage(item: MessageChatItem) {
        showRawMessageFn(shellBag(), item);
    }

    function openReactionPicker(item: MessageChatItem) {
        openReactionPickerFn(shellBag(), item);
    }

    function scrollToMessage(hash: string) {
        scrollToMessageFn(shellBag(), hash);
    }

    function openImage(src: string, gallery: string[] = [], items: MessageChatItem[] = []) {
        imageLightbox = openImageLightboxState(src, gallery, items);
    }

    function navigateImageLightbox(delta: number) {
        imageLightbox = navigateImageLightboxState(imageLightbox, delta);
    }

    function closeImageLightbox() {
        imageLightbox = initialImageLightboxState();
    }

    async function downloadMessageImage(item: MessageChatItem) {
        await downloadMessageImageAttachment(window.api, item);
    }

    async function downloadFile(item: ViewerChatItem, index: number, name: string) {
        await downloadMessageFileAttachment(window.api, item, index, name);
    }

    async function sendReaction(emoji: string, targetItem: ViewerChatItem | null = null) {
        const item = targetItem || contextMenu.chatItem;
        contextMenu.show = false;
        if (!item) return;
        chatItems = await sendReactionToMessage({
            api: window.api,
            destinationHash: selectedHash,
            myLxmfAddressHash,
            emoji,
            targetItem: item,
            currentItems: chatItems,
        });
    }

    async function deleteMessage() {
        const item = contextMenu.chatItem;
        contextMenu.show = false;
        if (!item) return;
        const next = await deleteMessageItem({ api: window.api, item, currentItems: chatItems });
        if (next) chatItems = next;
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
        await composerHost?.sendNow?.();
    }

    async function cancelSending() {
        const item = contextMenu.chatItem;
        contextMenu.show = false;
        if (!item) return;
        chatItems = await cancelOutboundMessageItem({
            api: window.api,
            item,
            currentItems: chatItems,
            outboundQueue,
        });
    }

    function formatConversationTime(value: unknown) {
        return formatTimeAgo(value);
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

    function handleJobCreated(job: OutboundJob, pending: ReturnType<typeof optimisticMessage>) {
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
        outboundQueue.enqueue(job);
        void scrollMessagesToBottom();
    }

    async function confirmBubbleTranslate() {
        const item = bubbleTranslate.chatItem;
        if (!item) return;
        bubbleTranslate.working = true;
        try {
            const result = await translateText(window.api, {
                text: String(item.lxmf_message.content || ""),
                targetLang: bubbleTranslate.targetLang,
            });
            const hash = String(item.lxmf_message.hash || "");
            if (hash && result.translatedText) {
                chatItems = chatItems.map((candidate) =>
                    candidate.lxmf_message.hash === hash
                        ? {
                              ...candidate,
                              lxmf_message: {
                                  ...candidate.lxmf_message,
                                  _translation: { translatedText: result.translatedText, showOriginal: false },
                              },
                          }
                        : candidate
                );
            }
            bubbleTranslate.open = false;
        } catch {
            ToastUtils.error(t("translator.failed_translate"));
        } finally {
            bubbleTranslate.working = false;
        }
    }

    async function loadTranslateOptions() {
        const cfg = (GlobalState.config || {}) as Record<string, unknown>;
        const loaded = await loadTranslatorLanguages(window.api, cfg.libretranslate_url as string | undefined);
        translateOptions = loaded.languages;
        hasTranslator = loaded.hasTranslator;
    }

    function generatePaperMessage() {
        generatePaperMessagePayload(selectedHash, newMessageText);
    }

</script>

{#if selectedPeer}
    <div class="relative flex h-full min-h-0 flex-col overflow-hidden bg-sem-canvas">
        <ConversationViewerHeaderHost
            selectedPeer={selectedPeer as Peer}
            {hasFailedOrCancelledMessages}
            {peerPathSnapshot}
            {peerPathLoading}
            {peerPathWarming}
            {selectedPeerSignalMetrics}
            {selectedPeerLxmfStampInfo}
            {pathfinderInProgress}
            {isPopout}
            oneditdisplayname={updateCustomDisplayName}
            oncopyhash={(hash) => void copyTextToClipboard(hash)}
            ondestinationpathclick={(path) => {
                location.hash = `#/interfaces?highlight=${encodeURIComponent(String((path as { next_hop_interface?: string })?.next_hop_interface || path || ""))}`;
            }}
            onpathfinderquick={() => void runPathAction("quick")}
            onpathfinderforce={() => void runPathAction("force")}
            onpathfinderdrop={() => void runPathAction("drop_then_request")}
            onping={() => void pingSelectedPeer()}
            onstartcall={() => GlobalEmitter.emit("start-call", selectedHash)}
            onsharecontact={() => void openShareContactModal()}
            onopentelemetryhistory={() => {
                isTelemetryHistoryModalOpen = true;
            }}
            onbanish={() => void banishSelectedPeer()}
            onunbanish={() => void unbanishSelectedPeer()}
            onconversationdeleted={() => void deleteMessageHistory()}
            onretryfailed={() => {
                const failed = selectedMessages.find((m) => m.is_outbound && m.lxmf_message.state === "failed");
                if (failed) {
                    contextMenu.chatItem = failed;
                    void retryMessage();
                }
            }}
            onclose={() => onclose?.()}
            onaddstranger={() => void addStrangerAsContact()}
            ondismissstranger={() => {
                isStrangerPeer = false;
            }}
        />

        <ConversationViewerListPane
            bind:messagesScroll
            bind:this={listPane}
            {groups}
            {useVirtualMessageList}
            {hasMorePrevious}
            {isLoadingPrevious}
            {autoScrollOnNewMessage}
            {messagesViewportReady}
            {actions}
            onloadprevious={() => void loadPrevious()}
            onscrolltobottom={() => void scrollMessagesToBottom()}
            onscroll={onMessagesScroll}
        />

        <ConversationViewerComposerHost
            bind:this={composerHost}
            bind:text={newMessageText}
            bind:replyingTo
            {selectedPeer}
            {selectedHash}
            {myLxmfAddressHash}
            {peerPathSnapshot}
            {isSelectedPeerBlocked}
            {translateOptions}
            {hasTranslator}
            onjobCreated={handleJobCreated}
            onsendpapercompose={generatePaperMessage}
            onscrolltobottom={() => void scrollMessagesToBottom()}
        />
    </div>
{:else}
    <ConversationViewerEmptyHost
        {latestConversations}
        bind:composeAddress
        bind:isComposeInputFocused
        {composeSuggestions}
        bind:selectedComposeSuggestionIndex
        {myLxmfAddressHash}
        formatTimeAgo={formatConversationTime}
        {onupdateSelectedPeer}
        oncomposeenter={handleComposeAddress}
    />
{/if}

<ConversationViewerModalsBridge
    {imageLightbox}
    bind:contextMenu
    bind:reactionPicker
    bind:bubbleTranslate
    bind:isRawMessageModalOpen
    bind:rawMessageData
    bind:isPaperMessageResultModalOpen
    bind:generatedPaperMessageUri
    bind:isShareContactModalOpen
    bind:contactsSearch
    bind:isTelemetryHistoryModalOpen
    bind:showTelemetryInChat
    {selectedHash}
    {isSelectedPeerBlocked}
    {translateOptions}
    {filteredContacts}
    {conversations}
    {selectedPeerTelemetryItems}
    emojiPickerDataUrl=""
    emojiPickerThemeClass=""
    oncloselightbox={closeImageLightbox}
    onnavigatelightbox={navigateImageLightbox}
    ondownloadlightbox={() => {
        const item = imageLightbox.items?.[imageLightbox.index] || imageLightbox.items?.[0];
        if (item) void downloadMessageImage(item);
    }}
    onreply={() => {
        replyingTo = contextMenu.chatItem;
        contextMenu.show = false;
    }}
    oncopy={() => {
        void copyTextToClipboard(String(contextMenu.chatItem?.lxmf_message.content || ""));
        contextMenu.show = false;
    }}
    onreact={(emoji) => void sendReaction(emoji)}
    onopenreactionpicker={() => {
        if (contextMenu.chatItem) openReactionPicker(contextMenu.chatItem as MessageChatItem);
        contextMenu.show = false;
    }}
    onviewraw={() => {
        rawMessageData = contextMenu.chatItem?.lxmf_message || {};
        isRawMessageModalOpen = true;
        contextMenu.show = false;
    }}
    ondownloadimage={() => {
        if (contextMenu.chatItem) void downloadMessageImage(contextMenu.chatItem as MessageChatItem);
        contextMenu.show = false;
    }}
    oncancelsend={() => void cancelSending()}
    onretry={() => void retryMessage()}
    onliftbanishment={() => void unbanishSelectedPeer()}
    ondelete={() => void deleteMessage()}
    onemojireaction={(event) => {
        const char =
            (event.detail as { unicode?: string })?.unicode ||
            (event.detail as { emoji?: { unicode?: string } })?.emoji?.unicode ||
            String(event.detail || "");
        if (char && reactionPicker.chatItem) void sendReaction(char, reactionPicker.chatItem);
        reactionPicker = { ...reactionPicker, open: false };
    }}
    onsharecontact={(contact) => shareContact(contact)}
    onlocationclicktelemetry={viewLocationOnMap}
    onconfirmbubbletranslate={() => void confirmBubbleTranslate()}
/>
