<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<script lang="ts">
    import { t } from "../../../js/i18n.js";
    import ConversationImageLightbox from "./ConversationImageLightbox.svelte";
    import ConversationMessageContextMenu from "./ConversationMessageContextMenu.svelte";
    import ConversationReactionPicker from "./ConversationReactionPicker.svelte";
    import ConversationRawMessageModal from "./ConversationRawMessageModal.svelte";
    import ConversationTranslateBars from "./ConversationTranslateBars.svelte";
    import PaperMessageModal from "./modals/PaperMessageModal.svelte";
    import ShareContactModal from "./modals/ShareContactModal.svelte";
    import TelemetryHistoryModal from "./telemetry/TelemetryHistoryModal.svelte";
    import { MESSAGE_BODY_MAX_DISPLAY_CHARS } from "../lib/constants.js";
    import { fromNow } from "../../../libs/datetime.js";
    import type { LxmfMessage, ViewerChatItem } from "../lib/conversationViewerCtx.js";
    import type { MessageChatItem } from "../lib/viewerActions.js";
    import type { LangOption } from "../lib/conversationTranslate.js";

    export type ContextMenuState = {
        show: boolean;
        x: number;
        y: number;
        chatItem: ViewerChatItem | null;
        justOpened: boolean;
    };

    export type ReactionPickerState = {
        open: boolean;
        style: string;
        chatItem: ViewerChatItem | null;
    };

    export type BubbleTranslateState = {
        open: boolean;
        targetLang: string;
        chatItem: ViewerChatItem | null;
        working: boolean;
    };

    let {
        lightboxUrl = "",
        lightboxGallery = null as string[] | null,
        lightboxIndex = 0,
        lightboxItems = null as MessageChatItem[] | null,
        oncloselightbox,
        onnavigatelightbox,
        ondownloadlightbox,
        contextMenu = { show: false, x: 0, y: 0, chatItem: null, justOpened: false } as ContextMenuState,
        canLiftBanishment = false,
        reactionEmojis = [] as string[],
        onreplycontextmenu,
        oncopycontextmenu,
        ontranslatecontextmenu,
        onreactcontextmenu,
        onopenreactionpickercontextmenu,
        onviewrawcontextmenu,
        ondownloadimagecontextmenu,
        oncopyimagecontextmenu,
        onsavestickercontextmenu,
        onsavegifcontextmenu,
        oncancelsendcontextmenu,
        onretrycontextmenu,
        onliftbanishmentcontextmenu,
        ondeletecontextmenu,
        onclosecontextmenu,
        reactionPicker = { open: false, style: "", chatItem: null } as ReactionPickerState,
        emojiPickerDataUrl = "",
        emojiPickerThemeClass = "",
        onclosereactionpicker,
        onemojiclickreactionpicker,
        ondragstartreactionpicker,
        isRawMessageModalOpen = false,
        rawMessageData = {} as LxmfMessage,
        oncloserawmessage,
        oncopyhashrawmessage,
        oncopycontentrawmessage,
        isPaperMessageResultModalOpen = false,
        generatedPaperMessageUri = null as string | null,
        selectedHash = "",
        onclosepapermessage,
        isShareContactModalOpen = false,
        contactsSearch = $bindable(""),
        filteredContacts = [] as Array<Record<string, unknown>>,
        resolveContactIcon,
        destinationHexFromContact,
        onclosesharecontact,
        onsharecontact,
        isTelemetryHistoryModalOpen = false,
        selectedPeerTelemetryItems = [] as unknown[],
        showTelemetryInChat = false,
        onopentelemetrychange,
        onclosetelemetry,
        onshowtelemetrychange,
        onlocationclicktelemetry,
        bubbleTranslate = { open: false, targetLang: "en", chatItem: null, working: false } as BubbleTranslateState,
        translateOptions = [] as LangOption[],
        onconfirmbubbletranslate,
        onclosebubbletranslate,
    }: {
        lightboxUrl?: string;
        lightboxGallery?: string[] | null;
        lightboxIndex?: number;
        lightboxItems?: MessageChatItem[] | null;
        oncloselightbox?: () => void;
        onnavigatelightbox?: (delta: number) => void;
        ondownloadlightbox?: () => void;
        contextMenu?: ContextMenuState;
        canLiftBanishment?: boolean;
        reactionEmojis?: string[];
        onreplycontextmenu?: () => void;
        oncopycontextmenu?: () => void;
        ontranslatecontextmenu?: () => void;
        onreactcontextmenu?: (emoji: string) => void;
        onopenreactionpickercontextmenu?: () => void;
        onviewrawcontextmenu?: () => void;
        ondownloadimagecontextmenu?: () => void;
        oncopyimagecontextmenu?: () => void;
        onsavestickercontextmenu?: () => void;
        onsavegifcontextmenu?: () => void;
        oncancelsendcontextmenu?: () => void;
        onretrycontextmenu?: () => void;
        onliftbanishmentcontextmenu?: () => void;
        ondeletecontextmenu?: () => void;
        onclosecontextmenu?: () => void;
        reactionPicker?: ReactionPickerState;
        emojiPickerDataUrl?: string;
        emojiPickerThemeClass?: string;
        onclosereactionpicker?: () => void;
        onemojiclickreactionpicker?: (event: CustomEvent) => void;
        ondragstartreactionpicker?: (event: MouseEvent | TouchEvent) => void;
        isRawMessageModalOpen?: boolean;
        rawMessageData?: LxmfMessage;
        oncloserawmessage?: () => void;
        oncopyhashrawmessage?: (hash: string) => void;
        oncopycontentrawmessage?: () => void;
        isPaperMessageResultModalOpen?: boolean;
        generatedPaperMessageUri?: string | null;
        selectedHash?: string;
        onclosepapermessage?: () => void;
        isShareContactModalOpen?: boolean;
        contactsSearch?: string;
        filteredContacts?: Array<Record<string, unknown>>;
        resolveContactIcon?: (contact: unknown) => unknown;
        destinationHexFromContact?: (contact: unknown) => string;
        onclosesharecontact?: () => void;
        onsharecontact?: (contact: Record<string, unknown>) => void;
        isTelemetryHistoryModalOpen?: boolean;
        selectedPeerTelemetryItems?: unknown[];
        showTelemetryInChat?: boolean;
        onopentelemetrychange?: (open: boolean) => void;
        onclosetelemetry?: () => void;
        onshowtelemetrychange?: (show: boolean) => void;
        onlocationclicktelemetry?: (coords: { latitude: number; longitude: number }) => void;
        bubbleTranslate?: BubbleTranslateState;
        translateOptions?: LangOption[];
        onconfirmbubbletranslate?: () => void;
        onclosebubbletranslate?: () => void;
    } = $props();

    const rawContent = $derived(String(rawMessageData.content || ""));
</script>

<ConversationImageLightbox
    url={lightboxUrl}
    gallery={lightboxGallery}
    index={lightboxIndex}
    onclose={() => oncloselightbox?.()}
    onnavigate={(delta) => onnavigatelightbox?.(delta)}
    ondownload={() => ondownloadlightbox?.()}
/>

<ConversationMessageContextMenu
    show={contextMenu.show}
    x={contextMenu.x}
    y={contextMenu.y}
    justOpened={contextMenu.justOpened}
    openedFromBubble
    canCopy={Boolean(contextMenu.chatItem?.lxmf_message.content)}
    canTranslate={Boolean(contextMenu.chatItem?.lxmf_message.content && translateOptions.length > 0)}
    canReact={!contextMenu.chatItem?.lxmf_message.is_reaction}
    hasImage={Boolean(contextMenu.chatItem?.lxmf_message.fields?.image)}
    canSaveAsGif={Boolean(
        String((contextMenu.chatItem?.lxmf_message.fields?.image as Record<string, any>)?.image_type || "").toLowerCase() === "gif"
    )}
    canCancelSend={Boolean(
        contextMenu.chatItem?.is_outbound &&
        ["sending", "generating", "outbound"].includes(String(contextMenu.chatItem?.lxmf_message.state || ""))
    )}
    canRetry={Boolean(
        contextMenu.chatItem?.is_outbound &&
        ["failed", "cancelled"].includes(String(contextMenu.chatItem?.lxmf_message.state || ""))
    )}
    {canLiftBanishment}
    {reactionEmojis}
    onreply={() => onreplycontextmenu?.()}
    oncopy={() => oncopycontextmenu?.()}
    ontranslate={() => ontranslatecontextmenu?.()}
    onreact={(emoji) => onreactcontextmenu?.(emoji)}
    onopenreactionpicker={() => onopenreactionpickercontextmenu?.()}
    onviewraw={() => onviewrawcontextmenu?.()}
    ondownloadimage={() => ondownloadimagecontextmenu?.()}
    oncopyimage={() => oncopyimagecontextmenu?.()}
    onsavesticker={() => onsavestickercontextmenu?.()}
    onsavegif={() => onsavegifcontextmenu?.()}
    oncancelsend={() => oncancelsendcontextmenu?.()}
    onretry={() => onretrycontextmenu?.()}
    onliftbanishment={() => onliftbanishmentcontextmenu?.()}
    ondelete={() => ondeletecontextmenu?.()}
    onclose={() => onclosecontextmenu?.()}
/>

<ConversationReactionPicker
    open={reactionPicker.open}
    style={reactionPicker.style}
    {emojiPickerDataUrl}
    {emojiPickerThemeClass}
    onclose={() => onclosereactionpicker?.()}
    onemojiclick={(e) => onemojiclickreactionpicker?.(e)}
    ondragstart={(e) => ondragstartreactionpicker?.(e)}
/>

<ConversationRawMessageModal
    open={isRawMessageModalOpen}
    {rawMessageData}
    rawMessageJsonPreview={JSON.stringify(rawMessageData, null, 2)}
    isBodyOversized={rawContent.length > MESSAGE_BODY_MAX_DISPLAY_CHARS}
    bodyCharCount={rawContent.length}
    hasStoredPath={rawMessageData.path_hops_at_send != null || Boolean(rawMessageData.path_interface_at_send)}
    onclose={() => oncloserawmessage?.()}
    oncopyhash={(hash) => oncopyhashrawmessage?.(hash)}
    oncopycontent={() => oncopycontentrawmessage?.()}
/>

{#if isPaperMessageResultModalOpen}
    <PaperMessageModal
        initialUri={generatedPaperMessageUri}
        recipientHash={selectedHash}
        onclose={() => onclosepapermessage?.()}
    />
{/if}

<ShareContactModal
    show={isShareContactModalOpen}
    bind:search={contactsSearch}
    contacts={filteredContacts as never}
    resolveIcon={(contact) => resolveContactIcon?.(contact) as never}
    destinationHex={(contact) => destinationHexFromContact?.(contact) || ""}
    onclose={() => onclosesharecontact?.()}
    onshare={(contact) => onsharecontact?.(contact as Record<string, unknown>)}
/>

<TelemetryHistoryModal
    open={isTelemetryHistoryModalOpen}
    telemetryItems={selectedPeerTelemetryItems as never}
    {showTelemetryInChat}
    formatTimeAgo={(value) => fromNow(value as never)}
    gradientIdSuffix={selectedHash || "peer"}
    onopenchange={(open) => onopentelemetrychange?.(open)}
    onclose={() => onclosetelemetry?.()}
    onshowtelemetrychange={(show) => onshowtelemetrychange?.(show)}
    onlocationclick={(coords) => onlocationclicktelemetry?.(coords)}
/>

<ConversationTranslateBars
    mode="bubble"
    open={bubbleTranslate.open}
    options={translateOptions}
    bind:value={bubbleTranslate.targetLang}
    working={bubbleTranslate.working}
    onconfirm={() => onconfirmbubbletranslate?.()}
    onclose={() => onclosebubbletranslate?.()}
    onoutside={() => onclosebubbletranslate?.()}
/>
