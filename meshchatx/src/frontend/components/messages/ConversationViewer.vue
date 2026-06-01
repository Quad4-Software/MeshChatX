<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <!-- peer selected -->
    <div v-if="selectedPeer" class="flex flex-col h-full bg-white dark:bg-zinc-950 overflow-hidden relative">
        <!-- banished overlay -->
        <div
            v-if="GlobalState?.config?.banished_effect_enabled && isSelectedPeerBlocked"
            class="banished-overlay"
            :style="{ background: (GlobalState?.config?.banished_color || '#dc2626') + '33' }"
        >
            <span
                class="banished-text opacity-100! text-white! shadow-lg! bg-red-600! px-4! py-2! rounded-xl! border-2! tracking-widest!"
                :style="{
                    'background-color': GlobalState?.config?.banished_color || '#dc2626',
                    'border-color': GlobalState?.config?.banished_color || '#dc2626',
                }"
                >{{ GlobalState?.config?.banished_text || "BANISHED" }}</span
            >
        </div>

        <ConversationPeerHeader
            ref="conversationPeerHeader"
            :selected-peer="selectedPeer"
            :compact-peer-actions="compactPeerActions"
            :has-failed-or-cancelled-messages="hasFailedOrCancelledMessages"
            :message-icon-style="messageIconStyle"
            :selected-peer-path="selectedPeerPath"
            :selected-peer-signal-metrics="selectedPeerSignalMetrics"
            :selected-peer-lxmf-stamp-info="selectedPeerLxmfStampInfo"
            @edit-display-name="updateCustomDisplayName"
            @copy-hash="copyHash"
            @destination-path-click="onDestinationPathClick"
            @signal-metrics-click="onSignalMetricsClick"
            @stamp-info-click="onStampInfoClick"
            @conversation-deleted="onConversationDeleted"
            @popout="openConversationPopout"
            @retry-failed="retryAllFailedOrCancelledMessages"
            @open-telemetry-history="isTelemetryHistoryModalOpen = true"
            @start-call="onStartCall"
            @share-contact="openShareContactModal"
            @close="close"
        />

        <TelemetryHistoryModal
            v-model="isTelemetryHistoryModalOpen"
            v-model:show-telemetry-in-chat="showTelemetryInChat"
            :telemetry-items="selectedPeerTelemetryItems"
            :format-time-ago="formatTimeAgo"
            :gradient-id-suffix="telemetryModalGradientSuffix"
            @location-click="viewLocationOnMap"
        />

        <!-- Share Contact Modal -->
        <div
            v-if="isShareContactModalOpen"
            class="fixed inset-0 z-100 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs"
            @click.self="isShareContactModalOpen = false"
        >
            <div class="w-full max-w-md bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl overflow-hidden">
                <div class="px-6 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">
                        {{ $t("messages.share_contact_modal_title") }}
                    </h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors"
                        @click="isShareContactModalOpen = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                </div>
                <div class="p-6">
                    <div class="mb-4">
                        <div class="relative">
                            <input
                                v-model="contactsSearch"
                                type="text"
                                :placeholder="$t('messages.share_contact_search_placeholder')"
                                class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-xs ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
                            />
                            <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                                <MaterialDesignIcon icon-name="magnify" class="size-5 text-gray-400" />
                            </div>
                        </div>
                    </div>
                    <div class="max-h-64 overflow-y-auto space-y-2">
                        <button
                            v-for="contact in filteredContacts"
                            :key="contact.id"
                            type="button"
                            class="w-full flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-zinc-800 transition-colors text-left"
                            @click="shareContact(contact)"
                        >
                            <div class="shrink-0">
                                <LxmfUserIcon
                                    :custom-image="contact.custom_image"
                                    :icon-name="lxmfContactResolvedIcon(contact).iconName"
                                    :icon-foreground-colour="lxmfContactResolvedIcon(contact).foreground"
                                    :icon-background-colour="lxmfContactResolvedIcon(contact).background"
                                    icon-class="size-10"
                                />
                            </div>
                            <div class="min-w-0">
                                <div class="font-bold text-gray-900 dark:text-white truncate">
                                    {{ contact.name }}
                                </div>
                                <div class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate">
                                    {{ lxmfDeliveryDestinationHexFromContact(contact) || contact.remote_identity_hash }}
                                </div>
                                <div
                                    v-if="contact.lxmf_address"
                                    class="text-[9px] text-gray-400 dark:text-zinc-500 font-mono truncate"
                                >
                                    LXMF: {{ contact.lxmf_address }}
                                </div>
                                <div
                                    v-if="contact.lxst_address"
                                    class="text-[9px] text-gray-400 dark:text-zinc-500 font-mono truncate"
                                >
                                    LXST: {{ contact.lxst_address }}
                                </div>
                            </div>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div
            class="flex flex-col flex-1 min-h-0 min-w-0 relative"
            @dragover.prevent="onComposerImageDragOver"
            @dragleave="onComposerImageDragLeave"
            @drop.prevent="onComposerImageDrop"
        >
            <div
                v-show="composerImageDropActive"
                class="pointer-events-none absolute inset-0 z-5 border-2 border-dashed border-blue-400/70 bg-blue-500/6 dark:bg-blue-400/8"
                aria-hidden="true"
            />

            <!-- stranger trust banner -->
            <div
                v-if="isStrangerPeer && !strangerBannerDismissed && showUnknownContactBanner"
                class="mx-3 mt-2 mb-0 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-lg flex items-center gap-3 text-sm"
            >
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                    class="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 9v3.75m0 3.75h.008v-.008H12v.008Zm9.303-5.626a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                    />
                </svg>
                <span class="flex-1 text-amber-900 dark:text-amber-200">
                    {{ $t("messages.stranger_banner_text") }}
                </span>
                <button
                    class="px-3 py-1 text-xs font-medium rounded-md bg-amber-600 hover:bg-amber-700 text-white transition-colors"
                    @click="addStrangerAsContact"
                >
                    {{ $t("messages.add_to_contacts") }}
                </button>
                <button
                    class="px-2 py-1 text-xs text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200 transition-colors"
                    @click="strangerBannerDismissed = true"
                >
                    {{ $t("messages.dismiss") }}
                </button>
            </div>

            <!-- chat items -->
            <div class="flex-1 min-h-0 min-w-0 relative flex flex-col">
                <div
                    id="messages"
                    ref="messagesScroll"
                    class="flex-1 min-h-0 overflow-y-scroll bg-white dark:bg-zinc-950"
                    style="overflow-anchor: none; overscroll-behavior-y: contain"
                    :data-message-list-mode="useVirtualMessageList ? 'virtual' : 'reverse'"
                    :aria-busy="!messagesViewportReady ? 'true' : undefined"
                    @scroll="onMessagesScroll"
                >
                    <div
                        v-if="selectedPeerChatItems.length > 0"
                        :key="selectedPeer ? selectedPeer.destination_hash : ''"
                        class="min-w-0 px-4 py-6"
                        :class="useVirtualMessageList ? 'relative flex flex-col' : ''"
                    >
                        <template v-if="!useVirtualMessageList">
                            <div class="flex flex-col flex-col-reverse min-w-0">
                                <template
                                    v-for="entry in selectedPeerChatDisplayGroupsNewestFirstAugmented"
                                    :key="entry.key"
                                >
                                    <ConversationMessageEntry :entry="entry" :cv="conversationViewerSelf" />
                                </template>
                                <!-- load previous -->
                                <button
                                    v-show="!isLoadingPrevious && hasMorePrevious"
                                    id="load-previous"
                                    type="button"
                                    class="flex items-center gap-2 mx-auto mt-4 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 px-4 py-2 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-full shadow-xs text-sm font-medium text-gray-700 dark:text-zinc-300 transition-colors"
                                    @click="loadPrevious"
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke-width="1.5"
                                        stroke="currentColor"
                                        class="w-4 h-4"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="m15 11.25-3-3m0 0-3 3m3-3v7.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                                        />
                                    </svg>
                                    <span>Load Previous</span>
                                </button>
                            </div>
                        </template>
                        <template v-else>
                            <button
                                v-show="!isLoadingPrevious && hasMorePrevious"
                                id="load-previous"
                                type="button"
                                class="absolute top-2 left-1/2 z-20 -translate-x-1/2 flex items-center gap-2 bg-white/95 dark:bg-zinc-950/95 backdrop-blur-sm border border-gray-200 dark:border-zinc-800 px-4 py-2 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-full shadow-xs text-sm font-medium text-gray-700 dark:text-zinc-300 transition-colors"
                                @click="loadPrevious"
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                    class="w-4 h-4"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="m15 11.25-3-3m0 0-3 3m3-3v7.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                                    />
                                </svg>
                                <span>Load Previous</span>
                            </button>
                            <ConversationMessageListVirtual
                                ref="messageListVirtual"
                                :groups="selectedPeerChatDisplayGroupsOldestFirstAugmented"
                                :get-scroll-element="getMessagesScrollElement"
                                :cv="conversationViewerSelf"
                            />
                        </template>
                    </div>
                </div>
                <div
                    v-if="!messagesViewportReady"
                    class="absolute inset-0 z-20 bg-white dark:bg-zinc-950 pointer-events-none select-none"
                    aria-hidden="true"
                />
            </div>

            <Transition name="scroll-fab">
                <div
                    v-if="!autoScrollOnNewMessage && messagesViewportReady"
                    class="flex justify-center pb-1.5 pt-0.5 shrink-0"
                >
                    <button
                        type="button"
                        class="flex items-center justify-center size-8 rounded-full bg-white/90 dark:bg-zinc-800/90 backdrop-blur-sm border border-gray-200 dark:border-zinc-700 shadow-sm text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-700 hover:text-gray-700 dark:hover:text-zinc-200 transition-colors"
                        title="Scroll to bottom"
                        @click="scrollMessagesToBottom()"
                    >
                        <MaterialDesignIcon icon-name="chevron-down" class="size-5" />
                    </button>
                </div>
            </Transition>

            <Transition name="scroll-fab">
                <div v-if="reactionPickerChatItem" class="absolute inset-0 z-40" @click.self="closeReactionPicker">
                    <div
                        ref="reactionPickerPanel"
                        class="absolute w-[min(24rem,calc(100%-1rem))] rounded-2xl overflow-hidden border border-gray-200 dark:border-zinc-700 shadow-2xl bg-white dark:bg-zinc-900"
                        :style="reactionPickerStyle"
                    >
                        <div
                            class="flex items-center justify-between px-3 py-2 border-b border-gray-100 dark:border-zinc-800 cursor-grab active:cursor-grabbing select-none"
                            @mousedown.prevent="onReactionPickerDragStart"
                            @touchstart.prevent="onReactionPickerDragStart"
                        >
                            <span class="text-xs font-medium text-gray-500 dark:text-zinc-400">{{
                                $t("messages.react")
                            }}</span>
                            <button
                                type="button"
                                class="p-0.5 rounded-sm hover:bg-gray-100 dark:hover:bg-zinc-800 text-gray-400 dark:text-zinc-500"
                                @click="closeReactionPicker"
                            >
                                <MaterialDesignIcon icon-name="close" class="size-4" />
                            </button>
                        </div>
                        <emoji-picker
                            :data-source="emojiPickerDataUrl"
                            :class="emojiPickerThemeClass"
                            class="reaction-emoji-picker"
                            @emoji-click="onReactionPickerEmojiClick"
                        />
                    </div>
                </div>
            </Transition>

            <!-- send message -->
            <div
                class="w-full border-t border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-3 sm:px-4 py-2.5"
            >
                <div class="w-full">
                    <!-- banished user notification -->
                    <div
                        v-if="isSelectedPeerBlocked"
                        class="mb-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg flex items-center gap-2"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="2"
                            stroke="currentColor"
                            class="w-5 h-5 text-yellow-600 dark:text-yellow-400 shrink-0"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                            />
                        </svg>
                        <span class="text-sm text-yellow-800 dark:text-yellow-200"
                            >You have banished this user. They cannot send you messages or establish links.</span
                        >
                    </div>

                    <!-- message composer -->
                    <div>
                        <div class="space-y-2 mb-2">
                            <!-- image attachments (mosaic, separate from text field) -->
                            <div
                                v-if="newMessageImages.length > 0"
                                class="w-full max-w-[min(280px,100%)] rounded-xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 shadow-xs bg-black/5 dark:bg-white/5"
                            >
                                <div v-if="newMessageImages.length === 1" class="relative group">
                                    <button
                                        type="button"
                                        class="block w-full overflow-hidden focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/60"
                                        @click.stop="openImage(newMessageImageUrls[0], newMessageImageUrls)"
                                    >
                                        <img
                                            v-if="newMessageImageUrls[0]"
                                            :src="newMessageImageUrls[0]"
                                            class="max-h-52 w-full object-contain object-center bg-black/5 dark:bg-white/5"
                                        />
                                    </button>
                                    <button
                                        type="button"
                                        class="absolute top-1.5 right-1.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-600 dark:text-gray-200 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/40 shadow-md"
                                        @click.stop="removeImageAttachment(0)"
                                    >
                                        <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <div v-else-if="newMessageImages.length === 2" class="grid grid-cols-2 gap-0.5">
                                    <div v-for="(image, index) in newMessageImages" :key="index" class="relative group">
                                        <button
                                            type="button"
                                            class="relative block aspect-square min-h-[88px] w-full overflow-hidden focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/60"
                                            @click.stop="openImage(newMessageImageUrls[index], newMessageImageUrls)"
                                        >
                                            <img
                                                v-if="newMessageImageUrls[index]"
                                                :src="newMessageImageUrls[index]"
                                                class="h-full w-full object-cover"
                                            />
                                        </button>
                                        <button
                                            type="button"
                                            class="absolute top-1.5 right-1.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
                                            @click.stop="removeImageAttachment(index)"
                                        >
                                            <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                                <div v-else-if="newMessageImages.length === 3" class="grid grid-cols-2 gap-0.5">
                                    <div v-for="index in [0, 1]" :key="index" class="relative group">
                                        <button
                                            type="button"
                                            class="relative block aspect-square min-h-[88px] w-full overflow-hidden focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/60"
                                            @click.stop="openImage(newMessageImageUrls[index], newMessageImageUrls)"
                                        >
                                            <img
                                                v-if="newMessageImageUrls[index]"
                                                :src="newMessageImageUrls[index]"
                                                class="h-full w-full object-cover"
                                            />
                                        </button>
                                        <button
                                            type="button"
                                            class="absolute top-1.5 right-1.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
                                            @click.stop="removeImageAttachment(index)"
                                        >
                                            <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                    <div class="relative group col-span-2">
                                        <button
                                            type="button"
                                            class="relative block aspect-2/1 max-h-44 w-full min-h-[72px] overflow-hidden focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/60"
                                            @click.stop="openImage(newMessageImageUrls[2], newMessageImageUrls)"
                                        >
                                            <img
                                                v-if="newMessageImageUrls[2]"
                                                :src="newMessageImageUrls[2]"
                                                class="h-full w-full object-cover"
                                            />
                                        </button>
                                        <button
                                            type="button"
                                            class="absolute top-1.5 right-1.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
                                            @click.stop="removeImageAttachment(2)"
                                        >
                                            <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                                <div v-else class="grid grid-cols-2 gap-0.5">
                                    <div
                                        v-for="slot in Math.min(4, newMessageImages.length)"
                                        :key="'compose-mosaic-' + slot"
                                        class="relative group"
                                    >
                                        <button
                                            type="button"
                                            class="relative block aspect-square min-h-[88px] w-full overflow-hidden focus:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500/60"
                                            @click.stop="openImage(newMessageImageUrls[slot - 1], newMessageImageUrls)"
                                        >
                                            <img
                                                v-if="newMessageImageUrls[slot - 1]"
                                                :src="newMessageImageUrls[slot - 1]"
                                                class="h-full w-full object-cover"
                                            />
                                            <div
                                                v-if="slot === 4 && newMessageImages.length > 4"
                                                class="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/55 text-2xl font-bold text-white"
                                            >
                                                +{{ newMessageImages.length - 4 }}
                                            </div>
                                        </button>
                                        <button
                                            type="button"
                                            class="absolute top-1.5 right-1.5 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
                                            @click.stop="removeImageAttachment(slot - 1)"
                                        >
                                            <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- audio attachment -->
                            <div v-if="newMessageAudio" class="attachment-card">
                                <div class="attachment-card__body w-full">
                                    <div class="attachment-card__title">Voice Note</div>
                                    <div class="attachment-card__meta mb-2">
                                        {{ formatBytes(newMessageAudio.audio_blob.size) }}
                                    </div>
                                    <AudioWaveformPlayer :src="newMessageAudio.audio_preview_url" :is-outbound="true" />
                                </div>
                                <button type="button" class="attachment-card__remove" @click="removeAudioAttachment">
                                    <MaterialDesignIcon icon-name="delete" class="w-4 h-4" />
                                </button>
                            </div>

                            <!-- file attachments -->
                            <div v-if="newMessageFiles.length > 0" class="flex flex-wrap gap-2">
                                <div
                                    v-for="file in newMessageFiles"
                                    :key="file.name + file.size"
                                    class="attachment-chip"
                                >
                                    <div class="flex items-center gap-2">
                                        <MaterialDesignIcon
                                            icon-name="paperclip"
                                            class="w-4 h-4 text-gray-500 dark:text-gray-300"
                                        />
                                        <div class="text-sm text-gray-800 dark:text-gray-200 truncate max-w-[160px]">
                                            {{ file.name }}
                                        </div>
                                        <span class="text-xs text-gray-500 dark:text-gray-400">{{
                                            formatBytes(file.size)
                                        }}</span>
                                    </div>
                                    <button
                                        type="button"
                                        class="attachment-chip__remove"
                                        @click="removeFileAttachment(file)"
                                    >
                                        <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- text input + send -->
                        <div class="flex items-center gap-2 min-w-0">
                            <div
                                v-click-outside="{ handler: onStickerPickerClickOutside, capture: true }"
                                class="relative flex-1 min-w-0"
                            >
                                <textarea
                                    id="message-input"
                                    ref="message-input"
                                    v-model="newMessageText"
                                    :readonly="isTranslatingMessage"
                                    class="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 block w-full min-w-0 pl-3 sm:pl-4 pr-[76px] py-2.5 resize-none shadow-xs transition-all placeholder:text-gray-400 dark:placeholder:text-zinc-500 min-h-[44px] max-h-[200px] overflow-y-auto leading-snug"
                                    rows="1"
                                    spellcheck="true"
                                    :placeholder="composeInputPlaceholder"
                                    @keydown.enter.exact.prevent="onEnterPressed"
                                    @keydown.enter.shift.exact.prevent="onShiftEnterPressed"
                                    @paste="onMessagePaste"
                                ></textarea>
                                <div class="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
                                    <AddAudioButton
                                        :is-recording-audio-attachment="isRecordingAudioAttachment"
                                        @start-recording="startRecordingAudioAttachment($event)"
                                        @stop-recording="stopRecordingAudioAttachment"
                                    >
                                        <span class="text-[10px] whitespace-nowrap">
                                            {{
                                                $t("messages.recording", {
                                                    duration: audioAttachmentRecordingDuration,
                                                })
                                            }}
                                        </span>
                                    </AddAudioButton>
                                    <button
                                        type="button"
                                        class="inline-flex items-center justify-center rounded-lg p-1.5 text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800 hover:text-gray-800 dark:hover:text-zinc-100 transition-colors"
                                        :title="$t('stickers.picker_tooltip')"
                                        @click.stop="toggleStickerPicker"
                                    >
                                        <MaterialDesignIcon icon-name="emoticon-outline" class="w-5 h-5" />
                                    </button>
                                </div>
                                <div
                                    v-if="isStickerPickerOpen"
                                    class="absolute bottom-full right-0 mb-2 z-50 w-[min(320px,85vw)] max-h-[min(420px,70vh)] flex flex-col rounded-2xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-xl overflow-hidden"
                                    :class="{
                                        'ring-2 ring-blue-500/50 ring-offset-2 ring-offset-white dark:ring-offset-zinc-900':
                                            (stickerDropActive && emojiStickerTab === 'stickers') ||
                                            (gifDropActive && emojiStickerTab === 'gifs'),
                                    }"
                                    @click.stop
                                >
                                    <div
                                        class="flex shrink-0 border-b border-gray-200 dark:border-zinc-700 p-1 gap-0.5"
                                        role="tablist"
                                    >
                                        <button
                                            type="button"
                                            role="tab"
                                            :aria-selected="emojiStickerTab === 'emoji'"
                                            class="flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors"
                                            :class="
                                                emojiStickerTab === 'emoji'
                                                    ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200'
                                                    : 'text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                                            "
                                            @click="emojiStickerTab = 'emoji'"
                                        >
                                            {{ $t("stickers.tab_emojis") }}
                                        </button>
                                        <button
                                            type="button"
                                            role="tab"
                                            :aria-selected="emojiStickerTab === 'stickers'"
                                            class="flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors"
                                            :class="
                                                emojiStickerTab === 'stickers'
                                                    ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200'
                                                    : 'text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                                            "
                                            @click="emojiStickerTab = 'stickers'"
                                        >
                                            {{ $t("stickers.tab_stickers") }}
                                        </button>
                                        <button
                                            type="button"
                                            role="tab"
                                            :aria-selected="emojiStickerTab === 'gifs'"
                                            class="flex-1 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors"
                                            :class="
                                                emojiStickerTab === 'gifs'
                                                    ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200'
                                                    : 'text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                                            "
                                            @click="onGifsTabSelected"
                                        >
                                            {{ $t("gifs.tab_gifs") }}
                                        </button>
                                    </div>
                                    <div
                                        v-show="emojiStickerTab === 'emoji'"
                                        class="min-h-0 flex-1 flex flex-col overflow-hidden p-0"
                                        role="tabpanel"
                                    >
                                        <emoji-picker
                                            :data-source="emojiPickerDataUrl"
                                            :class="emojiPickerThemeClass"
                                            class="compose-emoji-picker"
                                            @emoji-click="onEmojiPickerClick"
                                        />
                                    </div>
                                    <div
                                        v-show="emojiStickerTab === 'stickers'"
                                        class="min-h-0 flex-1 overflow-y-auto p-2"
                                        role="tabpanel"
                                        @dragover.prevent.stop="onStickerPanelDragOver"
                                        @dragleave.prevent.stop="onStickerPanelDragLeave"
                                        @drop.prevent.stop="onStickerPanelDrop"
                                    >
                                        <input
                                            ref="sticker-upload-input"
                                            type="file"
                                            accept="image/png,image/jpeg,image/gif,image/webp,image/bmp,video/webm,application/x-tgsticker,.png,.jpg,.jpeg,.gif,.webp,.bmp,.webm,.tgs"
                                            multiple
                                            class="hidden"
                                            @change="onStickerUploadInputChange"
                                        />
                                        <div
                                            v-if="userStickerPacks.length > 0"
                                            class="flex shrink-0 gap-1 overflow-x-auto pb-2 mb-2 border-b border-gray-200 dark:border-zinc-800"
                                        >
                                            <button
                                                type="button"
                                                class="shrink-0 rounded-lg px-2 py-1 text-[11px] font-medium border"
                                                :class="
                                                    activeStickerPackId === null
                                                        ? 'bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200'
                                                        : 'border-transparent text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                                                "
                                                @click="activeStickerPackId = null"
                                            >
                                                {{ $t("sticker_packs.all") }}
                                            </button>
                                            <button
                                                v-for="pack in userStickerPacks"
                                                :key="pack.id"
                                                type="button"
                                                class="shrink-0 rounded-lg px-2 py-1 text-[11px] font-medium border max-w-[120px] truncate"
                                                :class="
                                                    activeStickerPackId === pack.id
                                                        ? 'bg-blue-100 dark:bg-blue-950/60 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200'
                                                        : 'border-transparent text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                                                "
                                                :title="pack.title"
                                                @click="activeStickerPackId = pack.id"
                                            >
                                                {{ pack.title }}
                                            </button>
                                        </div>
                                        <div v-if="visibleStickers.length > 0" class="grid grid-cols-4 gap-2 mb-2">
                                            <button
                                                v-for="s in visibleStickers"
                                                :key="s.id"
                                                type="button"
                                                class="aspect-square rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-700 hover:ring-2 hover:ring-blue-500/50 bg-gray-50 dark:bg-zinc-800"
                                                :title="s.name || s.emoji || 'Sticker'"
                                                @click="addStickerFromLibrary(s)"
                                            >
                                                <StickerView :src="stickerImageUrl(s.id)" :image-type="s.image_type" />
                                            </button>
                                        </div>
                                        <div
                                            v-if="visibleStickers.length === 0"
                                            class="text-center text-sm text-gray-500 dark:text-zinc-400 mb-2 px-1"
                                        >
                                            {{ $t("stickers.empty_library") }}
                                        </div>
                                        <button
                                            type="button"
                                            class="w-full rounded-xl border-2 border-dashed border-gray-300 dark:border-zinc-600 px-2 py-2 text-xs hover:border-blue-400"
                                            :class="
                                                stickerDropActive
                                                    ? 'border-blue-500 bg-blue-50/70 dark:bg-blue-950/40'
                                                    : ''
                                            "
                                            :disabled="isStickerUploading"
                                            @click="triggerStickerUploadInput"
                                        >
                                            <div class="flex items-center justify-center gap-1">
                                                <MaterialDesignIcon icon-name="upload" class="size-4 text-blue-500" />
                                                {{ $t("stickers.upload_short") }}
                                            </div>
                                        </button>
                                    </div>
                                    <div
                                        v-show="emojiStickerTab === 'gifs'"
                                        class="min-h-0 flex-1 overflow-y-auto p-2"
                                        role="tabpanel"
                                        @dragover.prevent.stop="onGifPanelDragOver"
                                        @dragleave.prevent.stop="onGifPanelDragLeave"
                                        @drop.prevent.stop="onGifPanelDrop"
                                    >
                                        <input
                                            ref="gif-upload-input"
                                            type="file"
                                            accept="image/gif,image/webp,.gif,.webp"
                                            multiple
                                            class="hidden"
                                            @change="onGifUploadInputChange"
                                        />
                                        <div v-if="userGifs.length > 0" class="grid grid-cols-2 gap-2 mb-2">
                                            <button
                                                v-for="g in userGifs"
                                                :key="g.id"
                                                type="button"
                                                class="relative aspect-video rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-700 hover:ring-2 hover:ring-blue-500/50 group"
                                                :title="g.name || 'GIF'"
                                                @click="addGifFromLibrary(g)"
                                            >
                                                <InViewAnimatedImg
                                                    :src="gifImageUrl(g.id)"
                                                    fit-parent
                                                    img-class="w-full h-full object-contain bg-gray-50 dark:bg-zinc-800"
                                                />
                                                <span
                                                    v-if="g.usage_count > 0"
                                                    class="pointer-events-none absolute bottom-1 right-1 rounded-full bg-black/60 text-white text-[10px] px-1.5 py-0.5"
                                                >
                                                    {{ g.usage_count }}
                                                </span>
                                            </button>
                                        </div>
                                        <div
                                            v-if="userGifs.length === 0"
                                            class="text-center text-sm text-gray-500 dark:text-zinc-400 mb-2 px-1"
                                        >
                                            {{ $t("gifs.empty_library") }}
                                        </div>
                                        <button
                                            type="button"
                                            class="w-full rounded-xl border-2 border-dashed border-gray-300 dark:border-zinc-600 px-3 py-3 text-left transition-colors hover:border-blue-400 hover:bg-blue-50/60 dark:hover:bg-blue-950/30"
                                            :class="
                                                gifDropActive ? 'border-blue-500 bg-blue-50/70 dark:bg-blue-950/40' : ''
                                            "
                                            :disabled="isGifUploading"
                                            @click="triggerGifUploadInput"
                                        >
                                            <div class="flex items-start gap-2">
                                                <MaterialDesignIcon
                                                    icon-name="upload"
                                                    class="size-5 shrink-0 text-blue-500 mt-0.5"
                                                />
                                                <div class="min-w-0">
                                                    <div class="text-xs font-medium text-gray-800 dark:text-zinc-100">
                                                        {{
                                                            userGifs.length > 0
                                                                ? $t("gifs.add_more_hint")
                                                                : $t("gifs.drop_or_click_hint")
                                                        }}
                                                    </div>
                                                    <div
                                                        v-if="isGifUploading"
                                                        class="text-[11px] text-blue-600 dark:text-blue-400 mt-1"
                                                    >
                                                        {{ $t("common.loading") }}
                                                    </div>
                                                </div>
                                            </div>
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <div class="shrink-0 flex items-center">
                                <SendMessageButton
                                    :is-sending-message="false"
                                    :can-send-message="canSendMessage"
                                    :can-open-send-menu="Boolean(selectedPeer)"
                                    :delivery-method="newMessageDeliveryMethod"
                                    :compact="compactSendLayout"
                                    :sending-tooltip="sendMessagePathfindingTooltip"
                                    @send="onComposerSendClick"
                                    @delivery-method-changed="newMessageDeliveryMethod = $event"
                                    @send-command-or-request="enableNextSendAsCommandOrRequest"
                                    @send-paper-compose="generatePaperMessageFromComposition"
                                />
                            </div>
                        </div>

                        <!-- reply preview -->
                        <div
                            v-if="replyingTo"
                            class="mt-2 p-2 rounded-xl bg-gray-50 dark:bg-zinc-800/50 border border-gray-200 dark:border-zinc-700/50 flex items-center gap-3 animate-in fade-in slide-in-from-bottom-2 duration-200"
                        >
                            <div class="flex-1 min-w-0 border-l-2 border-blue-500 pl-3">
                                <div
                                    class="flex items-center gap-1 text-[10px] font-bold text-blue-500 uppercase tracking-wider mb-0.5"
                                >
                                    <MaterialDesignIcon icon-name="reply" class="size-3" />
                                    {{ $t("messages.replying_to") }}
                                </div>
                                <div class="text-xs text-gray-600 dark:text-zinc-400 truncate italic">
                                    {{ replyingTo.lxmf_message.content || "(Attachment)" }}
                                </div>
                            </div>
                            <button
                                type="button"
                                class="p-1.5 hover:bg-gray-200 dark:hover:bg-zinc-700 rounded-lg transition-colors text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200"
                                @click="cancelReply"
                            >
                                <MaterialDesignIcon icon-name="close" class="w-4 h-4" />
                            </button>
                        </div>

                        <!-- inline translate: target language (compose) -->
                        <div
                            v-show="translateTargetBarOpen && translateTargetModalContext?.type === 'compose'"
                            class="mt-2 flex flex-wrap items-stretch sm:items-center gap-2 rounded-xl border border-indigo-200/60 dark:border-indigo-500/30 bg-indigo-50/80 dark:bg-indigo-950/25 px-2.5 py-2"
                        >
                            <MaterialDesignIcon
                                icon-name="translate"
                                class="size-4 text-indigo-600 dark:text-indigo-400 shrink-0 self-center"
                            />
                            <label
                                class="text-xs font-semibold text-indigo-900/90 dark:text-indigo-200/90 shrink-0 self-center"
                                >{{ $t("messages.translate_select_target") }}</label
                            >
                            <select
                                v-model="translateTargetModalValue"
                                class="flex-1 min-w-0 min-h-[2.25rem] sm:min-h-0 text-sm rounded-lg border border-gray-200/90 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-2.5 py-1.5 text-gray-900 dark:text-zinc-100"
                                :aria-label="$t('messages.translate_select_target')"
                            >
                                <option
                                    v-for="opt in translateTargetSelectOptions"
                                    :key="`c-${opt.value}`"
                                    :value="opt.value"
                                >
                                    {{ opt.label }}
                                </option>
                            </select>
                            <button
                                type="button"
                                class="primary-chip text-xs px-3.5 py-1.5 shrink-0"
                                :disabled="!translateTargetSelectOptions.length || isTranslateTargetModalWorking"
                                @click="confirmTranslateTargetModal"
                            >
                                <span
                                    v-if="isTranslateTargetModalWorking"
                                    class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin align-[-0.1em] mr-1.5"
                                ></span>
                                {{ $t("translator.translate") }}
                            </button>
                            <button
                                type="button"
                                class="p-1.5 shrink-0 rounded-lg text-zinc-500 hover:bg-black/5 dark:hover:bg-white/10 self-center"
                                :title="$t('common.close')"
                                :disabled="isTranslateTargetModalWorking"
                                @click="closeTranslateTargetModal"
                            >
                                <MaterialDesignIcon icon-name="close" class="size-4" />
                            </button>
                            <p
                                v-if="!translateTargetSelectOptions.length"
                                class="w-full text-xs text-amber-700/90 dark:text-amber-300/90 -mt-0.5"
                            >
                                No translation languages available yet. Open the Translator tool or enable a backend,
                                then return here.
                            </p>
                        </div>

                        <!-- action button -->
                        <div class="flex flex-wrap gap-2 items-center mt-2">
                            <button type="button" class="attachment-action-button" @click="addFilesToMessage">
                                <MaterialDesignIcon icon-name="paperclip-plus" class="w-4 h-4" />
                                <span class="hidden sm:inline">{{ $t("messages.add_files") }}</span>
                            </button>
                            <AddImageButton @add-image="onImageSelected" />
                            <div v-click-outside="closeLocationActionMenu" class="relative">
                                <button
                                    type="button"
                                    class="attachment-action-button"
                                    :title="$t('messages.location')"
                                    @click.stop="toggleLocationActionMenu"
                                >
                                    <MaterialDesignIcon icon-name="map-marker" class="w-4 h-4" />
                                    <span class="hidden sm:inline">{{ $t("messages.location") }}</span>
                                </button>
                                <div
                                    v-if="showLocationActionMenu"
                                    class="absolute left-0 bottom-full mb-2 z-50 min-w-[220px] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
                                >
                                    <button
                                        type="button"
                                        class="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800"
                                        @click="selectSendLocation"
                                    >
                                        {{ $t("messages.share_location") }}
                                    </button>
                                    <button
                                        type="button"
                                        class="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800"
                                        @click="selectRequestLocation"
                                    >
                                        {{ $t("messages.request_location") }}
                                    </button>
                                </div>
                            </div>
                            <button
                                v-if="hasTranslator && newMessageText"
                                type="button"
                                class="attachment-action-button"
                                :class="{
                                    'ring-1 ring-indigo-400/60 dark:ring-indigo-500/40':
                                        translateTargetBarOpen && translateTargetModalContext?.type === 'compose',
                                }"
                                :title="$t('translator.translate')"
                                @click="toggleComposeTranslateTargetBar"
                            >
                                <MaterialDesignIcon icon-name="translate" class="w-4 h-4" />
                                <span class="hidden sm:inline">{{ $t("translator.translate") }}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- hidden file input for selecting files -->
        <input ref="file-input" type="file" multiple style="display: none" @change="onFileInputChange" />

        <!-- Message Context Menu (Teleport to body to avoid overflow clipping) -->
        <Teleport to="body">
            <ContextMenuPanel
                v-click-outside="{
                    handler: () => {
                        if (!messageContextMenu.justOpened) messageContextMenu.show = false;
                    },
                    capture: true,
                }"
                :show="messageContextMenu.show"
                :x="messageContextMenu.x"
                :y="messageContextMenu.y"
                panel-class="z-200"
            >
                <ContextMenuItem @click="replyToMessage(messageContextMenu.chatItem)">
                    <MaterialDesignIcon icon-name="reply" class="size-4 text-indigo-500" />
                    Reply
                </ContextMenuItem>
                <ContextMenuItem
                    v-if="messageContextMenu.openedFromBubble && copyableMessagePlainText(messageContextMenu.chatItem)"
                    @click="copyMessageFromContextMenu(messageContextMenu.chatItem)"
                >
                    <MaterialDesignIcon icon-name="content-copy" class="size-4 text-gray-500 dark:text-zinc-400" />
                    {{ $t("messages.copy_message") }}
                </ContextMenuItem>
                <ContextMenuItem
                    v-if="hasTranslator && canTranslateMessageBubbleFromMenu(messageContextMenu.chatItem)"
                    @click="openBubbleTranslateFromContextMenu"
                >
                    <MaterialDesignIcon icon-name="translate" class="size-4 text-indigo-500" />
                    {{ $t("messages.translate_message") }}
                </ContextMenuItem>
                <div
                    v-if="messageContextMenu.chatItem && !messageContextMenu.chatItem.lxmf_message?.is_reaction"
                    class="px-3 py-2 border-t border-gray-100 dark:border-zinc-700"
                >
                    <div
                        class="text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-zinc-400 mb-1.5"
                    >
                        {{ $t("messages.react") }}
                    </div>
                    <div class="flex flex-wrap gap-1">
                        <button
                            v-for="(emo, emi) in lxmfReactionEmojis"
                            :key="emi"
                            type="button"
                            class="text-lg leading-none px-1.5 py-0.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                            :title="emo"
                            @click="sendReactionEmojiFromMenu(messageContextMenu.chatItem, emo)"
                        >
                            {{ emo }}
                        </button>
                        <button
                            type="button"
                            class="text-lg leading-none px-1.5 py-0.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors text-gray-400 dark:text-zinc-500"
                            :title="$t('messages.react')"
                            @click="
                                openReactionPicker(messageContextMenu.chatItem);
                                messageContextMenu.show = false;
                            "
                        >
                            <MaterialDesignIcon icon-name="emoticon-plus-outline" class="size-5" />
                        </button>
                    </div>
                </div>
                <ContextMenuItem
                    @click="
                        showRawMessage(messageContextMenu.chatItem);
                        messageContextMenu.show = false;
                    "
                >
                    <MaterialDesignIcon icon-name="code-json" class="size-4 text-gray-400" />
                    View Raw LXM
                </ContextMenuItem>
                <ContextMenuItem
                    v-if="messageContextMenu.chatItem?.lxmf_message?.fields?.image"
                    @click="saveMessageImageToStickers(messageContextMenu.chatItem)"
                >
                    <MaterialDesignIcon icon-name="bookmark-plus-outline" class="size-4 text-teal-500" />
                    {{ $t("stickers.save_to_library") }}
                </ContextMenuItem>
                <ContextMenuItem
                    v-if="canSaveMessageImageAsGif(messageContextMenu.chatItem)"
                    @click="saveMessageImageToGifs(messageContextMenu.chatItem)"
                >
                    <MaterialDesignIcon icon-name="file-gif-box" class="size-4 text-pink-500" />
                    {{ $t("gifs.save_to_library") }}
                </ContextMenuItem>
                <ContextMenuItem
                    v-if="
                        messageContextMenu.chatItem?.is_outbound &&
                        ['failed', 'cancelled'].includes(messageContextMenu.chatItem?.lxmf_message?.state)
                    "
                    item-class="text-amber-600 dark:text-amber-400"
                    @click="
                        retrySendingMessage(messageContextMenu.chatItem);
                        messageContextMenu.show = false;
                    "
                >
                    <MaterialDesignIcon icon-name="refresh" class="size-4" />
                    Retry
                </ContextMenuItem>
                <ContextMenuItem
                    v-if="isSelectedPeerBlocked && selectedPeer"
                    item-class="text-emerald-600 dark:text-emerald-400"
                    @click="liftBanishmentFromMessageMenu"
                >
                    <MaterialDesignIcon icon-name="check-circle" class="size-4" />
                    {{ $t("banishment.lift_banishment") }}
                </ContextMenuItem>
                <ContextMenuDivider />
                <ContextMenuItem
                    item-class="text-red-600 dark:text-red-400"
                    @click="
                        deleteChatItem(messageContextMenu.chatItem);
                        messageContextMenu.show = false;
                    "
                >
                    <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                    Delete
                </ContextMenuItem>
            </ContextMenuPanel>
        </Teleport>
    </div>

    <!-- no peer selected -->
    <div v-else class="flex flex-col h-full overflow-y-auto bg-gray-50/50 dark:bg-zinc-950/50">
        <div class="max-w-4xl mx-auto w-full px-4 py-8 sm:py-12 flex flex-col items-center">
            <!-- welcome header -->
            <div class="text-center mb-12">
                <div
                    class="inline-flex items-center justify-center p-4 rounded-3xl bg-indigo-600 shadow-xl shadow-indigo-500/20 mb-6"
                >
                    <MaterialDesignIcon icon-name="message-text" class="size-10 text-white" />
                </div>
                <h1 class="text-3xl font-black text-gray-900 dark:text-white tracking-tight mb-3">
                    {{ $t("messages.no_active_chat") }}
                </h1>
                <p class="text-gray-500 dark:text-zinc-400 max-w-sm mx-auto">
                    {{ $t("messages.select_peer_or_enter_address") }}
                </p>
            </div>

            <!-- main actions grid -->
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 w-full mb-12">
                <button
                    type="button"
                    class="flex flex-col items-center gap-3 p-6 rounded-3xl bg-white dark:bg-zinc-900 border border-gray-100 dark:border-zinc-800 hover:border-indigo-500/50 hover:shadow-xl hover:shadow-indigo-500/5 transition-all group"
                    @click="focusComposeInput"
                >
                    <div
                        class="size-12 rounded-2xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 flex items-center justify-center group-hover:scale-110 transition-transform"
                    >
                        <MaterialDesignIcon icon-name="plus" class="size-6" />
                    </div>
                    <span class="text-sm font-bold text-gray-900 dark:text-zinc-100">New Message</span>
                </button>

                <button
                    type="button"
                    class="flex flex-col items-center gap-3 p-6 rounded-3xl bg-white dark:bg-zinc-900 border border-gray-100 dark:border-zinc-800 hover:border-blue-500/50 hover:shadow-xl hover:shadow-blue-500/5 transition-all group"
                    @click="syncPropagationNode"
                >
                    <div
                        class="size-12 rounded-2xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 flex items-center justify-center group-hover:scale-110 transition-transform"
                    >
                        <MaterialDesignIcon
                            icon-name="sync"
                            class="size-6"
                            :class="{ 'animate-spin': isSyncingPropagationNode }"
                            :style="isSyncingPropagationNode ? { animationDirection: 'reverse' } : {}"
                        />
                    </div>
                    <span class="text-sm font-bold text-gray-900 dark:text-zinc-100">{{
                        isSyncingPropagationNode ? "Syncing..." : "Sync Node"
                    }}</span>
                </button>

                <button
                    type="button"
                    class="flex flex-col items-center gap-3 p-6 rounded-3xl bg-white dark:bg-zinc-900 border border-gray-100 dark:border-zinc-800 hover:border-blue-500/50 hover:shadow-xl hover:shadow-blue-500/5 transition-all group"
                    @click="copyMyAddress"
                >
                    <div
                        class="size-12 rounded-2xl bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 flex items-center justify-center group-hover:scale-110 transition-transform"
                    >
                        <MaterialDesignIcon icon-name="content-copy" class="size-6" />
                    </div>
                    <span class="text-sm font-bold text-gray-900 dark:text-zinc-100">My Address</span>
                </button>

                <button
                    type="button"
                    class="flex flex-col items-center gap-3 p-6 rounded-3xl bg-white dark:bg-zinc-900 border border-gray-100 dark:border-zinc-800 hover:border-blue-500/50 hover:shadow-xl hover:shadow-blue-500/5 transition-all group"
                    @click="$router.push({ name: 'identities' })"
                >
                    <div
                        class="size-12 rounded-2xl bg-purple-50 dark:bg-purple-900/20 text-purple-600 flex items-center justify-center group-hover:scale-110 transition-transform"
                    >
                        <MaterialDesignIcon icon-name="account-multiple" class="size-6" />
                    </div>
                    <span class="text-sm font-bold text-gray-900 dark:text-zinc-100">Identities</span>
                </button>
            </div>

            <!-- latest chats section -->
            <div v-if="latestConversations.length > 0" class="w-full mb-12">
                <div class="flex items-center justify-between mb-6">
                    <h2
                        class="text-sm font-black text-gray-400 dark:text-zinc-500 uppercase tracking-widest flex items-center gap-2"
                    >
                        <MaterialDesignIcon icon-name="history" class="size-4" />
                        Latest Conversations
                    </h2>
                </div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div
                        v-for="chat in latestConversations"
                        :key="chat.destination_hash"
                        class="group cursor-pointer p-4 bg-white dark:bg-zinc-900 border border-gray-100 dark:border-zinc-800 rounded-3xl hover:border-blue-500/50 hover:shadow-xl transition-all flex items-center gap-4"
                        @click="$emit('update:selectedPeer', chat)"
                    >
                        <div class="shrink-0">
                            <LxmfUserIcon
                                :custom-image="chat.contact_image"
                                :icon-name="
                                    chat.lxmf_user_icon && chat.lxmf_user_icon.icon_name
                                        ? chat.lxmf_user_icon.icon_name
                                        : 'account'
                                "
                                :icon-foreground-colour="
                                    chat.lxmf_user_icon ? chat.lxmf_user_icon.foreground_colour : ''
                                "
                                :icon-background-colour="
                                    chat.lxmf_user_icon ? chat.lxmf_user_icon.background_colour : ''
                                "
                                icon-class="size-12 sm:size-14"
                            />
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center justify-between gap-2">
                                <div class="font-bold text-gray-900 dark:text-zinc-100 truncate">
                                    {{ chat.custom_display_name ?? chat.display_name }}
                                </div>
                                <div class="text-[10px] text-gray-400 dark:text-zinc-500 whitespace-nowrap">
                                    {{ formatTimeAgo(chat.updated_at) }}
                                </div>
                            </div>
                            <div class="text-xs text-gray-500 dark:text-zinc-500 truncate mt-0.5">
                                {{ chat.latest_message_preview || chat.latest_message_title || "No messages yet" }}
                            </div>
                        </div>
                        <MaterialDesignIcon
                            icon-name="chevron-right"
                            class="size-5 text-gray-300 dark:text-zinc-700 group-hover:text-blue-500 transition-colors"
                        />
                    </div>
                </div>
            </div>

            <!-- address input composer -->
            <div class="w-full max-w-xl">
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <MaterialDesignIcon
                            icon-name="at"
                            class="size-5 text-gray-400 group-focus-within:text-blue-500 transition-colors"
                        />
                    </div>
                    <input
                        id="compose-input"
                        ref="compose-input"
                        v-model="composeAddress"
                        :readonly="isTranslatingMessage"
                        type="text"
                        class="w-full bg-white dark:bg-zinc-900 border-2 border-gray-100 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-base rounded-3xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 pl-12 pr-4 py-4 shadow-xs transition-all placeholder:text-gray-400 dark:placeholder:text-zinc-600 font-medium"
                        placeholder="Enter LXMF address to start a conversation..."
                        @keydown.enter.exact.prevent="onComposeEnterPressed"
                        @keydown.up.prevent="handleComposeInputUp"
                        @keydown.down.prevent="handleComposeInputDown"
                        @focus="isComposeInputFocused = true"
                        @blur="onComposeInputBlur"
                    />

                    <!-- Suggestions Dropdown -->
                    <div
                        v-if="isComposeInputFocused && composeSuggestions.length > 0"
                        class="absolute z-50 left-0 right-0 bottom-full mb-4 bg-white dark:bg-zinc-900 border border-gray-100 dark:border-zinc-800 rounded-3xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-300"
                    >
                        <div class="p-2 space-y-1">
                            <div
                                v-for="(suggestion, index) in composeSuggestions"
                                :key="suggestion.hash"
                                class="px-4 py-3 flex items-center gap-3 cursor-pointer rounded-2xl transition-all"
                                :class="[
                                    index === selectedComposeSuggestionIndex
                                        ? 'bg-blue-600 text-white shadow-lg'
                                        : 'hover:bg-gray-50 dark:hover:bg-zinc-800/50 text-gray-700 dark:text-zinc-300',
                                ]"
                                @mousedown.prevent="selectComposeSuggestion(suggestion)"
                            >
                                <div
                                    class="shrink-0 size-10 rounded-xl flex items-center justify-center"
                                    :class="[
                                        index === selectedComposeSuggestionIndex
                                            ? 'bg-white/20'
                                            : suggestion.type === 'contact'
                                              ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600'
                                              : 'bg-gray-100 dark:bg-zinc-800 text-gray-500',
                                    ]"
                                >
                                    <MaterialDesignIcon :icon-name="suggestion.icon" class="size-5" />
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-sm font-bold truncate">
                                        {{ suggestion.name }}
                                    </div>
                                    <div class="text-[10px] font-mono opacity-60 truncate">
                                        {{ formatDestinationHash(suggestion.hash) }}
                                    </div>
                                </div>
                                <div
                                    v-if="suggestion.type === 'contact'"
                                    class="text-[10px] uppercase font-black tracking-widest opacity-40 px-2 py-1 rounded-md bg-black/5"
                                >
                                    Contact
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- image modal -->
    <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
    >
        <div
            v-if="imageModalUrl"
            ref="imageModalOverlay"
            tabindex="0"
            class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 dark:bg-black/90 backdrop-blur-xs p-4 outline-hidden"
            @click="closeImageModal"
            @keydown.left.prevent="imageModalNavigate(-1)"
            @keydown.right.prevent="imageModalNavigate(1)"
            @keydown.escape.prevent="closeImageModal"
        >
            <div class="relative max-w-7xl max-h-full" @click.stop>
                <button
                    type="button"
                    class="absolute -top-12 right-0 inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 dark:bg-zinc-900/10 hover:bg-white/20 dark:hover:bg-zinc-900/20 text-white transition-colors"
                    @click="closeImageModal"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
                <button
                    v-if="imageModalGallery && imageModalGallery.length > 1"
                    type="button"
                    class="absolute left-0 top-1/2 z-10 -translate-y-1/2 inline-flex items-center justify-center w-11 h-11 rounded-full bg-black/40 hover:bg-black/55 text-white transition-colors"
                    aria-label="Previous image"
                    @click.stop="imageModalNavigate(-1)"
                >
                    <MaterialDesignIcon icon-name="chevron-left" class="size-7" />
                </button>
                <button
                    v-if="imageModalGallery && imageModalGallery.length > 1"
                    type="button"
                    class="absolute right-0 top-1/2 z-10 -translate-y-1/2 inline-flex items-center justify-center w-11 h-11 rounded-full bg-black/40 hover:bg-black/55 text-white transition-colors"
                    aria-label="Next image"
                    @click.stop="imageModalNavigate(1)"
                >
                    <MaterialDesignIcon icon-name="chevron-right" class="size-7" />
                </button>
                <div
                    v-if="imageModalGallery && imageModalGallery.length > 1"
                    class="pointer-events-none absolute bottom-2 left-1/2 z-10 -translate-x-1/2 rounded-full bg-black/50 px-3 py-1 text-xs font-medium text-white"
                >
                    {{ imageModalIndex + 1 }} / {{ imageModalGallery.length }}
                </div>
                <img :src="imageModalUrl" class="max-w-full max-h-[90vh] rounded-xl shadow-2xl" alt="Image preview" />
            </div>
        </div>
    </Transition>

    <PaperMessageModal
        v-if="isPaperMessageModalOpen"
        :message-hash="paperMessageHash"
        :recipient-hash="selectedPeer?.destination_hash"
        @close="isPaperMessageModalOpen = false"
    />

    <PaperMessageModal
        v-if="isPaperMessageResultModalOpen"
        :initial-uri="generatedPaperMessageUri"
        :recipient-hash="selectedPeer?.destination_hash"
        @close="
            isPaperMessageResultModalOpen = false;
            generatedPaperMessageUri = null;
        "
    />

    <Teleport to="body">
        <Transition
            enter-active-class="transition duration-200 ease-out"
            enter-from-class="opacity-0 translate-y-2"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition duration-150 ease-in"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 translate-y-2"
        >
            <div
                v-show="translateTargetBarOpen && translateTargetModalContext?.type === 'bubble'"
                v-click-outside="{
                    handler: onTranslateTargetBarClickOutside,
                    capture: true,
                }"
                class="translate-bubble-bar fixed z-200 w-[min(calc(100%-1.25rem),24rem)] left-1/2 -translate-x-1/2 bottom-4 sm:bottom-5 pb-[max(0.25rem,env(safe-area-inset-bottom))] pointer-events-auto"
            >
                <div
                    class="flex flex-col gap-2 rounded-2xl border border-indigo-200/60 dark:border-indigo-500/30 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md shadow-xl shadow-indigo-900/5 dark:shadow-black/30 px-3 py-2.5"
                >
                    <div class="flex items-center gap-1.5 text-indigo-700/90 dark:text-indigo-300/90">
                        <MaterialDesignIcon icon-name="translate" class="size-4 shrink-0" />
                        <span class="text-sm font-semibold leading-none">{{
                            $t("messages.translate_select_target")
                        }}</span>
                    </div>
                    <div class="flex flex-wrap sm:flex-nowrap items-stretch gap-2">
                        <select
                            v-model="translateTargetModalValue"
                            class="flex-1 min-w-0 min-h-[2.5rem] text-sm rounded-lg border border-gray-200/90 dark:border-zinc-600 bg-white dark:bg-zinc-900/90 px-2.5 py-1.5 text-gray-900 dark:text-zinc-100"
                            :aria-label="$t('messages.translate_select_target')"
                        >
                            <option
                                v-for="opt in translateTargetSelectOptions"
                                :key="`b-${opt.value}`"
                                :value="opt.value"
                            >
                                {{ opt.label }}
                            </option>
                        </select>
                        <div class="flex items-center gap-1.5 w-full sm:w-auto justify-end sm:justify-start">
                            <button
                                type="button"
                                class="primary-chip text-xs px-3.5 py-2"
                                :disabled="!translateTargetSelectOptions.length || isTranslateTargetModalWorking"
                                @click="confirmTranslateTargetModal"
                            >
                                <span
                                    v-if="isTranslateTargetModalWorking"
                                    class="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin align-[-0.1em] mr-1.5"
                                ></span>
                                {{ $t("translator.translate") }}
                            </button>
                            <button
                                type="button"
                                class="p-2 rounded-lg text-zinc-500 hover:bg-black/5 dark:hover:bg-white/10"
                                :title="$t('common.close')"
                                :disabled="isTranslateTargetModalWorking"
                                @click="closeTranslateTargetModal"
                            >
                                <MaterialDesignIcon icon-name="close" class="size-4" />
                            </button>
                        </div>
                    </div>
                    <p
                        v-if="!translateTargetSelectOptions.length"
                        class="text-xs text-amber-700/90 dark:text-amber-300/90 -mt-0.5"
                    >
                        No translation languages available yet. Check the translator tool in Tools.
                    </p>
                </div>
            </div>
        </Transition>
    </Teleport>

    <!-- Raw Message Modal -->
    <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 scale-95"
        enter-to-class="opacity-100 scale-100"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-95"
    >
        <div
            v-if="isRawMessageModalOpen"
            class="fixed inset-0 z-150 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs"
            @click.self="isRawMessageModalOpen = false"
        >
            <div
                class="w-full max-w-2xl bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
            >
                <div
                    class="px-6 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between shrink-0"
                >
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">Raw LXMF Message</h3>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors"
                        @click="isRawMessageModalOpen = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                </div>
                <div class="p-0 overflow-y-auto bg-gray-50 dark:bg-zinc-950 grow">
                    <div class="p-6 space-y-6">
                        <!-- header / status info -->
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >Message ID</label
                                >
                                <div class="text-sm font-mono text-gray-900 dark:text-zinc-200">
                                    {{ rawMessageData.id }}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >State</label
                                >
                                <div class="flex items-center gap-2">
                                    <span
                                        class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset"
                                        :class="
                                            rawMessageData.state === 'delivered'
                                                ? 'bg-green-50 text-green-700 ring-green-600/20 dark:bg-green-900/30 dark:text-green-400'
                                                : 'bg-blue-50 text-blue-700 ring-blue-700/10 dark:bg-blue-900/30 dark:text-blue-400'
                                        "
                                    >
                                        {{ rawMessageData.state }}
                                    </span>
                                    <span v-if="rawMessageData.is_incoming" class="text-[10px] text-gray-400"
                                        >Incoming</span
                                    >
                                    <span v-else class="text-[10px] text-gray-400">Outbound</span>
                                </div>
                            </div>
                        </div>

                        <div class="space-y-1">
                            <label
                                class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                >Message Hash</label
                            >
                            <div
                                class="text-sm font-mono break-all text-gray-900 dark:text-zinc-200 bg-white dark:bg-zinc-900 p-2 rounded-sm border border-gray-100 dark:border-zinc-800"
                            >
                                {{ rawMessageData.hash }}
                            </div>
                        </div>

                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >Source Hash</label
                                >
                                <div class="text-xs font-mono break-all text-gray-900 dark:text-zinc-200">
                                    {{ rawMessageData.source_hash }}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >Destination Hash</label
                                >
                                <div class="text-xs font-mono break-all text-gray-900 dark:text-zinc-200">
                                    {{ rawMessageData.destination_hash }}
                                </div>
                            </div>
                        </div>

                        <div v-if="rawMessageHasStoredPath" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >{{ $t("messages.raw_path_interface_at_send") }}</label
                                >
                                <div class="text-sm text-gray-900 dark:text-zinc-200 wrap-break-word">
                                    {{
                                        rawMessageData.path_interface_at_send != null &&
                                        rawMessageData.path_interface_at_send !== ""
                                            ? rawMessageData.path_interface_at_send
                                            : $t("messages.raw_path_value_unknown")
                                    }}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >{{ $t("messages.raw_path_hops_at_send") }}</label
                                >
                                <div class="text-sm text-gray-900 dark:text-zinc-200">
                                    {{
                                        rawMessageData.path_hops_at_send != null
                                            ? rawMessageData.path_hops_at_send
                                            : $t("messages.raw_path_value_unknown")
                                    }}
                                </div>
                            </div>
                        </div>

                        <div
                            v-if="rawMessageData.path_finding_measure || rawMessageData.path_row_hash_hex"
                            class="grid grid-cols-1 sm:grid-cols-2 gap-4"
                        >
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >{{ $t("messages.raw_path_finding_measure") }}</label
                                >
                                <div class="text-sm font-mono text-gray-900 dark:text-zinc-200 wrap-break-word">
                                    {{ rawMessageData.path_finding_measure || $t("messages.raw_path_value_unknown") }}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >{{ $t("messages.raw_path_row_hash_rnpath") }}</label
                                >
                                <div class="flex flex-wrap items-center gap-2">
                                    <div class="text-xs font-mono break-all text-gray-900 dark:text-zinc-200">
                                        {{ rawMessageData.path_row_hash_hex || $t("messages.raw_path_value_unknown") }}
                                    </div>
                                    <button
                                        v-if="rawMessageData.path_row_hash_hex"
                                        type="button"
                                        class="text-xs text-blue-600 dark:text-blue-400 hover:underline shrink-0"
                                        @click="copyHash(rawMessageData.path_row_hash_hex)"
                                    >
                                        {{ $t("messages.copy_hash") }}
                                    </button>
                                </div>
                                <div class="text-[10px] text-gray-500 dark:text-zinc-500">
                                    {{ $t("messages.raw_path_row_hash_rnpath_hint") }}
                                </div>
                            </div>
                        </div>

                        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >Method</label
                                >
                                <div class="text-sm text-gray-900 dark:text-zinc-200 capitalize">
                                    {{ rawMessageData.method }}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >RSSI</label
                                >
                                <div class="text-sm text-gray-900 dark:text-zinc-200">
                                    {{ rawMessageData.rssi || "N/A" }}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >SNR</label
                                >
                                <div class="text-sm text-gray-900 dark:text-zinc-200">
                                    {{ rawMessageData.snr || "N/A" }}
                                </div>
                            </div>
                            <div class="space-y-1">
                                <label
                                    class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                    >Attempts</label
                                >
                                <div class="text-sm text-gray-900 dark:text-zinc-200">
                                    {{ rawMessageData.delivery_attempts }}
                                </div>
                            </div>
                        </div>

                        <div class="space-y-1">
                            <label
                                class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                >Content / App Data</label
                            >
                            <div
                                v-if="!isRawMessageBodyOversized"
                                class="text-xs font-mono bg-white dark:bg-zinc-900 p-3 rounded-sm border border-gray-100 dark:border-zinc-800 whitespace-pre-wrap break-all text-gray-800 dark:text-zinc-300"
                            >
                                {{ rawMessageData.content }}
                            </div>
                            <div
                                v-else
                                class="rounded-lg border border-amber-200/90 dark:border-amber-800/50 bg-amber-50/90 dark:bg-amber-950/25 p-3 space-y-2"
                            >
                                <p class="text-xs text-amber-950 dark:text-amber-100/90 leading-relaxed">
                                    {{
                                        $t("messages.oversized_body_notice", {
                                            count: rawMessageBodyCharCount,
                                        })
                                    }}
                                </p>
                                <button
                                    type="button"
                                    class="inline-flex items-center gap-2 rounded-lg bg-amber-700 hover:bg-amber-800 dark:bg-amber-700 dark:hover:bg-amber-600 px-3 py-2 text-xs font-semibold text-white transition-colors"
                                    @click="copyRawMessageModalContent"
                                >
                                    <MaterialDesignIcon icon-name="content-copy" class="size-4 shrink-0" />
                                    {{ $t("messages.oversized_body_copy") }}
                                </button>
                            </div>
                        </div>

                        <div v-if="rawMessageData.raw_uri" class="space-y-1">
                            <label
                                class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                >Raw LXMF URI</label
                            >
                            <div
                                class="text-[10px] font-mono bg-white dark:bg-zinc-900 p-2 rounded-sm border border-gray-100 dark:border-zinc-800 break-all text-gray-600 dark:text-zinc-400"
                            >
                                {{ rawMessageData.raw_uri }}
                            </div>
                        </div>

                        <!-- JSON fallback for full detail -->
                        <details class="group">
                            <summary
                                class="flex items-center gap-2 cursor-pointer text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500 hover:text-gray-600 dark:hover:text-zinc-300 transition-colors"
                            >
                                <MaterialDesignIcon
                                    icon-name="chevron-right"
                                    class="size-4 group-open:rotate-90 transition-transform"
                                />
                                View Full JSON Object
                            </summary>
                            <div class="mt-2 p-4 bg-black/5 dark:bg-black/20 rounded-lg overflow-x-auto">
                                <pre class="text-[10px] font-mono text-gray-600 dark:text-zinc-400">{{
                                    rawMessageJsonPreviewPretty
                                }}</pre>
                            </div>
                        </details>
                    </div>
                </div>
                <div class="px-6 py-4 border-t border-gray-100 dark:border-zinc-800 flex justify-end shrink-0">
                    <button
                        type="button"
                        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-bold transition-colors"
                        @click="isRawMessageModalOpen = false"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    </Transition>
</template>

<script>
import Utils from "../../js/Utils";
import { copyTextToClipboard, readTextFromClipboard } from "../../js/clipboardUtils.js";
import { MESSAGE_BODY_MAX_DISPLAY_CHARS, isStringTooLargeForInlineDisplay } from "../../js/messageDisplayLimits.js";
import { buildTimestampGroupedOldestFirst } from "../../js/messageTimestampGrouping.js";
import DownloadUtils from "../../js/DownloadUtils";
import { clampFloatingToViewport } from "../../js/clampFloatingToViewport.js";
import {
    canTrustScrollNearBottomHeuristic,
    isNearBottom,
    resetMessagesScrollSurface,
    scrollContainerToBottom,
    shouldLoadPreviousMessages,
} from "./conversationScroll.js";
import {
    isTelemetryOnly as isTelemetryOnlyMessage,
    hasRenderableContent as messageHasRenderableContent,
    isImageOnlyMessage as computeIsImageOnlyMessage,
    collectImageFilesFromDataTransfer as collectImagesFromDataTransfer,
    extractClipboardImageFiles,
} from "./conversationMessageHelpers.js";
import ConversationPeerHeader from "./ConversationPeerHeader.vue";
import ConversationMessageEntry from "./ConversationMessageEntry.vue";
import ConversationMessageListVirtual from "./ConversationMessageListVirtual.vue";
import { displayGroupsOldestFirst, MIN_VIRTUAL_DISPLAY_GROUPS } from "./messageListVirtual.js";
import DialogUtils from "../../js/DialogUtils";
import { getDestinationPath, postRequestPath } from "../../js/reticulumPathfinding.js";
import MicrophoneRecorder from "../../js/MicrophoneRecorder";
import WebSocketConnection from "../../js/WebSocketConnection";
import AddAudioButton from "./AddAudioButton.vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

const SCROLL_SETTLE_MAX_PASSES = 24;
const OPEN_CONVERSATION_SCROLL_PIN_MS = 900;

import SendMessageButton from "./SendMessageButton.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ContextMenuDivider from "../contextmenu/ContextMenuDivider.vue";
import ContextMenuItem from "../contextmenu/ContextMenuItem.vue";
import ContextMenuPanel from "../contextmenu/ContextMenuPanel.vue";
import AddImageButton from "./AddImageButton.vue";
import AudioWaveformPlayer from "./AudioWaveformPlayer.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import GlobalEmitter from "../../js/GlobalEmitter";
import ToastUtils from "../../js/ToastUtils";
import PaperMessageModal from "./PaperMessageModal.vue";
import GlobalState from "../../js/GlobalState";
import MarkdownRenderer from "../../js/MarkdownRenderer";
import LinkUtils from "../../js/LinkUtils";
import { findMapUriInContent, mapLinkKindFromMessage, parseMeshchatMapUri } from "../../js/mapLinkUtils.js";
import { LXMF_REACTION_EMOJIS, mergeLxmfReactionRowsIntoMessages } from "../../js/lxmfReactions";
import { createOutboundQueue } from "../../js/outboundSendQueue";
import emojiPickerEnDataUrl from "emoji-picker-element-data/en/emojibase/data.json?url";
import "emoji-picker-element";
import StickerView from "../stickers/StickerView.vue";
import InViewAnimatedImg from "./InViewAnimatedImg.vue";
import TelemetryHistoryModal from "./telemetry/TelemetryHistoryModal.vue";
import { v4 as uuidv4 } from "uuid";

export default {
    name: "ConversationViewer",
    components: {
        AddImageButton,
        ContextMenuDivider,
        ContextMenuItem,
        ContextMenuPanel,
        ConversationPeerHeader,
        MaterialDesignIcon,
        SendMessageButton,
        AddAudioButton,
        AudioWaveformPlayer,
        PaperMessageModal,
        LxmfUserIcon,
        ConversationMessageEntry,
        ConversationMessageListVirtual,
        StickerView,
        InViewAnimatedImg,
        TelemetryHistoryModal,
    },
    props: {
        config: {
            type: Object,
            required: false,
            default: null,
        },
        myLxmfAddressHash: {
            type: String,
            required: false,
            default: "",
        },
        selectedPeer: {
            type: Object,
            required: true,
        },
        conversations: {
            type: Array,
            required: true,
        },
    },
    emits: ["close", "reload-conversations", "update:selectedPeer", "update-peer-tracking"],
    data() {
        return {
            GlobalState,
            selectedPeerPath: null,
            selectedPeerLxmfStampInfo: null,
            selectedPeerSignalMetrics: null,

            lxmfMessagesRequestSequence: 0,
            chatItems: [],

            isLoadingPrevious: false,
            loadPreviousInFlight: 0,
            hasMorePrevious: true,

            newMessageDeliveryMethod: null,
            newMessageText: "",
            newMessageImages: [],
            newMessageImageUrls: [],
            newMessageAudio: null,
            newMessageTelemetry: null,
            newMessageFiles: [],
            pendingSendAsCommandOrRequest: false,
            showLocationActionMenu: false,
            isTranslatingMessage: false,
            autoScrollOnNewMessage: true,
            composeAddress: "",
            isComposeInputFocused: false,
            selectedComposeSuggestionIndex: -1,

            isShareContactModalOpen: false,
            contacts: [],
            contactsSearch: "",

            isRecordingAudioAttachment: false,
            audioAttachmentMicrophoneRecorder: null,
            audioAttachmentMicrophoneRecorderCodec: null,
            audioAttachmentRecordingStartedAt: null,
            audioAttachmentRecordingDuration: null,
            audioAttachmentRecordingTimer: null,
            androidNativeOpusAttachment: false,
            lxmfMessageAudioAttachmentCache: {},
            isDownloadingAudio: {},
            expandedMessageInfo: null,
            imageModalUrl: null,
            imageModalGallery: null,
            imageModalIndex: 0,
            isSelectedPeerBlocked: false,
            isStrangerPeer: false,
            strangerBannerDismissed: false,
            isGeneratingPaperMessage: false,
            generatedPaperMessageUri: null,
            isPaperMessageResultModalOpen: false,
            lxmfAudioModeToCodec2ModeMap: {
                // https://github.com/markqvist/LXMF/blob/master/LXMF/LXMF.py#L21
                0x01: "450PWB", // AM_CODEC2_450PWB
                0x02: "450", // AM_CODEC2_450
                0x03: "700C", // AM_CODEC2_700C
                0x04: "1200", // AM_CODEC2_1200
                0x05: "1300", // AM_CODEC2_1300
                0x06: "1400", // AM_CODEC2_1400
                0x07: "1600", // AM_CODEC2_1600
                0x08: "2400", // AM_CODEC2_2400
                0x09: "3200", // AM_CODEC2_3200
            },
            isPaperMessageModalOpen: false,
            paperMessageHash: null,
            isRawMessageModalOpen: false,
            rawMessageData: null,
            hasTranslator: false,
            translatorLanguages: [],
            translateTargetBarOpen: false,
            translateTargetModalValue: "en",
            translateTargetModalContext: null,
            isTranslateTargetModalWorking: false,
            bubbleTranslateBarIgnoreOutsideUntil: 0,
            messageBubbleTranslation: {},
            propagationNodeStatus: null,
            propagationStatusInterval: null,

            showTelemetryInChat: false,
            isTelemetryHistoryModalOpen: false,
            replyingTo: null,
            messageContextMenu: {
                show: false,
                x: 0,
                y: 0,
                chatItem: null,
                justOpened: false,
                openedFromBubble: false,
            },
            lxmfReactionEmojis: LXMF_REACTION_EMOJIS,
            reactionPickerChatItem: null,
            reactionPickerPos: null,
            reactionDragState: null,
            userStickers: [],
            userStickerPacks: [],
            activeStickerPackId: null,
            isStickerPickerOpen: false,
            emojiStickerTab: "emoji",
            emojiPickerDataUrl: emojiPickerEnDataUrl,
            stickerDropActive: false,
            composerImageDropActive: false,
            isStickerUploading: false,
            userGifs: [],
            gifDropActive: false,
            isGifUploading: false,
            now: Date.now(),
            updateTimer: null,
            sendStatusUiMs: Date.now(),
            sendStatusTickInterval: null,
            windowWidth: typeof window !== "undefined" ? window.innerWidth : 1024,
            peerHeaderCompact: false,
            peerHeaderResizeObserver: null,
            scrollBottomGen: 0,
            prevScrollWantedLoadPrevious: false,
            initialLoadActive: false,
            messagesViewportReady: true,
            openConversationScrollObserver: null,
            conversationOpenPinUntil: 0,
        };
    },
    computed: {
        visibleStickers() {
            if (this.activeStickerPackId === null) {
                return this.userStickers;
            }
            return this.userStickers.filter((s) => s.pack_id === this.activeStickerPackId);
        },
        compactPeerActions() {
            return this.windowWidth < 640 || this.peerHeaderCompact;
        },
        compactSendLayout() {
            return this.windowWidth < 640 || this.peerHeaderCompact;
        },
        emojiPickerThemeClass() {
            void GlobalState.config?.theme;
            return GlobalState.config?.theme === "dark" ? "dark" : "light";
        },
        reactionPickerStyle() {
            if (this.reactionPickerPos) {
                return {
                    left: this.reactionPickerPos.x + "px",
                    top: this.reactionPickerPos.y + "px",
                    position: "fixed",
                };
            }
            return {
                bottom: "0.5rem",
                left: "50%",
                transform: "translateX(-50%)",
            };
        },
        isRawMessageBodyOversized() {
            return isStringTooLargeForInlineDisplay(this.rawMessageData?.content);
        },
        rawMessageBodyCharCount() {
            const c = this.rawMessageData?.content;
            return typeof c === "string" ? c.length : 0;
        },
        rawMessageJsonPreviewPretty() {
            if (!this.rawMessageData) {
                return "";
            }
            const d = { ...this.rawMessageData };
            const c = d.content;
            if (typeof c === "string" && c.length > MESSAGE_BODY_MAX_DISPLAY_CHARS) {
                d.content = `[Omitted ${c.length} characters — use Copy full text above]`;
            }
            try {
                return JSON.stringify(d, null, 2);
            } catch {
                return "";
            }
        },
        rawMessageHasStoredPath() {
            const d = this.rawMessageData;
            if (!d) {
                return false;
            }
            const hops = d.path_hops_at_send;
            const iface = d.path_interface_at_send;
            return hops != null || (iface != null && iface !== "");
        },
        usesThemeOutboundBubbleColor() {
            const c = GlobalState?.config?.message_outbound_bubble_color;
            if (c == null || String(c).trim() === "") {
                return true;
            }
            return String(c).trim().toLowerCase() === "#4f46e5";
        },
        bubbleStyles() {
            void GlobalState.detailedOutboundSendStatus;
            void GlobalState.messageTimestampGroupingEnabled;
            void this.sendStatusUiMs;
            void this.usesThemeOutboundBubbleColor;
            void GlobalState.config?.theme;
            const useThemeOutbound = this.usesThemeOutboundBubbleColor;
            return (chatItem) => {
                const styles = {};
                const cfg = GlobalState?.config;
                const m = chatItem.lxmf_message;
                const isFailed = ["cancelled", "failed"].includes(m.state);

                if (isFailed) {
                    if (m.state === "failed" && m.method === "opportunistic") {
                        styles["background-color"] = "#b45309";
                        styles["color"] = "#ffffff";
                        return styles;
                    }
                    const color = cfg?.message_failed_bubble_color || "#ef4444";
                    styles["background-color"] = color;
                    styles["color"] = "#ffffff";
                } else if (chatItem.is_outbound) {
                    if (chatItem.lxmf_message?._pendingPathfinding) {
                        const raw = cfg?.message_waiting_bubble_color;
                        let hex = raw != null && String(raw).trim() !== "" ? String(raw).trim() : "#e5e7eb";
                        if (cfg?.theme === "dark" && /^#e5e7eb$/i.test(hex)) {
                            hex = "#3f3f46";
                        }
                        styles["background-color"] = hex;
                        styles["color"] = this.pickTextColorForBubbleBackground(hex);
                        styles["border"] = this.waitingBubbleBorderForHex(hex);
                        return styles;
                    }
                    if (useThemeOutbound) {
                        return {};
                    }
                    const color = cfg?.message_outbound_bubble_color || "#4f46e5";
                    styles["background-color"] = color;
                    styles["color"] = "#ffffff";
                } else if (cfg?.message_inbound_bubble_color) {
                    styles["background-color"] = cfg.message_inbound_bubble_color;
                }

                return styles;
            };
        },
        messageIconStyle() {
            const size = Number(this.config?.message_icon_size) || 28;
            return {
                width: `${size}px`,
                height: `${size}px`,
                minWidth: `${size}px`,
                minHeight: `${size}px`,
            };
        },
        sendMessagePathfindingTooltip() {
            if (GlobalState.detailedOutboundSendStatus) {
                return this.$t("messages.send_pathfinding_tooltip");
            }
            return this.$t("messages.sending_ellipsis");
        },
        composeInputPlaceholder() {
            void this.newMessageDeliveryMethod;
            const dm = this.newMessageDeliveryMethod;
            if (dm === "direct") {
                return this.$t("messages.compose_hint_direct");
            }
            if (dm === "propagated") {
                return this.$t("messages.compose_hint_propagated");
            }
            if (dm === "opportunistic") {
                return this.$t("messages.compose_hint_opportunistic");
            }
            return this.$t("messages.compose_hint_automatic");
        },
        isSyncingPropagationNode() {
            return [
                "path_requested",
                "link_establishing",
                "link_established",
                "request_sent",
                "receiving",
                "response_received",
            ].includes(this.propagationNodeStatus?.state);
        },
        blockedDestinations() {
            return GlobalState.blockedDestinations;
        },
        showUnknownContactBanner() {
            return GlobalState.config?.show_unknown_contact_banner !== false;
        },
        warnOnStrangerLinksEnabled() {
            return GlobalState.config?.warn_on_stranger_links !== false;
        },
        filteredContacts() {
            if (!this.contactsSearch) return this.contacts;
            const s = this.contactsSearch.toLowerCase();
            return this.contacts.filter(
                (c) => c.name.toLowerCase().includes(s) || c.remote_identity_hash.toLowerCase().includes(s)
            );
        },
        isMobile() {
            return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        },
        latestConversations() {
            return this.conversations.slice(0, 4);
        },
        composeSuggestions() {
            if (!this.isComposeInputFocused) return [];

            const search = this.composeAddress.toLowerCase().trim();
            const suggestions = [];
            const seenHashes = new Set();

            // 1. Check contacts
            this.contacts.forEach((c) => {
                const hash = c.remote_identity_hash;
                if (!seenHashes.has(hash)) {
                    if (!search || c.name.toLowerCase().includes(search) || hash.toLowerCase().includes(search)) {
                        suggestions.push({
                            name: c.name,
                            hash: hash,
                            type: "contact",
                            icon: "account",
                        });
                        seenHashes.add(hash);
                    }
                }
            });

            // 2. Check recent conversations
            this.conversations.forEach((c) => {
                const hash = c.destination_hash;
                if (!seenHashes.has(hash)) {
                    const name = c.custom_display_name ?? c.display_name;
                    if (!search || name.toLowerCase().includes(search) || hash.toLowerCase().includes(search)) {
                        suggestions.push({
                            name: name,
                            hash: hash,
                            type: "recent",
                            icon: "history",
                        });
                        seenHashes.add(hash);
                    }
                }
            });

            return suggestions.slice(0, 10);
        },
        canSendMessage() {
            if (this.pendingSendAsCommandOrRequest && this.selectedPeer) {
                return true;
            }
            // can send if message text is present
            const messageText = this.newMessageText.trim();
            const hasText = messageText != null && messageText !== "";

            // or if any attachments are present
            const hasAttachments =
                this.newMessageImages.length > 0 ||
                this.newMessageAudio != null ||
                this.newMessageFiles.length > 0 ||
                this.newMessageTelemetry != null;

            if (!hasText && !hasAttachments) {
                return false;
            }

            return true;
        },
        selectedPeerChatItems() {
            // get all chat items related to the selected peer
            if (this.selectedPeer) {
                const peer = (this.selectedPeer.destination_hash || "").toLowerCase();
                return this.chatItems.filter((chatItem) => {
                    if (chatItem.type === "lxmf_message") {
                        const src = (chatItem.lxmf_message.source_hash || "").toLowerCase();
                        const dst = (chatItem.lxmf_message.destination_hash || "").toLowerCase();
                        const isFromSelectedPeer = src === peer;
                        const isToSelectedPeer = dst === peer;

                        if (!(isFromSelectedPeer || isToSelectedPeer)) return false;

                        // filter telemetry if disabled
                        if (!this.showTelemetryInChat && this.isTelemetryOnly(chatItem.lxmf_message)) {
                            return false;
                        }

                        if (chatItem.lxmf_message.is_reaction) {
                            return false;
                        }

                        if (!this.hasRenderableContent(chatItem.lxmf_message)) {
                            return false;
                        }

                        return true;
                    }

                    return false;
                });
            }

            // no peer, so no chat items!
            return [];
        },
        selectedPeerTelemetryItems() {
            if (!this.selectedPeer) return [];
            const peer = (this.selectedPeer.destination_hash || "").toLowerCase();
            return this.chatItems
                .filter((chatItem) => {
                    if (chatItem.type === "lxmf_message") {
                        const src = (chatItem.lxmf_message.source_hash || "").toLowerCase();
                        const dst = (chatItem.lxmf_message.destination_hash || "").toLowerCase();
                        const isFromSelectedPeer = src === peer;
                        const isToSelectedPeer = dst === peer;

                        if (!(isFromSelectedPeer || isToSelectedPeer)) return false;

                        return this.isTelemetryOnly(chatItem.lxmf_message);
                    }
                    return false;
                })
                .reverse();
        },
        selectedPeerChatDisplayGroups() {
            const items = this.selectedPeerChatItems;
            const n = items.length;
            const groups = [];
            let r = 0;
            while (r < n) {
                const item = items[n - 1 - r];
                if (this.canMergeImageIntoImageStrip(item)) {
                    const run = [item];
                    let j = r + 1;
                    while (j < n && run.length < 12) {
                        const next = items[n - 1 - j];
                        if (next.is_outbound !== item.is_outbound) break;
                        if (!this.canMergeImageIntoImageStrip(next)) break;
                        run.push(next);
                        j++;
                    }
                    if (run.length >= 2) {
                        groups.push({
                            type: "imageGroup",
                            items: run,
                            key: run.map((x) => x.lxmf_message.hash).join("-"),
                        });
                        r = j;
                        continue;
                    }
                }
                groups.push({
                    type: "single",
                    chatItem: item,
                    key: item.lxmf_message.hash,
                });
                r++;
            }
            return groups;
        },
        selectedPeerChatDisplayGroupsOldestFirst() {
            return displayGroupsOldestFirst(this.selectedPeerChatDisplayGroups);
        },
        selectedPeerChatDisplayGroupsOldestFirstAugmented() {
            void GlobalState.messageTimestampGroupingEnabled;
            const base = this.selectedPeerChatDisplayGroupsOldestFirst;
            if (!GlobalState.messageTimestampGroupingEnabled) {
                return buildTimestampGroupedOldestFirst(base, { groupingEnabled: false });
            }
            return buildTimestampGroupedOldestFirst(base);
        },
        selectedPeerChatDisplayGroupsNewestFirstAugmented() {
            const a = this.selectedPeerChatDisplayGroupsOldestFirstAugmented;
            if (!a?.length) {
                return [];
            }
            return a.slice().reverse();
        },
        conversationViewerSelf() {
            return this;
        },
        useVirtualMessageList() {
            const n = this.selectedPeerChatDisplayGroups.length;
            if (n < MIN_VIRTUAL_DISPLAY_GROUPS) {
                return false;
            }
            return GlobalState?.config?.message_list_virtualization !== false;
        },
        oldestMessageId() {
            if (!this.selectedPeer) {
                return null;
            }
            const peer = (this.selectedPeer.destination_hash || "").toLowerCase();
            let minId = null;
            for (const chatItem of this.chatItems) {
                if (chatItem.type !== "lxmf_message") {
                    continue;
                }
                const m = chatItem.lxmf_message;
                const src = (m.source_hash || "").toLowerCase();
                const dst = (m.destination_hash || "").toLowerCase();
                if (src !== peer && dst !== peer) {
                    continue;
                }
                const id = m.id;
                if (id == null) {
                    continue;
                }
                if (minId == null || id < minId) {
                    minId = id;
                }
            }
            return minId;
        },
        hasFailedOrCancelledMessages() {
            return this.selectedPeerChatItems.some(
                (item) => item.is_outbound && ["failed", "cancelled"].includes(item.lxmf_message?.state)
            );
        },
        telemetryModalGradientSuffix() {
            const h = this.selectedPeer?.destination_hash || "default";
            return h.replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 24) || "default";
        },
        translateTargetSelectOptions() {
            const seen = new Map();
            for (const l of this.translatorLanguages || []) {
                if (l && l.code) {
                    const c = String(l.code).toLowerCase().slice(0, 8);
                    if (!seen.has(c)) {
                        const name = l.name || c;
                        seen.set(c, { value: c, label: `${name} (${c})` });
                    }
                }
            }
            return Array.from(seen.values()).sort((a, b) =>
                a.label.localeCompare(b.label, undefined, { sensitivity: "base" })
            );
        },
    },
    watch: {
        selectedPeer: {
            handler(newPeer, oldPeer) {
                this.messageBubbleTranslation = {};
                if (oldPeer) {
                    this.saveDraft(oldPeer.destination_hash);
                }
                this.teardownPeerHeaderResizeObserver();
                this.disconnectOpenConversationScrollObserver();
                this.scrollBottomGen += 1;
                this.autoScrollOnNewMessage = true;
                this.messagesViewportReady = false;
                if (!newPeer) {
                    this.peerHeaderCompact = false;
                }
                this.checkIfSelectedPeerBlocked();
                this.strangerBannerDismissed = false;
                this.checkIfStrangerPeer();
                this.prevScrollWantedLoadPrevious = false;
                this.initialLoad();
                this.$nextTick(() => {
                    this.resetStaleConversationScrollSurface();
                });
                if (newPeer) {
                    this.loadDraft(newPeer.destination_hash);
                    this.$nextTick(() => this.setupPeerHeaderResizeObserver());
                }
            },
            immediate: true,
        },
        useVirtualMessageList: {
            handler(value) {
                if (!value && !this.initialLoadActive) {
                    this.messagesViewportReady = true;
                }
            },
        },
        newMessageText() {
            this.$nextTick(() => {
                this.adjustTextareaHeight();
            });
        },
        config: {
            handler() {
                this.checkTranslator();
            },
            deep: true,
        },
        blockedDestinations: {
            handler() {
                this.checkIfSelectedPeerBlocked();
            },
            deep: true,
        },
        selectedPeerChatItems: {
            async handler() {
                await this.processAudioForSelectedPeerChatItems();
                this.$nextTick(() => this._scheduleOutboundSendStatusTick());
            },
            deep: true,
        },
    },
    created() {
        this._outboundQueue = createOutboundQueue((job) => this._executeOutboundSendJob(job));
        this.sendStatusUiMs = Date.now();
    },
    mounted() {
        this.updateTimer = setInterval(() => {
            this.now = Date.now();
        }, 30000); // Update every 30 seconds

        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        // listen for compose new message event
        GlobalEmitter.on("compose-new-message", this.onComposeNewMessageEvent);

        // listen for contact updates to refresh stranger banner
        GlobalEmitter.on("contact-updated", this.onContactUpdatedForBanner);

        // check translator
        this.checkTranslator();

        // fetch contacts for suggestions
        this.fetchContacts();

        // fetch propagation status
        this.updatePropagationNodeStatus();
        this.propagationStatusInterval = setInterval(() => {
            this.updatePropagationNodeStatus();
        }, 2000);

        this._scheduleOutboundSendStatusTick();
        this.loadUserStickers();

        this._onWindowResize = () => {
            this.windowWidth = window.innerWidth;
        };
        window.addEventListener("resize", this._onWindowResize);
        this._visualViewport = typeof window !== "undefined" ? window.visualViewport : null;
        if (this._visualViewport) {
            this._visualViewport.addEventListener("resize", this._onWindowResize);
            this._visualViewport.addEventListener("scroll", this._onWindowResize);
        }
    },
    beforeUnmount() {
        this.scrollBottomGen += 1;
        this.teardownPeerHeaderResizeObserver();
        if (this.selectedPeer) {
            this.saveDraft(this.selectedPeer.destination_hash);
        }
        if (this._onWindowResize) {
            window.removeEventListener("resize", this._onWindowResize);
            if (this._visualViewport) {
                this._visualViewport.removeEventListener("resize", this._onWindowResize);
                this._visualViewport.removeEventListener("scroll", this._onWindowResize);
                this._visualViewport = null;
            }
            this._onWindowResize = null;
        }
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
        if (this.sendStatusTickInterval) {
            clearInterval(this.sendStatusTickInterval);
            this.sendStatusTickInterval = null;
        }
        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
        GlobalEmitter.off("compose-new-message", this.onComposeNewMessageEvent);
        GlobalEmitter.off("contact-updated", this.onContactUpdatedForBanner);
        if (this.propagationStatusInterval) {
            clearInterval(this.propagationStatusInterval);
        }
        this.disconnectOpenConversationScrollObserver();
    },
    methods: {
        isMeshChatXAndroid() {
            return (
                window.MeshChatXAndroid &&
                typeof window.MeshChatXAndroid.getPlatform === "function" &&
                window.MeshChatXAndroid.getPlatform() === "android"
            );
        },
        androidNativeWavAttachmentAllowed() {
            const b = window.MeshChatXAndroid;
            if (!b || typeof b.startNativeWavAttachment !== "function") {
                return false;
            }
            if (typeof b.isNativeWavAttachmentAvailable === "function") {
                return b.isNativeWavAttachmentAvailable() === true;
            }
            if (typeof b.isNativePcmAudioAvailable === "function") {
                return b.isNativePcmAudioAvailable() === true;
            }
            return true;
        },
        setupPeerHeaderResizeObserver() {
            this.teardownPeerHeaderResizeObserver();
            const root = this.$refs.conversationPeerHeader;
            const el = root && root.$el ? root.$el : root;
            if (!el || typeof ResizeObserver === "undefined") {
                return;
            }
            const threshold = 820;
            const apply = (width) => {
                this.peerHeaderCompact = width > 0 && width < threshold;
            };
            this.peerHeaderResizeObserver = new ResizeObserver((entries) => {
                const w = entries[0]?.contentRect?.width ?? 0;
                apply(w);
            });
            this.peerHeaderResizeObserver.observe(el);
            apply(el.clientWidth);
        },
        teardownPeerHeaderResizeObserver() {
            if (this.peerHeaderResizeObserver) {
                this.peerHeaderResizeObserver.disconnect();
                this.peerHeaderResizeObserver = null;
            }
        },
        renderMarkdown(text) {
            return MarkdownRenderer.render(text);
        },
        messageMarkdownSingleEmoji(chatItem) {
            const c = chatItem?.lxmf_message?.content;
            if (!c) {
                return false;
            }
            if (this.isMessageBodyTooLargeForDisplay(chatItem)) {
                return false;
            }
            if (this.getParsedItems(chatItem)?.isOnlyPaperMessage) {
                return false;
            }
            if (this.getParsedItems(chatItem)?.isOnlyMapLink) {
                return false;
            }
            if (this.shouldHideAutoImageCaption(chatItem)) {
                return false;
            }
            return MarkdownRenderer.isSingleEmojiMessage(c);
        },
        messageMarkdownFontSizePx(chatItem) {
            const base = Number(this.config?.message_font_size) || 14;
            if (this.messageMarkdownSingleEmoji(chatItem)) {
                return Math.round(base * 2.75);
            }
            return base;
        },
        async handleMessageClick(event) {
            const hex32 = /^[a-fA-F0-9]{32}$/;
            const nomadnetLink = event.target.closest(".nomadnet-link");
            if (nomadnetLink) {
                event.preventDefault();
                const url = nomadnetLink.getAttribute("data-nomadnet-url");
                if (url) {
                    const [hash, ...pathParts] = url.split(":");
                    const path = pathParts.join(":");
                    if (!hex32.test(hash)) {
                        return;
                    }
                    const routeName = this.$route.meta.isPopout ? "nomadnetwork-popout" : "nomadnetwork";
                    this.$router.push({
                        name: routeName,
                        params: { destinationHash: hash },
                        query: { path: path },
                    });
                }
                return;
            }

            const lxmfLink = event.target.closest(".lxmf-link");
            if (lxmfLink) {
                event.preventDefault();
                const address = lxmfLink.getAttribute("data-lxmf-address");
                if (address && hex32.test(address)) {
                    this.$router.push({
                        name: "messages",
                        params: { destinationHash: address },
                    });
                }
                return;
            }

            const standardLink = event.target.closest("a[href]");
            if (!standardLink) {
                return;
            }

            const hrefRaw = String(standardLink.getAttribute("href") || "").trim();
            const safeHttp = LinkUtils.httpUrlHrefOrNull(hrefRaw);
            if (!safeHttp) {
                event.preventDefault();
                return;
            }

            event.preventDefault();
            if (this.isStrangerPeer && this.warnOnStrangerLinksEnabled) {
                const proceed = await DialogUtils.confirm(
                    this.$t("messages.stranger_link_open_confirm", { url: safeHttp })
                );
                if (!proceed) {
                    return;
                }
            }

            window.open(safeHttp, "_blank", "noopener,noreferrer");
        },
        async updatePropagationNodeStatus() {
            try {
                const response = await window.api.get("/api/v1/lxmf/propagation-node/status");
                this.propagationNodeStatus = response.data.propagation_node_status;
            } catch {
                // do nothing on error
            }
        },
        async syncPropagationNode() {
            GlobalEmitter.emit("sync-propagation-node");
        },
        async copyMyAddress() {
            const ok = await copyTextToClipboard(this.myLxmfAddressHash);
            if (ok) {
                ToastUtils.success(this.$t("messages.address_copied"));
            } else {
                ToastUtils.error(this.$t("messages.clipboard_write_unavailable"));
            }
        },
        focusComposeInput() {
            this.$nextTick(() => {
                const input = document.getElementById("compose-input");
                if (input) {
                    input.focus();
                }
            });
        },
        async fetchContacts() {
            try {
                const response = await window.api.get("/api/v1/telephone/contacts");
                this.contacts = response.data?.contacts ?? (Array.isArray(response.data) ? response.data : []);
            } catch (e) {
                console.log("Failed to fetch contacts:", e);
            }
        },
        async checkTranslator() {
            const argosOn = this.config?.translator_argos_enabled;
            const libreOn = this.config?.translator_libretranslate_enabled;
            if (!argosOn && !libreOn) {
                this.hasTranslator = false;
                this.translatorLanguages = [];
                return;
            }
            try {
                const response = await window.api.get("/api/v1/translator/languages");
                const raw = response.data.languages || [];
                this.translatorLanguages = raw.filter(
                    (lang) => (lang.source === "argos" && argosOn) || (lang.source === "libretranslate" && libreOn)
                );
                this.hasTranslator = this.translatorLanguages.length > 0;
            } catch (e) {
                console.log("Failed to check translator:", e);
                this.hasTranslator = false;
            }
        },
        normalizedLocaleCode(loc) {
            if (loc == null) {
                return "en";
            }
            const s = String(loc);
            const t = s.split(/[-_]/)[0] || s;
            const c = t.toLowerCase();
            if (c.length < 2) {
                return "en";
            }
            return c.slice(0, 2);
        },
        composeSourceLangForTranslate() {
            const cfg = this.config;
            const a = cfg?.translator_argos_enabled;
            const l = cfg?.translator_libretranslate_enabled;
            if (!a && !l) {
                return this.normalizedLocaleCode(cfg?.language || this.$i18n.locale) || "en";
            }

            return "auto";
        },
        _readSavedTranslateTargetLang() {
            let v = null;
            try {
                v =
                    localStorage.getItem("meshchatx.translateTargetLang") ||
                    localStorage.getItem("meshchatx.composeTranslateTargetLang");
            } catch {
                v = null;
            }
            if (!v) {
                return null;
            }
            return String(v).toLowerCase().slice(0, 8);
        },
        _persistTranslateTargetLang(targetLang) {
            const t = String(targetLang || "")
                .toLowerCase()
                .slice(0, 8);
            if (!t) {
                return;
            }
            try {
                localStorage.setItem("meshchatx.translateTargetLang", t);
                localStorage.setItem("meshchatx.composeTranslateTargetLang", t);
            } catch {
                /* empty */
            }
        },
        defaultTranslateTargetForModal() {
            const source = String(this.composeSourceLangForTranslate() || "").toLowerCase();
            const opts = this.translateTargetSelectOptions;
            if (!opts.length) {
                return "en";
            }
            const fromStorage = this._readSavedTranslateTargetLang();
            if (fromStorage && opts.some((o) => o.value === fromStorage) && fromStorage !== source) {
                return fromStorage;
            }
            const diff = opts.find((o) => o.value !== source);
            if (diff) {
                return diff.value;
            }
            return opts[0].value;
        },
        defaultBubbleTranslateTargetForModal() {
            const source = this._bubbleTranslateSourcePreview();
            const opts = this.translateTargetSelectOptions;
            if (!opts.length) {
                return "en";
            }
            const fromStorage = this._readSavedTranslateTargetLang();
            if (fromStorage && opts.some((o) => o.value === fromStorage)) {
                if (String(source).toLowerCase() === "auto") {
                    return fromStorage;
                }
                const s2 = String(source).toLowerCase().slice(0, 2);
                if (fromStorage !== s2) {
                    return fromStorage;
                }
            }
            if (String(source).toLowerCase() === "auto") {
                return opts[0].value;
            }
            const s2 = String(source).toLowerCase().slice(0, 2);
            const diff = opts.find((o) => o.value !== s2);
            return diff ? diff.value : opts[0].value;
        },
        _bubbleTranslateSourcePreview() {
            const cfg = this.config;
            const a = cfg?.translator_argos_enabled;
            const l = cfg?.translator_libretranslate_enabled;
            if (!a && !l) {
                return this.normalizedLocaleCode(cfg?.language || this.$i18n.locale) || "en";
            }
            return "auto";
        },
        onTranslateTargetBarClickOutside() {
            if (this.isTranslateTargetModalWorking) {
                return;
            }
            const now = typeof performance !== "undefined" ? performance.now() : Date.now();
            if (now < this.bubbleTranslateBarIgnoreOutsideUntil) {
                return;
            }
            if (this.translateTargetModalContext?.type === "bubble") {
                this.closeTranslateTargetModal();
            }
        },
        async toggleComposeTranslateTargetBar() {
            if (this.translateTargetBarOpen && this.translateTargetModalContext?.type === "compose") {
                this.closeTranslateTargetModal();
                return;
            }
            if (!this.newMessageText?.trim() || this.isTranslatingMessage) {
                return;
            }
            if (!this.translatorLanguages || this.translatorLanguages.length === 0) {
                await this.checkTranslator();
            }
            this.translateTargetModalContext = { type: "compose" };
            this.translateTargetModalValue = this.defaultTranslateTargetForModal();
            this.translateTargetBarOpen = true;
        },
        openBubbleTranslateFromContextMenu() {
            const chatItem = this.messageContextMenu.chatItem;
            this.messageContextMenu.show = false;
            if (!chatItem || !this.canTranslateMessageBubbleFromMenu(chatItem)) {
                return;
            }
            const doOpen = async () => {
                if (!this.translatorLanguages || this.translatorLanguages.length === 0) {
                    await this.checkTranslator();
                }
                if (!this.canTranslateMessageBubbleFromMenu(chatItem)) {
                    return;
                }
                const t = typeof performance !== "undefined" ? performance.now() : Date.now();
                this.bubbleTranslateBarIgnoreOutsideUntil = t + 500;
                this.translateTargetModalContext = { type: "bubble", chatItem };
                this.translateTargetModalValue = this.defaultBubbleTranslateTargetForModal();
                this.translateTargetBarOpen = true;
            };
            queueMicrotask(() => {
                void doOpen();
            });
        },
        closeTranslateTargetModal() {
            if (this.isTranslateTargetModalWorking) {
                return;
            }
            this.translateTargetBarOpen = false;
            this.translateTargetModalContext = null;
        },
        async confirmTranslateTargetModal() {
            if (this.isTranslateTargetModalWorking || !this.translateTargetSelectOptions.length) {
                return;
            }
            const targetLang = this.translateTargetModalValue;
            const ctx = this.translateTargetModalContext;
            if (!ctx) {
                return;
            }
            this.isTranslateTargetModalWorking = true;
            try {
                this._persistTranslateTargetLang(targetLang);
                if (ctx.type === "compose") {
                    await this.applyComposeTranslation(targetLang);
                } else if (ctx.type === "bubble" && ctx.chatItem) {
                    await this.applyBubbleMessageTranslation(ctx.chatItem, targetLang);
                }
                this.translateTargetBarOpen = false;
                this.translateTargetModalContext = null;
            } catch (e) {
                console.error(e);
            } finally {
                this.isTranslateTargetModalWorking = false;
            }
        },
        canTranslateMessageBubbleFromMenu(chatItem) {
            if (!this.hasTranslator || !chatItem || chatItem.lxmf_message?.is_reaction) {
                return false;
            }
            const t = this.copyableMessagePlainText(chatItem);
            if (!t) {
                return false;
            }
            if (this.isMessageBodyTooLargeForDisplay(chatItem)) {
                return false;
            }
            return true;
        },
        async applyComposeTranslation(targetLang) {
            if (!this.newMessageText?.trim()) {
                return;
            }
            const cfg = this.config;
            const a = cfg?.translator_argos_enabled;
            const l = cfg?.translator_libretranslate_enabled;
            if (!a && !l) {
                return;
            }
            const useArgos = Boolean(a) && !l;
            const target = String(targetLang).toLowerCase().slice(0, 8);
            const source_lang = "auto";
            this.isTranslatingMessage = true;
            try {
                const response = await window.api.post("/api/v1/translator/translate", {
                    text: this.newMessageText,
                    source_lang,
                    target_lang: target,
                    use_argos: useArgos,
                });
                if (response.data.translated_text) {
                    this.newMessageText = response.data.translated_text;
                    this.$nextTick(() => {
                        this.adjustTextareaHeight();
                    });
                }
            } catch (e) {
                console.error("Translation failed:", e);
                ToastUtils.error(this.$t("messages.translation_failed"));
                throw e;
            } finally {
                this.isTranslatingMessage = false;
            }
        },
        async applyBubbleMessageTranslation(chatItem, targetLang) {
            const hash = chatItem?.lxmf_message?.hash;
            const text = this.copyableMessagePlainText(chatItem);
            if (!hash || !text) {
                return;
            }
            const cfg = this.config;
            const a = cfg?.translator_argos_enabled;
            const l = cfg?.translator_libretranslate_enabled;
            if (!a && !l) {
                return;
            }
            const useArgos = Boolean(a) && !l;
            const target = String(targetLang).toLowerCase().slice(0, 8);
            const source_lang = "auto";
            this.messageBubbleTranslation[hash] = {
                loading: true,
                showOriginal: false,
                translatedText: "",
                resolvedSourceLang: "",
                targetLang: target,
                source: "",
            };
            try {
                const response = await window.api.post("/api/v1/translator/translate", {
                    text,
                    source_lang,
                    target_lang: target,
                    use_argos: useArgos,
                });
                const data = response.data;
                this.messageBubbleTranslation[hash] = {
                    loading: false,
                    showOriginal: false,
                    translatedText: data.translated_text || "",
                    resolvedSourceLang: data.source_lang || source_lang,
                    targetLang: data.target_lang || target,
                    source: data.source || "",
                };
            } catch (e) {
                delete this.messageBubbleTranslation[hash];
                console.error("Translation failed:", e);
                ToastUtils.error(this.$t("messages.translation_failed"));
            }
        },
        setBubbleMessageShowOriginal(hash, show) {
            const t = this.messageBubbleTranslation[hash];
            if (!t || !t.translatedText) {
                return;
            }
            this.messageBubbleTranslation[hash] = {
                ...t,
                showOriginal: show,
            };
        },
        bubbleViewModel(chatItem) {
            const c = chatItem.lxmf_message?.content;
            if (!c) {
                return { kind: "html", textForRender: "", singleEmoji: false, showFooter: false };
            }
            const h = chatItem.lxmf_message.hash;
            const tr = this.messageBubbleTranslation[h];
            if (tr?.loading) {
                return { kind: "loading" };
            }
            const hasTr = tr && tr.translatedText;
            const showingTranslated = hasTr && !tr.showOriginal;
            const textForRender = showingTranslated ? tr.translatedText : c;
            let singleEmoji = this.messageMarkdownSingleEmoji(chatItem);
            if (showingTranslated) {
                singleEmoji =
                    !this.isMessageBodyTooLargeForDisplay(chatItem) &&
                    MarkdownRenderer.isSingleEmojiMessage(tr.translatedText);
            }
            return {
                kind: "html",
                textForRender,
                isTranslatedView: showingTranslated,
                showFooter: Boolean(hasTr),
                showOriginalLink: hasTr && !tr.showOriginal,
                showTranslationLink: hasTr && tr.showOriginal,
                fromCode: (tr && tr.resolvedSourceLang) || "–",
                toCode: (tr && tr.targetLang) || "–",
                messageHash: h,
                singleEmoji,
            };
        },
        bubbleMessageBodyFontSizePx(vm) {
            const base = Number(this.config?.message_font_size) || 14;
            if (vm && vm.singleEmoji) {
                return Math.round(base * 2.75);
            }
            return base;
        },
        async translateMessage() {
            this.translateTargetModalValue = this.defaultTranslateTargetForModal();
            await this.applyComposeTranslation(this.translateTargetModalValue);
        },
        adjustTextareaHeight() {
            const textarea = this.$refs["message-input"];
            if (textarea) {
                textarea.style.height = "auto";
                textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px";
            }
        },
        checkIfSelectedPeerBlocked() {
            if (!this.selectedPeer) {
                this.isSelectedPeerBlocked = false;
                return;
            }
            this.isSelectedPeerBlocked = GlobalState.blockedDestinations.some(
                (b) => b.destination_hash === this.selectedPeer.destination_hash
            );
        },
        onContactUpdatedForBanner(data) {
            if (this.selectedPeer?.destination_hash === data?.remote_identity_hash) {
                this.isStrangerPeer = false;
                this.strangerBannerDismissed = true;
            }
        },
        async checkIfStrangerPeer() {
            if (!this.selectedPeer) {
                this.isStrangerPeer = false;
                return;
            }
            if (this.selectedPeer.is_contact || this.selectedPeer.contact_image) {
                this.isStrangerPeer = false;
                return;
            }
            try {
                const response = await window.api.get(
                    `/api/v1/telephone/contacts/check/${this.selectedPeer.destination_hash}`
                );
                this.isStrangerPeer = !response.data.is_contact;
            } catch {
                this.isStrangerPeer = !this.selectedPeer.is_contact && !this.selectedPeer.contact_image;
            }
        },
        async addStrangerAsContact() {
            if (!this.selectedPeer) return;
            try {
                const displayName =
                    this.selectedPeer.custom_display_name ?? this.selectedPeer.display_name ?? "Unknown";
                await fetch(`/api/v1/telephone/contacts`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        lxmf_address: this.selectedPeer.destination_hash,
                        name: displayName,
                    }),
                });
                this.isStrangerPeer = false;
                this.strangerBannerDismissed = true;
                GlobalEmitter.emit("contact-updated", {
                    remote_identity_hash: this.selectedPeer.destination_hash,
                });
                this.$emit("reload-conversations");
            } catch (e) {
                console.error("Failed to add contact:", e);
            }
        },
        loadDraft(destinationHash) {
            try {
                const drafts = JSON.parse(localStorage.getItem("meshchat.drafts") || "{}");
                this.newMessageText = drafts[destinationHash] || "";
                this.$nextTick(() => {
                    this.adjustTextareaHeight();
                });
            } catch (e) {
                console.error("Failed to load draft:", e);
            }
        },
        saveDraft(destinationHash) {
            try {
                const drafts = JSON.parse(localStorage.getItem("meshchat.drafts") || "{}");
                if (this.newMessageText) {
                    drafts[destinationHash] = this.newMessageText;
                } else {
                    delete drafts[destinationHash];
                }
                localStorage.setItem("meshchat.drafts", JSON.stringify(drafts));
            } catch (e) {
                console.error("Failed to save draft:", e);
            }
        },
        close() {
            this.$emit("close");
        },
        getMessagesScrollElement() {
            return this.$refs.messagesScroll ?? null;
        },
        onMessagesScroll(event) {
            const element = event.target;
            const nearBottom = isNearBottom(element);
            this.autoScrollOnNewMessage = nearBottom;
            if (!nearBottom) {
                this.conversationOpenPinUntil = 0;
                this.disconnectOpenConversationScrollObserver();
            }

            const wantLoad = shouldLoadPreviousMessages(element);
            if (wantLoad && !this.prevScrollWantedLoadPrevious) {
                this.loadPrevious();
            }
            this.prevScrollWantedLoadPrevious = wantLoad;
        },
        async initialLoad() {
            this.initialLoadActive = true;
            this.messagesViewportReady = false;
            this.chatItems = [];
            this.hasMorePrevious = true;
            this.selectedPeerPath = null;
            this.selectedPeerLxmfStampInfo = null;
            this.selectedPeerSignalMetrics = null;
            if (!this.selectedPeer) {
                this.initialLoadActive = false;
                this.messagesViewportReady = true;
                return;
            }

            await this.$nextTick();
            this.resetStaleConversationScrollSurface();

            this.getPeerPath();
            this.getPeerLxmfStampInfo();
            this.getPeerSignalMetrics();
            this.warmPathToPeer();

            this.markConversationAsRead(this.selectedPeer);

            await this.loadPrevious();

            await this.$nextTick();
            await this.$nextTick();
            await new Promise((resolve) => {
                requestAnimationFrame(() => resolve());
            });

            this.initialLoadActive = false;
            this.scrollMessagesToBottom({ pinAfter: true });

            this.autoLoadAudioAttachments();
        },
        async loadPrevious() {
            // Pagination requests must not overlap. Initial page loads (empty thread) must still run
            // if a previous peer's fetch or a scroll load left isLoadingPrevious true; otherwise
            // initialLoad clears chatItems and loadPrevious returns without fetching (empty UI).
            if (this.isLoadingPrevious && this.oldestMessageId != null) {
                return;
            }

            this.loadPreviousInFlight += 1;
            this.isLoadingPrevious = true;

            try {
                const seq = ++this.lxmfMessagesRequestSequence;

                // fetch lxmf messages from "us to destination" and from "destination to us"
                const pageSize = 30;
                const response = await window.api.get(
                    `/api/v1/lxmf-messages/conversation/${this.selectedPeer.destination_hash}`,
                    {
                        params: {
                            count: pageSize,
                            order: "desc",
                            after_id: this.oldestMessageId,
                        },
                    }
                );

                if (seq !== this.lxmfMessagesRequestSequence) {
                    return;
                }

                // convert lxmf messages to chat items
                const chatItems = [];
                const rawList = response.data?.lxmf_messages;
                const lxmfMessages = mergeLxmfReactionRowsIntoMessages(Array.isArray(rawList) ? rawList : []);
                const myHash = (this.myLxmfAddressHash || "").toLowerCase();
                for (const lxmfMessage of lxmfMessages) {
                    const src = (lxmfMessage.source_hash || "").toLowerCase();
                    chatItems.push({
                        type: "lxmf_message",
                        is_outbound: myHash !== "" && myHash === src,
                        lxmf_message: lxmfMessage,
                    });
                }

                const scrollEl = this.$refs.messagesScroll;
                const needsAnchor = scrollEl && this.chatItems.length > 0 && this.oldestMessageId != null;

                if (needsAnchor) {
                    scrollEl.style.overflowY = "hidden";
                }

                const prevScrollHeight = scrollEl ? scrollEl.scrollHeight : 0;
                const prevScrollTop = scrollEl ? scrollEl.scrollTop : 0;

                const seenHashes = new Set(
                    this.chatItems.map((c) => c.lxmf_message?.hash).filter((h) => h != null && h !== "")
                );
                for (const chatItem of chatItems) {
                    const h = chatItem.lxmf_message?.hash;
                    if (h && seenHashes.has(h)) {
                        continue;
                    }
                    if (h) {
                        seenHashes.add(h);
                    }
                    this.chatItems.unshift(chatItem);
                }

                if (needsAnchor) {
                    this.$nextTick(() => {
                        const newScrollHeight = scrollEl.scrollHeight;
                        const delta = newScrollHeight - prevScrollHeight;
                        scrollEl.scrollTop = prevScrollTop + delta;
                        scrollEl.style.overflowY = "";
                    });
                }

                if (chatItems.length < pageSize) {
                    this.hasMorePrevious = false;
                }

                // auto load audio
                this.autoLoadAudioAttachments();
            } catch {
                this.hasMorePrevious = false;
            } finally {
                this.loadPreviousInFlight = Math.max(0, this.loadPreviousInFlight - 1);
                this.isLoadingPrevious = this.loadPreviousInFlight > 0;
            }
        },
        getParsedItems(chatItem) {
            const content = chatItem.lxmf_message.content;
            if (!content) return null;

            const items = {
                contact: null,
                paperMessage: null,
                mapLink: null,
            };

            // Parse contact: Contact: ivan <ca314c30b27eacec5f6ca6ac504e94c9> [LXMF: ...] [LXST: ...]
            const contactMatch = content.match(
                // eslint-disable-next-line security/detect-unsafe-regex -- bounded pattern, single-line contact header
                /^Contact:\s+(.+?)\s+<([a-fA-F0-9]{32})>(?:\s+\[LXMF:\s+([a-fA-F0-9]{32})\])?(?:\s+\[LXST:\s+([a-fA-F0-9]{32})\])?/i
            );
            if (contactMatch) {
                const contactHash = contactMatch[2];
                const lxmfAddress = contactMatch[3];
                const lxstAddress = contactMatch[4];

                // try to find enriched info from existing conversations/peers
                const existing = this.conversations.find(
                    (c) =>
                        c.destination_hash === contactHash ||
                        c.destination_hash === lxmfAddress ||
                        c.destination_hash === lxstAddress
                );

                items.contact = {
                    name: contactMatch[1],
                    hash: contactHash,
                    lxmf_address: lxmfAddress,
                    lxst_address: lxstAddress,
                    custom_image: existing?.contact_image,
                    lxmf_user_icon: existing?.lxmf_user_icon,
                };
            }

            // Parse paper message link
            const paperMatch = content.match(/(lxm|lxmf):\/\/[a-zA-Z0-9+/=._-]+/i);
            if (paperMatch) {
                items.paperMessage = paperMatch[0];
                // if content is only the paper message, or it already contains the detected text,
                // we'll hide the raw content div to avoid double rendering.
                const trimmedContent = content.trim();
                if (trimmedContent === items.paperMessage || trimmedContent.includes("Paper Message detected")) {
                    items.isOnlyPaperMessage = true;
                }
            }

            const mapUri = findMapUriInContent(content);
            if (mapUri && !items.paperMessage) {
                const parsed = parseMeshchatMapUri(mapUri);
                if (parsed) {
                    const kind = mapLinkKindFromMessage(content, parsed);
                    let t = content.trim().replace(mapUri, "").trim();
                    t = t
                        .replace(/^MeshChatX\s+map\s+ping:\s*/i, "")
                        .replace(/^MeshChatX\s+map:\s*/i, "")
                        .trim();
                    items.mapLink = { uri: mapUri, parsed, kind };
                    if (t === "") {
                        items.isOnlyMapLink = true;
                    }
                }
            }

            return items;
        },
        async addContact(name, hash, lxmf_address = null, lxst_address = null) {
            try {
                // Check if contact already exists
                const checkResponse = await window.api.get(`/api/v1/telephone/contacts/check/${hash}`);
                if (checkResponse.data?.id) {
                    ToastUtils.info(`${name} is already in your contacts`);
                    return;
                }

                await window.api.post("/api/v1/telephone/contacts", {
                    name: name,
                    remote_identity_hash: hash,
                    lxmf_address: lxmf_address,
                    lxst_address: lxst_address,
                });
                ToastUtils.success(`Added ${name} to contacts`);
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("messages.failed_add_contact"));
            }
        },
        async ingestPaperMessage(uri) {
            try {
                WebSocketConnection.send(
                    JSON.stringify({
                        type: "lxm.ingest_uri",
                        uri: uri,
                    })
                );
                ToastUtils.info(this.$t("messages.ingesting_paper_message"));
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("messages.failed_ingest_paper"));
            }
        },
        async generatePaperMessageFromComposition() {
            if (!this.canSendMessage) return;

            this.isGeneratingPaperMessage = true;
            WebSocketConnection.send(
                JSON.stringify({
                    type: "lxm.generate_paper_uri",
                    destination_hash: this.selectedPeer.destination_hash,
                    content: this.newMessageText,
                })
            );
        },
        async onWebsocketMessage(message) {
            const json = JSON.parse(message.data);
            switch (json.type) {
                case "announce": {
                    // update stamp info and signal metrics if an announce is received from the selected peer
                    if (json.announce.destination_hash === this.selectedPeer?.destination_hash) {
                        await this.getPeerPath();
                        await this.getPeerLxmfStampInfo();
                        await this.getPeerSignalMetrics();
                    }
                    break;
                }
                case "lxmf.delivery": {
                    this.onLxmfMessageReceived(json.lxmf_message);
                    await this.getPeerPath();
                    await this.getPeerSignalMetrics();
                    break;
                }
                case "lxmf_message_created": {
                    this.onLxmfMessageCreated(json.lxmf_message);
                    await this.getPeerPath();
                    break;
                }
                case "lxmf_message_state_updated": {
                    this.onLxmfMessageUpdated(json.lxmf_message);
                    break;
                }
                case "lxmf_message_deleted": {
                    this.onLxmfMessageDeleted(json.hash);
                    break;
                }
                case "lxm.generate_paper_uri.result": {
                    this.isGeneratingPaperMessage = false;
                    if (json.status === "success") {
                        this.generatedPaperMessageUri = json.uri;
                        this.isPaperMessageResultModalOpen = true;
                    } else {
                        ToastUtils.error(json.message);
                    }
                    break;
                }
                case "lxm.ingest_uri.result": {
                    // Handled in App.vue or MessagesPage.vue
                    break;
                }
            }
        },
        openLXMFAddress() {
            GlobalEmitter.emit("compose-new-message");
        },
        onComposeNewMessageEvent(destinationHash) {
            if (!this.selectedPeer && !destinationHash) {
                this.$nextTick(() => {
                    const composeInput = document.getElementById("compose-input");
                    if (composeInput) {
                        composeInput.focus();
                    }
                });
            }
        },
        async onComposeSubmit() {
            if (!this.composeAddress || this.composeAddress.trim() === "") {
                return;
            }
            let destinationHash = this.composeAddress.trim();
            this.composeAddress = "";
            await this.handleComposeAddress(destinationHash);
        },
        onComposeEnterPressed() {
            if (
                this.selectedComposeSuggestionIndex >= 0 &&
                this.selectedComposeSuggestionIndex < this.composeSuggestions.length
            ) {
                const suggestion = this.composeSuggestions[this.selectedComposeSuggestionIndex];
                this.selectComposeSuggestion(suggestion);
            } else {
                this.onComposeSubmit();
            }
        },
        handleComposeInputUp() {
            if (this.composeSuggestions.length > 0) {
                if (this.selectedComposeSuggestionIndex > 0) {
                    this.selectedComposeSuggestionIndex--;
                } else {
                    this.selectedComposeSuggestionIndex = this.composeSuggestions.length - 1;
                }
            }
        },
        handleComposeInputDown() {
            if (this.composeSuggestions.length > 0) {
                if (this.selectedComposeSuggestionIndex < this.composeSuggestions.length - 1) {
                    this.selectedComposeSuggestionIndex++;
                } else {
                    this.selectedComposeSuggestionIndex = 0;
                }
            }
        },
        selectComposeSuggestion(suggestion) {
            this.composeAddress = suggestion.hash;
            this.isComposeInputFocused = false;
            this.selectedComposeSuggestionIndex = -1;
            this.onComposeSubmit();
        },
        onComposeInputBlur() {
            // Delay blur to allow mousedown on suggestions
            setTimeout(() => {
                this.isComposeInputFocused = false;
                this.selectedComposeSuggestionIndex = -1;
            }, 200);
        },
        async handleComposeAddress(destinationHash) {
            destinationHash = Utils.normalizeMeshchatHashHex(destinationHash);
            if (destinationHash.length !== 32) {
                DialogUtils.alert(this.$t("common.invalid_address"));
                return;
            }
            GlobalEmitter.emit("compose-new-message", destinationHash);
        },
        normalizeLxmfMessage(msg, isOutbound) {
            const normalized = { ...msg };
            if (!normalized.created_at && normalized.timestamp) {
                normalized.created_at = new Date(normalized.timestamp * 1000).toISOString();
            }
            if (isOutbound && normalized.state === "unknown") {
                normalized.state = "outbound";
            }
            return normalized;
        },
        _hexEqual(a, b) {
            return (a || "").toLowerCase() === (b || "").toLowerCase();
        },
        onLxmfMessageReceived(lxmfMessage) {
            if (!this._hexEqual(lxmfMessage.source_hash, this.selectedPeer?.destination_hash)) {
                return;
            }

            if (lxmfMessage.is_reaction && lxmfMessage.reaction_to) {
                this.applyIncomingReaction(lxmfMessage);
                return;
            }

            this.chatItems.push({
                type: "lxmf_message",
                is_outbound: false,
                lxmf_message: this.normalizeLxmfMessage(lxmfMessage, false),
            });

            const conversation = this.findConversation(this.selectedPeer.destination_hash);
            if (conversation) {
                this.markConversationAsRead(conversation);
            }

            if (this.autoScrollOnNewMessage) {
                this.scrollMessagesToBottom();
            }

            this.autoLoadAudioAttachments();
        },
        onLxmfMessageCreated(lxmfMessage) {
            if (!this._hexEqual(lxmfMessage.destination_hash, this.selectedPeer?.destination_hash)) {
                return;
            }

            this.removeFirstPendingOutboundPlaceholderForPeer(lxmfMessage.destination_hash);

            if (!this.isLxmfMessageInUi(lxmfMessage.hash)) {
                this.chatItems.push({
                    type: "lxmf_message",
                    lxmf_message: this.normalizeLxmfMessage(lxmfMessage, true),
                    is_outbound: true,
                });
            }

            this.autoLoadAudioAttachments();
        },
        onLxmfMessageUpdated(lxmfMessage) {
            const lxmfMessageHash = lxmfMessage.hash;
            const chatItemIndex = this.chatItems.findIndex((chatItem) =>
                this._hexEqual(chatItem.lxmf_message?.hash, lxmfMessageHash)
            );
            if (chatItemIndex === -1) {
                return;
            }

            const prev = this.chatItems[chatItemIndex].lxmf_message;
            const merged = { ...prev, ...lxmfMessage };
            if (!Object.prototype.hasOwnProperty.call(lxmfMessage, "_pendingPathfinding")) {
                delete merged._pendingPathfinding;
            }
            this.chatItems[chatItemIndex].lxmf_message = merged;
        },
        onLxmfMessageDeleted(hash) {
            if (hash) {
                this.chatItems = this.chatItems.filter((item) => {
                    return !this._hexEqual(item.lxmf_message?.hash, hash);
                });
            }
        },
        async getPeerPath() {
            if (this.selectedPeer) {
                try {
                    const response = await getDestinationPath(window.api, this.selectedPeer.destination_hash, {});
                    this.selectedPeerPath = response.data.path;
                } catch (e) {
                    console.log(e);
                    this.selectedPeerPath = null;
                }
            }
        },
        async getPeerLxmfStampInfo() {
            if (this.selectedPeer) {
                try {
                    // get lxmf stamp info
                    const response = await window.api.get(
                        `/api/v1/destination/${this.selectedPeer.destination_hash}/lxmf-stamp-info`
                    );

                    // update ui
                    this.selectedPeerLxmfStampInfo = response.data.lxmf_stamp_info;
                } catch (e) {
                    console.log(e);

                    // clear previous stamp info
                    this.selectedPeerLxmfStampInfo = null;
                }
            }
        },
        async getPeerSignalMetrics() {
            if (this.selectedPeer) {
                try {
                    // get signal metrics
                    const response = await window.api.get(
                        `/api/v1/destination/${this.selectedPeer.destination_hash}/signal-metrics`
                    );

                    // update ui
                    this.selectedPeerSignalMetrics = response.data.signal_metrics;
                } catch (e) {
                    console.log(e);

                    // clear previous signal metrics
                    this.selectedPeerSignalMetrics = null;
                }
            }
        },
        onDestinationPathClick(path) {
            DialogUtils.alert(`${path.hops} ${path.hops === 1 ? "hop" : "hops"} away via ${path.next_hop_interface}`);
        },
        onStampInfoClick(stampInfo) {
            const stampCost = stampInfo.stamp_cost;
            const outboundTicketExpiry = stampInfo.outbound_ticket_expiry;

            // determine estimated time to generate a stamp
            var estimatedTimeForStamp = "";
            if (stampCost >= 24) {
                estimatedTimeForStamp = "several hours";
            } else if (stampCost >= 20) {
                estimatedTimeForStamp = "more than an hour";
            } else if (stampCost >= 18) {
                estimatedTimeForStamp = "~5 minutes";
            } else if (stampCost >= 17) {
                estimatedTimeForStamp = "a few minutes";
            } else if (stampCost >= 16) {
                estimatedTimeForStamp = "~1 minute";
            } else if (stampCost >= 13) {
                estimatedTimeForStamp = "~30 seconds";
            } else if (stampCost >= 9) {
                estimatedTimeForStamp = "~10 seconds";
            } else if (stampCost >= 1) {
                estimatedTimeForStamp = "a few seconds";
            } else {
                estimatedTimeForStamp = "0 seconds";
            }

            // check if we have an outbound ticket available
            if (outboundTicketExpiry != null) {
                estimatedTimeForStamp = `instant (ticket expires ${dayjs(outboundTicketExpiry * 1000).fromNow()})`;
            }

            DialogUtils.alert(
                `This peer has enabled stamp security.\n\nYour device must have a ticket, or solve an automated proof of work task each time you send them a message.\n\nTime per message: ${estimatedTimeForStamp}`
            );
        },
        onSignalMetricsClick(signalMetrics) {
            DialogUtils.alert(
                [
                    `Signal Quality: ${signalMetrics.quality ?? "???"}%`,
                    `RSSI: ${signalMetrics.rssi ?? "???"}dBm`,
                    `SNR: ${signalMetrics.snr ?? "???"}dB`,
                ].join("\n")
            );
        },
        resetStaleConversationScrollSurface() {
            resetMessagesScrollSurface(this.$refs.messagesScroll ?? null);
        },

        disconnectOpenConversationScrollObserver() {
            if (this.openConversationScrollObserver) {
                try {
                    this.openConversationScrollObserver.disconnect();
                } catch {
                    /* ignore */
                }
                this.openConversationScrollObserver = null;
            }
            if (this._openConversationScrollPinTimer) {
                clearTimeout(this._openConversationScrollPinTimer);
                this._openConversationScrollPinTimer = null;
            }
        },

        _startOpenConversationScrollPin(gen, stale) {
            this.disconnectOpenConversationScrollObserver();
            const container = this.$refs.messagesScroll;
            const observed = container?.firstElementChild;
            if (!observed || typeof ResizeObserver === "undefined") {
                return;
            }
            this.conversationOpenPinUntil = Date.now() + OPEN_CONVERSATION_SCROLL_PIN_MS;
            const ro = new ResizeObserver(() => {
                if (stale() || Date.now() > this.conversationOpenPinUntil || !this.autoScrollOnNewMessage) {
                    this.disconnectOpenConversationScrollObserver();
                    return;
                }
                requestAnimationFrame(() => {
                    if (stale() || Date.now() > this.conversationOpenPinUntil || !this.autoScrollOnNewMessage) {
                        return;
                    }
                    const c = this.$refs.messagesScroll;
                    if (!c) {
                        return;
                    }
                    try {
                        if (this.useVirtualMessageList && this.$refs.messageListVirtual) {
                            this.$refs.messageListVirtual.scrollToBottom();
                        }
                        scrollContainerToBottom(c);
                    } catch (e) {
                        console.error(e);
                    }
                });
            });
            this.openConversationScrollObserver = ro;
            ro.observe(observed);
            this._openConversationScrollPinTimer = setTimeout(() => {
                this.disconnectOpenConversationScrollObserver();
            }, OPEN_CONVERSATION_SCROLL_PIN_MS + 80);
        },

        scrollMessagesToBottom: function (options) {
            const pinAfter = options && options.pinAfter === true;
            this.scrollBottomGen += 1;
            const gen = this.scrollBottomGen;
            const stale = () => gen !== this.scrollBottomGen;

            const pump = () => {
                const container = this.$refs.messagesScroll;
                if (!container) {
                    return;
                }
                try {
                    if (this.useVirtualMessageList && this.$refs.messageListVirtual) {
                        this.$refs.messageListVirtual.scrollToBottom();
                    }
                    scrollContainerToBottom(container);
                } catch (e) {
                    console.error(e);
                }
            };

            this.$nextTick(() => {
                if (stale()) return;
                this.$nextTick(() => {
                    if (stale()) return;
                    const container = this.$refs.messagesScroll;
                    if (!container) {
                        this.messagesViewportReady = true;
                        return;
                    }
                    const hasItems = this.selectedPeerChatItems.length > 0;
                    if (!hasItems) {
                        pump();
                        requestAnimationFrame(() => {
                            if (stale()) return;
                            this.messagesViewportReady = true;
                            if (pinAfter) {
                                this._startOpenConversationScrollPin(gen, stale);
                            }
                        });
                        return;
                    }

                    let passes = 0;
                    const settle = () => {
                        if (stale()) return;
                        pump();
                        passes++;
                        const trustNear = canTrustScrollNearBottomHeuristic(container);
                        if ((trustNear && isNearBottom(container)) || passes >= SCROLL_SETTLE_MAX_PASSES) {
                            this.messagesViewportReady = true;
                            if (pinAfter) {
                                this._startOpenConversationScrollPin(gen, stale);
                            }
                        } else {
                            requestAnimationFrame(settle);
                        }
                    };
                    pump();
                    requestAnimationFrame(settle);
                });
            });
        },

        isLxmfMessageInUi: function (hash) {
            return this.chatItems.findIndex((chatItem) => this._hexEqual(chatItem.lxmf_message?.hash, hash)) !== -1;
        },
        async getCustomDisplayName() {
            if (this.selectedPeer) {
                try {
                    // get custom display name
                    const response = await window.api.get(
                        `/api/v1/destination/${this.selectedPeer.destination_hash}/custom-display-name`
                    );

                    // update ui
                    this.$emit("update:selectedPeer", {
                        ...this.selectedPeer,
                        custom_display_name: response.data.custom_display_name,
                    });
                } catch (error) {
                    console.log(error);
                }
            }
        },
        async updateCustomDisplayName() {
            if (!this.selectedPeer) {
                return;
            }

            const displayName = await DialogUtils.prompt(this.$t("messages.enter_display_name"));
            if (displayName == null) {
                return;
            }

            try {
                await window.api.post(
                    `/api/v1/destination/${this.selectedPeer.destination_hash}/custom-display-name/update`,
                    {
                        display_name: displayName,
                    }
                );

                if (displayName.length > 0) {
                    try {
                        const checkResp = await window.api.get(
                            `/api/v1/telephone/contacts/check/${this.selectedPeer.destination_hash}`
                        );
                        const contactId = checkResp.data?.contact?.id;
                        if (contactId) {
                            await window.api.patch(`/api/v1/telephone/contacts/${contactId}`, { name: displayName });
                        }
                    } catch {
                        // non-critical
                    }
                }

                await this.getCustomDisplayName();
                this.$emit("reload-conversations");
            } catch (error) {
                console.log(error);
                DialogUtils.alert(this.$t("messages.failed_update_display_name"));
            }
        },
        onConversationDeleted() {
            this.$emit("reload-conversations");
            this.$emit("close");
        },
        async onBanishHeaderClick() {
            if (!this.selectedPeer) return;
            if (
                !(await DialogUtils.confirm(
                    this.$t("messages.banish_confirm") ||
                        "Are you sure you want to banish this user? They will not be able to send you messages or establish links."
                ))
            ) {
                return;
            }
            try {
                await window.api.post("/api/v1/blocked-destinations", {
                    destination_hash: this.selectedPeer.destination_hash,
                });
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("messages.user_banished"));
            } catch (e) {
                DialogUtils.alert(this.$t("messages.failed_banish_user"));
                console.error(e);
            }
        },
        async liftBanishmentFromMessageMenu() {
            if (!this.selectedPeer?.destination_hash) {
                this.messageContextMenu.show = false;
                return;
            }
            try {
                await window.api.delete(`/api/v1/blocked-destinations/${this.selectedPeer.destination_hash}`);
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("banishment.banishment_lifted"));
            } catch (e) {
                DialogUtils.alert(this.$t("banishment.failed_lift_banishment"));
                console.error(e);
            }
            this.messageContextMenu.show = false;
        },
        onChatItemClick: function (chatItem) {
            if (!chatItem.is_actions_expanded) {
                chatItem.is_actions_expanded = true;
            } else {
                chatItem.is_actions_expanded = false;
            }
        },
        copyableMessagePlainText(chatItem) {
            const raw = chatItem?.lxmf_message?.content;
            if (typeof raw !== "string") {
                return "";
            }
            const t = raw.trim();
            return t.length > 0 ? t : "";
        },
        async copyMessageFromContextMenu(chatItem) {
            const text = this.copyableMessagePlainText(chatItem);
            if (!text) {
                return;
            }
            const ok = await copyTextToClipboard(text);
            if (ok) {
                ToastUtils.success(this.$t("messages.message_copied"));
                this.messageContextMenu.show = false;
            } else {
                ToastUtils.error(this.$t("messages.clipboard_write_unavailable"));
            }
        },
        isMessageBodyTooLargeForDisplay(chatItem) {
            return isStringTooLargeForInlineDisplay(chatItem?.lxmf_message?.content);
        },
        messageBodyCharCount(chatItem) {
            const c = chatItem?.lxmf_message?.content;
            return typeof c === "string" ? c.length : 0;
        },
        async copyOversizedMessageBody(chatItem) {
            const text = this.copyableMessagePlainText(chatItem);
            if (!text) {
                return;
            }
            const ok = await copyTextToClipboard(text);
            if (ok) {
                ToastUtils.success(this.$t("messages.oversized_body_copied"));
            } else {
                ToastUtils.error(this.$t("messages.clipboard_write_unavailable"));
            }
        },
        async copyRawMessageModalContent() {
            const c = this.rawMessageData?.content;
            if (typeof c !== "string" || c.length === 0) {
                return;
            }
            const ok = await copyTextToClipboard(c);
            if (ok) {
                ToastUtils.success(this.$t("messages.oversized_body_copied"));
            } else {
                ToastUtils.error(this.$t("messages.clipboard_write_unavailable"));
            }
        },
        replyToMessage(chatItem) {
            this.replyingTo = chatItem;
            this.messageContextMenu.show = false;
            chatItem.is_actions_expanded = false;
            // focus the input
            this.$nextTick(() => {
                const textarea = this.$refs["message-input"];
                if (textarea) {
                    textarea.focus();
                }
            });
        },
        cancelReply() {
            this.replyingTo = null;
        },
        scrollToMessage(hash) {
            const index = this.chatItems.findIndex((item) => item.lxmf_message?.hash === hash);
            if (index === -1) {
                DialogUtils.alert(this.$t("messages.message_not_found_in_cache"));
                return;
            }
            const el = document.getElementById(`message-${hash}`);
            if (el) {
                el.scrollIntoView({ behavior: "smooth", block: "center" });
                el.classList.add("ring-2", "ring-blue-500", "ring-offset-2");
                setTimeout(() => {
                    el.classList.remove("ring-2", "ring-blue-500", "ring-offset-2");
                }, 2000);
                return;
            }
            if (this.useVirtualMessageList && this.$refs.messageListVirtual) {
                this.$refs.messageListVirtual.scrollToMessageHash(hash);
                this.$nextTick(() => {
                    requestAnimationFrame(() => {
                        const el2 = document.getElementById(`message-${hash}`);
                        if (el2) {
                            el2.classList.add("ring-2", "ring-blue-500", "ring-offset-2");
                            setTimeout(() => {
                                el2.classList.remove("ring-2", "ring-blue-500", "ring-offset-2");
                            }, 2000);
                        }
                    });
                });
                return;
            }
            DialogUtils.alert(this.$t("messages.message_not_found_in_cache"));
        },
        getRepliedMessage(hash) {
            const item = this.chatItems.find((i) => i.lxmf_message?.hash === hash);
            return item ? item.lxmf_message : null;
        },
        reactionReactorLabel(senderHex) {
            if (!senderHex || typeof senderHex !== "string") {
                return "";
            }
            const hex = senderHex.toLowerCase();
            if (this.myLxmfAddressHash && hex === String(this.myLxmfAddressHash).toLowerCase()) {
                return this.$t("messages.reaction_you");
            }
            if (
                this.selectedPeer?.destination_hash &&
                hex === String(this.selectedPeer.destination_hash).toLowerCase()
            ) {
                return (
                    this.selectedPeer.custom_display_name ??
                    this.selectedPeer.display_name ??
                    this.formatDestinationHash(hex)
                );
            }
            const conv = this.conversations.find(
                (c) => c.destination_hash && String(c.destination_hash).toLowerCase() === hex
            );
            if (conv) {
                return conv.custom_display_name ?? conv.display_name ?? this.formatDestinationHash(hex);
            }
            return this.formatDestinationHash(hex);
        },
        applyIncomingReaction(lxmfMessage) {
            const target = this.chatItems.find((i) => i.lxmf_message?.hash === lxmfMessage.reaction_to);
            if (!target || !target.lxmf_message) {
                return;
            }
            if (!target.lxmf_message.reactions) {
                target.lxmf_message.reactions = [];
            }
            const sender = lxmfMessage.reaction_sender || lxmfMessage.source_hash || "";
            const emoji = lxmfMessage.reaction_emoji || "";
            const dup = target.lxmf_message.reactions.some((r) => r.sender === sender && r.emoji === emoji);
            if (dup) {
                return;
            }
            target.lxmf_message.reactions.push({
                emoji,
                sender,
                reactionHash: lxmfMessage.hash,
            });
        },
        openReactionPicker(chatItem) {
            this.reactionPickerPos = null;
            this.reactionPickerChatItem = chatItem;
        },
        closeReactionPicker() {
            this.reactionPickerChatItem = null;
            this.reactionPickerPos = null;
            this.reactionDragState = null;
        },
        onReactionPickerDragStart(e) {
            const evt = e.touches ? e.touches[0] : e;
            const panel = this.$refs.reactionPickerPanel;
            if (!panel) return;
            const rect = panel.getBoundingClientRect();
            this.reactionDragState = {
                startX: evt.clientX,
                startY: evt.clientY,
                originX: rect.left,
                originY: rect.top,
            };
            const onMove = (me) => {
                const mv = me.touches ? me.touches[0] : me;
                const dx = mv.clientX - this.reactionDragState.startX;
                const dy = mv.clientY - this.reactionDragState.startY;
                const panelEl = this.$refs.reactionPickerPanel;
                if (!panelEl) return;
                const pr = panelEl.getBoundingClientRect();
                const nx = this.reactionDragState.originX + dx;
                const ny = this.reactionDragState.originY + dy;
                const { left, top } = clampFloatingToViewport(nx, ny, pr.width, pr.height);
                this.reactionPickerPos = { x: left, y: top };
            };
            const onUp = () => {
                document.removeEventListener("mousemove", onMove);
                document.removeEventListener("mouseup", onUp);
                document.removeEventListener("touchmove", onMove);
                document.removeEventListener("touchend", onUp);
            };
            document.addEventListener("mousemove", onMove);
            document.addEventListener("mouseup", onUp);
            document.addEventListener("touchmove", onMove, { passive: false });
            document.addEventListener("touchend", onUp);
        },
        onReactionPickerEmojiClick(event) {
            const emoji = event.detail?.unicode;
            if (!emoji || !this.reactionPickerChatItem) {
                return;
            }
            const chatItem = this.reactionPickerChatItem;
            this.reactionPickerChatItem = null;
            this.sendReactionEmojiFromMenu(chatItem, emoji);
        },
        async sendReactionEmojiFromMenu(chatItem, emoji) {
            this.messageContextMenu.show = false;
            const hash = chatItem.lxmf_message?.hash;
            if (!hash || !this.selectedPeer?.destination_hash) {
                return;
            }
            try {
                await window.api.post("/api/v1/lxmf-messages/reactions", {
                    destination_hash: this.selectedPeer.destination_hash,
                    target_message_hash: hash,
                    emoji,
                });
                const sender = this.myLxmfAddressHash;
                if (!chatItem.lxmf_message.reactions) {
                    chatItem.lxmf_message.reactions = [];
                }
                const dup = chatItem.lxmf_message.reactions.some((r) => r.sender === sender && r.emoji === emoji);
                if (!dup) {
                    chatItem.lxmf_message.reactions.push({
                        emoji,
                        sender,
                        reactionHash: null,
                    });
                }
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("messages.reaction_send_failed"));
            }
        },
        onMessageContextMenu(event, chatItem, openedFromBubble = false) {
            this.messageContextMenu.chatItem = chatItem;
            this.messageContextMenu.openedFromBubble = openedFromBubble;
            this.messageContextMenu.justOpened = true;
            this.messageContextMenu.show = true;

            this.$nextTick(() => {
                const menuWidth = 200;
                const menuHeight = 280;

                let x = event.clientX;
                let y = event.clientY;

                if (x + menuWidth > window.innerWidth) {
                    x = window.innerWidth - menuWidth - 10;
                }
                if (y + menuHeight > window.innerHeight) {
                    y = window.innerHeight - menuHeight - 10;
                }

                this.messageContextMenu.x = x;
                this.messageContextMenu.y = y;
                setTimeout(() => {
                    this.messageContextMenu.justOpened = false;
                }, 50);
            });
        },
        async showRawMessage(chatItem) {
            const base = { ...chatItem.lxmf_message };
            const uriPromise = window.api
                .get(`/api/v1/lxmf-messages/${chatItem.lxmf_message.hash}/uri`)
                .then((r) => r.data?.uri ?? null)
                .catch(() => null);
            const rawUri = await uriPromise;
            this.rawMessageData = {
                ...base,
                raw_uri: rawUri ?? undefined,
            };
            this.isRawMessageModalOpen = true;
        },
        async downloadAndDecodeAudio(chatItem) {
            if (this.isDownloadingAudio[chatItem.lxmf_message.hash]) return;

            this.isDownloadingAudio[chatItem.lxmf_message.hash] = true;
            try {
                // fetch audio bytes from api
                const response = await window.api.get(
                    `/api/v1/lxmf-messages/attachment/${chatItem.lxmf_message.hash}/audio`,
                    {
                        responseType: "arraybuffer",
                    }
                );
                const audioBytes = response.data; // this will be an ArrayBuffer

                // ensure we have the bytes
                if (!audioBytes) {
                    throw new Error("No audio bytes received");
                }

                // decode audio to blob url
                // note: decodeLxmfAudioFieldToBlobUrl expects a field object with audio_mode and audio_bytes
                const audioField = {
                    audio_mode: chatItem.lxmf_message.fields.audio.audio_mode,
                    audio_bytes: audioBytes,
                };

                const objectUrl = await this.decodeLxmfAudioFieldToBlobUrl(audioField);
                if (objectUrl) {
                    this.lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash] = objectUrl;
                }
            } catch (e) {
                console.error("Failed to download or decode audio:", e);
                DialogUtils.alert(this.$t("messages.failed_load_audio"));
            } finally {
                this.isDownloadingAudio[chatItem.lxmf_message.hash] = false;
            }
        },
        autoLoadAudioAttachments() {
            for (const chatItem of this.chatItems) {
                if (
                    chatItem.lxmf_message.fields?.audio &&
                    !this.lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash] &&
                    !this.isDownloadingAudio[chatItem.lxmf_message.hash]
                ) {
                    this.downloadAndDecodeAudio(chatItem);
                }
            }
        },
        formatAttachmentSize(attachment, type) {
            if (attachment[`${type}_size`] !== undefined && attachment[`${type}_size`] !== null) {
                return this.formatBytes(attachment[`${type}_size`]);
            }
            if (attachment[`${type}_bytes`]) {
                return this.formatBase64Bytes(attachment[`${type}_bytes`]);
            }
            return "0 B";
        },
        openImage: async function (url, galleryUrls) {
            if (galleryUrls && galleryUrls.length > 1) {
                this.imageModalGallery = galleryUrls.slice();
                let idx = galleryUrls.indexOf(url);
                if (idx < 0) idx = 0;
                this.imageModalIndex = idx;
                this.imageModalUrl = galleryUrls[idx];
            } else {
                this.imageModalGallery = null;
                this.imageModalIndex = 0;
                this.imageModalUrl = url;
            }
            this.$nextTick(() => {
                this.$refs.imageModalOverlay?.focus?.();
            });
        },
        closeImageModal() {
            this.imageModalUrl = null;
            this.imageModalGallery = null;
            this.imageModalIndex = 0;
        },
        imageModalNavigate(delta) {
            if (!this.imageModalGallery || this.imageModalGallery.length < 2) return;
            const n = this.imageModalGallery.length;
            this.imageModalIndex = (this.imageModalIndex + delta + n) % n;
            this.imageModalUrl = this.imageModalGallery[this.imageModalIndex];
        },
        canMergeImageIntoImageStrip(chatItem) {
            const m = chatItem.lxmf_message;
            if (m.is_spam) return false;
            if (["cancelled", "failed", "rejected"].includes(m.state)) return false;
            if (!m.fields?.image) return false;
            if (m.reply_to_hash) return false;
            const c = (m.content || "").trim();
            if (c && !this.isLikelyMultiImagePlaceholderCaption(c)) return false;
            if (m.fields?.audio) return false;
            if (m.fields?.file_attachments?.length) return false;
            if (m.fields?.telemetry) return false;
            if (m.fields?.telemetry_stream) return false;
            if (m.fields?.commands?.length) return false;
            return true;
        },
        isLikelyMultiImagePlaceholderCaption(text) {
            if (!text || text.includes("\n") || text.includes("\r")) return false;
            if (text.length > 240) return false;
            if (/[\\/]/.test(text)) return false;
            if (/[<>[\]{}]/.test(text)) return false;
            return /^[\w.\- ()#@%&!+,;=']+\.(png|jpe?g|gif|webp|bmp|heif|heic|avif|svg|ico)$/i.test(text.trim());
        },
        shouldHideAutoImageCaption(chatItem) {
            const m = chatItem.lxmf_message;
            if (!m.fields?.image) return false;
            return this.isLikelyMultiImagePlaceholderCaption((m.content || "").trim());
        },
        imageGroupSortedChron(items) {
            return [...items].sort((a, b) => {
                const ta = a.lxmf_message.timestamp ?? 0;
                const tb = b.lxmf_message.timestamp ?? 0;
                return ta - tb;
            });
        },
        lxmfImageUrl(hash) {
            return `/api/v1/lxmf-messages/attachment/${hash}/image`;
        },
        lxmfDataUrlFromOutboundJobImage(img) {
            if (!img?.image_bytes || typeof img.image_bytes !== "string") {
                return null;
            }
            const raw = (img.image_type || "png").toLowerCase().replace(/^image\//, "");
            let mime = "image/png";
            if (raw === "jpg" || raw === "jpeg") {
                mime = "image/jpeg";
            } else if (raw === "png" || raw === "gif" || raw === "webp" || raw === "bmp") {
                mime = `image/${raw}`;
            } else if (raw === "webm") {
                mime = "video/webm";
            } else if (raw === "svg" || raw === "svg+xml") {
                mime = "image/svg+xml";
            } else {
                mime = `image/${raw}`;
            }
            return `data:${mime};base64,${img.image_bytes}`;
        },
        pendingOutboundImageSrc(chatItem) {
            const prev = chatItem.lxmf_message?.fields?.image?._preview_url;
            if (prev) {
                return prev;
            }
            const h = chatItem.lxmf_message?.hash;
            if (typeof h === "string" && h.startsWith("pending-")) {
                return "";
            }
            return this.lxmfImageUrl(h);
        },
        removePendingOutboundPlaceholder(hash) {
            if (!hash) {
                return;
            }
            this.chatItems = this.chatItems.filter((item) => item.lxmf_message?.hash !== hash);
        },
        removeFirstPendingOutboundPlaceholderForPeer(destinationHash) {
            let removed = false;
            this.chatItems = this.chatItems.filter((item) => {
                if (removed) {
                    return true;
                }
                const h = item.lxmf_message?.hash;
                if (
                    item.is_outbound &&
                    h?.startsWith("pending-") &&
                    item.lxmf_message.destination_hash === destinationHash
                ) {
                    removed = true;
                    return false;
                }
                return true;
            });
        },
        outboundSendingStatusTooltip(lxmfMessage) {
            if (!lxmfMessage) {
                return "";
            }
            const synthetic = { is_outbound: true, lxmf_message: lxmfMessage };
            if (!this.showRichOutboundPendingUi(synthetic)) {
                return this.$t("messages.sending_ellipsis");
            }
            if (lxmfMessage._pendingPathfinding) {
                return this.$t("messages.outbound_pathfinding_tooltip");
            }
            if (lxmfMessage.solving_stamps) {
                return this.$t("messages.outbound_solving_stamps");
            }
            if (lxmfMessage.method === "propagated") {
                if (lxmfMessage.state === "sending" && (lxmfMessage.progress ?? 0) > 0) {
                    return this.$t("messages.outbound_pending_propagation_with_progress", {
                        progress: Number(lxmfMessage.progress).toFixed(0),
                    });
                }
                if (["sending", "outbound", "generating"].includes(lxmfMessage.state)) {
                    return this.$t("messages.outbound_pending_propagation");
                }
            }
            if (lxmfMessage.state === "generating") {
                return this.$t("messages.outbound_preparing_message");
            }
            if (lxmfMessage.state === "sending" && (lxmfMessage.progress ?? 0) > 0) {
                return this.$t("messages.outbound_sending_with_progress", {
                    progress: Number(lxmfMessage.progress).toFixed(0),
                });
            }
            if (lxmfMessage.state === "sending") {
                return this.$t("messages.sending_ellipsis");
            }
            return this.$t("messages.outbound_pending");
        },
        outboundSentStatusTitle(lxmfMessage) {
            if (!lxmfMessage) {
                return "";
            }
            if (lxmfMessage.method === "propagated") {
                return this.$t("messages.outbound_on_propagation_node");
            }
            return this.$t("messages.outbound_sent_network");
        },
        isOutboundWaitingBubble(chatItem) {
            return Boolean(chatItem?.is_outbound && chatItem?.lxmf_message?._pendingPathfinding);
        },
        _hexToRgb(hex) {
            const s = String(hex ?? "")
                .trim()
                .replace(/^#/, "");
            if (s.length !== 6 || !/^[0-9a-fA-F]{6}$/.test(s)) {
                return null;
            }
            return {
                r: parseInt(s.slice(0, 2), 16),
                g: parseInt(s.slice(2, 4), 16),
                b: parseInt(s.slice(4, 6), 16),
            };
        },
        _hexRelativeLuminance(hex) {
            const rgb = this._hexToRgb(hex);
            if (!rgb) {
                return null;
            }
            const toLinear = (c) => {
                const x = c / 255;
                return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
            };
            const R = toLinear(rgb.r);
            const G = toLinear(rgb.g);
            const B = toLinear(rgb.b);
            return 0.2126 * R + 0.7152 * G + 0.0722 * B;
        },
        pickTextColorForBubbleBackground(hex) {
            const lum = this._hexRelativeLuminance(hex);
            if (lum == null) {
                return "#111827";
            }
            return lum > 0.45 ? "#111827" : "#ffffff";
        },
        waitingBubbleBorderForHex(hex) {
            const lum = this._hexRelativeLuminance(hex);
            if (lum == null) {
                return "1px solid rgba(15, 23, 42, 0.12)";
            }
            return lum > 0.45 ? "1px solid rgba(15, 23, 42, 0.12)" : "1px solid rgba(255, 255, 255, 0.14)";
        },
        isOutboundSendingBusy(chatItem) {
            const m = chatItem?.lxmf_message;
            if (!chatItem?.is_outbound || !m) {
                return false;
            }
            return ["outbound", "sending", "generating"].includes(m.state);
        },
        isOutboundPendingForUi(chatItem) {
            const m = chatItem?.lxmf_message;
            if (!chatItem?.is_outbound || !m) {
                return false;
            }
            if (m._pendingPathfinding) {
                return true;
            }
            return ["outbound", "sending", "generating"].includes(m.state);
        },
        isOutboundSendEscalated(chatItem) {
            const m = chatItem?.lxmf_message;
            if (!chatItem?.is_outbound || !m) {
                return false;
            }
            if (!this.isOutboundPendingForUi(chatItem)) {
                return false;
            }
            const created = m.created_at ? new Date(m.created_at).getTime() : 0;
            if (!created) {
                return false;
            }
            return this.sendStatusUiMs - created >= 3000;
        },
        showRichOutboundPendingUi(chatItem) {
            if (GlobalState.detailedOutboundSendStatus) {
                return true;
            }
            return this.isOutboundSendEscalated(chatItem);
        },
        _shouldTickOutboundSendStatusUi() {
            return this.selectedPeerChatItems.some((item) => this.isOutboundPendingForUi(item));
        },
        _scheduleOutboundSendStatusTick() {
            if (this.sendStatusTickInterval) {
                clearInterval(this.sendStatusTickInterval);
                this.sendStatusTickInterval = null;
            }
            if (!this._shouldTickOutboundSendStatusUi()) {
                return;
            }
            this.sendStatusUiMs = Date.now();
            this.sendStatusTickInterval = setInterval(() => {
                this.sendStatusUiMs = Date.now();
            }, 1000);
        },
        isThemeOutboundBubble(chatItem) {
            if (!chatItem?.is_outbound) {
                return false;
            }
            const st = chatItem.lxmf_message?.state;
            if (["cancelled", "failed"].includes(st)) {
                return false;
            }
            return this.usesThemeOutboundBubbleColor;
        },
        outboundBubbleSurfaceClass(chatItem) {
            if (!chatItem?.is_outbound) {
                return "";
            }
            if (["cancelled", "failed"].includes(chatItem.lxmf_message.state)) {
                return "";
            }
            if (chatItem.lxmf_message.is_spam) {
                return "";
            }
            if (chatItem.lxmf_message?._pendingPathfinding) {
                return "";
            }
            if (!this.usesThemeOutboundBubbleColor) {
                return "shadow-xs";
            }
            return "shadow-xs bg-sky-100 text-slate-900 border border-sky-200/90 dark:bg-sky-950/45 dark:text-sky-50 dark:border-sky-800/55";
        },
        outboundBubbleFooterTimeClass(chatItem) {
            if (!chatItem.is_outbound) {
                return "text-gray-500 dark:text-zinc-400";
            }
            if (this.isOutboundWaitingBubble(chatItem)) {
                return "text-gray-600 dark:text-zinc-400";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-700/90 dark:text-sky-200/85";
            }
            return "text-white";
        },
        outboundSendingStatusIconClass(chatItem) {
            if (this.isOutboundWaitingBubble(chatItem)) {
                return "text-gray-600 dark:text-zinc-400";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-700 dark:text-sky-300";
            }
            return "text-white";
        },
        outboundReplySnippetTitleClass(chatItem) {
            if (!chatItem.is_outbound) {
                return "text-indigo-500/80";
            }
            if (this.isOutboundWaitingBubble(chatItem)) {
                return "text-gray-700 dark:text-gray-300";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-800 dark:text-sky-200";
            }
            return "text-white/80";
        },
        outboundAttachmentCaptionClass(chatItem) {
            if (!chatItem.is_outbound) {
                return "text-gray-500 dark:text-zinc-400";
            }
            if (this.isOutboundWaitingBubble(chatItem)) {
                return "text-gray-600 dark:text-zinc-400";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-800 dark:text-sky-200";
            }
            return "text-white";
        },
        outboundBubbleDeliveredIconClass(chatItem) {
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-600 dark:text-sky-400";
            }
            return "text-blue-300";
        },
        outboundBubbleSentCheckIconClass(chatItem) {
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-700 dark:text-sky-300";
            }
            return "text-white";
        },
        outboundBubblePendingCheckIconClass(chatItem) {
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-700 dark:text-sky-300 opacity-50";
            }
            return "text-white opacity-50";
        },
        outboundEmbeddedCardClass(chatItem) {
            if (!chatItem?.is_outbound) {
                return "";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "bg-sky-900/10 text-sky-900 border-sky-300/45 hover:bg-sky-900/14 dark:bg-white/10 dark:text-sky-50 dark:border-sky-700/45 dark:hover:bg-white/15";
            }
            return "bg-white/20 text-white border-white/20 hover:bg-white/30";
        },
        outboundEmbeddedSecondaryTextClass(chatItem) {
            if (!chatItem?.is_outbound) {
                return "";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-800/75 dark:text-sky-200/75";
            }
            return "text-white/60";
        },
        outboundExpandedActionsShellClass(chatItem) {
            if (!chatItem?.is_outbound) {
                return "border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "border-sky-200/70 dark:border-sky-800/50 bg-sky-50/40 dark:bg-sky-950/35";
            }
            return "border-white/20 bg-white/10";
        },
        outboundMessageMenuButtonClass(chatItem) {
            if (!chatItem?.is_outbound) {
                return "text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300 dark:text-zinc-500";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-700/90 dark:text-sky-200/85";
            }
            return "text-white/90 hover:text-white";
        },
        outboundMessageMenuButtonHoverClass(chatItem) {
            if (!chatItem?.is_outbound) {
                return "hover:bg-gray-200 dark:hover:bg-zinc-700";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "hover:bg-sky-900/10 dark:hover:bg-white/10";
            }
            return "hover:bg-white/20";
        },
        outboundBubbleStatusHoverTitle(lxmfMessage) {
            if (!lxmfMessage) {
                return "";
            }
            const synthetic = { is_outbound: true, lxmf_message: lxmfMessage };
            if (!this.showRichOutboundPendingUi(synthetic)) {
                return this.$t("messages.sending_ellipsis");
            }
            if (lxmfMessage._pendingPathfinding) {
                return this.$t("messages.outbound_pathfinding_short");
            }
            if (lxmfMessage.solving_stamps) {
                return this.$t("messages.outbound_solving_stamps_short");
            }
            if (lxmfMessage.state === "generating") {
                return this.$t("messages.outbound_preparing_message_short");
            }
            if (lxmfMessage.state === "sending" && (lxmfMessage.progress ?? 0) > 0) {
                return this.$t("messages.outbound_sending_with_progress", {
                    progress: Number(lxmfMessage.progress).toFixed(0),
                });
            }
            if (lxmfMessage.state === "sending") {
                return this.$t("messages.outbound_sending_short");
            }
            if (lxmfMessage.state === "outbound") {
                if (lxmfMessage.method === "propagated") {
                    return this.$t("messages.outbound_pending_propagation");
                }
                return this.$t("messages.outbound_outbound_short");
            }
            return this.outboundSendingStatusTooltip(lxmfMessage);
        },
        outboundBubbleFailedTitle(lxmfMessage) {
            if (!lxmfMessage) {
                return "";
            }
            if (lxmfMessage.state === "rejected") {
                return "Rejected";
            }
            if (lxmfMessage.state === "cancelled") {
                return "Cancelled";
            }
            if (lxmfMessage.method === "opportunistic") {
                return this.$t("messages.opportunistic_deferred_tooltip");
            }
            return this.$t("messages.failed_waiting_announce_tooltip");
        },
        isOpportunisticDeferredDelivery(lxmfMessage) {
            if (!lxmfMessage) {
                return false;
            }
            return lxmfMessage.method === "opportunistic" && lxmfMessage.state === "failed";
        },
        async warmPathToPeer() {
            if (!this.selectedPeer?.destination_hash) {
                return;
            }
            try {
                await postRequestPath(window.api, this.selectedPeer.destination_hash);
            } catch (e) {
                console.log(e);
            }
        },
        imageGroupGalleryUrls(items) {
            return this.imageGroupSortedChron(items).map((it) => this.lxmfImageUrl(it.lxmf_message.hash));
        },
        downloadFileFromBase64: async function (fileName, fileBytesBase64) {
            DownloadUtils.downloadFromBase64(fileName, fileBytesBase64);
        },
        async processAudioForSelectedPeerChatItems() {
            for (const chatItem of this.selectedPeerChatItems) {
                // skip if no audio, or if audio bytes are missing (must be downloaded manually)
                if (!chatItem.lxmf_message?.fields?.audio || !chatItem.lxmf_message.fields.audio.audio_bytes) {
                    continue;
                }

                // skip if audio already cached
                if (this.lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash]) {
                    continue;
                }

                // decode audio to blob url
                const objectUrl = await this.decodeLxmfAudioFieldToBlobUrl(chatItem.lxmf_message.fields.audio);
                if (!objectUrl) {
                    continue;
                }

                // update audio cache
                this.lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash] = objectUrl;
            }
        },
        async decodeLxmfAudioFieldToBlobUrl(audioField) {
            try {
                // get audio mode and audio bytes from audio field
                const audioMode = audioField.audio_mode;
                const audioBytes = audioField.audio_bytes;

                // handle opus: AM_OPUS_OGG
                if (audioMode === 0x10) {
                    return this.decodeOpusAudioToBlobUrl(audioField.audio_bytes);
                }

                // determine codec2 mode, or skip if unknown
                const codecMode = this.lxmfAudioModeToCodec2ModeMap[audioMode];
                if (!codecMode) {
                    console.log("unsupported audio mode: " + audioMode);
                    return null;
                }

                // convert to uint8 array
                let encoded;
                if (typeof audioBytes === "string") {
                    encoded = this.base64ToArrayBuffer(audioBytes);
                } else {
                    encoded = new Uint8Array(audioBytes);
                }

                // decode codec2 audio
                const decoded = await Codec2Lib.runDecode(codecMode, encoded);

                // convert decoded codec2 to wav audio
                const wavAudio = await Codec2Lib.rawToWav(decoded);

                // create blob from wav audio
                const blob = new Blob([wavAudio], {
                    type: "audio/wav",
                });

                // create object url for blob
                return URL.createObjectURL(blob);
            } catch (e) {
                // failed to decode lxmf audio field
                console.log(e);
                return null;
            }
        },
        async decodeOpusAudioToBlobUrl(audioBytes) {
            try {
                // convert to uint8 array
                let opusAudioBytes;
                if (typeof audioBytes === "string") {
                    opusAudioBytes = this.base64ToArrayBuffer(audioBytes);
                } else {
                    opusAudioBytes = new Uint8Array(audioBytes);
                }

                // create blob from opus audio
                const blob = new Blob([opusAudioBytes], {
                    type: "audio/opus",
                });

                // create object url for blob
                return URL.createObjectURL(blob);
            } catch (e) {
                // failed to decode opus audio
                console.log(e);
                return null;
            }
        },
        base64ToArrayBuffer: function (base64) {
            return Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
        },
        async deleteChatItem(chatItem, shouldConfirm = true) {
            try {
                // ask user to confirm deleting message
                if (
                    shouldConfirm &&
                    !(await DialogUtils.confirm(
                        "Are you sure you want to delete this message? This can not be undone!"
                    ))
                ) {
                    return;
                }

                // make sure it's an lxmf message
                if (chatItem.type !== "lxmf_message") {
                    return;
                }

                // delete lxmf message from server
                await window.api.delete(`/api/v1/lxmf-messages/${chatItem.lxmf_message.hash}`);

                // remove lxmf message from chat items using hash, as other pending items might not have an id yet
                this.chatItems = this.chatItems.filter((item) => {
                    return item.lxmf_message?.hash !== chatItem.lxmf_message.hash;
                });
            } catch {
                // do nothing if failed to delete message
            }
        },
        async openShareContactModal() {
            try {
                const response = await window.api.get("/api/v1/telephone/contacts");
                this.contacts = response.data?.contacts ?? (Array.isArray(response.data) ? response.data : []);

                if (this.contacts.length === 0) {
                    ToastUtils.info(this.$t("messages.no_contacts_telephone"));
                    return;
                }

                this.isShareContactModalOpen = true;
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("messages.failed_load_contacts"));
            }
        },
        shareContact(contact) {
            let sharedString = `Contact: ${contact.name} <${contact.remote_identity_hash}>`;
            if (contact.lxmf_address) sharedString += ` [LXMF: ${contact.lxmf_address}]`;
            if (contact.lxst_address) sharedString += ` [LXST: ${contact.lxst_address}]`;
            this.newMessageText = sharedString;
            this.isShareContactModalOpen = false;
            this.sendMessage();
        },
        lxmfDeliveryDestinationHexFromContact(contact) {
            if (!contact) return "";
            const order = [contact.remote_destination_hash, contact.lxmf_address, contact.remote_identity_hash];
            for (const c of order) {
                const h = Utils.normalizeMeshchatHashHex(c);
                if (h) {
                    return h;
                }
            }
            return "";
        },
        lxmfContactResolvedIcon(contact) {
            const empty = { iconName: "", foreground: "", background: "" };
            if (!contact) {
                return empty;
            }
            const ri = contact.remote_icon;
            if (ri?.icon_name) {
                return {
                    iconName: ri.icon_name,
                    foreground: ri.foreground_colour || "",
                    background: ri.background_colour || "",
                };
            }
            const dest = this.lxmfDeliveryDestinationHexFromContact(contact);
            if (!dest) {
                return empty;
            }
            const conv =
                this.conversations.find((c) => Utils.normalizeMeshchatHashHex(c.destination_hash || "") === dest) ||
                null;
            const lu = conv?.lxmf_user_icon;
            if (lu?.icon_name) {
                return {
                    iconName: lu.icon_name,
                    foreground: lu.foreground_colour || "",
                    background: lu.background_colour || "",
                };
            }
            return empty;
        },
        shareAsPaperMessage(chatItem) {
            this.paperMessageHash = chatItem.lxmf_message.hash;
            this.isPaperMessageModalOpen = true;
        },
        clearComposeAfterEnqueue() {
            this.newMessageText = "";
            if (this.selectedPeer) {
                this.saveDraft(this.selectedPeer.destination_hash);
            }
            this.newMessageImages = [];
            this.newMessageImageUrls = [];
            this.newMessageAudio = null;
            this.newMessageTelemetry = null;
            this.newMessageFiles = [];
            this.clearFileInput();
            this.replyingTo = null;
        },
        async buildOutboundJobSnapshot() {
            const destinationHash = this.selectedPeer.destination_hash;
            const deliveryMethod = this.newMessageDeliveryMethod;
            const text = this.newMessageText;
            const replyToHash = this.replyingTo?.lxmf_message?.hash || null;
            const replyQuotedContent =
                (this.replyingTo && this.getRepliedMessage(this.replyingTo.lxmf_message?.hash)?.content) || null;

            const fields = {};

            if (this.newMessageTelemetry) {
                fields["telemetry"] = this.newMessageTelemetry;
            }

            let fileAttachmentsTotalSize = 0;
            if (this.newMessageFiles.length > 0) {
                const fileAttachments = [];
                for (const file of this.newMessageFiles) {
                    fileAttachmentsTotalSize += file.size;
                    fileAttachments.push({
                        file_name: file.name,
                        file_size: file.size,
                        file_bytes: Utils.arrayBufferToBase64(await file.arrayBuffer()),
                    });
                }
                fields["file_attachments"] = fileAttachments;
            }

            let imageTotalSize = 0;
            const images = [];
            if (this.newMessageImages.length > 0) {
                for (const image of this.newMessageImages) {
                    imageTotalSize += image.size;
                    images.push({
                        image_type: image.type.replace("image/", ""),
                        image_size: image.size,
                        image_bytes: Utils.arrayBufferToBase64(await image.arrayBuffer()),
                        name: image.name,
                    });
                }
            }

            let audioTotalSize = 0;
            if (this.newMessageAudio) {
                audioTotalSize = this.newMessageAudio.audio_blob?.size ?? 0;
                fields["audio"] = {
                    audio_mode: this.newMessageAudio.audio_mode,
                    audio_size: this.newMessageAudio.audio_blob?.size ?? 0,
                    audio_bytes: Utils.arrayBufferToBase64(await this.newMessageAudio.audio_blob.arrayBuffer()),
                };
            }

            const contentSize = text.length;
            const totalMessageSize = contentSize + fileAttachmentsTotalSize + imageTotalSize + audioTotalSize;

            if (totalMessageSize > 1000 * 900) {
                if (
                    !(await DialogUtils.confirm(
                        `Your message exceeds 900KB (It's ${this.formatBytes(totalMessageSize)}). It may be rejected by the recipient unless they have increased their delivery limit. Do you want to try sending anyway?`
                    ))
                ) {
                    return null;
                }
            }

            const canOptimisticPending =
                this.newMessageFiles.length === 0 &&
                this.newMessageAudio == null &&
                this.newMessageTelemetry == null &&
                this.newMessageImages.length <= 1;

            return {
                destinationHash,
                deliveryMethod,
                text,
                fields,
                images,
                imagePreviewUrls: [...this.newMessageImageUrls],
                replyToHash,
                replyQuotedContent,
                myLxmfAddressHash: this.myLxmfAddressHash,
                canOptimisticPending,
            };
        },
        async sendMessage() {
            if (!this.canSendMessage) {
                return;
            }
            if (!this.selectedPeer) {
                return;
            }
            this._sendMessageChain = (this._sendMessageChain || Promise.resolve()).then(() =>
                this._enqueueOutboundFromCompose()
            );
            await this._sendMessageChain;
        },
        async _enqueueOutboundFromCompose() {
            try {
                const job = await this.buildOutboundJobSnapshot();
                if (!job) {
                    return;
                }
                this._outboundQueue.enqueue(job);
                this.clearComposeAfterEnqueue();
                this.$nextTick(() => {
                    this.adjustTextareaHeight();
                    this.scrollMessagesToBottom();
                });
            } catch (e) {
                console.error(e);
                const msg = e?.response?.data?.message ?? e?.message ?? "failed to prepare message";
                DialogUtils.alert(msg);
            }
        },
        async _executeOutboundSendJob(job) {
            try {
                job.pendingHash = null;
                if (job.canOptimisticPending) {
                    const pendingHash = `pending-${uuidv4()}`;
                    job.pendingHash = pendingHash;
                    const pendingFields = {};
                    if (job.images.length > 0) {
                        const previewUrl =
                            job.imagePreviewUrls[0] || this.lxmfDataUrlFromOutboundJobImage(job.images[0]);
                        pendingFields.image = {
                            image_type: job.images[0].image_type,
                            image_size: job.images[0].image_size,
                            _preview_url: previewUrl,
                        };
                    }
                    this.chatItems.push({
                        type: "lxmf_message",
                        lxmf_message: {
                            hash: pendingHash,
                            content: job.text,
                            state: "sending",
                            progress: 0,
                            created_at: new Date().toISOString(),
                            destination_hash: job.destinationHash,
                            source_hash: job.myLxmfAddressHash,
                            fields: Object.keys(pendingFields).length > 0 ? pendingFields : undefined,
                            reply_to_hash: job.replyToHash,
                            _pendingPathfinding: true,
                        },
                        is_outbound: true,
                    });
                    this.$nextTick(() => {
                        this.scrollMessagesToBottom();
                    });
                }

                if (job.images.length === 0) {
                    const response = await window.api.post(`/api/v1/lxmf-messages/send`, {
                        delivery_method: job.deliveryMethod,
                        lxmf_message: {
                            destination_hash: job.destinationHash,
                            content: job.text,
                            reply_to_hash: job.replyToHash,
                            reply_quoted_content: job.replyQuotedContent || null,
                            fields: job.fields,
                        },
                    });

                    this.removePendingOutboundPlaceholder(job.pendingHash);

                    if (!this.isLxmfMessageInUi(response.data.lxmf_message.hash)) {
                        this.chatItems.push({
                            type: "lxmf_message",
                            lxmf_message: this.normalizeLxmfMessage(response.data.lxmf_message, true),
                            is_outbound: true,
                        });
                    }
                } else {
                    const firstImage = job.images[0];
                    const firstFields = {
                        ...job.fields,
                        image: { image_type: firstImage.image_type, image_bytes: firstImage.image_bytes },
                    };

                    const response = await window.api.post(`/api/v1/lxmf-messages/send`, {
                        delivery_method: job.deliveryMethod,
                        lxmf_message: {
                            destination_hash: job.destinationHash,
                            content: job.text,
                            reply_to_hash: job.replyToHash,
                            reply_quoted_content: job.replyQuotedContent || null,
                            fields: firstFields,
                        },
                    });

                    this.removePendingOutboundPlaceholder(job.pendingHash);

                    if (!this.isLxmfMessageInUi(response.data.lxmf_message.hash)) {
                        this.chatItems.push({
                            type: "lxmf_message",
                            lxmf_message: this.normalizeLxmfMessage(response.data.lxmf_message, true),
                            is_outbound: true,
                        });
                    }

                    for (let i = 1; i < job.images.length; i++) {
                        const image = job.images[i];
                        const subsequentFields = {
                            image: { image_type: image.image_type, image_bytes: image.image_bytes },
                        };

                        try {
                            const subResponse = await window.api.post(`/api/v1/lxmf-messages/send`, {
                                delivery_method: job.deliveryMethod,
                                lxmf_message: {
                                    destination_hash: job.destinationHash,
                                    content: "",
                                    fields: subsequentFields,
                                },
                            });

                            if (!this.isLxmfMessageInUi(subResponse.data.lxmf_message.hash)) {
                                this.chatItems.push({
                                    type: "lxmf_message",
                                    lxmf_message: this.normalizeLxmfMessage(subResponse.data.lxmf_message, true),
                                    is_outbound: true,
                                });
                            }
                        } catch (subError) {
                            console.error(`Failed to send image ${i + 1}:`, subError);
                        }
                    }
                }

                this.scrollMessagesToBottom();
            } catch (e) {
                this.removePendingOutboundPlaceholder(job.pendingHash);
                const message = e.response?.data?.message ?? "failed to send message";
                DialogUtils.alert(message);
                console.log(e);
            }
        },
        async cancelSendingMessage(chatItem) {
            // get lxmf message hash else do nothing
            const lxmfMessageHash = chatItem.lxmf_message.hash;
            if (!lxmfMessageHash) {
                return;
            }

            try {
                // cancel sending lxmf message
                const response = await window.api.post(`/api/v1/lxmf-messages/${lxmfMessageHash}/cancel`);

                // get lxmf message from response
                const lxmfMessage = response.data.lxmf_message;
                if (!lxmfMessage) {
                    return;
                }

                // update lxmf message in ui
                this.onLxmfMessageUpdated(lxmfMessage);
            } catch (e) {
                // show error
                const message = e.response?.data?.message ?? "failed to cancel message";
                DialogUtils.alert(message);
                console.log(e);
            }
        },
        async retrySendingMessage(chatItem) {
            await this.deleteChatItem(chatItem, false);

            try {
                const replyQuoted =
                    chatItem.lxmf_message.fields?.reply_quoted_content ||
                    (chatItem.lxmf_message.reply_to_hash &&
                        this.getRepliedMessage(chatItem.lxmf_message.reply_to_hash)?.content);
                const response = await window.api.post(`/api/v1/lxmf-messages/send`, {
                    lxmf_message: {
                        destination_hash: chatItem.lxmf_message.destination_hash,
                        content: chatItem.lxmf_message.content,
                        reply_to_hash: chatItem.lxmf_message.reply_to_hash || null,
                        reply_quoted_content: replyQuoted || null,
                        fields: chatItem.lxmf_message.fields,
                    },
                });

                if (!this.isLxmfMessageInUi(response.data.lxmf_message.hash)) {
                    this.chatItems.push({
                        type: "lxmf_message",
                        lxmf_message: this.normalizeLxmfMessage(response.data.lxmf_message, true),
                        is_outbound: true,
                    });
                }

                this.scrollMessagesToBottom();
            } catch (e) {
                const message = e.response?.data?.message ?? "failed to send message";
                DialogUtils.alert(message);
                console.log(e);
            }
        },
        async retryAllFailedOrCancelledMessages() {
            const failedItems = this.selectedPeerChatItems.filter(
                (item) => item.is_outbound && ["failed", "cancelled"].includes(item.lxmf_message?.state)
            );
            if (failedItems.length === 0) return;

            if (
                !(await DialogUtils.confirm(
                    `Are you sure you want to retry sending all ${failedItems.length} failed/cancelled messages?`
                ))
            ) {
                return;
            }

            for (const item of failedItems) {
                await this.retrySendingMessage(item);
            }
        },
        async shareLocation() {
            const toastKey = "location_share";
            try {
                if (this.config?.location_source === "manual") {
                    const lat = parseFloat(this.config.location_manual_lat);
                    const lon = parseFloat(this.config.location_manual_lon);
                    const alt = parseFloat(this.config.location_manual_alt);

                    if (isNaN(lat) || isNaN(lon)) {
                        ToastUtils.error("Invalid manual coordinates in settings", 5000, toastKey);
                        return;
                    }

                    this.newMessageTelemetry = {
                        latitude: lat,
                        longitude: lon,
                        altitude: isNaN(alt) ? 0 : alt,
                        speed: 0,
                        bearing: 0,
                        accuracy: 0,
                        last_update: Math.floor(Date.now() / 1000),
                    };
                    this.sendMessage();
                    ToastUtils.success(this.$t("messages.location_sent"), 3000, toastKey);
                    return;
                }

                if (!navigator.geolocation) {
                    DialogUtils.alert(this.$t("map.geolocation_not_supported"));
                    return;
                }

                ToastUtils.loading(this.$t("messages.fetching_location"), 0, toastKey);

                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        this.newMessageTelemetry = {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            altitude: position.coords.altitude || 0,
                            speed: (position.coords.speed || 0) * 3.6, // m/s to km/h
                            bearing: position.coords.heading || 0,
                            accuracy: position.coords.accuracy || 0,
                            last_update: Math.floor(Date.now() / 1000),
                        };
                        this.sendMessage();
                        ToastUtils.success(this.$t("messages.location_sent"), 3000, toastKey);
                    },
                    (error) => {
                        ToastUtils.error(
                            `Failed to get location: ${error.message}. Try setting location manually in Settings.`,
                            5000,
                            toastKey
                        );
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 30000,
                        maximumAge: 0,
                    }
                );
            } catch (e) {
                console.log(e);
                ToastUtils.error(`Error: ${e.message}`, 5000, toastKey);
            }
        },
        async requestLocation() {
            try {
                if (!this.selectedPeer) return;

                // Send a telemetry request command
                await window.api.post(`/api/v1/lxmf-messages/send`, {
                    lxmf_message: {
                        destination_hash: this.selectedPeer.destination_hash,
                        content: "",
                        fields: {
                            commands: [{ "0x01": Math.floor(Date.now() / 1000) }],
                        },
                    },
                });

                ToastUtils.success(this.$t("messages.location_request_sent"));
            } catch (e) {
                console.log(e);
                ToastUtils.error(this.$t("messages.failed_send_location_request"));
            }
        },
        normalizeSidebandCommandKey(key) {
            const raw = String(key ?? "").trim();
            if (!raw) {
                return null;
            }
            const known = {
                plugin: "0x00",
                telemetry_request: "0x01",
                request: "0x01",
                location_request: "0x01",
                ping: "0x02",
                echo: "0x03",
                signal_report: "0x04",
            };
            if (Object.prototype.hasOwnProperty.call(known, raw.toLowerCase())) {
                return known[raw.toLowerCase()];
            }
            if (/^\d+$/.test(raw)) {
                const n = Number.parseInt(raw, 10);
                if (Number.isInteger(n) && n >= 0 && n <= 255) {
                    return `0x${n.toString(16).padStart(2, "0")}`;
                }
            }
            if (/^0x[0-9a-f]{1,2}$/i.test(raw)) {
                return `0x${raw.slice(2).toLowerCase().padStart(2, "0")}`;
            }
            return null;
        },
        parseCommandOrRequestText(text) {
            const trimmed = String(text || "").trim();
            const nowTs = Math.floor(Date.now() / 1000);

            if (!trimmed) {
                // Keep old behavior for empty input: telemetry/location request.
                return [{ "0x01": nowTs }];
            }

            if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
                const parsed = JSON.parse(trimmed);
                const list = Array.isArray(parsed) ? parsed : [parsed];
                const out = [];
                for (const cmd of list) {
                    if (!cmd || typeof cmd !== "object" || Array.isArray(cmd)) {
                        continue;
                    }
                    const mapped = {};
                    for (const [k, v] of Object.entries(cmd)) {
                        const normalized = this.normalizeSidebandCommandKey(k);
                        if (!normalized) {
                            continue;
                        }
                        mapped[normalized] = v;
                    }
                    if (Object.keys(mapped).length > 0) {
                        out.push(mapped);
                    }
                }
                if (out.length === 0) {
                    throw new Error("No valid command keys found");
                }
                return out;
            }

            const firstSpace = trimmed.search(/\s/);
            const keyToken = firstSpace === -1 ? trimmed : trimmed.slice(0, firstSpace);
            const arg = firstSpace === -1 ? "" : trimmed.slice(firstSpace + 1).trim();
            const key = this.normalizeSidebandCommandKey(keyToken);
            if (!key) {
                return [{ "0x00": trimmed }];
            }

            if (key === "0x01") {
                // request/location_request/telemetry_request
                return [{ "0x01": arg ? Number.parseInt(arg, 10) || nowTs : nowTs }];
            }
            if (key === "0x02" || key === "0x04") {
                return [{ [key]: arg ? arg.toLowerCase() !== "false" : true }];
            }
            if (key === "0x03") {
                return [{ "0x03": arg || "ping" }];
            }
            if (key === "0x00") {
                return [{ "0x00": arg || trimmed }];
            }
            return [{ [key]: arg || true }];
        },
        onComposerSendClick() {
            if (this.pendingSendAsCommandOrRequest) {
                void this.sendCommandOrRequest();
                return;
            }
            void this.sendMessage();
        },
        toggleLocationActionMenu() {
            this.showLocationActionMenu = !this.showLocationActionMenu;
        },
        closeLocationActionMenu() {
            this.showLocationActionMenu = false;
        },
        async selectSendLocation() {
            this.closeLocationActionMenu();
            await this.shareLocation();
        },
        async selectRequestLocation() {
            this.closeLocationActionMenu();
            await this.requestLocation();
        },
        enableNextSendAsCommandOrRequest() {
            this.pendingSendAsCommandOrRequest = true;
        },
        async sendCommandOrRequest() {
            try {
                if (!this.selectedPeer) return;
                const commands = this.parseCommandOrRequestText(this.newMessageText);
                await window.api.post(`/api/v1/lxmf-messages/send`, {
                    lxmf_message: {
                        destination_hash: this.selectedPeer.destination_hash,
                        content: "",
                        fields: { commands },
                    },
                });
                this.newMessageText = "";
                this.pendingSendAsCommandOrRequest = false;
                ToastUtils.success("Command or request sent");
            } catch (e) {
                console.log(e);
                ToastUtils.error(`Failed to send command/request: ${e.message}`);
            }
        },
        viewLocationOnMap(location) {
            // navigate to map and center on location
            this.$router.push({
                name: "map",
                query: {
                    lat: location.latitude,
                    lon: location.longitude,
                    zoom: 15,
                },
            });
        },
        openMapShareFromParsed(parsed) {
            if (!parsed) {
                return;
            }
            const query = {
                lat: String(parsed.lat),
                lon: String(parsed.lon),
                zoom: String(parsed.zoom),
            };
            if (parsed.layers) {
                query.layers = parsed.layers;
            }
            if (parsed.label) {
                query.label = parsed.label;
            }
            this.$router.push({
                name: "map",
                query,
            });
        },
        async copyMapShareUri(uri) {
            if (!uri) {
                return;
            }
            const ok = await copyTextToClipboard(uri);
            if (ok) {
                ToastUtils.success(this.$t("messages.map_link_copied"));
            } else {
                ToastUtils.error(this.$t("messages.clipboard_write_unavailable"));
            }
        },
        isTelemetryOnly(msg) {
            return isTelemetryOnlyMessage(msg);
        },
        hasRenderableContent(msg) {
            return messageHasRenderableContent(msg);
        },
        isImageOnlyMessage(chatItem) {
            return computeIsImageOnlyMessage(chatItem, (item) => this.shouldHideAutoImageCaption(item));
        },
        async toggleTracking() {
            if (!this.selectedPeer) return;
            const hash = this.selectedPeer.destination_hash;
            try {
                const response = await window.api.post(`/api/v1/telemetry/tracking/${hash}/toggle`, {
                    is_tracking: !this.selectedPeer.is_tracking,
                });
                // Emit event to parent to update peer status
                this.$emit("update-peer-tracking", {
                    destination_hash: hash,
                    is_tracking: response.data.is_tracking,
                });
                ToastUtils.success(response.data.is_tracking ? "Live tracking enabled" : "Live tracking disabled");
            } catch (e) {
                console.error("Failed to toggle tracking", e);
                ToastUtils.error("Failed to update tracking status");
            }
        },
        formatTimeAgo: function (datetimeString) {
            // Using this.now ensures the computed value updates when the timer ticks
            return this.now ? Utils.formatTimeAgo(datetimeString) : Utils.formatTimeAgo(datetimeString);
        },
        formatDateDividerLabel(dayKey) {
            if (!dayKey || typeof dayKey !== "string") {
                return "";
            }
            const p = dayKey.split("-").map((x) => parseInt(x, 10));
            if (p.length !== 3 || p.some((n) => Number.isNaN(n))) {
                return dayKey;
            }
            const d = new Date(p[0], p[1] - 1, p[2]);
            if (Number.isNaN(d.getTime())) {
                return dayKey;
            }
            const startOf = (dt) => {
                const x = new Date(dt);
                x.setHours(0, 0, 0, 0);
                return x.getTime();
            };
            const today = new Date();
            if (startOf(d) === startOf(today)) {
                return this.$t("messages.date_divider_today");
            }
            const y = new Date(today);
            y.setDate(y.getDate() - 1);
            if (startOf(d) === startOf(y)) {
                return this.$t("messages.date_divider_yesterday");
            }
            try {
                const loc = typeof this.$i18n?.locale === "string" ? this.$i18n.locale : "en";
                return new Intl.DateTimeFormat(loc, {
                    weekday: "long",
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                }).format(d);
            } catch {
                return dayKey;
            }
        },
        formatDestinationHash(hash) {
            return Utils.formatDestinationHash(hash);
        },
        async copyHash(hash) {
            const ok = await copyTextToClipboard(hash);
            if (ok) {
                ToastUtils.success(this.$t("messages.hash_copied"));
            } else {
                ToastUtils.error(this.$t("messages.clipboard_write_unavailable"));
            }
        },
        formatBytes: function (bytes) {
            return Utils.formatBytes(bytes);
        },
        base64ByteLength(base64String) {
            if (!base64String) {
                return 0;
            }
            const padding = (base64String.match(/=+$/) || [""])[0].length;
            return Math.floor((base64String.length * 3) / 4) - padding;
        },
        formatBase64Bytes(base64String) {
            return this.formatBytes(this.base64ByteLength(base64String));
        },
        openConversationPopout() {
            if (!this.selectedPeer) return;
            const destinationHash = this.selectedPeer.destination_hash || "";
            const encodedHash = encodeURIComponent(destinationHash);
            const url = `${window.location.origin}${window.location.pathname}#/popout/messages/${encodedHash}`;
            window.open(url, "_blank", "width=960,height=720,noopener");
        },
        async onStartCall() {
            try {
                await window.api.get(`/api/v1/telephone/call/${this.selectedPeer.destination_hash}`);
            } catch (e) {
                const message = e.response?.data?.message ?? "Failed to start call";
                DialogUtils.alert(message);
            }
        },
        collectImageFilesFromDataTransfer(dt) {
            return collectImagesFromDataTransfer(dt);
        },
        attachPastedOrDroppedImageFiles(imageBlobs, idPrefix) {
            const t = Date.now();
            imageBlobs.forEach((file, idx) => {
                let f = file;
                const ext = (file.type.split("/")[1] || "png").replace("jpeg", "jpg");
                if (!file.name || file.name === "image.png" || file.name === "image.jpeg") {
                    f = new File([file], `${idPrefix}-${t}-${idx}.${ext}`, { type: file.type });
                }
                this.onImageSelected(f);
            });
        },
        onMessagePaste(event) {
            const imageBlobs = extractClipboardImageFiles(event);
            if (imageBlobs.length === 0) {
                return;
            }
            event.preventDefault();
            this.attachPastedOrDroppedImageFiles(imageBlobs, "paste");
        },
        onComposerImageDragOver(event) {
            event.preventDefault();
            if (this.isTranslatingMessage) {
                return;
            }
            if (event.dataTransfer) {
                event.dataTransfer.dropEffect = "copy";
            }
            this.composerImageDropActive = true;
        },
        onComposerImageDragLeave(event) {
            const el = event.currentTarget;
            if (el && event.relatedTarget && el.contains(event.relatedTarget)) {
                return;
            }
            this.composerImageDropActive = false;
        },
        onComposerImageDrop(event) {
            this.composerImageDropActive = false;
            if (this.isTranslatingMessage) {
                return;
            }
            const dt = event.dataTransfer;
            const imageFiles = this.collectImageFilesFromDataTransfer(dt);
            if (imageFiles.length === 0) {
                return;
            }
            this.attachPastedOrDroppedImageFiles(imageFiles, "drop");
        },
        async pasteFromClipboard() {
            const result = await readTextFromClipboard();
            if (!result.ok) {
                if (result.code === "insecure_context") {
                    ToastUtils.error(this.$t("messages.clipboard_read_requires_secure_context"));
                } else {
                    ToastUtils.error(this.$t("messages.failed_read_clipboard"));
                }
                return;
            }
            const text = result.text;
            if (!text) {
                return;
            }
            const input = this.$refs["message-input"];
            if (!input) {
                return;
            }
            const start = input.selectionStart;
            const end = input.selectionEnd;
            const currentText = this.newMessageText || "";
            this.newMessageText = currentText.substring(0, start) + text + currentText.substring(end);

            this.$nextTick(() => {
                input.focus();
                const newCursorPos = start + text.length;
                input.setSelectionRange(newCursorPos, newCursorPos);
                input.style.height = "auto";
                input.style.height = Math.min(input.scrollHeight, 200) + "px";
            });
        },
        onFileInputChange: function (event) {
            const selectedFiles = Array.from(event.target.files || []);
            for (const file of selectedFiles) {
                const looksLikeImage =
                    file?.type?.startsWith("image/") ||
                    /\.(png|jpe?g|gif|webp|bmp|svg|avif|heic|heif)$/i.test(file?.name || "");
                if (looksLikeImage) {
                    this.onImageSelected(file);
                } else {
                    this.newMessageFiles.push(file);
                }
            }
            this.clearFileInput();
        },
        clearFileInput: function () {
            this.$refs["file-input"].value = null;
        },
        async removeImageAttachment(index) {
            // remove image
            this.newMessageImages.splice(index, 1);
            this.newMessageImageUrls.splice(index, 1);
        },
        onImageSelected: function (imageBlob) {
            // update selected file
            const index = this.newMessageImages.length;
            this.newMessageImages.push(imageBlob);

            // update image url when file is read
            const fileReader = new FileReader();
            fileReader.onload = (event) => {
                this.newMessageImageUrls[index] = event.target.result;
            };

            // convert image to data url
            fileReader.readAsDataURL(imageBlob);
        },
        onStickerPickerClickOutside() {
            this.isStickerPickerOpen = false;
            this.stickerDropActive = false;
            this.gifDropActive = false;
        },
        toggleStickerPicker() {
            if (!this.isStickerPickerOpen) {
                this.loadUserStickers();
                this.emojiStickerTab = "emoji";
            }
            this.isStickerPickerOpen = !this.isStickerPickerOpen;
        },
        onEmojiPickerClick(event) {
            const unicode = event?.detail?.unicode;
            if (unicode) {
                this.insertEmojiAtCaret(unicode);
            }
        },
        insertEmojiAtCaret(emoji) {
            const ta = this.$refs["message-input"];
            const text = this.newMessageText ?? "";
            if (!ta || typeof ta.selectionStart !== "number") {
                this.newMessageText = text + emoji;
                return;
            }
            const start = ta.selectionStart;
            const end = ta.selectionEnd ?? start;
            this.newMessageText = text.slice(0, start) + emoji + text.slice(end);
            this.$nextTick(() => {
                const el = this.$refs["message-input"];
                if (!el) {
                    return;
                }
                el.focus();
                const pos = start + emoji.length;
                el.setSelectionRange(pos, pos);
            });
        },
        async loadUserStickers() {
            try {
                const r = await window.api.get("/api/v1/stickers");
                this.userStickers = r.data?.stickers ?? [];
            } catch {
                this.userStickers = [];
            }
            try {
                const r = await window.api.get("/api/v1/sticker-packs");
                this.userStickerPacks = r.data?.packs ?? [];
            } catch {
                this.userStickerPacks = [];
            }
        },
        stickerImageUrl(stickerId) {
            return `/api/v1/stickers/${stickerId}/image`;
        },
        onStickerPanelDragOver(event) {
            event.preventDefault();
            if (event.dataTransfer) {
                event.dataTransfer.dropEffect = "copy";
            }
            this.stickerDropActive = true;
        },
        onStickerPanelDragLeave(event) {
            const el = event.currentTarget;
            if (el && event.relatedTarget && el.contains(event.relatedTarget)) {
                return;
            }
            this.stickerDropActive = false;
        },
        onStickerPanelDrop(event) {
            event.preventDefault();
            this.stickerDropActive = false;
            const files = event.dataTransfer?.files;
            if (files?.length) {
                this.uploadStickerImageFiles(files);
            }
        },
        triggerStickerUploadInput() {
            const input = this.$refs["sticker-upload-input"];
            if (input) input.click();
        },
        onStickerUploadInputChange(event) {
            const files = event.target.files;
            if (files?.length) {
                this.uploadStickerImageFiles(files);
            }
            event.target.value = "";
        },
        mimeToStickerType(mime, name = "") {
            const m = (mime || "").toLowerCase().split(";")[0].trim();
            const map = {
                "image/png": "png",
                "image/jpeg": "jpeg",
                "image/jpg": "jpeg",
                "image/gif": "gif",
                "image/webp": "webp",
                "image/bmp": "bmp",
                "image/x-ms-bmp": "bmp",
                "video/webm": "webm",
                "application/x-tgsticker": "tgs",
            };
            if (map[m]) {
                return map[m];
            }
            const ext = (name.split(".").pop() || "").toLowerCase();
            const extMap = {
                png: "png",
                jpg: "jpeg",
                jpeg: "jpeg",
                gif: "gif",
                webp: "webp",
                bmp: "bmp",
                webm: "webm",
                tgs: "tgs",
            };
            return extMap[ext] || null;
        },
        stickerTypeMaxBytes(type) {
            if (type === "tgs") return 64 * 1024;
            if (type === "webm") return 256 * 1024;
            return 512 * 1024;
        },
        async uploadStickerImageFiles(fileList) {
            const files = Array.from(fileList || []).filter((f) => f && f.size > 0);
            if (files.length === 0) {
                return;
            }
            this.isStickerUploading = true;
            let added = 0;
            let dup = 0;
            let failed = 0;
            try {
                for (const file of files) {
                    const imageType = this.mimeToStickerType(file.type, file.name);
                    if (!imageType) {
                        ToastUtils.error(this.$t("stickers.unsupported_type"));
                        failed++;
                        continue;
                    }
                    if (file.size > this.stickerTypeMaxBytes(imageType)) {
                        ToastUtils.error(this.$t("stickers.file_too_large"));
                        failed++;
                        continue;
                    }
                    try {
                        const buf = await file.arrayBuffer();
                        const imageBytes = Utils.arrayBufferToBase64(buf);
                        const payload = {
                            image_bytes: imageBytes,
                            image_type: imageType,
                            name: null,
                        };
                        if (imageType === "tgs" || imageType === "webm") {
                            payload.strict = true;
                        }
                        if (this.activeStickerPackId !== null) {
                            payload.pack_id = this.activeStickerPackId;
                        }
                        await window.api.post("/api/v1/stickers", payload);
                        added++;
                    } catch (e) {
                        const err = e?.response?.data?.error;
                        if (err === "duplicate_sticker") {
                            dup++;
                        } else {
                            failed++;
                            console.error(e);
                        }
                    }
                }
                await this.loadUserStickers();
                if (added > 0) {
                    ToastUtils.success(this.$t("stickers.uploaded_count", { count: added }));
                }
                if (dup > 0 && added === 0 && failed === 0) {
                    ToastUtils.info(this.$t("stickers.duplicate"));
                } else if (dup > 0 && added > 0) {
                    ToastUtils.info(this.$t("stickers.duplicate"));
                }
                if (failed > 0 && added === 0 && dup === 0) {
                    ToastUtils.error(this.$t("stickers.save_failed"));
                }
            } finally {
                this.isStickerUploading = false;
            }
        },
        async addStickerFromLibrary(sticker) {
            try {
                const res = await window.api.get(`/api/v1/stickers/${sticker.id}/image`, {
                    responseType: "blob",
                });
                const blob = res.data;
                const ext = sticker.image_type === "jpeg" ? "jpg" : sticker.image_type;
                const mime = blob.type || `image/${sticker.image_type}`;
                const file = new File([blob], `sticker-${sticker.id}.${ext}`, { type: mime });
                this.onImageSelected(file);
                this.isStickerPickerOpen = false;
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("stickers.save_failed"));
            }
        },
        async saveMessageImageToStickers(chatItem) {
            this.messageContextMenu.show = false;
            const msg = chatItem.lxmf_message;
            const img = msg.fields?.image;
            if (!img) {
                return;
            }
            let b64 = img.image_bytes;
            if (!b64) {
                try {
                    const res = await window.api.get(`/api/v1/lxmf-messages/attachment/${msg.hash}/image`, {
                        responseType: "arraybuffer",
                    });
                    b64 = Utils.arrayBufferToBase64(res.data);
                } catch (e) {
                    console.error(e);
                    ToastUtils.error(this.$t("stickers.save_failed"));
                    return;
                }
            }
            const imageType = String(img.image_type || "png").replace(/^image\//, "");
            try {
                await window.api.post("/api/v1/stickers", {
                    image_bytes: b64,
                    image_type: imageType,
                    source_message_hash: msg.hash,
                    name: null,
                });
                ToastUtils.success(this.$t("stickers.saved"));
                await this.loadUserStickers();
            } catch (e) {
                const err = e?.response?.data?.error;
                if (err === "duplicate_sticker") {
                    ToastUtils.info(this.$t("stickers.duplicate"));
                } else {
                    ToastUtils.error(this.$t("stickers.save_failed"));
                }
            }
        },
        onGifsTabSelected() {
            this.emojiStickerTab = "gifs";
            this.loadUserGifs();
        },
        async loadUserGifs() {
            try {
                const r = await window.api.get("/api/v1/gifs");
                this.userGifs = r.data?.gifs ?? [];
            } catch {
                this.userGifs = [];
            }
        },
        gifImageUrl(gifId) {
            return `/api/v1/gifs/${gifId}/image`;
        },
        onGifPanelDragOver(event) {
            event.preventDefault();
            if (event.dataTransfer) {
                event.dataTransfer.dropEffect = "copy";
            }
            this.gifDropActive = true;
        },
        onGifPanelDragLeave(event) {
            const el = event.currentTarget;
            if (el && event.relatedTarget && el.contains(event.relatedTarget)) {
                return;
            }
            this.gifDropActive = false;
        },
        onGifPanelDrop(event) {
            event.preventDefault();
            this.gifDropActive = false;
            const files = event.dataTransfer?.files;
            if (files?.length) {
                this.uploadGifFiles(files);
            }
        },
        triggerGifUploadInput() {
            const input = this.$refs["gif-upload-input"];
            if (input) input.click();
        },
        onGifUploadInputChange(event) {
            const files = event.target.files;
            if (files?.length) {
                this.uploadGifFiles(files);
            }
            event.target.value = "";
        },
        mimeToGifType(mime, name = "") {
            const m = (mime || "").toLowerCase().split(";")[0].trim();
            const map = {
                "image/gif": "gif",
                "image/webp": "webp",
            };
            if (map[m]) {
                return map[m];
            }
            const ext = (name.split(".").pop() || "").toLowerCase();
            const extMap = { gif: "gif", webp: "webp" };
            return extMap[ext] || null;
        },
        async uploadGifFiles(fileList) {
            const maxBytes = 5 * 1024 * 1024;
            const files = Array.from(fileList || []).filter((f) => f && f.size > 0);
            if (files.length === 0) {
                return;
            }
            this.isGifUploading = true;
            let added = 0;
            let dup = 0;
            let failed = 0;
            try {
                for (const file of files) {
                    if (file.size > maxBytes) {
                        ToastUtils.error(this.$t("gifs.file_too_large"));
                        failed++;
                        continue;
                    }
                    const imageType = this.mimeToGifType(file.type, file.name);
                    if (!imageType) {
                        ToastUtils.error(this.$t("gifs.unsupported_type"));
                        failed++;
                        continue;
                    }
                    try {
                        const buf = await file.arrayBuffer();
                        const imageBytes = Utils.arrayBufferToBase64(buf);
                        await window.api.post("/api/v1/gifs", {
                            image_bytes: imageBytes,
                            image_type: imageType,
                            name: null,
                        });
                        added++;
                    } catch (e) {
                        const err = e?.response?.data?.error;
                        if (err === "duplicate_gif") {
                            dup++;
                        } else {
                            failed++;
                            console.error(e);
                        }
                    }
                }
                await this.loadUserGifs();
                if (added > 0) {
                    ToastUtils.success(this.$t("gifs.uploaded_count", { count: added }));
                }
                if (dup > 0 && added === 0 && failed === 0) {
                    ToastUtils.info(this.$t("gifs.duplicate"));
                } else if (dup > 0 && added > 0) {
                    ToastUtils.info(this.$t("gifs.duplicate"));
                }
                if (failed > 0 && added === 0 && dup === 0) {
                    ToastUtils.error(this.$t("gifs.save_failed"));
                }
            } finally {
                this.isGifUploading = false;
            }
        },
        async addGifFromLibrary(gif) {
            try {
                const res = await window.api.get(`/api/v1/gifs/${gif.id}/image`, {
                    responseType: "blob",
                });
                const blob = res.data;
                const ext = gif.image_type;
                const mime = blob.type || `image/${gif.image_type}`;
                const file = new File([blob], `gif-${gif.id}.${ext}`, { type: mime });
                this.onImageSelected(file);
                this.isStickerPickerOpen = false;
                window.api.post(`/api/v1/gifs/${gif.id}/use`).catch(() => {});
                const idx = this.userGifs.findIndex((g) => g.id === gif.id);
                if (idx >= 0) {
                    const updated = { ...this.userGifs[idx], usage_count: (this.userGifs[idx].usage_count || 0) + 1 };
                    this.userGifs.splice(idx, 1);
                    let inserted = false;
                    for (let i = 0; i < this.userGifs.length; i++) {
                        if ((this.userGifs[i].usage_count || 0) <= updated.usage_count) {
                            this.userGifs.splice(i, 0, updated);
                            inserted = true;
                            break;
                        }
                    }
                    if (!inserted) this.userGifs.push(updated);
                }
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("gifs.save_failed"));
            }
        },
        canSaveMessageImageAsGif(chatItem) {
            const img = chatItem?.lxmf_message?.fields?.image;
            if (!img) return false;
            const t = String(img.image_type || "")
                .toLowerCase()
                .replace(/^image\//, "");
            return t === "gif" || t === "webp";
        },
        async saveMessageImageToGifs(chatItem) {
            this.messageContextMenu.show = false;
            const msg = chatItem.lxmf_message;
            const img = msg.fields?.image;
            if (!img) {
                return;
            }
            let b64 = img.image_bytes;
            if (!b64) {
                try {
                    const res = await window.api.get(`/api/v1/lxmf-messages/attachment/${msg.hash}/image`, {
                        responseType: "arraybuffer",
                    });
                    b64 = Utils.arrayBufferToBase64(res.data);
                } catch (e) {
                    console.error(e);
                    ToastUtils.error(this.$t("gifs.save_failed"));
                    return;
                }
            }
            const imageType = String(img.image_type || "gif").replace(/^image\//, "");
            try {
                await window.api.post("/api/v1/gifs", {
                    image_bytes: b64,
                    image_type: imageType,
                    source_message_hash: msg.hash,
                    name: null,
                });
                ToastUtils.success(this.$t("gifs.saved"));
                await this.loadUserGifs();
            } catch (e) {
                const err = e?.response?.data?.error;
                if (err === "duplicate_gif") {
                    ToastUtils.info(this.$t("gifs.duplicate"));
                } else {
                    ToastUtils.error(this.$t("gifs.save_failed"));
                }
            }
        },
        async startRecordingAudioAttachment(args) {
            // do nothing if already recording
            if (this.isRecordingAudioAttachment) {
                return;
            }

            // ask user to confirm recording new audio attachment, if an existing audio attachment exists
            if (
                this.newMessageAudio &&
                !(await DialogUtils.confirm(
                    "An audio recording is already attached. A new recording will replace it. Do you want to continue?"
                ))
            ) {
                return;
            }

            // handle selected codec
            switch (args.codec) {
                case "codec2": {
                    // start recording microphone
                    this.audioAttachmentMicrophoneRecorderCodec = "codec2";
                    this.audioAttachmentMicrophoneRecorder = new Codec2MicrophoneRecorder();
                    this.audioAttachmentMicrophoneRecorder.codec2Mode = args.mode;
                    this.audioAttachmentRecordingStartedAt = Date.now();
                    this.isRecordingAudioAttachment = await this.audioAttachmentMicrophoneRecorder.start();

                    // update recording time in ui every second
                    this.audioAttachmentRecordingDuration = Utils.formatMinutesSeconds(0);
                    this.audioAttachmentRecordingTimer = setInterval(() => {
                        const recordingDurationMillis = Date.now() - this.audioAttachmentRecordingStartedAt;
                        const recordingDurationSeconds = recordingDurationMillis / 1000;
                        this.audioAttachmentRecordingDuration = Utils.formatMinutesSeconds(recordingDurationSeconds);
                    }, 1000);

                    // alert if failed to start recording
                    if (!this.isRecordingAudioAttachment) {
                        DialogUtils.alert(this.buildAudioRecordingFailureMessage());
                    }

                    break;
                }
                case "opus": {
                    if (this.isMeshChatXAndroid() && this.androidNativeWavAttachmentAllowed()) {
                        const res = window.MeshChatXAndroid.startNativeWavAttachment();
                        if (res === "ok") {
                            this.androidNativeOpusAttachment = true;
                            this.audioAttachmentMicrophoneRecorderCodec = "opus";
                            this.audioAttachmentMicrophoneRecorder = { _androidNative: true };
                            this.audioAttachmentRecordingStartedAt = Date.now();
                            this.isRecordingAudioAttachment = true;
                            this.audioAttachmentRecordingDuration = Utils.formatMinutesSeconds(0);
                            this.audioAttachmentRecordingTimer = setInterval(() => {
                                const recordingDurationMillis = Date.now() - this.audioAttachmentRecordingStartedAt;
                                const recordingDurationSeconds = recordingDurationMillis / 1000;
                                this.audioAttachmentRecordingDuration =
                                    Utils.formatMinutesSeconds(recordingDurationSeconds);
                            }, 1000);
                            break;
                        }
                    }
                    this.audioAttachmentMicrophoneRecorderCodec = "opus";
                    this.audioAttachmentMicrophoneRecorder = new MicrophoneRecorder();
                    this.audioAttachmentRecordingStartedAt = Date.now();
                    this.isRecordingAudioAttachment = await this.audioAttachmentMicrophoneRecorder.start();

                    this.audioAttachmentRecordingDuration = Utils.formatMinutesSeconds(0);
                    this.audioAttachmentRecordingTimer = setInterval(() => {
                        const recordingDurationMillis = Date.now() - this.audioAttachmentRecordingStartedAt;
                        const recordingDurationSeconds = recordingDurationMillis / 1000;
                        this.audioAttachmentRecordingDuration = Utils.formatMinutesSeconds(recordingDurationSeconds);
                    }, 1000);

                    if (!this.isRecordingAudioAttachment) {
                        DialogUtils.alert(this.buildAudioRecordingFailureMessage());
                    }

                    break;
                }
                default: {
                    DialogUtils.alert(`Unhandled microphone recorder codec: ${args.codec}`);
                    break;
                }
            }
        },
        async stopRecordingAudioAttachment() {
            // clear audio recording timer
            clearInterval(this.audioAttachmentRecordingTimer);

            if (!this.isRecordingAudioAttachment) {
                return;
            }

            this.isRecordingAudioAttachment = false;
            if (this.androidNativeOpusAttachment) {
                this.androidNativeOpusAttachment = false;
                const p = new Promise((resolve) => {
                    const done = () => {
                        try {
                            if (window.__meshchatXNative) {
                                window.__meshchatXNative = undefined;
                            }
                        } catch {
                            // ignore
                        }
                        resolve();
                    };
                    window.__meshchatXNative = {
                        onWav: (payload) => {
                            if (!payload || !payload.ok) {
                                const err = payload && payload.error ? String(payload.error) : "unknown";
                                if (err !== "empty") {
                                    DialogUtils.alert(`${this.$t("messages.failed")}${err ? ` (${err})` : ""}`);
                                }
                                done();
                                return;
                            }
                            try {
                                const binary = atob(payload.data);
                                const bytes = new Uint8Array(binary.length);
                                for (let i = 0; i < binary.length; i += 1) {
                                    bytes[i] = binary.charCodeAt(i);
                                }
                                const audio = new Blob([bytes], { type: "audio/wav" });
                                this.newMessageAudio = {
                                    audio_mode: 0x10,
                                    audio_blob: audio,
                                    audio_preview_url: URL.createObjectURL(audio),
                                };
                            } catch {
                                DialogUtils.alert(this.buildAudioRecordingFailureMessage());
                            }
                            done();
                        },
                    };
                    try {
                        window.MeshChatXAndroid.stopNativeWavAttachment();
                    } catch {
                        DialogUtils.alert(this.buildAudioRecordingFailureMessage());
                        done();
                    }
                });
                await p;
                this.audioAttachmentMicrophoneRecorder = null;
                this.audioAttachmentMicrophoneRecorderCodec = null;
                return;
            }

            const audio = await this.audioAttachmentMicrophoneRecorder.stop();

            // handle audio based on codec
            switch (this.audioAttachmentMicrophoneRecorderCodec) {
                case "codec2": {
                    // do nothing if no audio was provided
                    if (audio.length === 0) {
                        return;
                    }

                    // decode codec2 audio back to wav so we can show a preview audio player before user sends it
                    const codec2Mode = this.audioAttachmentMicrophoneRecorder.codec2Mode;
                    const decoded = await Codec2Lib.runDecode(codec2Mode, new Uint8Array(audio));

                    // convert decoded codec2 to wav audio and create a blob
                    const wavAudio = await Codec2Lib.rawToWav(decoded);
                    const wavBlob = new Blob([wavAudio], {
                        type: "audio/wav",
                    });

                    // determine audio mode
                    var audioMode = null;
                    switch (codec2Mode) {
                        case "1200": {
                            audioMode = 0x04; // LXMF.AM_CODEC2_1200
                            break;
                        }
                        case "3200": {
                            audioMode = 0x09; // LXMF.AM_CODEC2_3200
                            break;
                        }
                        default: {
                            DialogUtils.alert(`Unhandled microphone recorder codec2Mode: ${codec2Mode}`);
                            return;
                        }
                    }

                    // update message audio attachment
                    this.newMessageAudio = {
                        audio_mode: audioMode,
                        audio_blob: new Blob([audio]),
                        audio_preview_url: URL.createObjectURL(wavBlob),
                    };

                    break;
                }
                case "opus": {
                    // do nothing if no audio was provided
                    if (audio.size === 0) {
                        return;
                    }

                    // update message audio attachment
                    this.newMessageAudio = {
                        audio_mode: 0x10, // LXMF.AM_OPUS_OGG
                        audio_blob: audio, // opus microphone recorder returns a blob
                        audio_preview_url: URL.createObjectURL(audio),
                    };

                    break;
                }
            }
        },
        async removeAudioAttachment() {
            // remove audio
            this.newMessageAudio = null;
        },
        buildAudioRecordingFailureMessage() {
            if (!navigator?.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== "function") {
                return `${this.$t("messages.failed_start_recording")}. ${this.$t("messages.failed_start_recording_help_mediadevices")}`;
            }
            const AudioContextCtor = globalThis.AudioContext || globalThis.webkitAudioContext;
            if (typeof AudioContextCtor !== "function") {
                return `${this.$t("messages.failed_start_recording")}. ${this.$t("messages.failed_start_recording_help_web_audio")}`;
            }
            let probe = null;
            try {
                probe = new AudioContextCtor();
                const canWorklet =
                    globalThis.isSecureContext !== false &&
                    probe.audioWorklet &&
                    typeof probe.audioWorklet.addModule === "function";
                const canScriptProcessor = typeof probe.createScriptProcessor === "function";
                if (!canWorklet && !canScriptProcessor) {
                    return `${this.$t("messages.failed_start_recording")}. ${this.$t("messages.failed_start_recording_help_audio_worklet")}`;
                }
            } catch {
                return `${this.$t("messages.failed_start_recording")}. ${this.$t("messages.failed_start_recording_help_web_audio")}`;
            } finally {
                try {
                    if (probe && typeof probe.close === "function") {
                        const closed = probe.close();
                        if (closed && typeof closed.catch === "function") {
                            void closed.catch(() => {});
                        }
                    }
                } catch {
                    // ignore
                }
            }
            return `${this.$t("messages.failed_start_recording")}. ${this.$t("messages.failed_start_recording_help_permission")}`;
        },
        removeFileAttachment: function (file) {
            this.newMessageFiles = this.newMessageFiles.filter((newMessageFile) => {
                return newMessageFile !== file;
            });
        },
        addNewLine: function () {
            // get cursor position for message input
            const input = this.$refs["message-input"];
            const cursorPosition = input.selectionStart;

            // insert a newline character after the cursor position
            const text = this.newMessageText;
            this.newMessageText = text.slice(0, cursorPosition) + "\n" + text.slice(cursorPosition);

            // move cursor to the position after the added newline
            const newCursorPosition = cursorPosition + 1;
            this.$nextTick(() => {
                input.selectionStart = newCursorPosition;
                input.selectionEnd = newCursorPosition;
            });
        },
        onEnterPressed: function () {
            // add new line on mobile
            if (this.isMobile) {
                this.addNewLine();
                return;
            }

            // send message on desktop
            this.sendMessage();
        },
        onShiftEnterPressed: function () {
            this.addNewLine();
        },
        addFilesToMessage: function () {
            this.$refs["file-input"].click();
        },
        findConversation: function (destinationHash) {
            return this.conversations.find((conversation) => {
                return conversation.destination_hash === destinationHash;
            });
        },
        async markConversationAsRead(conversation) {
            // manually mark conversation read in memory to avoid delay updating ui
            conversation.is_unread = false;

            // mark conversation as read on server
            try {
                await window.api.post(`/api/v1/lxmf/conversations/${conversation.destination_hash}/mark-as-read`);
            } catch (e) {
                // do nothing if failed to mark as read
                console.log(e);
            }

            // reload conversations
            this.$emit("reload-conversations");
        },
        toggleSentMessageInfo: function (messageHash) {
            if (this.expandedMessageInfo === messageHash) {
                this.expandedMessageInfo = null;
            } else {
                this.expandedMessageInfo = messageHash;
            }
        },
        toggleReceivedMessageInfo: function (messageHash) {
            if (this.expandedMessageInfo === messageHash) {
                this.expandedMessageInfo = null;
            } else {
                this.expandedMessageInfo = messageHash;
            }
        },
        getMessageInfoLines: function (lxmfMessage, isOutbound) {
            const lines = [];

            if (isOutbound) {
                lines.push(`Created: ${Utils.convertUnixMillisToLocalDateTimeString(lxmfMessage.timestamp * 1000)}`);
            } else {
                lines.push(`Sent: ${Utils.convertUnixMillisToLocalDateTimeString(lxmfMessage.timestamp * 1000)}`);
                lines.push(`Received: ${Utils.convertDateTimeToLocalDateTimeString(new Date(lxmfMessage.created_at))}`);
            }

            lines.push(`Method: ${lxmfMessage.method ?? "unknown"}`);

            if (lxmfMessage.fields?.audio) {
                const audioSize =
                    lxmfMessage.fields.audio.audio_size ??
                    (lxmfMessage.fields.audio.audio_bytes ? atob(lxmfMessage.fields.audio.audio_bytes).length : 0);
                if (audioSize > 0) lines.push(`Audio Attachment: ${this.formatBytes(audioSize)}`);
            }

            if (lxmfMessage.fields?.image) {
                const imageSize =
                    lxmfMessage.fields.image.image_size ??
                    (lxmfMessage.fields.image.image_bytes ? atob(lxmfMessage.fields.image.image_bytes).length : 0);
                if (imageSize > 0) lines.push(`Image Attachment: ${this.formatBytes(imageSize)}`);
            }

            if (lxmfMessage.fields?.file_attachments) {
                let filesLength = 0;
                const fileAttachments = lxmfMessage.fields.file_attachments;
                for (const fileAttachment of fileAttachments) {
                    const fileBytesLength =
                        fileAttachment.file_size ??
                        (fileAttachment.file_bytes ? atob(fileAttachment.file_bytes).length : 0);
                    filesLength += fileBytesLength;
                }
                if (filesLength > 0) lines.push(`File Attachments: ${this.formatBytes(filesLength)}`);
            }

            if (!isOutbound) {
                if (lxmfMessage.quality != null) {
                    lines.push(`Signal Quality: ${lxmfMessage.quality}%`);
                }
                if (lxmfMessage.rssi != null) {
                    lines.push(`RSSI: ${lxmfMessage.rssi}dBm`);
                }
                if (lxmfMessage.snr != null) {
                    lines.push(`SNR: ${lxmfMessage.snr}dB`);
                }
            }

            return lines;
        },
    },
};
</script>

<style scoped>
@reference "../../style.css";
.attachment-card {
    @apply relative flex gap-3 border border-gray-200 dark:border-zinc-800 rounded-2xl p-3 shadow-sm;
    background-color: white;
}
.dark .attachment-card {
    background-color: rgb(24 24 27);
}
.attachment-card__preview {
    @apply w-24 h-24 overflow-hidden rounded-xl bg-gray-100 dark:bg-zinc-800 cursor-pointer;
}
.attachment-card__body {
    @apply flex-1;
}
.attachment-card__title {
    @apply text-sm font-semibold text-gray-800 dark:text-gray-100;
}
.attachment-card__meta {
    @apply text-xs text-gray-500 dark:text-gray-400;
}
.attachment-card__remove {
    @apply absolute top-2 right-2 inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-200 dark:bg-zinc-800 text-gray-600 dark:text-gray-200 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/40;
}
.attachment-chip {
    @apply flex items-center justify-between gap-2 border border-gray-200 dark:border-zinc-800 rounded-full px-3 py-1 text-xs shadow-sm;
    background-color: white;
}
.dark .attachment-chip {
    background-color: rgb(24 24 27);
}
.attachment-chip__remove {
    @apply inline-flex items-center justify-center text-gray-500 dark:text-gray-300 hover:text-red-500;
}
.attachment-action-button {
    @apply inline-flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1.5 text-xs font-bold text-gray-700 bg-white shadow-xs transition-all;
}
.attachment-action-button:hover {
    @apply bg-gray-50 text-gray-900 border-blue-400;
}
.dark .attachment-action-button {
    @apply border-zinc-700 text-zinc-100 bg-zinc-900;
}
.dark .attachment-action-button:hover {
    @apply bg-zinc-800 text-white border-blue-500;
}

.compose-emoji-picker {
    width: 100%;
    height: min(320px, 50vh);
    min-height: 220px;
    --border-radius: 0.75rem;
}

.audio-controls-light {
    filter: invert(1) hue-rotate(180deg);
}

.dark .audio-controls-light {
    filter: none;
}

.audio-controls-dark {
    filter: none;
}

.dark .audio-controls-dark {
    filter: invert(1) hue-rotate(180deg);
}
.markdown-content :deep(p) {
    margin: 0.5rem 0;
}

.markdown-content--single-emoji {
    line-height: 1;
}

.markdown-content--single-emoji :deep(p) {
    margin: 0;
    line-height: 1;
}

.markdown-content :deep(strong) {
    font-weight: 700;
}

.markdown-content :deep(em) {
    font-style: italic;
}

.markdown-content :deep(pre) {
    margin: 0.75rem 0;
}

.markdown-content :deep(code) {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3) {
    line-height: 1.2;
}

.markdown-content :deep(a) {
    color: #0369a1;
    text-decoration: underline;
    text-underline-offset: 2px;
}

.dark .markdown-content :deep(a) {
    color: #7dd3fc;
}

.markdown-content--outbound-theme :deep(a) {
    color: #075985;
}

.dark .markdown-content--outbound-theme :deep(a) {
    color: #bae6fd;
}

.markdown-content--outbound-solid :deep(a) {
    color: #dbeafe;
}

.scroll-fab-enter-active,
.scroll-fab-leave-active {
    transition:
        opacity 0.15s ease,
        transform 0.15s ease;
}
.scroll-fab-enter-from,
.scroll-fab-leave-to {
    opacity: 0;
}

.reaction-emoji-picker {
    width: 100%;
    height: min(280px, 45vh);
    min-height: 200px;
    --border-radius: 0;
    --border-size: 0;
}
</style>
