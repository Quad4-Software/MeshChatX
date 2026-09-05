<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import type { Action } from "svelte/action";
    import { t } from "../../../js/i18n.js";
    import { isAnimatedRasterType } from "../../../js/inViewObserver.js";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import AudioWaveformPlayer from "./AudioWaveformPlayer.svelte";
    import InViewAnimatedImg from "./InViewAnimatedImg.svelte";
    import MessageReactionsOverlay from "./MessageReactionsOverlay.svelte";
    import OutboundTransferProgressFooter from "./outbound/OutboundTransferProgressFooter.svelte";
    import type { ConversationViewerActions, MessageChatItem, ParsedMessageItems } from "../lib/viewerActions.js";

    export type MessageDisplayEntry =
        | { type: "dateDivider"; key?: string; dayKey?: unknown }
        | { type: "imageGroup"; key?: string; items: MessageChatItem[]; showTimestamp?: boolean }
        | { type: "single"; key?: string; chatItem: MessageChatItem; showTimestamp?: boolean };

    let {
        entry,
        actions,
    }: {
        entry: MessageDisplayEntry;
        actions: ConversationViewerActions;
    } = $props();

    const singleItem = $derived(entry.type === "single" ? entry.chatItem : null);
    const sortedImages = $derived(entry.type === "imageGroup" ? actions.imageGroupSortedChron(entry.items) : []);
    const showTimestamp = $derived(entry.type === "dateDivider" ? true : entry.showTimestamp !== false);

    function contextMenu(event: MouseEvent, chatItem: MessageChatItem, suppressToggle = false) {
        event.preventDefault();
        actions.onMessageContextMenu(event, chatItem, suppressToggle);
    }

    function openGroupedImage(chatItem: MessageChatItem) {
        if (entry.type !== "imageGroup") {
            return;
        }
        actions.openImage(
            actions.lxmfImageUrl(chatItem.lxmf_message.hash),
            actions.imageGroupGalleryUrls(entry.items),
            sortedImages
        );
    }

    function parsed(chatItem: MessageChatItem): ParsedMessageItems {
        return actions.getParsedItems(chatItem) || {};
    }

    function attachmentImageType(chatItem: MessageChatItem) {
        return String(chatItem.lxmf_message.fields?.image?.image_type || "").toLowerCase();
    }

    function bubbleStyle(chatItem: MessageChatItem) {
        const value = actions.bubbleStyles(chatItem);
        if (typeof value === "string") {
            return value;
        }
        return Object.entries(value)
            .map(([key, item]) => `${key}:${item}`)
            .join(";");
    }

    const messageLinkHandlers: Action<HTMLElement> = (node) => {
        const handle = (event: MouseEvent) => actions.handleMessageClick(event);
        node.addEventListener("click", handle);
        node.addEventListener("auxclick", handle);
        return {
            destroy: () => {
                node.removeEventListener("click", handle);
                node.removeEventListener("auxclick", handle);
            },
        };
    };

    const renderHtml: Action<HTMLElement, string> = (node, html) => {
        node.innerHTML = html;
        return {
            update: (nextHtml) => {
                node.innerHTML = nextHtml;
            },
        };
    };
</script>

{#snippet outboundStatus(chatItem: MessageChatItem)}
    {@const message = chatItem.lxmf_message}
    {#if message.state === "delivered"}
        <MaterialDesignIcon
            iconName={actions.outboundBubbleStatusIconName(message)}
            class="size-3 {actions.outboundBubbleDeliveredIconClass(chatItem)}"
        />
    {:else if ["sent", "propagated", "unknown"].includes(message.state || "")}
        <MaterialDesignIcon
            iconName={actions.outboundBubbleStatusIconName(message)}
            class="size-3 {actions.outboundBubbleSentCheckIconClass(chatItem)}"
        />
    {:else if actions.showRichOutboundPendingUi(chatItem) && actions.isOutboundPendingForUi(chatItem)}
        <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            class="animate-spin size-3.5 shrink-0 {actions.outboundSendingStatusIconClass(chatItem)}"
            aria-label={actions.outboundBubbleStatusHoverTitle(message)}
        >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
        </svg>
    {:else if actions.isOutboundPendingForUi(chatItem)}
        <MaterialDesignIcon iconName="check" class="size-3 {actions.outboundBubblePendingCheckIconClass(chatItem)}" />
    {:else if actions.isOpportunisticDeferredDelivery(message)}
        <div
            class="relative flex size-3.5 shrink-0 items-center justify-center rounded-full border border-dashed border-amber-200/85"
            title={t("messages.opportunistic_deferred_tooltip")}
        >
            <MaterialDesignIcon iconName="clock-outline" class="size-2.5 text-amber-200/95" />
        </div>
    {:else if ["failed", "cancelled", "rejected"].includes(message.state || "")}
        <span title={actions.outboundBubbleFailedTitle(message)}>
            <MaterialDesignIcon iconName="alert-circle-outline" class="size-3 text-white" />
        </span>
    {/if}
{/snippet}

{#snippet messageFooter(chatItem: MessageChatItem, showTimestamp = true)}
    {@const message = chatItem.lxmf_message}
    {#if showTimestamp || chatItem.is_outbound}
        <div class="flex items-center justify-end gap-1.5 mt-1.5 select-none h-3">
            {#if showTimestamp}
                <span
                    class="text-[9px] opacity-80 font-medium {actions.outboundBubbleFooterTimeClass(chatItem)}"
                    title={actions.getMessageInfoLines(message, chatItem.is_outbound).join("\n")}
                >
                    {actions.formatTimeAgo(message.created_at)}
                </span>
            {/if}
            {#if chatItem.is_outbound}
                <div class="flex items-center gap-1">
                    {#if actions.isOpportunisticDeferredDelivery(message)}
                        <span class="text-[9px] font-bold uppercase tracking-wider text-amber-200">
                            {t("messages.opportunistic_deferred_label")}
                        </span>
                    {:else if ["failed", "cancelled", "rejected"].includes(message.state || "")}
                        <span class="text-[9px] font-bold uppercase tracking-wider text-white">
                            {message.state === "rejected" ? "Rejected" : t("messages.failed_waiting_announce")}
                        </span>
                    {/if}
                    {#if ["failed", "cancelled"].includes(message.state || "")}
                        <button
                            type="button"
                            class="ml-0.5 p-0.5 rounded-sm hover:bg-white/20 transition-colors"
                            title={t("messages.retry")}
                            onclick={(event) => {
                                event.stopPropagation();
                                actions.retrySendingMessage(chatItem);
                            }}
                        >
                            <MaterialDesignIcon iconName="refresh" class="size-3 text-white" />
                        </button>
                    {/if}
                    {@render outboundStatus(chatItem)}
                </div>
            {/if}
        </div>
    {/if}
{/snippet}

{#snippet expandedActions(chatItem: MessageChatItem)}
    {#if chatItem.is_actions_expanded}
        <div class="border-t px-4 py-2.5 {actions.outboundExpandedActionsShellClass(chatItem)}">
            <div class="flex flex-wrap items-center gap-2">
                {#if actions.canCancelOutboundSend(chatItem)}
                    <button
                        type="button"
                        class="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white"
                        onclick={(event) => {
                            event.stopPropagation();
                            actions.cancelSendingMessage(chatItem);
                        }}>{t("messages.cancel_send")}</button
                    >
                {/if}
                <button
                    type="button"
                    class="rounded-lg bg-blue-500 px-3 py-1.5 text-xs font-semibold text-white"
                    onclick={(event) => {
                        event.stopPropagation();
                        actions.replyToMessage(chatItem);
                    }}>{t("messages.reply")}</button
                >
                <button
                    type="button"
                    class="rounded-lg bg-red-500 px-3 py-1.5 text-xs font-semibold text-white"
                    onclick={(event) => {
                        event.stopPropagation();
                        actions.deleteChatItem(chatItem);
                    }}>Delete</button
                >
                <button
                    type="button"
                    class="rounded-lg bg-gray-600 px-3 py-1.5 text-xs font-semibold text-white"
                    onclick={(event) => {
                        event.stopPropagation();
                        actions.showRawMessage(chatItem);
                    }}>Raw LXM</button
                >
            </div>
        </div>
    {/if}
{/snippet}

{#snippet imageAttachment(chatItem: MessageChatItem)}
    {@const message = chatItem.lxmf_message}
    {@const imageType = attachmentImageType(chatItem)}
    <div
        class="relative w-full max-w-[min(280px,85vw)] mb-1.5 min-h-[120px] {chatItem.is_outbound
            ? 'ml-auto'
            : 'mr-auto'}"
    >
        <div
            class="relative rounded-2xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 shadow-md"
            role="group"
            oncontextmenu={(event) => contextMenu(event, chatItem, true)}
        >
            {#if imageType === "webm"}
                <video
                    src={actions.pendingOutboundImageSrc(chatItem)}
                    class="max-h-[min(320px,55vh)] w-full bg-black/5 dark:bg-white/5"
                    loop
                    muted
                    autoplay
                    playsinline
                ></video>
            {:else if imageType === "tgs"}
                <div
                    class="flex min-h-[180px] items-center justify-center bg-gray-200/80 text-sem-fg-muted dark:bg-zinc-700/50"
                    aria-label="Animated sticker"
                >
                    <MaterialDesignIcon iconName="animation-outline" class="size-16 opacity-70" />
                </div>
            {:else}
                <button
                    type="button"
                    class="absolute top-1 left-1 z-10 p-1 rounded-lg opacity-0 group-hover:opacity-100 text-white hover:bg-white/20"
                    title={t("messages.save_image_to_device")}
                    onclick={(event) => {
                        event.stopPropagation();
                        actions.downloadMessageImage(chatItem);
                    }}
                >
                    <MaterialDesignIcon iconName="download" class="size-4" />
                </button>
                {#if isAnimatedRasterType(imageType)}
                    <InViewAnimatedImg
                        src={actions.pendingOutboundImageSrc(chatItem)}
                        imgClass="max-h-[min(320px,55vh)] w-full cursor-pointer object-contain object-center bg-black/5 dark:bg-white/5"
                        onclick={(event) => {
                            event.stopPropagation();
                            actions.onOutboundImageClick(chatItem);
                        }}
                    />
                {:else}
                    <button
                        type="button"
                        class="block w-full p-0 border-0 bg-transparent"
                        onclick={(event) => {
                            event.stopPropagation();
                            actions.onOutboundImageClick(chatItem);
                        }}
                    >
                        <img
                            src={actions.pendingOutboundImageSrc(chatItem)}
                            loading="lazy"
                            decoding="async"
                            class="max-h-[min(320px,55vh)] min-h-[120px] w-full object-contain object-center bg-black/5 dark:bg-white/5"
                            alt=""
                        />
                    </button>
                {/if}
            {/if}
            <div
                class="pointer-events-none absolute bottom-2 left-2 rounded-lg bg-black/60 px-2.5 py-1 text-xs text-white opacity-0 backdrop-blur-xs transition-opacity group-hover:opacity-100 sm:opacity-100"
            >
                {imageType.toUpperCase() || "IMAGE"} · {actions.formatAttachmentSize(message.fields?.image, "image")}
            </div>
            {#if chatItem.is_outbound}
                <OutboundTransferProgressFooter lxmfMessage={message} {chatItem} {actions} variant="image" />
            {/if}
        </div>
    </div>
{/snippet}

{#snippet bubbleContent(chatItem: MessageChatItem)}
    {@const message = chatItem.lxmf_message}
    {@const model = actions.bubbleViewModel(chatItem)}
    {@const parsedItems = parsed(chatItem)}
    <div class="w-full space-y-1 px-4 py-2.5 min-w-0">
        {#if message.reply_to_hash}
            <button
                type="button"
                class="block w-full mb-2 p-2 rounded-lg bg-black/5 dark:bg-white/5 border-l-2 border-blue-500/50 text-left"
                onclick={(event) => {
                    event.stopPropagation();
                    actions.scrollToMessage(message.reply_to_hash || "");
                }}
            >
                <span class="flex items-center gap-1 text-[10px] font-bold uppercase">
                    <MaterialDesignIcon iconName="reply" class="size-3" />
                    {t("messages.replying_to")}
                </span>
                <span class="block text-xs opacity-70 wrap-break-word italic">
                    {message.fields?.reply_quoted_content ||
                        actions.getRepliedMessage(message.reply_to_hash)?.content ||
                        `Message <${message.reply_to_hash.substring(0, 8)}...>`}
                </span>
            </button>
        {/if}
        {#if message.is_spam}
            <div class="flex items-center gap-1.5 text-xs font-medium text-orange-700 dark:text-orange-300">
                <MaterialDesignIcon iconName="alert-decagram" class="size-4" />
                <span>Marked as Spam</span>
            </div>
        {/if}
        {#if message.content && !parsedItems.isOnlyPaperMessage && !parsedItems.isOnlyMapLink && !parsedItems.isOnlyRelayLink && !actions.shouldHideAutoImageCaption(chatItem)}
            {#if actions.isMessageBodyTooLargeForDisplay(chatItem)}
                <div
                    class="rounded-lg border border-amber-200/90 bg-amber-50/90 px-3 py-2.5 dark:border-amber-800/50 dark:bg-amber-950/25"
                >
                    <p class="text-xs">
                        {t("messages.oversized_body_notice", { count: actions.messageBodyCharCount(chatItem) })}
                    </p>
                    <button
                        type="button"
                        class="mt-2 rounded-lg bg-amber-700 px-3 py-2 text-xs font-semibold text-white"
                        onclick={(event) => {
                            event.stopPropagation();
                            actions.copyOversizedMessageBody(chatItem);
                        }}>{t("messages.oversized_body_copy")}</button
                    >
                </div>
            {:else if model.kind === "loading"}
                <div class="text-sm text-indigo-600/90 dark:text-indigo-300">
                    {t("messages.translating_message")}
                </div>
            {:else}
                <div
                    class="leading-relaxed wrap-break-word min-w-0 markdown-content {model.singleEmoji
                        ? 'markdown-content--single-emoji'
                        : ''}"
                    style:font-size={`${actions.bubbleMessageBodyFontSizePx(model)}px`}
                    use:messageLinkHandlers
                    use:renderHtml={actions.renderMarkdown(model.textForRender)}
                ></div>
                {#if model.showFooter}
                    <div class="mt-1.5 pt-1.5 border-t border-black/5 text-xs text-sem-fg-muted dark:border-white/5">
                        {#if model.showOriginalLink}
                            {t("messages.translated_from_to", {
                                source: String(model.fromCode || "").toUpperCase(),
                                target: String(model.toCode || "").toUpperCase(),
                            })}
                            <button
                                type="button"
                                class="ml-1.5 text-indigo-600 hover:underline dark:text-indigo-400"
                                onclick={(event) => {
                                    event.stopPropagation();
                                    actions.setBubbleMessageShowOriginal(model.messageHash, true);
                                }}>{t("messages.show_original")}</button
                            >
                        {:else if model.showTranslationLink}
                            <button
                                type="button"
                                class="text-indigo-600 hover:underline dark:text-indigo-400"
                                onclick={(event) => {
                                    event.stopPropagation();
                                    actions.setBubbleMessageShowOriginal(model.messageHash, false);
                                }}>{t("messages.show_translation")}</button
                            >
                        {/if}
                    </div>
                {/if}
            {/if}
        {/if}
        {#if parsedItems.contact}
            <div
                class="flex flex-col gap-2 p-3 rounded-xl border bg-sem-surface-muted border-blue-100 dark:border-blue-800/30"
            >
                <div class="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                    <MaterialDesignIcon iconName="account-plus-outline" class="size-5" />
                    <span class="text-sm font-bold">Contact Shared</span>
                </div>
                <div class="text-sm font-bold truncate">{parsedItems.contact.name}</div>
                <div class="text-[10px] font-mono truncate">{parsedItems.contact.hash}</div>
                {#if !chatItem.is_outbound}
                    <button
                        type="button"
                        class="w-full py-2 bg-blue-600 text-white rounded-lg text-xs font-bold"
                        onclick={() =>
                            actions.addContact(
                                parsedItems.contact?.name,
                                parsedItems.contact?.hash,
                                parsedItems.contact?.lxmf_address,
                                parsedItems.contact?.lxst_address
                            )}>Add to Contacts</button
                    >
                {/if}
            </div>
        {/if}
        {#if parsedItems.paperMessage}
            <div class="flex flex-col gap-2 p-3 rounded-xl border bg-emerald-50 dark:bg-black/60">
                <div class="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                    <MaterialDesignIcon
                        iconName={actions.isPaperMessageIngested(chatItem) ? "qrcode" : "qrcode-scan"}
                        class="size-5"
                    />
                    <span class="text-sm font-bold">
                        {t(
                            actions.isPaperMessageIngested(chatItem)
                                ? "messages.paper_message_ingested"
                                : "messages.paper_message_detected"
                        )}
                    </span>
                </div>
                {#if !chatItem.is_outbound && !actions.isPaperMessageIngested(chatItem)}
                    <button
                        type="button"
                        class="w-full py-2 bg-emerald-600 text-white rounded-lg text-xs font-bold"
                        onclick={() => actions.ingestPaperMessage(parsedItems.paperMessage, message.hash)}
                        >{t("messages.paper_message_ingest")}</button
                    >
                {/if}
            </div>
        {/if}
        {#if parsedItems.mapLink}
            <div
                class="flex flex-col gap-2 p-3 rounded-xl bg-sky-50 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-800/50"
            >
                <div class="flex items-center gap-2 text-sky-800 dark:text-sky-300">
                    <MaterialDesignIcon iconName="map-marker-radius" class="size-5" />
                    <span class="text-sm font-bold">
                        {t(
                            parsedItems.mapLink.kind === "ping"
                                ? "messages.map_link_ping_title"
                                : "messages.map_link_share_title"
                        )}
                    </span>
                </div>
                <div class="text-[10px] font-mono text-sky-900/80 dark:text-sky-200/90 break-all">
                    {Number(parsedItems.mapLink.parsed?.lat).toFixed(5)},
                    {Number(parsedItems.mapLink.parsed?.lon).toFixed(5)}
                    (z{parsedItems.mapLink.parsed?.zoom})
                </div>
                <button
                    type="button"
                    class="w-full py-2 bg-sky-600 text-white rounded-lg text-xs font-bold"
                    onclick={() => actions.openMapShareFromParsed(parsedItems.mapLink?.parsed)}
                >
                    {t("messages.map_link_open")}
                </button>
                <button
                    type="button"
                    class="w-full py-2 bg-sem-surface border border-sky-200 dark:border-sky-800 text-sky-800 dark:text-sky-200 rounded-lg text-xs font-bold"
                    onclick={() => actions.copyMapShareUri(parsedItems.mapLink?.uri)}
                >
                    {t("messages.map_link_copy_uri")}
                </button>
            </div>
        {/if}
        {#if parsedItems.relayLink}
            <div
                class="flex flex-col gap-2 p-3 rounded-xl bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800/50"
            >
                <div class="flex items-center gap-2 text-violet-800 dark:text-violet-300">
                    <MaterialDesignIcon iconName="forum-outline" class="size-5" />
                    <span class="text-sm font-bold">
                        {t(
                            parsedItems.relayLink.parsed?.room
                                ? "messages.relay_link_room_title"
                                : "messages.relay_link_hub_title"
                        )}
                    </span>
                </div>
                {#if parsedItems.relayLink.parsed?.name}
                    <div class="text-xs font-semibold truncate">{parsedItems.relayLink.parsed.name}</div>
                {/if}
                {#if parsedItems.relayLink.parsed?.room}
                    <div class="text-xs">#{parsedItems.relayLink.parsed.room}</div>
                {/if}
                <div class="text-[10px] font-mono break-all">{parsedItems.relayLink.parsed?.hub}</div>
                <button
                    type="button"
                    class="w-full py-2 bg-violet-600 text-white rounded-lg text-xs font-bold"
                    onclick={() => actions.openRelayShareFromParsed(parsedItems.relayLink?.parsed)}
                >
                    {t("messages.relay_link_join")}
                </button>
                <button
                    type="button"
                    class="w-full py-2 bg-sem-surface border border-violet-200 dark:border-violet-800 text-violet-800 dark:text-violet-200 rounded-lg text-xs font-bold"
                    onclick={() => actions.copyRelayShareUri(parsedItems.relayLink?.uri)}
                >
                    {t("messages.relay_link_copy_uri")}
                </button>
            </div>
        {/if}
        {#if message.fields?.audio}
            <div class="pb-1">
                {#if message.hash && actions.audioAttachmentUrls?.[message.hash]}
                    <AudioWaveformPlayer
                        src={actions.audioAttachmentUrls[message.hash]}
                        isOutbound={chatItem.is_outbound}
                    />
                {:else}
                    <div class="flex min-h-[54px] items-center justify-center rounded-xl border border-sem-border p-2">
                        <span class="text-[10px] font-bold uppercase text-gray-400">{t("messages.downloading")}</span>
                    </div>
                {/if}
                <div class="text-[10px] mt-1 text-right opacity-60 {actions.outboundAttachmentCaptionClass(chatItem)}">
                    {t("messages.voice_note")} · {actions.formatAttachmentSize(message.fields.audio, "audio")}
                </div>
            </div>
        {/if}
        {#if actions.hasFileAttachments(message)}
            <div class="space-y-2 mt-1">
                {#each message.fields?.file_attachments || [] as attachment, index (attachment.file_name || index)}
                    <button
                        type="button"
                        class="flex w-full items-center gap-3 border rounded-lg px-3 py-2 text-sm font-medium text-left {chatItem.is_outbound
                            ? actions.outboundEmbeddedCardClass(chatItem)
                            : 'bg-gray-50 dark:bg-zinc-800/50 text-sem-fg-muted border-gray-200/60 dark:border-zinc-700'}"
                        onclick={(event) => {
                            event.stopPropagation();
                            actions.downloadLxmfFileAttachment(chatItem, index);
                        }}
                    >
                        <MaterialDesignIcon iconName="paperclip" class="size-5" />
                        <span class="flex-1 min-w-0">
                            <span class="block truncate text-xs font-bold">{attachment.file_name}</span>
                            <span class="block text-[10px] font-normal"
                                >{actions.formatAttachmentSize(attachment, "file")}</span
                            >
                        </span>
                        <MaterialDesignIcon iconName="download" class="size-5" />
                    </button>
                {/each}
            </div>
        {/if}
        {#if message.fields?.commands}
            <div class="space-y-2 mt-1">
                {#each message.fields.commands as command, index (`${index}-${Object.keys(command).join("-")}`)}
                    {#if command["0x01"] || command["1"] || command["0x1"]}
                        <div class="flex items-center gap-2 border rounded-lg px-3 py-2 text-sm font-medium">
                            <MaterialDesignIcon iconName="crosshairs-question" class="size-5" />
                            <div class="text-left">
                                <div class="font-bold text-xs uppercase tracking-wider opacity-80">
                                    {t("messages.location_requested")}
                                </div>
                            </div>
                        </div>
                    {/if}
                {/each}
            </div>
        {/if}
        {#if message.fields?.telemetry?.location}
            <button
                type="button"
                class="flex items-center gap-2 border rounded-lg px-3 py-2 text-sm font-medium"
                onclick={() => actions.viewLocationOnMap(message.fields?.telemetry?.location)}
            >
                <MaterialDesignIcon iconName="map-marker" class="size-5" />
                <span class="text-left">
                    <span class="block font-bold text-[10px] uppercase">Location</span>
                    <span class="block text-[9px] font-mono opacity-70">
                        {Number(message.fields.telemetry.location.latitude).toFixed(6)},
                        {Number(message.fields.telemetry.location.longitude).toFixed(6)}
                    </span>
                </span>
            </button>
        {/if}
        {@render messageFooter(chatItem, showTimestamp)}
    </div>
{/snippet}

{#if entry.type === "dateDivider"}
    <div
        class="flex items-center justify-center gap-3 w-full max-w-full my-3 shrink-0 px-2 select-none"
        role="separator"
        aria-label={actions.formatDateDividerLabel(entry.dayKey)}
    >
        <span class="h-px w-10 shrink-0 bg-gray-300/85 sm:w-14 dark:bg-zinc-600/70"></span>
        <span class="max-w-[min(100%,18rem)] text-center text-[11px] font-medium text-sem-fg-muted">
            {actions.formatDateDividerLabel(entry.dayKey)}
        </span>
        <span class="h-px w-10 shrink-0 bg-gray-300/85 sm:w-14 dark:bg-zinc-600/70"></span>
    </div>
{:else if entry.type === "imageGroup"}
    {@const first = entry.items[0]}
    {#if first}
        <div
            class="flex flex-col max-w-[85%] sm:max-w-[75%] lg:max-w-[65%] mb-2 group min-w-0 shrink-0 {first.is_outbound
                ? 'ml-auto items-end'
                : 'mr-auto items-start'}"
            role="group"
            oncontextmenu={(event) => contextMenu(event, first)}
        >
            <div class="relative w-full max-w-[min(280px,85vw)] mb-1.5 min-h-[120px]">
                <div class="relative rounded-2xl overflow-hidden ring-1 ring-black/10 shadow-md">
                    <div class="grid grid-cols-2 gap-0.5 bg-black/5 dark:bg-white/5">
                        {#each sortedImages.slice(0, 4) as image, index (image.lxmf_message.hash)}
                            <button
                                id={`message-${image.lxmf_message.hash}`}
                                type="button"
                                class="relative aspect-square min-h-[96px] max-h-[220px] min-w-0 overflow-hidden group/img"
                                onclick={(event) => {
                                    event.stopPropagation();
                                    openGroupedImage(image);
                                }}
                                oncontextmenu={(event) => contextMenu(event, image, true)}
                            >
                                {#if isAnimatedRasterType(attachmentImageType(image))}
                                    <InViewAnimatedImg
                                        src={actions.lxmfImageUrl(image.lxmf_message.hash)}
                                        fitParent
                                        imgClass="h-full w-full object-cover object-center"
                                    />
                                {:else}
                                    <img
                                        src={actions.lxmfImageUrl(image.lxmf_message.hash)}
                                        loading="lazy"
                                        decoding="async"
                                        class="h-full w-full object-cover"
                                        alt=""
                                    />
                                {/if}
                                {#if index === 3 && sortedImages.length > 4}
                                    <span
                                        class="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/55 text-white text-3xl font-bold"
                                    >
                                        +{sortedImages.length - 4}
                                    </span>
                                {/if}
                            </button>
                        {/each}
                    </div>
                    {#if first.is_outbound}
                        <OutboundTransferProgressFooter
                            lxmfMessage={first.lxmf_message}
                            chatItem={first}
                            {actions}
                            variant="image"
                        />
                    {/if}
                </div>
                <MessageReactionsOverlay
                    reactions={first.lxmf_message.reactions}
                    isOutbound={first.is_outbound}
                    chatItem={first}
                    {actions}
                    elevated={Boolean(first.is_outbound && actions.showOutboundTransferProgress(first.lxmf_message))}
                />
            </div>
            {@render messageFooter(first, showTimestamp)}
            {@render expandedActions(first)}
        </div>
    {/if}
{:else if singleItem}
    {@const chatItem = singleItem}
    {@const message = chatItem.lxmf_message}
    <div
        class="flex flex-col max-w-[85%] sm:max-w-[75%] lg:max-w-[65%] mb-2 group min-w-0 shrink-0 {chatItem.is_outbound
            ? 'ml-auto items-end'
            : 'mr-auto items-start'}"
        role="group"
        oncontextmenu={(event) => contextMenu(event, chatItem)}
    >
        {#if message.fields?.image}
            {@render imageAttachment(chatItem)}
        {/if}
        {#if actions.isImageOnlyMessage(chatItem)}
            {@render messageFooter(chatItem, showTimestamp)}
        {/if}
        {#if actions.hasMessageBubble(chatItem)}
            <div id={`message-${message.hash}`} data-message-bubble class="relative min-w-0 w-fit max-w-full shrink-0">
                <div
                    class="relative rounded-2xl overflow-hidden transition-all duration-200 hover:shadow-md min-w-0 w-fit max-w-full {message.is_spam
                        ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-900 dark:text-yellow-100 border border-yellow-300 dark:border-yellow-700'
                        : chatItem.is_outbound
                          ? actions.outboundBubbleSurfaceClass(chatItem)
                          : 'bg-sem-surface text-sem-fg border border-sem-border shadow-xs'}"
                    style={bubbleStyle(chatItem)}
                    role="button"
                    tabindex="0"
                    onclick={() => actions.onChatItemClick(chatItem)}
                    onkeydown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                            actions.onChatItemClick(chatItem);
                        }
                    }}
                    oncontextmenu={(event) => contextMenu(event, chatItem, true)}
                >
                    <button
                        type="button"
                        class="absolute top-1 right-1 p-1 rounded-lg opacity-0 group-hover:opacity-100 {actions.outboundMessageMenuButtonClass(
                            chatItem
                        )} {actions.outboundMessageMenuButtonHoverClass(chatItem)}"
                        title={t("messages.message_actions")}
                        onclick={(event) => {
                            event.stopPropagation();
                            actions.onMessageContextMenu(event, chatItem, false);
                        }}
                    >
                        <MaterialDesignIcon iconName="dots-vertical" class="size-4" />
                    </button>
                    {@render bubbleContent(chatItem)}
                    {#if chatItem.is_outbound && !message.fields?.image}
                        <OutboundTransferProgressFooter lxmfMessage={message} {chatItem} {actions} />
                    {/if}
                    {@render expandedActions(chatItem)}
                </div>
                <MessageReactionsOverlay
                    reactions={message.reactions}
                    isOutbound={chatItem.is_outbound}
                    {chatItem}
                    {actions}
                    showReactButton={!message.is_reaction}
                    elevated={Boolean(
                        chatItem.is_outbound && actions.showOutboundTransferProgress(message) && !message.fields?.image
                    )}
                />
            </div>
        {/if}
        {#if actions.expandedMessageInfo === message.hash}
            <div class="mt-2 px-1 text-xs text-sem-fg-muted space-y-0.5">
                {#each actions.getMessageInfoLines(message, chatItem.is_outbound) as line, index (`${index}-${line}`)}
                    <div class="break-all">{line}</div>
                {/each}
            </div>
        {/if}
    </div>
{/if}
