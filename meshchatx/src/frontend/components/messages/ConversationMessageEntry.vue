<template>
    <div
        v-if="entry.type === 'imageGroup'"
        class="flex flex-col max-w-[85%] sm:max-w-[75%] md:max-lg:max-w-[70%] lg:max-w-[65%] mb-4 group min-w-0"
        :class="{
            'ml-auto items-end': entry.items[0].is_outbound,
            'mr-auto items-start': !entry.items[0].is_outbound,
        }"
        @contextmenu.prevent="cv.onMessageContextMenu($event, entry.items[0])"
    >
        <div
            class="relative w-full max-w-[min(280px,85vw)] rounded-2xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 shadow-md mb-1.5"
            :class="entry.items[0].is_outbound ? 'ml-auto' : 'mr-auto'"
            @click.stop="cv.onChatItemClick(entry.items[0])"
        >
            <button
                type="button"
                class="absolute top-1 right-1 z-10 p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity text-white hover:bg-white/20"
                :title="$t('messages.message_actions')"
                @click.stop="cv.onMessageContextMenu($event, entry.items[0])"
            >
                <MaterialDesignIcon icon-name="dots-vertical" class="size-4" />
            </button>
            <div
                v-if="cv.imageGroupSortedChron(entry.items).length === 2"
                class="grid grid-cols-2 gap-0.5 bg-black/5 dark:bg-white/5"
            >
                <button
                    v-for="imgItem in cv.imageGroupSortedChron(entry.items)"
                    :id="`message-${imgItem.lxmf_message.hash}`"
                    :key="imgItem.lxmf_message.hash"
                    type="button"
                    class="relative aspect-square min-h-[96px] max-h-[220px] min-w-0 overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                    @click.stop="
                        cv.openImage(cv.lxmfImageUrl(imgItem.lxmf_message.hash), cv.imageGroupGalleryUrls(entry.items))
                    "
                >
                    <img
                        :src="cv.lxmfImageUrl(imgItem.lxmf_message.hash)"
                        loading="lazy"
                        decoding="async"
                        class="h-full w-full object-cover object-center transition-transform hover:scale-[1.02]"
                        alt=""
                    />
                </button>
            </div>
            <div
                v-else-if="cv.imageGroupSortedChron(entry.items).length === 3"
                class="grid grid-cols-2 gap-0.5 bg-black/5 dark:bg-white/5"
            >
                <button
                    v-for="imgItem in cv.imageGroupSortedChron(entry.items).slice(0, 2)"
                    :id="`message-${imgItem.lxmf_message.hash}`"
                    :key="imgItem.lxmf_message.hash"
                    type="button"
                    class="relative aspect-square min-h-[96px] max-h-[220px] min-w-0 overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                    @click.stop="
                        cv.openImage(cv.lxmfImageUrl(imgItem.lxmf_message.hash), cv.imageGroupGalleryUrls(entry.items))
                    "
                >
                    <img
                        :src="cv.lxmfImageUrl(imgItem.lxmf_message.hash)"
                        loading="lazy"
                        decoding="async"
                        class="h-full w-full object-cover object-center transition-transform hover:scale-[1.02]"
                        alt=""
                    />
                </button>
                <button
                    :id="`message-${cv.imageGroupSortedChron(entry.items)[2].lxmf_message.hash}`"
                    type="button"
                    class="relative col-span-2 aspect-[2/1] max-h-52 min-h-[80px] w-full overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                    @click.stop="
                        cv.openImage(
                            cv.lxmfImageUrl(cv.imageGroupSortedChron(entry.items)[2].lxmf_message.hash),
                            cv.imageGroupGalleryUrls(entry.items)
                        )
                    "
                >
                    <img
                        :src="cv.lxmfImageUrl(cv.imageGroupSortedChron(entry.items)[2].lxmf_message.hash)"
                        loading="lazy"
                        decoding="async"
                        class="h-full w-full object-cover object-center transition-transform hover:scale-[1.02]"
                        alt=""
                    />
                </button>
            </div>
            <div v-else class="grid grid-cols-2 gap-0.5 bg-black/5 dark:bg-white/5">
                <button
                    v-for="(cell, idx) in cv.imageGroupSortedChron(entry.items).slice(0, 4)"
                    :id="`message-${cell.lxmf_message.hash}`"
                    :key="cell.lxmf_message.hash"
                    type="button"
                    class="relative aspect-square min-h-[96px] max-h-[220px] min-w-0 overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                    @click.stop="
                        cv.openImage(cv.lxmfImageUrl(cell.lxmf_message.hash), cv.imageGroupGalleryUrls(entry.items))
                    "
                >
                    <img
                        :src="cv.lxmfImageUrl(cell.lxmf_message.hash)"
                        loading="lazy"
                        decoding="async"
                        class="h-full w-full object-cover object-center transition-transform hover:scale-[1.02]"
                        alt=""
                    />
                    <div
                        v-if="idx === 3 && cv.imageGroupSortedChron(entry.items).length > 4"
                        class="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/55 text-white text-3xl font-bold"
                    >
                        +{{ cv.imageGroupSortedChron(entry.items).length - 4 }}
                    </div>
                </button>
            </div>
        </div>
        <div
            class="relative rounded-2xl overflow-hidden transition-all duration-200 hover:shadow-md min-w-0 px-3 py-2"
            :class="[
                ['cancelled', 'failed'].includes(entry.items[0].lxmf_message.state)
                    ? 'shadow-sm'
                    : entry.items[0].lxmf_message.is_spam
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-900 dark:text-yellow-100 border border-yellow-300 dark:border-yellow-700 shadow-sm'
                      : cv.isOutboundWaitingBubble(entry.items[0])
                        ? 'shadow-sm'
                        : entry.items[0].is_outbound
                          ? cv.outboundBubbleSurfaceClass(entry.items[0])
                          : 'bg-white dark:bg-zinc-900 text-gray-900 dark:text-zinc-100 border border-gray-200/60 dark:border-zinc-800/60 shadow-sm',
            ]"
            :style="cv.bubbleStyles(entry.items[0])"
        >
            <div class="flex items-center justify-end gap-1.5 select-none h-3">
                <span
                    class="text-[9px] opacity-80 font-medium"
                    :class="cv.outboundBubbleFooterTimeClass(entry.items[0])"
                    :title="cv.getMessageInfoLines(entry.items[0].lxmf_message, entry.items[0].is_outbound).join('\n')"
                >
                    {{ cv.formatTimeAgo(entry.items[0].lxmf_message.created_at) }}
                </span>
                <div v-if="entry.items[0].is_outbound" class="flex items-center gap-1">
                    <span
                        v-if="cv.isOpportunisticDeferredDelivery(entry.items[0].lxmf_message)"
                        class="text-[9px] font-bold uppercase tracking-wider"
                        :class="
                            cv.isThemeOutboundBubble(entry.items[0])
                                ? 'text-amber-800 dark:text-amber-300'
                                : 'text-amber-200'
                        "
                    >
                        {{ $t("messages.opportunistic_deferred_label") }}
                    </span>
                    <span
                        v-else-if="['failed', 'cancelled', 'rejected'].includes(entry.items[0].lxmf_message.state)"
                        class="text-[9px] font-bold uppercase tracking-wider text-white"
                    >
                        {{ entry.items[0].lxmf_message.state === "rejected" ? "Rejected" : "Failed" }}
                    </span>
                    <button
                        v-if="['failed', 'cancelled'].includes(entry.items[0].lxmf_message.state)"
                        type="button"
                        class="ml-0.5 p-0.5 rounded hover:bg-white/20 transition-colors"
                        title="Retry sending"
                        @click.stop="cv.retrySendingMessage(entry.items[0])"
                    >
                        <MaterialDesignIcon icon-name="refresh" class="size-3 text-white" />
                    </button>
                    <MaterialDesignIcon
                        v-if="entry.items[0].lxmf_message.state === 'delivered'"
                        icon-name="check-all"
                        class="size-3"
                        :class="cv.outboundBubbleDeliveredIconClass(entry.items[0])"
                        title="Delivered"
                    />
                    <MaterialDesignIcon
                        v-else-if="['sent', 'propagated', 'unknown'].includes(entry.items[0].lxmf_message.state)"
                        icon-name="check"
                        class="size-3"
                        :class="cv.outboundBubbleSentCheckIconClass(entry.items[0])"
                        :title="
                            entry.items[0].lxmf_message.state === 'propagated' ? 'Sent to propagation node' : 'Sent'
                        "
                    />
                    <svg
                        v-else-if="
                            cv.showRichOutboundPendingUi(entry.items[0]) && cv.isOutboundPendingForUi(entry.items[0])
                        "
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        class="animate-spin size-3.5 shrink-0"
                        :class="cv.outboundSendingStatusIconClass(entry.items[0])"
                        :title="cv.outboundBubbleStatusHoverTitle(entry.items[0].lxmf_message)"
                    >
                        <title>
                            {{ cv.outboundBubbleStatusHoverTitle(entry.items[0].lxmf_message) }}
                        </title>
                        <circle
                            class="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            stroke-width="4"
                        ></circle>
                        <path
                            class="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                    </svg>
                    <MaterialDesignIcon
                        v-else-if="cv.isOutboundPendingForUi(entry.items[0])"
                        icon-name="check"
                        class="size-3"
                        :class="cv.outboundBubblePendingCheckIconClass(entry.items[0])"
                        :title="$t('messages.sending_ellipsis')"
                    />
                    <div
                        v-else-if="cv.isOpportunisticDeferredDelivery(entry.items[0].lxmf_message)"
                        class="relative flex size-3.5 shrink-0 items-center justify-center rounded-full border border-dashed border-amber-200/85"
                        :title="$t('messages.opportunistic_deferred_tooltip')"
                    >
                        <MaterialDesignIcon icon-name="clock-outline" class="size-2.5 text-amber-200/95" />
                    </div>
                    <MaterialDesignIcon
                        v-else-if="['failed', 'cancelled', 'rejected'].includes(entry.items[0].lxmf_message.state)"
                        icon-name="alert-circle-outline"
                        class="size-3 text-white"
                        :title="cv.outboundBubbleFailedTitle(entry.items[0].lxmf_message)"
                    />
                </div>
            </div>
        </div>
        <div
            v-if="entry.items[0].is_actions_expanded"
            class="border-t px-4 py-2.5 rounded-b-2xl rounded-t-md w-full max-w-[min(280px,85vw)]"
            :class="cv.outboundExpandedActionsShellClass(entry.items[0])"
        >
            <div class="flex items-center gap-2">
                <button
                    type="button"
                    class="inline-flex items-center gap-x-1.5 rounded-lg bg-blue-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-600 transition-colors"
                    @click.stop="cv.replyToMessage(entry.items[0])"
                >
                    {{ $t("messages.reply") }}
                </button>
                <button
                    type="button"
                    class="inline-flex items-center gap-x-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-red-600 transition-colors"
                    @click.stop="cv.deleteChatItem(entry.items[0])"
                >
                    Delete
                </button>
                <button
                    type="button"
                    class="inline-flex items-center gap-x-1.5 rounded-lg bg-gray-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-gray-700 transition-colors"
                    @click.stop="cv.showRawMessage(entry.items[0])"
                >
                    Raw LXM
                </button>
            </div>
        </div>
        <div
            v-if="cv.expandedMessageInfo === entry.items[0].lxmf_message.hash"
            class="mt-2 px-1 text-xs text-gray-500 dark:text-zinc-400 space-y-0.5"
            :class="entry.items[0].is_outbound ? 'self-end' : 'self-start'"
        >
            <div
                v-for="(line, index) in cv.getMessageInfoLines(entry.items[0].lxmf_message, entry.items[0].is_outbound)"
                :key="index"
                class="break-all"
            >
                {{ line }}
            </div>
        </div>
        <div
            class="mt-1 flex w-full flex-wrap gap-0.5 px-0.5"
            :class="entry.items[0].is_outbound ? 'justify-end' : 'justify-start'"
        >
            <span
                v-for="(r, ridx) in entry.items[0].lxmf_message.reactions"
                :key="r.reactionHash || ridx"
                class="inline-flex min-h-[1.35rem] min-w-[1.35rem] cursor-default select-none items-center justify-center rounded-full border border-gray-200/90 bg-white px-1.5 py-0.5 text-sm leading-none shadow-sm dark:border-zinc-600/90 dark:bg-zinc-900"
                :title="cv.reactionReactorLabel(r.sender)"
                >{{ r.emoji }}</span
            >
            <button
                type="button"
                class="inline-flex min-h-[1.35rem] min-w-[1.35rem] items-center justify-center rounded-full border border-dashed border-gray-300 bg-transparent px-1 py-0.5 text-xs leading-none text-gray-400 hover:border-gray-400 hover:text-gray-600 hover:bg-gray-50 dark:border-zinc-600 dark:text-zinc-500 dark:hover:border-zinc-500 dark:hover:text-zinc-300 dark:hover:bg-zinc-800 transition-colors opacity-0 group-hover:opacity-100"
                :title="$t('messages.react')"
                @click.stop="cv.openReactionPicker(entry.items[0])"
            >
                <MaterialDesignIcon icon-name="emoticon-plus-outline" class="size-3.5" />
            </button>
        </div>
    </div>
    <div
        v-for="chatItem in [entry.chatItem]"
        v-else
        :id="`message-${chatItem.lxmf_message.hash}`"
        :key="chatItem.lxmf_message.hash"
        class="flex flex-col max-w-[85%] sm:max-w-[75%] md:max-lg:max-w-[70%] lg:max-w-[65%] mb-4 group min-w-0"
        :class="{
            'ml-auto items-end': chatItem.is_outbound,
            'mr-auto items-start': !chatItem.is_outbound,
        }"
        @contextmenu.prevent="cv.onMessageContextMenu($event, chatItem)"
    >
        <!-- standalone image (outside bubble) -->
        <div
            v-if="chatItem.lxmf_message.fields?.image"
            class="relative group w-full max-w-[min(280px,85vw)] rounded-2xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 shadow-md mb-1.5"
            :class="chatItem.is_outbound ? 'ml-auto' : 'mr-auto'"
        >
            <img
                :src="cv.pendingOutboundImageSrc(chatItem)"
                loading="lazy"
                decoding="async"
                class="max-h-[min(320px,55vh)] w-full cursor-pointer object-cover object-center transition-transform hover:scale-[1.01]"
                alt=""
                @click.stop="cv.openImage(cv.pendingOutboundImageSrc(chatItem))"
            />
            <div
                class="pointer-events-none absolute bottom-2 left-2 rounded-lg bg-black/60 px-2.5 py-1 text-xs text-white opacity-0 backdrop-blur-sm transition-opacity group-hover:opacity-100 sm:opacity-100"
            >
                <span>{{ (chatItem.lxmf_message.fields.image.image_type ?? "image").toUpperCase() }}</span>
                <span class="mx-1">·</span>
                <span>{{ cv.formatAttachmentSize(chatItem.lxmf_message.fields.image, "image") }}</span>
            </div>
        </div>
        <!-- image-only: inline timestamp overlay (no bubble) -->
        <div
            v-if="cv.isImageOnlyMessage(chatItem)"
            class="flex items-center gap-1.5 select-none mt-0.5"
            :class="chatItem.is_outbound ? 'justify-end' : 'justify-start'"
        >
            <span class="text-[9px] opacity-50 font-medium">
                {{ cv.formatTimeAgo(chatItem.lxmf_message.created_at) }}
            </span>
            <template v-if="chatItem.is_outbound">
                <MaterialDesignIcon
                    v-if="chatItem.lxmf_message.state === 'delivered'"
                    icon-name="check-all"
                    class="size-3 opacity-50"
                />
                <MaterialDesignIcon
                    v-else-if="['sent', 'propagated', 'unknown'].includes(chatItem.lxmf_message.state)"
                    icon-name="check"
                    class="size-3 opacity-50"
                />
                <span
                    v-else-if="['failed', 'cancelled', 'rejected'].includes(chatItem.lxmf_message.state)"
                    class="text-[9px] font-bold uppercase tracking-wider text-red-500"
                >
                    {{ chatItem.lxmf_message.state === "rejected" ? "Rejected" : "Failed" }}
                </span>
            </template>
        </div>

        <!-- message content -->
        <div
            v-if="!cv.isImageOnlyMessage(chatItem)"
            class="relative rounded-2xl overflow-hidden transition-all duration-200 hover:shadow-md min-w-0"
            :class="[
                ['cancelled', 'failed'].includes(chatItem.lxmf_message.state)
                    ? 'shadow-sm'
                    : chatItem.lxmf_message.is_spam
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-900 dark:text-yellow-100 border border-yellow-300 dark:border-yellow-700 shadow-sm'
                      : cv.isOutboundWaitingBubble(chatItem)
                        ? 'shadow-sm'
                        : chatItem.is_outbound
                          ? cv.outboundBubbleSurfaceClass(chatItem)
                          : 'bg-white dark:bg-zinc-900 text-gray-900 dark:text-zinc-100 border border-gray-200/60 dark:border-zinc-800/60 shadow-sm',
            ]"
            :style="cv.bubbleStyles(chatItem)"
            @click="cv.onChatItemClick(chatItem)"
        >
            <button
                type="button"
                class="absolute top-1 right-1 p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300 dark:text-zinc-500"
                :class="cv.outboundMessageMenuButtonHoverClass(chatItem)"
                :title="$t('messages.message_actions')"
                @click.stop="cv.onMessageContextMenu($event, chatItem)"
            >
                <MaterialDesignIcon icon-name="dots-vertical" class="size-4" />
            </button>
            <div class="w-full space-y-1 px-4 py-2.5 min-w-0">
                <!-- reply snippet -->
                <div
                    v-if="chatItem.lxmf_message.reply_to_hash"
                    class="mb-2 p-2 rounded-lg bg-black/5 dark:bg-white/5 border-l-2 border-blue-500/50 cursor-pointer hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
                    @click.stop="cv.scrollToMessage(chatItem.lxmf_message.reply_to_hash)"
                >
                    <div
                        class="flex items-center gap-1 text-[10px] font-bold uppercase tracking-tight mb-0.5"
                        :class="cv.outboundReplySnippetTitleClass(chatItem)"
                    >
                        <MaterialDesignIcon icon-name="reply" class="size-3" />
                        {{ $t("messages.replying_to") }}
                    </div>
                    <div class="text-xs opacity-70 truncate line-clamp-1 italic">
                        {{
                            chatItem.lxmf_message.fields?.reply_quoted_content ||
                            cv.getRepliedMessage(chatItem.lxmf_message.reply_to_hash)?.content ||
                            (chatItem.lxmf_message.reply_to_hash
                                ? `Message <${chatItem.lxmf_message.reply_to_hash.substring(0, 8)}...>`
                                : "(Message not found)")
                        }}
                    </div>
                </div>

                <!-- spam badge -->
                <div
                    v-if="chatItem.lxmf_message.is_spam"
                    class="flex items-center gap-1.5 text-xs font-medium mb-1"
                    :class="
                        chatItem.is_outbound
                            ? cv.isThemeOutboundBubble(chatItem)
                                ? 'text-orange-800 dark:text-orange-300'
                                : 'text-orange-200'
                            : 'text-orange-700 dark:text-orange-300'
                    "
                >
                    <MaterialDesignIcon icon-name="alert-decagram" class="size-4" />
                    <span>Marked as Spam</span>
                </div>

                <!-- content -->
                <!-- eslint-disable vue/no-v-html -->
                <div
                    v-if="
                        chatItem.lxmf_message.content &&
                        !cv.getParsedItems(chatItem)?.isOnlyPaperMessage &&
                        !cv.shouldHideAutoImageCaption(chatItem)
                    "
                    class="leading-relaxed break-words [word-break:break-word] min-w-0 markdown-content"
                    :class="{
                        'markdown-content--outbound-theme': chatItem.is_outbound && cv.isThemeOutboundBubble(chatItem),
                        'markdown-content--outbound-solid': chatItem.is_outbound && !cv.isThemeOutboundBubble(chatItem),
                        'markdown-content--inbound': !chatItem.is_outbound,
                        'markdown-content--single-emoji': cv.messageMarkdownSingleEmoji(chatItem),
                    }"
                    :style="{
                        'font-family': 'inherit',
                        'font-size': cv.messageMarkdownFontSizePx(chatItem) + 'px',
                    }"
                    @click="cv.handleMessageClick"
                    v-html="cv.renderMarkdown(chatItem.lxmf_message.content)"
                ></div>
                <!-- eslint-enable vue/no-v-html -->

                <!-- telemetry placeholder for empty content messages -->
                <div
                    v-if="!chatItem.lxmf_message.content && chatItem.lxmf_message.fields?.telemetry"
                    class="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100/20"
                >
                    <MaterialDesignIcon icon-name="satellite-variant" class="size-4 opacity-60" />
                    <span class="text-[10px] font-bold uppercase tracking-wider opacity-60">
                        {{ chatItem.is_outbound ? "Telemetry update sent" : "Telemetry update received" }}
                    </span>
                </div>

                <div
                    v-if="!chatItem.lxmf_message.content && chatItem.lxmf_message.fields?.telemetry_stream"
                    class="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100/20"
                >
                    <MaterialDesignIcon icon-name="database-sync" class="size-4 opacity-60" />
                    <span class="text-[10px] font-bold uppercase tracking-wider opacity-60"
                        >Telemetry stream received ({{
                            chatItem.lxmf_message.fields.telemetry_stream.length
                        }}
                        entries)</span
                    >
                </div>

                <div
                    v-if="
                        !chatItem.lxmf_message.content &&
                        chatItem.lxmf_message.fields?.commands?.some((c) => c['0x01'] || c['1'] || c['0x1'])
                    "
                    class="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100/20"
                >
                    <MaterialDesignIcon icon-name="crosshairs-question" class="size-4 opacity-60" />
                    <span class="text-[10px] font-bold uppercase tracking-wider opacity-60">
                        {{ chatItem.is_outbound ? "Location Request Sent" : "Location Request Received" }}
                    </span>
                </div>

                <!-- parsed items (contacts / paper messages) -->
                <div v-if="cv.getParsedItems(chatItem)" class="mt-2 space-y-2">
                    <!-- contact -->
                    <div
                        v-if="cv.getParsedItems(chatItem).contact && !chatItem.is_outbound"
                        class="flex flex-col gap-2 p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/30"
                    >
                        <div class="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                            <MaterialDesignIcon icon-name="account-plus-outline" class="size-5" />
                            <span class="text-sm font-bold">Contact Shared</span>
                        </div>
                        <div class="flex items-center gap-3">
                            <LxmfUserIcon
                                :custom-image="cv.getParsedItems(chatItem).contact.custom_image"
                                :icon-name="cv.getParsedItems(chatItem).contact.lxmf_user_icon?.icon_name"
                                :icon-foreground-colour="
                                    cv.getParsedItems(chatItem).contact.lxmf_user_icon?.foreground_colour
                                "
                                :icon-background-colour="
                                    cv.getParsedItems(chatItem).contact.lxmf_user_icon?.background_colour
                                "
                                icon-class="size-10"
                            />
                            <div class="flex-1 min-w-0">
                                <div class="text-sm font-bold text-gray-900 dark:text-white truncate">
                                    {{ cv.getParsedItems(chatItem).contact.name }}
                                </div>
                                <div class="text-[10px] font-mono text-gray-500 dark:text-zinc-400 truncate">
                                    {{ cv.getParsedItems(chatItem).contact.hash }}
                                </div>
                                <div
                                    v-if="cv.getParsedItems(chatItem).contact.lxmf_address"
                                    class="text-[9px] font-mono text-gray-400 dark:text-zinc-500 truncate"
                                >
                                    LXMF: {{ cv.getParsedItems(chatItem).contact.lxmf_address }}
                                </div>
                                <div
                                    v-if="cv.getParsedItems(chatItem).contact.lxst_address"
                                    class="text-[9px] font-mono text-gray-400 dark:text-zinc-500 truncate"
                                >
                                    LXST: {{ cv.getParsedItems(chatItem).contact.lxst_address }}
                                </div>
                            </div>
                        </div>
                        <button
                            type="button"
                            class="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
                            @click="
                                cv.addContact(
                                    cv.getParsedItems(chatItem).contact.name,
                                    cv.getParsedItems(chatItem).contact.hash,
                                    cv.getParsedItems(chatItem).contact.lxmf_address,
                                    cv.getParsedItems(chatItem).contact.lxst_address
                                )
                            "
                        >
                            Add to Contacts
                        </button>
                    </div>

                    <!-- paper message auto-conversion -->
                    <div
                        v-if="cv.getParsedItems(chatItem).paperMessage && !chatItem.is_outbound"
                        class="flex flex-col gap-2 p-3 rounded-xl bg-emerald-50 dark:bg-black/60 border border-emerald-100 dark:border-zinc-700/50"
                    >
                        <div class="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                            <MaterialDesignIcon icon-name="qrcode-scan" class="size-5" />
                            <span class="text-sm font-bold">Paper Message detected</span>
                        </div>
                        <p class="text-xs text-emerald-600/80 dark:text-zinc-400 leading-relaxed">
                            This message contains a signed LXMF URI that can be ingested into your conversations.
                        </p>
                        <button
                            type="button"
                            class="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
                            @click="cv.ingestPaperMessage(cv.getParsedItems(chatItem).paperMessage)"
                        >
                            Ingest Message
                        </button>
                    </div>
                </div>

                <!-- audio field -->
                <div v-if="chatItem.lxmf_message.fields?.audio" class="pb-1">
                    <!-- audio is loaded -->
                    <AudioWaveformPlayer
                        v-if="cv.lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash]"
                        :src="cv.lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash]"
                        :is-outbound="chatItem.is_outbound"
                    />

                    <!-- audio is not yet loaded -->
                    <div
                        v-else
                        class="flex items-center justify-center p-2 rounded-xl bg-gray-50/50 dark:bg-zinc-800/50 border border-gray-100 dark:border-zinc-800 min-h-[54px]"
                    >
                        <div class="flex items-center gap-2">
                            <div
                                class="size-4 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"
                            ></div>
                            <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">{{
                                $t("messages.downloading")
                            }}</span>
                        </div>
                    </div>

                    <div
                        class="text-[10px] mt-1 text-right opacity-60"
                        :class="cv.outboundAttachmentCaptionClass(chatItem)"
                    >
                        Voice Note •
                        {{ cv.formatAttachmentSize(chatItem.lxmf_message.fields.audio, "audio") }}
                    </div>
                </div>

                <!-- file attachment fields -->
                <div v-if="chatItem.lxmf_message.fields?.file_attachments" class="space-y-2 mt-1">
                    <a
                        v-for="(file_attachment, index) of chatItem.lxmf_message.fields?.file_attachments ?? []"
                        :key="file_attachment.file_name"
                        target="_blank"
                        :download="file_attachment.file_name"
                        :href="`/api/v1/lxmf-messages/attachment/${chatItem.lxmf_message.hash}/file?file_index=${index}`"
                        class="flex items-center gap-3 border rounded-lg px-3 py-2 text-sm font-medium cursor-pointer transition-colors"
                        :class="
                            chatItem.is_outbound
                                ? cv.outboundEmbeddedCardClass(chatItem)
                                : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300 border-gray-200/60 dark:border-zinc-700 hover:bg-gray-100 dark:hover:bg-zinc-800'
                        "
                        @click.stop
                    >
                        <div class="my-auto">
                            <MaterialDesignIcon icon-name="paperclip" class="size-5" />
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="truncate text-xs font-bold">
                                {{ file_attachment.file_name }}
                            </div>
                            <div
                                class="text-[10px] font-normal"
                                :class="
                                    chatItem.is_outbound
                                        ? cv.outboundEmbeddedSecondaryTextClass(chatItem)
                                        : 'text-gray-500 dark:text-zinc-400'
                                "
                            >
                                {{ cv.formatAttachmentSize(file_attachment, "file") }}
                            </div>
                        </div>
                        <div class="my-auto">
                            <MaterialDesignIcon icon-name="download" class="size-5" />
                        </div>
                    </a>
                </div>

                <!-- commands -->
                <div v-if="chatItem.lxmf_message.fields?.commands" class="space-y-2 mt-1">
                    <div v-for="(command, index) in chatItem.lxmf_message.fields.commands" :key="index">
                        <div
                            v-if="command['0x01'] || command['1'] || command['0x1']"
                            class="flex items-center gap-2 border border-gray-200/60 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                            :class="
                                chatItem.is_outbound
                                    ? cv.outboundEmbeddedCardClass(chatItem)
                                    : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300'
                            "
                        >
                            <MaterialDesignIcon icon-name="crosshairs-question" class="size-5" />
                            <div class="text-left">
                                <div class="font-bold text-xs uppercase tracking-wider opacity-80">
                                    {{ $t("messages.location_requested") }}
                                </div>
                                <div v-if="!chatItem.is_outbound" class="text-[10px] opacity-70">
                                    Peer is requesting your location
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- telemetry / location field -->
                <div v-if="chatItem.lxmf_message.fields?.telemetry" class="pb-1 mt-1 space-y-2">
                    <div class="flex flex-wrap gap-2">
                        <button
                            v-if="chatItem.lxmf_message.fields.telemetry.location"
                            type="button"
                            class="flex items-center gap-2 border border-gray-200/60 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                            :class="
                                chatItem.is_outbound
                                    ? cv.outboundEmbeddedCardClass(chatItem)
                                    : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300'
                            "
                            @click="cv.viewLocationOnMap(chatItem.lxmf_message.fields.telemetry.location)"
                        >
                            <MaterialDesignIcon icon-name="map-marker" class="size-5" />
                            <div class="text-left">
                                <div class="font-bold text-[10px] uppercase tracking-wider opacity-80">Location</div>
                                <div class="text-[9px] font-mono opacity-70">
                                    {{ chatItem.lxmf_message.fields.telemetry.location.latitude.toFixed(6) }},
                                    {{ chatItem.lxmf_message.fields.telemetry.location.longitude.toFixed(6) }}
                                </div>
                            </div>
                        </button>

                        <!-- Live Track Toggle Button (only for incoming) -->
                        <button
                            v-if="!chatItem.is_outbound"
                            type="button"
                            class="flex items-center gap-2 border border-gray-200/60 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                            :class="[
                                cv.selectedPeer?.is_tracking
                                    ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30 shadow-inner'
                                    : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300',
                            ]"
                            @click="cv.toggleTracking()"
                        >
                            <MaterialDesignIcon
                                :icon-name="cv.selectedPeer?.is_tracking ? 'radar' : 'crosshairs'"
                                class="size-5"
                                :class="{
                                    'animate-pulse text-blue-500': cv.selectedPeer?.is_tracking,
                                }"
                            />
                            <div class="text-left">
                                <div class="font-bold text-[10px] uppercase tracking-wider opacity-80">
                                    {{ cv.selectedPeer?.is_tracking ? "Tracking Active" : "Live Track" }}
                                </div>
                                <div class="text-[9px] opacity-70">
                                    {{
                                        cv.selectedPeer?.is_tracking
                                            ? "Auto-requesting location"
                                            : "Enable live tracking"
                                    }}
                                </div>
                            </div>
                        </button>
                    </div>

                    <!-- other sensor data if available -->
                    <div
                        v-if="
                            chatItem.lxmf_message.fields.telemetry.battery ||
                            chatItem.lxmf_message.fields.telemetry.physical_link
                        "
                        class="flex gap-3 px-1"
                    >
                        <div
                            v-if="chatItem.lxmf_message.fields.telemetry.battery"
                            class="flex items-center gap-1 opacity-60 text-[10px]"
                        >
                            <MaterialDesignIcon icon-name="battery" class="size-3" />
                            <span>{{ chatItem.lxmf_message.fields.telemetry.battery.charge_percent }}%</span>
                        </div>
                        <div
                            v-if="chatItem.lxmf_message.fields.telemetry.physical_link"
                            class="flex items-center gap-1 opacity-60 text-[10px]"
                        >
                            <MaterialDesignIcon icon-name="antenna" class="size-3" />
                            <span>SNR: {{ chatItem.lxmf_message.fields.telemetry.physical_link.snr }}dB</span>
                        </div>
                    </div>
                </div>

                <!-- message footer: timestamp and status icons -->
                <div class="flex items-center justify-end gap-1.5 mt-1.5 select-none h-3">
                    <span
                        class="text-[9px] opacity-80 font-medium"
                        :class="cv.outboundBubbleFooterTimeClass(chatItem)"
                        :title="cv.getMessageInfoLines(chatItem.lxmf_message, chatItem.is_outbound).join('\n')"
                    >
                        {{ cv.formatTimeAgo(chatItem.lxmf_message.created_at) }}
                    </span>

                    <!-- outbound status icons -->
                    <div v-if="chatItem.is_outbound" class="flex items-center gap-1">
                        <span
                            v-if="cv.isOpportunisticDeferredDelivery(chatItem.lxmf_message)"
                            class="text-[9px] font-bold uppercase tracking-wider"
                            :class="
                                cv.isThemeOutboundBubble(chatItem)
                                    ? 'text-amber-800 dark:text-amber-300'
                                    : 'text-amber-200'
                            "
                        >
                            {{ $t("messages.opportunistic_deferred_label") }}
                        </span>
                        <span
                            v-else-if="['failed', 'cancelled', 'rejected'].includes(chatItem.lxmf_message.state)"
                            class="text-[9px] font-bold uppercase tracking-wider text-white"
                        >
                            {{ chatItem.lxmf_message.state === "rejected" ? "Rejected" : "Failed" }}
                        </span>
                        <button
                            v-if="['failed', 'cancelled'].includes(chatItem.lxmf_message.state)"
                            type="button"
                            class="ml-0.5 p-0.5 rounded hover:bg-white/20 transition-colors"
                            title="Retry sending"
                            @click.stop="cv.retrySendingMessage(chatItem)"
                        >
                            <MaterialDesignIcon icon-name="refresh" class="size-3 text-white" />
                        </button>

                        <!-- delivered: double check -->
                        <MaterialDesignIcon
                            v-if="chatItem.lxmf_message.state === 'delivered'"
                            icon-name="check-all"
                            class="size-3"
                            :class="cv.outboundBubbleDeliveredIconClass(chatItem)"
                            title="Delivered"
                        />
                        <!-- sent: single check (include unknown for initial outbound when server confirmed creation) -->
                        <MaterialDesignIcon
                            v-else-if="['sent', 'propagated', 'unknown'].includes(chatItem.lxmf_message.state)"
                            icon-name="check"
                            class="size-3"
                            :class="cv.outboundBubbleSentCheckIconClass(chatItem)"
                            :title="chatItem.lxmf_message.state === 'propagated' ? 'Sent to propagation node' : 'Sent'"
                        />
                        <svg
                            v-else-if="cv.showRichOutboundPendingUi(chatItem) && cv.isOutboundPendingForUi(chatItem)"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            class="animate-spin size-3.5 shrink-0"
                            :class="cv.outboundSendingStatusIconClass(chatItem)"
                            :title="cv.outboundBubbleStatusHoverTitle(chatItem.lxmf_message)"
                        >
                            <title>
                                {{ cv.outboundBubbleStatusHoverTitle(chatItem.lxmf_message) }}
                            </title>
                            <circle
                                class="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                stroke-width="4"
                            ></circle>
                            <path
                                class="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                            ></path>
                        </svg>
                        <MaterialDesignIcon
                            v-else-if="cv.isOutboundPendingForUi(chatItem)"
                            icon-name="check"
                            class="size-3"
                            :class="cv.outboundBubblePendingCheckIconClass(chatItem)"
                            :title="$t('messages.sending_ellipsis')"
                        />
                        <div
                            v-else-if="cv.isOpportunisticDeferredDelivery(chatItem.lxmf_message)"
                            class="relative flex size-3.5 shrink-0 items-center justify-center rounded-full border border-dashed border-amber-200/85"
                            :title="$t('messages.opportunistic_deferred_tooltip')"
                        >
                            <MaterialDesignIcon icon-name="clock-outline" class="size-2.5 text-amber-200/95" />
                        </div>
                        <!-- failed/cancelled/rejected: alert -->
                        <MaterialDesignIcon
                            v-else-if="['failed', 'cancelled', 'rejected'].includes(chatItem.lxmf_message.state)"
                            icon-name="alert-circle-outline"
                            class="size-3 text-white"
                            :title="cv.outboundBubbleFailedTitle(chatItem.lxmf_message)"
                        />
                    </div>
                </div>
            </div>

            <!-- actions (expanded) -->
            <div
                v-if="chatItem.is_actions_expanded"
                class="border-t px-4 py-2.5"
                :class="cv.outboundExpandedActionsShellClass(chatItem)"
            >
                <div class="flex items-center gap-2">
                    <button
                        type="button"
                        class="inline-flex items-center gap-x-1.5 rounded-lg bg-blue-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-600 transition-colors"
                        @click.stop="cv.replyToMessage(chatItem)"
                    >
                        {{ $t("messages.reply") }}
                    </button>
                    <button
                        type="button"
                        class="inline-flex items-center gap-x-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-red-600 transition-colors"
                        @click.stop="cv.deleteChatItem(chatItem)"
                    >
                        Delete
                    </button>
                    <button
                        type="button"
                        class="inline-flex items-center gap-x-1.5 rounded-lg bg-gray-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-gray-700 transition-colors"
                        @click.stop="cv.showRawMessage(chatItem)"
                    >
                        Raw LXM
                    </button>
                </div>
            </div>
        </div>

        <div
            v-if="chatItem.lxmf_message.reactions?.length || !chatItem.lxmf_message.is_reaction"
            class="mt-1 flex w-full flex-wrap gap-0.5 px-0.5"
            :class="chatItem.is_outbound ? 'justify-end' : 'justify-start'"
        >
            <span
                v-for="(r, ridx) in chatItem.lxmf_message.reactions"
                :key="r.reactionHash || ridx"
                class="inline-flex min-h-[1.35rem] min-w-[1.35rem] cursor-default select-none items-center justify-center rounded-full border border-gray-200/90 bg-white px-1.5 py-0.5 text-sm leading-none shadow-sm dark:border-zinc-600/90 dark:bg-zinc-900"
                :title="cv.reactionReactorLabel(r.sender)"
                >{{ r.emoji }}</span
            >
            <button
                v-if="!chatItem.lxmf_message.is_reaction"
                type="button"
                class="inline-flex min-h-[1.35rem] min-w-[1.35rem] items-center justify-center rounded-full border border-dashed border-gray-300 bg-transparent px-1 py-0.5 text-xs leading-none text-gray-400 hover:border-gray-400 hover:text-gray-600 hover:bg-gray-50 dark:border-zinc-600 dark:text-zinc-500 dark:hover:border-zinc-500 dark:hover:text-zinc-300 dark:hover:bg-zinc-800 transition-colors opacity-0 group-hover:opacity-100"
                :title="$t('messages.react')"
                @click.stop="cv.openReactionPicker(chatItem)"
            >
                <MaterialDesignIcon icon-name="emoticon-plus-outline" class="size-3.5" />
            </button>
        </div>

        <!-- expanded message details -->
        <div
            v-if="cv.expandedMessageInfo === chatItem.lxmf_message.hash"
            class="mt-2 px-1 text-xs text-gray-500 dark:text-zinc-400 space-y-0.5"
        >
            <div
                v-for="(line, index) in cv.getMessageInfoLines(chatItem.lxmf_message, chatItem.is_outbound)"
                :key="index"
                class="break-all"
            >
                {{ line }}
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import AudioWaveformPlayer from "./AudioWaveformPlayer.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";

export default {
    name: "ConversationMessageEntry",
    components: {
        MaterialDesignIcon,
        AudioWaveformPlayer,
        LxmfUserIcon,
    },
    props: {
        entry: {
            type: Object,
            required: true,
        },
        cv: {
            type: Object,
            required: true,
        },
    },
};
</script>
