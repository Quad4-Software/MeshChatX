<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import ConversationViewerModalsHost from "./ConversationViewerModalsHost.svelte";
    import { copyTextToClipboard } from "../../../js/clipboardUtils.js";
    import { LXMF_REACTION_EMOJIS } from "../../../js/lxmfReactions.js";
    import { lxmfContactResolvedIcon, lxmfDeliveryDestinationHexFromContact } from "../lib/lxmf/contactDisplay.js";
    import type { LxmfMessage, ViewerChatItem } from "../lib/conversationViewerCtx.js";
    import type { LangOption } from "../lib/conversationTranslate.js";
    import type { Conversation } from "../lib/types.js";
    import type { ImageLightboxState, LightboxContextMenuState } from "../lib/conversationViewerLightbox.js";

    type ContextMenuState = {
        show: boolean;
        x: number;
        y: number;
        chatItem: ViewerChatItem | null;
        justOpened: boolean;
    };

    type ReactionPickerState = {
        open: boolean;
        style: string;
        chatItem: ViewerChatItem | null;
    };

    type BubbleTranslateState = {
        open: boolean;
        targetLang: string;
        chatItem: ViewerChatItem | null;
        working: boolean;
    };

    let {
        imageLightbox,
        lightboxContextMenu = $bindable({ show: false, x: 0, y: 0 } as LightboxContextMenuState),
        contextMenu = $bindable({ show: false, x: 0, y: 0, chatItem: null, justOpened: false } as ContextMenuState),
        reactionPicker = $bindable({ open: false, style: "", chatItem: null } as ReactionPickerState),
        bubbleTranslate = $bindable({
            open: false,
            targetLang: "en",
            chatItem: null,
            working: false,
        } as BubbleTranslateState),
        isRawMessageModalOpen = $bindable(false),
        rawMessageData = $bindable({} as LxmfMessage),
        isPaperMessageResultModalOpen = $bindable(false),
        generatedPaperMessageUri = $bindable(null as string | null),
        isShareContactModalOpen = $bindable(false),
        contactsSearch = $bindable(""),
        isTelemetryHistoryModalOpen = $bindable(false),
        showTelemetryInChat = $bindable(false),
        selectedHash = "",
        isSelectedPeerBlocked = false,
        translateOptions = [] as LangOption[],
        filteredContacts = [] as Array<Record<string, unknown>>,
        conversations = [] as Conversation[],
        selectedPeerTelemetryItems = [] as unknown[],
        emojiPickerDataUrl = "",
        emojiPickerThemeClass = "",
        oncloselightbox,
        onnavigatelightbox,
        ondownloadlightbox,
        oncontextmenulightbox,
        oncopylightbox,
        onreply,
        oncopy,
        onreact,
        onopenreactionpicker,
        onviewraw,
        ondownloadimage,
        oncopyimage,
        onsavesticker,
        onsavegif,
        oncancelsend,
        onretry,
        onliftbanishment,
        ondelete,
        onemojireaction,
        onsharecontact,
        onlocationclicktelemetry,
        onconfirmbubbletranslate,
    }: {
        imageLightbox: ImageLightboxState;
        lightboxContextMenu?: LightboxContextMenuState;
        contextMenu?: ContextMenuState;
        reactionPicker?: ReactionPickerState;
        bubbleTranslate?: BubbleTranslateState;
        isRawMessageModalOpen?: boolean;
        rawMessageData?: LxmfMessage;
        isPaperMessageResultModalOpen?: boolean;
        generatedPaperMessageUri?: string | null;
        isShareContactModalOpen?: boolean;
        contactsSearch?: string;
        isTelemetryHistoryModalOpen?: boolean;
        showTelemetryInChat?: boolean;
        selectedHash?: string;
        isSelectedPeerBlocked?: boolean;
        translateOptions?: LangOption[];
        filteredContacts?: Array<Record<string, unknown>>;
        conversations?: Conversation[];
        selectedPeerTelemetryItems?: unknown[];
        emojiPickerDataUrl?: string;
        emojiPickerThemeClass?: string;
        oncloselightbox?: () => void;
        onnavigatelightbox?: (delta: number) => void;
        ondownloadlightbox?: () => void;
        oncontextmenulightbox?: (event: MouseEvent) => void;
        oncopylightbox?: () => void;
        onreply?: () => void;
        oncopy?: () => void;
        onreact?: (emoji: string) => void;
        onopenreactionpicker?: () => void;
        onviewraw?: () => void;
        ondownloadimage?: () => void;
        oncopyimage?: () => void;
        onsavesticker?: () => void;
        onsavegif?: () => void;
        oncancelsend?: () => void;
        onretry?: () => void;
        onliftbanishment?: () => void;
        ondelete?: () => void;
        onemojireaction?: (event: CustomEvent) => void;
        onsharecontact?: (contact: Record<string, unknown>) => void;
        onlocationclicktelemetry?: (coords: { latitude: number; longitude: number }) => void;
        onconfirmbubbletranslate?: () => void;
    } = $props();
</script>

<ConversationViewerModalsHost
    lightboxUrl={imageLightbox.url}
    lightboxGallery={imageLightbox.gallery}
    lightboxIndex={imageLightbox.index}
    lightboxItems={imageLightbox.items}
    {lightboxContextMenu}
    oncloselightbox={() => oncloselightbox?.()}
    onnavigatelightbox={(delta) => onnavigatelightbox?.(delta)}
    ondownloadlightbox={() => ondownloadlightbox?.()}
    oncontextmenulightbox={(event) => oncontextmenulightbox?.(event)}
    oncopylightbox={() => oncopylightbox?.()}
    oncloselightboxcontextmenu={() => {
        lightboxContextMenu = { ...lightboxContextMenu, show: false };
    }}
    {contextMenu}
    canLiftBanishment={isSelectedPeerBlocked}
    reactionEmojis={LXMF_REACTION_EMOJIS}
    onreplycontextmenu={() => onreply?.()}
    oncopycontextmenu={() => oncopy?.()}
    ontranslatecontextmenu={() => {
        bubbleTranslate = {
            open: true,
            targetLang: bubbleTranslate.targetLang || "en",
            chatItem: contextMenu.chatItem,
            working: false,
        };
        contextMenu.show = false;
    }}
    onreactcontextmenu={(emoji) => onreact?.(emoji)}
    onopenreactionpickercontextmenu={() => onopenreactionpicker?.()}
    onviewrawcontextmenu={() => onviewraw?.()}
    ondownloadimagecontextmenu={() => ondownloadimage?.()}
    oncopyimagecontextmenu={() => oncopyimage?.()}
    onsavestickercontextmenu={() => onsavesticker?.()}
    onsavegifcontextmenu={() => onsavegif?.()}
    oncancelsendcontextmenu={() => oncancelsend?.()}
    onretrycontextmenu={() => onretry?.()}
    onliftbanishmentcontextmenu={() => onliftbanishment?.()}
    ondeletecontextmenu={() => ondelete?.()}
    onclosecontextmenu={() => {
        contextMenu.show = false;
    }}
    {reactionPicker}
    {emojiPickerDataUrl}
    {emojiPickerThemeClass}
    onclosereactionpicker={() => {
        reactionPicker = { ...reactionPicker, open: false };
    }}
    onemojiclickreactionpicker={(event) => onemojireaction?.(event)}
    ondragstartreactionpicker={() => {}}
    {isRawMessageModalOpen}
    {rawMessageData}
    oncloserawmessage={() => {
        isRawMessageModalOpen = false;
    }}
    oncopyhashrawmessage={(hash) => void copyTextToClipboard(hash)}
    oncopycontentrawmessage={() => void copyTextToClipboard(String(rawMessageData.content || ""))}
    {isPaperMessageResultModalOpen}
    {generatedPaperMessageUri}
    {selectedHash}
    onclosepapermessage={() => {
        isPaperMessageResultModalOpen = false;
        generatedPaperMessageUri = null;
    }}
    {isShareContactModalOpen}
    bind:contactsSearch
    filteredContacts={filteredContacts as never}
    resolveContactIcon={(contact) => lxmfContactResolvedIcon(contact as never, conversations)}
    destinationHexFromContact={(contact) => lxmfDeliveryDestinationHexFromContact(contact as never)}
    onclosesharecontact={() => {
        isShareContactModalOpen = false;
    }}
    onsharecontact={(contact) => onsharecontact?.(contact)}
    {isTelemetryHistoryModalOpen}
    {selectedPeerTelemetryItems}
    {showTelemetryInChat}
    onopentelemetrychange={(open) => {
        isTelemetryHistoryModalOpen = open;
    }}
    onclosetelemetry={() => {
        isTelemetryHistoryModalOpen = false;
    }}
    onshowtelemetrychange={(show) => {
        showTelemetryInChat = show;
    }}
    onlocationclicktelemetry={(coords) => onlocationclicktelemetry?.(coords)}
    {bubbleTranslate}
    {translateOptions}
    onconfirmbubbletranslate={() => onconfirmbubbletranslate?.()}
    onclosebubbletranslate={() => {
        bubbleTranslate = { ...bubbleTranslate, open: false };
    }}
/>
