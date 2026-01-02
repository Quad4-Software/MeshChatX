<template>
    <!-- peer selected -->
    <div v-if="selectedPeer" class="flex flex-col h-full bg-white dark:bg-zinc-950 overflow-hidden transition-all">
        <!-- header -->
        <div
            class="flex items-center px-4 py-3 border-b border-gray-200/60 dark:border-zinc-800/60 bg-white/80 dark:bg-zinc-900/50 backdrop-blur-sm"
        >
            <!-- peer icon -->
            <div class="flex-shrink-0 mr-3">
                <div
                    v-if="selectedPeer.lxmf_user_icon"
                    class="p-2 rounded shadow-sm"
                    :style="{
                        color: selectedPeer.lxmf_user_icon.foreground_colour,
                        'background-color': selectedPeer.lxmf_user_icon.background_colour,
                    }"
                >
                    <MaterialDesignIcon :icon-name="selectedPeer.lxmf_user_icon.icon_name" class="w-6 h-6" />
                </div>
                <div v-else class="bg-gray-200 dark:bg-zinc-700 text-gray-500 dark:text-gray-400 p-2 rounded shadow-sm">
                    <MaterialDesignIcon icon-name="account-outline" class="w-6 h-6" />
                </div>
            </div>

            <!-- peer info -->
            <div class="min-w-0 flex-1">
                <div class="flex items-center cursor-pointer min-w-0 group" @click="updateCustomDisplayName">
                    <div
                        v-if="selectedPeer.custom_display_name != null"
                        class="mr-1.5 text-gray-500 dark:text-zinc-400 group-hover:text-gray-700 dark:group-hover:text-zinc-200 transition-colors"
                        :title="$t('messages.custom_display_name')"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="w-3.5 h-3.5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M9.568 3H5.25A2.25 2.25 0 0 0 3 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 0 0 5.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 0 0 9.568 3Z"
                            />
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6 6h.008v.008H6V6Z" />
                        </svg>
                    </div>
                    <div
                        class="font-semibold text-gray-900 dark:text-zinc-100 truncate max-w-xs sm:max-w-sm text-base"
                        :title="selectedPeer.custom_display_name ?? selectedPeer.display_name"
                    >
                        {{ selectedPeer.custom_display_name ?? selectedPeer.display_name }}
                    </div>
                </div>
                <div class="text-xs text-gray-500 dark:text-zinc-400 mt-0.5">
                    <!-- destination hash -->
                    <div class="inline-block mr-1">
                        <div>&lt;{{ selectedPeer.destination_hash }}&gt;</div>
                    </div>

                    <div class="inline-block">
                        <div class="flex space-x-1">
                            <!-- hops away -->
                            <span
                                v-if="selectedPeerPath"
                                class="flex my-auto cursor-pointer"
                                @click="onDestinationPathClick(selectedPeerPath)"
                            >
                                <span v-if="selectedPeerPath.hops === 0 || selectedPeerPath.hops === 1">{{
                                    $t("messages.direct")
                                }}</span>
                                <span v-else>{{ $t("messages.hops_away", { count: selectedPeerPath.hops }) }}</span>
                            </span>

                            <!-- snr -->
                            <span v-if="selectedPeerSignalMetrics?.snr != null" class="flex my-auto space-x-1">
                                <span v-if="selectedPeerPath">•</span>
                                <span class="cursor-pointer" @click="onSignalMetricsClick(selectedPeerSignalMetrics)">{{
                                    $t("messages.snr", { snr: selectedPeerSignalMetrics.snr })
                                }}</span>
                            </span>

                            <!-- stamp cost -->
                            <span v-if="selectedPeerLxmfStampInfo?.stamp_cost" class="flex my-auto space-x-1">
                                <span v-if="selectedPeerPath || selectedPeerSignalMetrics?.snr != null">•</span>
                                <span class="cursor-pointer" @click="onStampInfoClick(selectedPeerLxmfStampInfo)">{{
                                    $t("messages.stamp_cost", { cost: selectedPeerLxmfStampInfo.stamp_cost })
                                }}</span>
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- dropdown menu -->
            <div class="ml-auto flex items-center gap-1">
                <ConversationDropDownMenu
                    v-if="selectedPeer"
                    :peer="selectedPeer"
                    @conversation-deleted="onConversationDeleted"
                    @set-custom-display-name="updateCustomDisplayName"
                    @block-status-changed="loadBlockedDestinations"
                />

                <!-- popout button -->
                <IconButton :title="$t('messages.pop_out_chat')" @click="openConversationPopout">
                    <MaterialDesignIcon icon-name="open-in-new" class="w-4 h-4" />
                </IconButton>

                <!-- share contact button -->
                <IconButton title="Share Contact" @click="openShareContactModal">
                    <MaterialDesignIcon icon-name="notebook-outline" class="w-4 h-4" />
                </IconButton>

                <!-- close button -->
                <IconButton title="Close" @click="close">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                        <path
                            d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
                        />
                    </svg>
                </IconButton>
            </div>
        </div>

        <!-- Share Contact Modal -->
        <div
            v-if="isShareContactModalOpen"
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            @click.self="isShareContactModalOpen = false"
        >
            <div class="w-full max-w-md bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl overflow-hidden">
                <div class="px-6 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">Share Contact</h3>
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
                                placeholder="Search contacts..."
                                class="block w-full rounded-lg border-0 py-2 pl-10 text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-zinc-800 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm dark:bg-zinc-900"
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
                            <div
                                class="size-10 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-500 flex items-center justify-center shrink-0"
                            >
                                <MaterialDesignIcon icon-name="account" class="size-6" />
                            </div>
                            <div class="min-w-0">
                                <div class="font-bold text-gray-900 dark:text-white truncate">
                                    {{ contact.name }}
                                </div>
                                <div class="text-[10px] text-gray-500 dark:text-zinc-500 font-mono truncate">
                                    {{ contact.remote_identity_hash }}
                                </div>
                            </div>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- chat items -->
        <div
            id="messages"
            class="h-full overflow-y-scroll bg-gray-50/30 dark:bg-zinc-950/50"
            @scroll="onMessagesScroll"
        >
            <div v-if="selectedPeerChatItems.length > 0" class="flex flex-col flex-col-reverse px-4 py-6">
                <div
                    v-for="chatItem of selectedPeerChatItemsReversed"
                    :key="chatItem.lxmf_message.hash"
                    class="flex flex-col max-w-[75%] sm:max-w-[65%] lg:max-w-[55%] mb-4 group"
                    :class="{ 'ml-auto items-end': chatItem.is_outbound, 'mr-auto items-start': !chatItem.is_outbound }"
                >
                    <!-- message content -->
                    <div
                        class="relative rounded-2xl overflow-hidden transition-all duration-200 hover:shadow-md"
                        :class="[
                            ['cancelled', 'failed'].includes(chatItem.lxmf_message.state)
                                ? 'bg-red-500 text-white shadow-sm'
                                : chatItem.lxmf_message.is_spam
                                  ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-900 dark:text-yellow-100 border border-yellow-300 dark:border-yellow-700 shadow-sm'
                                  : chatItem.is_outbound
                                    ? 'bg-blue-600 text-white shadow-sm'
                                    : 'bg-white dark:bg-zinc-900 text-gray-900 dark:text-zinc-100 border border-gray-200/60 dark:border-zinc-800/60 shadow-sm',
                        ]"
                        @click="onChatItemClick(chatItem)"
                    >
                        <div class="w-full space-y-1 px-4 py-2.5">
                            <!-- spam badge -->
                            <div
                                v-if="chatItem.lxmf_message.is_spam"
                                class="flex items-center gap-1.5 text-xs font-medium mb-1"
                                :class="
                                    chatItem.is_outbound ? 'text-yellow-200' : 'text-yellow-700 dark:text-yellow-300'
                                "
                            >
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="2"
                                    stroke="currentColor"
                                    class="w-4 h-4"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                                    />
                                </svg>
                                <span>Marked as Spam</span>
                            </div>

                            <!-- content -->
                            <div
                                v-if="chatItem.lxmf_message.content"
                                class="text-sm leading-relaxed whitespace-pre-wrap break-words"
                                style="font-family: inherit"
                            >
                                {{ chatItem.lxmf_message.content }}
                            </div>

                            <!-- image field -->
                            <div v-if="chatItem.lxmf_message.fields?.image" class="relative group mt-1 -mx-1">
                                <img
                                    :src="`/api/v1/lxmf-messages/attachment/${chatItem.lxmf_message.hash}/image`"
                                    class="w-full rounded-lg cursor-pointer transition-transform group-hover:scale-[1.01]"
                                    @click.stop="
                                        openImage(
                                            `/api/v1/lxmf-messages/attachment/${chatItem.lxmf_message.hash}/image`
                                        )
                                    "
                                />
                                <div
                                    class="absolute bottom-2 left-2 bg-black/60 backdrop-blur-sm text-white text-xs px-2.5 py-1 rounded-lg flex items-center gap-1.5"
                                >
                                    <span>{{
                                        (chatItem.lxmf_message.fields.image.image_type ?? "image").toUpperCase()
                                    }}</span>
                                    <span>•</span>
                                    <span>{{ formatAttachmentSize(chatItem.lxmf_message.fields.image, "image") }}</span>
                                </div>
                            </div>

                            <!-- audio field -->
                            <div v-if="chatItem.lxmf_message.fields?.audio" class="pb-1">
                                <!-- audio is loaded -->
                                <audio
                                    v-if="lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash]"
                                    :src="lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash]"
                                    controls
                                    class="w-full rounded-lg shadow-sm"
                                    style="height: 54px"
                                    :class="chatItem.is_outbound ? 'audio-controls-light' : 'audio-controls-dark'"
                                ></audio>

                                <!-- audio is not yet loaded -->
                                <!-- min height to make sure audio player doesn't cause height increase after loading -->
                                <div v-else style="min-height: 54px" class="flex">
                                    <button
                                        type="button"
                                        class="my-auto flex items-center gap-2 border border-gray-200/60 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                                        :class="
                                            chatItem.is_outbound
                                                ? 'bg-white/20 text-white border-white/20 hover:bg-white/30'
                                                : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300'
                                        "
                                        @click="downloadAndDecodeAudio(chatItem)"
                                    >
                                        <span class="my-auto">
                                            <svg
                                                xmlns="http://www.w3.org/2000/svg"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke-width="1.5"
                                                stroke="currentColor"
                                                class="size-6"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    d="m9 9 10.5-3m0 6.553v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 1 1-.99-3.467l2.31-.66a2.25 2.25 0 0 0 1.632-2.163Zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 0 1-.99-3.467l2.31-.66A2.25 2.25 0 0 0 9 15.553Z"
                                                />
                                            </svg>
                                        </span>
                                        <span class="my-auto w-full">
                                            {{
                                                isDownloadingAudio[chatItem.lxmf_message.hash]
                                                    ? "Downloading..."
                                                    : chatItem.lxmf_message.fields.audio.audio_mode === 0x10
                                                      ? "Load Audio"
                                                      : "Load Audio (Codec2)"
                                            }}
                                        </span>
                                        <span class="my-auto">
                                            <svg
                                                xmlns="http://www.w3.org/2000/svg"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke-width="1.5"
                                                stroke="currentColor"
                                                class="w-6 h-6"
                                                :class="
                                                    isDownloadingAudio[chatItem.lxmf_message.hash]
                                                        ? 'animate-bounce'
                                                        : ''
                                                "
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
                                                />
                                            </svg>
                                        </span>
                                    </button>
                                </div>

                                <div
                                    class="text-xs mt-1.5"
                                    :class="chatItem.is_outbound ? 'text-white/70' : 'text-gray-500 dark:text-zinc-400'"
                                >
                                    Audio • {{ formatAttachmentSize(chatItem.lxmf_message.fields.audio, "audio") }}
                                </div>
                            </div>

                            <!-- file attachment fields -->
                            <div v-if="chatItem.lxmf_message.fields?.file_attachments" class="space-y-2 mt-1">
                                <a
                                    v-for="(file_attachment, index) of chatItem.lxmf_message.fields?.file_attachments ??
                                    []"
                                    :key="file_attachment.file_name"
                                    target="_blank"
                                    :download="file_attachment.file_name"
                                    :href="`/api/v1/lxmf-messages/attachment/${chatItem.lxmf_message.hash}/file?file_index=${index}`"
                                    class="flex items-center gap-3 border rounded-lg px-3 py-2 text-sm font-medium cursor-pointer transition-colors"
                                    :class="
                                        chatItem.is_outbound
                                            ? 'bg-white/20 text-white border-white/20 hover:bg-white/30'
                                            : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300 border-gray-200/60 dark:border-zinc-700 hover:bg-gray-100 dark:hover:bg-zinc-800'
                                    "
                                    @click.stop
                                >
                                    <div class="my-auto">
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke-width="1.5"
                                            stroke="currentColor"
                                            class="w-6 h-6"
                                        >
                                            <path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                d="m18.375 12.739-7.693 7.693a4.5 4.5 0 0 1-6.364-6.364l10.94-10.94A3 3 0 1 1 19.5 7.372L8.552 18.32m.009-.01-.01.01m5.699-9.941-7.81 7.81a1.5 1.5 0 0 0 2.112 2.13"
                                            ></path>
                                        </svg>
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <div class="truncate">{{ file_attachment.file_name }}</div>
                                        <div
                                            class="text-xs font-normal mt-0.5"
                                            :class="
                                                chatItem.is_outbound
                                                    ? 'text-white/60'
                                                    : 'text-gray-500 dark:text-zinc-400'
                                            "
                                        >
                                            {{ formatAttachmentSize(file_attachment, "file") }}
                                        </div>
                                    </div>
                                    <div class="my-auto">
                                        <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke-width="1.5"
                                            stroke="currentColor"
                                            class="w-6 h-6"
                                        >
                                            <path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
                                            />
                                        </svg>
                                    </div>
                                </a>
                            </div>

                            <!-- telemetry / location field -->
                            <div v-if="chatItem.lxmf_message.fields?.telemetry?.location" class="pb-1 mt-1">
                                <button
                                    type="button"
                                    class="flex items-center gap-2 border border-gray-200/60 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                                    :class="
                                        chatItem.is_outbound
                                            ? 'bg-white/20 text-white border-white/20 hover:bg-white/30'
                                            : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300'
                                    "
                                    @click="viewLocationOnMap(chatItem.lxmf_message.fields.telemetry.location)"
                                >
                                    <MaterialDesignIcon icon-name="map-marker" class="size-5" />
                                    <div class="text-left">
                                        <div class="font-bold text-xs uppercase tracking-wider opacity-80">
                                            Location
                                        </div>
                                        <div class="text-[10px] font-mono opacity-70">
                                            {{ chatItem.lxmf_message.fields.telemetry.location.latitude.toFixed(6) }},
                                            {{ chatItem.lxmf_message.fields.telemetry.location.longitude.toFixed(6) }}
                                        </div>
                                    </div>
                                </button>
                            </div>
                        </div>

                        <!-- actions -->
                        <div
                            v-if="chatItem.is_actions_expanded"
                            class="border-t px-4 py-2.5"
                            :class="
                                chatItem.is_outbound
                                    ? 'border-white/20 bg-white/10'
                                    : 'border-gray-200/60 dark:border-zinc-800/60 bg-gray-50/50 dark:bg-zinc-900/50'
                            "
                        >
                            <!-- delete message -->
                            <button
                                type="button"
                                class="inline-flex items-center gap-x-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-red-600 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500"
                                @click.stop="deleteChatItem(chatItem)"
                            >
                                Delete
                            </button>
                        </div>
                    </div>

                    <!-- message state -->
                    <div
                        v-if="chatItem.is_outbound"
                        class="flex text-right mt-1.5 px-1"
                        :class="[
                            ['cancelled', 'failed'].includes(chatItem.lxmf_message.state)
                                ? 'text-red-500 dark:text-red-400'
                                : 'text-gray-400 dark:text-zinc-500',
                        ]"
                    >
                        <div class="flex ml-auto items-center space-x-1.5 text-xs">
                            <!-- state label -->
                            <div class="my-auto">
                                <span
                                    class="space-x-1 cursor-pointer hover:underline"
                                    @click="toggleSentMessageInfo(chatItem.lxmf_message.hash)"
                                >
                                    <span>{{ chatItem.lxmf_message.state }}</span>
                                    <span
                                        v-if="
                                            chatItem.lxmf_message.state === 'outbound' &&
                                            chatItem.lxmf_message.delivery_attempts >= 1
                                        "
                                        >(attempt {{ chatItem.lxmf_message.delivery_attempts + 1 }})</span
                                    >
                                    <span
                                        v-if="
                                            chatItem.lxmf_message.state === 'sent' &&
                                            chatItem.lxmf_message.method === 'opportunistic' &&
                                            chatItem.lxmf_message.delivery_attempts >= 1
                                        "
                                        >(attempt {{ chatItem.lxmf_message.delivery_attempts }})</span
                                    >
                                    <span
                                        v-if="
                                            chatItem.lxmf_message.state === 'sent' &&
                                            chatItem.lxmf_message.method === 'propagated'
                                        "
                                        >to propagation node</span
                                    >
                                    <span v-if="chatItem.lxmf_message.state === 'sending'"
                                        >{{ chatItem.lxmf_message.progress.toFixed(0) }}%</span
                                    >
                                </span>
                                <a
                                    v-if="
                                        chatItem.lxmf_message.state === 'outbound' ||
                                        chatItem.lxmf_message.state === 'sending' ||
                                        chatItem.lxmf_message.state === 'sent'
                                    "
                                    class="ml-1 cursor-pointer underline text-blue-500"
                                    @click="cancelSendingMessage(chatItem)"
                                    >cancel?</a
                                >
                                <a
                                    v-if="chatItem.lxmf_message.state === 'failed'"
                                    class="ml-1 cursor-pointer underline text-blue-500"
                                    @click="retrySendingMessage(chatItem)"
                                    >retry?</a
                                >
                            </div>

                            <!-- delivered icon -->
                            <div v-if="chatItem.lxmf_message.state === 'delivered'" class="my-auto">
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    viewBox="0 0 24 24"
                                    fill="currentColor"
                                    class="w-5 h-5"
                                >
                                    <path
                                        fill-rule="evenodd"
                                        d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Zm13.36-1.814a.75.75 0 1 0-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 0 0-1.06 1.06l2.25 2.25a.75.75 0 0 0 1.14-.094l3.75-5.25Z"
                                        clip-rule="evenodd"
                                    />
                                </svg>
                            </div>

                            <!-- cancelled icon -->
                            <div v-else-if="chatItem.lxmf_message.state === 'cancelled'" class="my-auto">
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    viewBox="0 0 24 24"
                                    fill="currentColor"
                                    class="size-5"
                                >
                                    <path
                                        fill-rule="evenodd"
                                        d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25Zm-1.72 6.97a.75.75 0 1 0-1.06 1.06L10.94 12l-1.72 1.72a.75.75 0 1 0 1.06 1.06L12 13.06l1.72 1.72a.75.75 0 1 0 1.06-1.06L13.06 12l1.72-1.72a.75.75 0 1 0-1.06-1.06L12 10.94l-1.72-1.72Z"
                                        clip-rule="evenodd"
                                    />
                                </svg>
                            </div>

                            <!-- failed icon -->
                            <div v-else-if="chatItem.lxmf_message.state === 'failed'" class="my-auto">
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    viewBox="0 0 24 24"
                                    fill="currentColor"
                                    class="w-5 h-5"
                                >
                                    <path
                                        fill-rule="evenodd"
                                        d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12ZM12 8.25a.75.75 0 0 1 .75.75v3.75a.75.75 0 0 1-1.5 0V9a.75.75 0 0 1 .75-.75Zm0 8.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"
                                        clip-rule="evenodd"
                                    />
                                </svg>
                            </div>

                            <!-- fallback icon -->
                            <div v-else class="my-auto">
                                <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke-width="1.5"
                                    stroke="currentColor"
                                    class="w-5 h-5"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                                    />
                                </svg>
                            </div>
                        </div>
                    </div>

                    <!-- inbound message info -->
                    <div
                        v-if="!chatItem.is_outbound"
                        class="text-xs text-gray-400 dark:text-zinc-500 mt-1.5 px-1 flex flex-col"
                    >
                        <!-- received timestamp -->
                        <span
                            class="cursor-pointer hover:underline"
                            @click="toggleReceivedMessageInfo(chatItem.lxmf_message.hash)"
                            >{{ formatTimeAgo(chatItem.lxmf_message.created_at) }}</span
                        >
                    </div>

                    <!-- expanded message details -->
                    <div
                        v-if="expandedMessageInfo === chatItem.lxmf_message.hash"
                        class="mt-2 px-1 text-xs text-gray-500 dark:text-zinc-400 space-y-0.5"
                    >
                        <div
                            v-for="(line, index) in getMessageInfoLines(chatItem.lxmf_message, chatItem.is_outbound)"
                            :key="index"
                        >
                            {{ line }}
                        </div>
                    </div>
                </div>

                <!-- load previous -->
                <button
                    v-show="!isLoadingPrevious && hasMorePrevious"
                    id="load-previous"
                    type="button"
                    class="flex items-center gap-2 mx-auto mt-4 bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 px-4 py-2 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-full shadow-sm text-sm font-medium text-gray-700 dark:text-zinc-300 transition-colors"
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
        </div>

        <!-- send message -->
        <div
            class="w-full border-t border-gray-200/60 dark:border-zinc-800/60 bg-white/80 dark:bg-zinc-900/50 backdrop-blur-sm px-3 sm:px-4 py-2.5"
        >
            <div class="w-full">
                <!-- blocked user notification -->
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
                        class="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                        />
                    </svg>
                    <span class="text-sm text-yellow-800 dark:text-yellow-200"
                        >You have blocked this user. They cannot send you messages or establish links.</span
                    >
                </div>

                <!-- message composer -->
                <div>
                    <div class="space-y-2">
                        <!-- image attachment -->
                        <div v-if="newMessageImage" class="attachment-card">
                            <div class="attachment-card__preview" @click.stop="openImage(newMessageImageUrl)">
                                <img
                                    v-if="newMessageImageUrl"
                                    :src="newMessageImageUrl"
                                    class="w-full h-full object-cover rounded-lg"
                                />
                            </div>
                            <div class="attachment-card__body">
                                <div class="attachment-card__title">Image Attachment</div>
                                <div class="attachment-card__meta">{{ formatBytes(newMessageImage.size) }}</div>
                            </div>
                            <button type="button" class="attachment-card__remove" @click.stop="removeImageAttachment">
                                <MaterialDesignIcon icon-name="close" class="w-4 h-4" />
                            </button>
                        </div>

                        <!-- audio attachment -->
                        <div v-if="newMessageAudio" class="attachment-card">
                            <div class="attachment-card__body w-full">
                                <div class="attachment-card__title">Voice Note</div>
                                <div class="attachment-card__meta">
                                    {{ formatBytes(newMessageAudio.audio_blob.size) }}
                                </div>
                                <audio
                                    controls
                                    class="w-full mt-2 rounded-lg shadow-sm audio-controls-dark"
                                    style="height: 54px"
                                >
                                    <source :src="newMessageAudio.audio_preview_url" type="audio/wav" />
                                </audio>
                            </div>
                            <button type="button" class="attachment-card__remove" @click="removeAudioAttachment">
                                <MaterialDesignIcon icon-name="delete" class="w-4 h-4" />
                            </button>
                        </div>

                        <!-- file attachments -->
                        <div v-if="newMessageFiles.length > 0" class="flex flex-wrap gap-2">
                            <div v-for="file in newMessageFiles" :key="file.name + file.size" class="attachment-chip">
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

                    <!-- text input -->
                    <textarea
                        id="message-input"
                        ref="message-input"
                        v-model="newMessageText"
                        :readonly="isSendingMessage"
                        class="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 block w-full px-3 sm:px-4 py-2 resize-none shadow-sm transition-all placeholder:text-gray-400 dark:placeholder:text-zinc-500"
                        rows="2"
                        :placeholder="$t('messages.send_placeholder')"
                        @keydown.enter.exact.prevent="onEnterPressed"
                        @keydown.enter.shift.exact.prevent="onShiftEnterPressed"
                    ></textarea>

                    <!-- action button -->
                    <div class="flex flex-wrap gap-2 items-center mt-2">
                        <button type="button" class="attachment-action-button" @click="addFilesToMessage">
                            <MaterialDesignIcon icon-name="paperclip-plus" class="w-4 h-4" />
                            <span>{{ $t("messages.add_files") }}</span>
                        </button>
                        <AddImageButton @add-image="onImageSelected" />
                        <AddAudioButton
                            :is-recording-audio-attachment="isRecordingAudioAttachment"
                            @start-recording="startRecordingAudioAttachment($event)"
                            @stop-recording="stopRecordingAudioAttachment"
                        >
                            <span>{{ $t("messages.recording", { duration: audioAttachmentRecordingDuration }) }}</span>
                        </AddAudioButton>
                        <button
                            type="button"
                            class="attachment-action-button"
                            :title="$t('messages.share_location')"
                            @click="shareLocation"
                        >
                            <MaterialDesignIcon icon-name="map-marker" class="w-4 h-4" />
                            <span>{{ $t("messages.location") }}</span>
                        </button>
                        <button
                            type="button"
                            class="attachment-action-button"
                            :title="$t('messages.request_location')"
                            @click="requestLocation"
                        >
                            <MaterialDesignIcon icon-name="crosshairs-question" class="w-4 h-4" />
                            <span>{{ $t("messages.request") }}</span>
                        </button>
                        <div class="ml-auto my-auto">
                            <SendMessageButton
                                :is-sending-message="isSendingMessage"
                                :can-send-message="canSendMessage"
                                :delivery-method="newMessageDeliveryMethod"
                                @send="sendMessage"
                                @delivery-method-changed="newMessageDeliveryMethod = $event"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- hidden file input for selecting files -->
        <input ref="file-input" type="file" multiple style="display: none" @change="onFileInputChange" />
    </div>

    <!-- no peer selected -->
    <div v-else class="flex flex-col h-full items-center justify-center">
        <div class="w-full max-w-md px-4">
            <div class="mb-6 text-center">
                <div
                    class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/30 dark:to-blue-800/30 flex items-center justify-center"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke-width="1.5"
                        stroke="currentColor"
                        class="w-8 h-8 text-blue-600 dark:text-blue-400"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155"
                        />
                    </svg>
                </div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-zinc-100 mb-1">
                    {{ $t("messages.no_active_chat") }}
                </h3>
                <p class="text-sm text-gray-500 dark:text-zinc-400">
                    {{ $t("messages.select_peer_or_enter_address") }}
                </p>
            </div>

            <!-- compose message input -->
            <div class="w-full">
                <input
                    id="compose-input"
                    ref="compose-input"
                    v-model="composeAddress"
                    :readonly="isSendingMessage"
                    type="text"
                    class="w-full bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 px-4 py-2.5 shadow-sm transition-all placeholder:text-gray-400 dark:placeholder:text-zinc-500"
                    placeholder="Enter LXMF address..."
                    @keydown.enter.exact.prevent="onComposeEnterPressed"
                />
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
            class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 dark:bg-black/90 backdrop-blur-sm p-4"
            @click="closeImageModal"
        >
            <div class="relative max-w-7xl max-h-full" @click.stop>
                <button
                    type="button"
                    class="absolute -top-12 right-0 inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/10 dark:bg-zinc-900/10 hover:bg-white/20 dark:hover:bg-zinc-900/20 text-white transition-colors"
                    @click="closeImageModal"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                        <path
                            d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
                        />
                    </svg>
                </button>
                <img :src="imageModalUrl" class="max-w-full max-h-[90vh] rounded-xl shadow-2xl" alt="Image preview" />
            </div>
        </div>
    </Transition>
</template>

<script>
import Utils from "../../js/Utils";
import DialogUtils from "../../js/DialogUtils";
import MicrophoneRecorder from "../../js/MicrophoneRecorder";
import NotificationUtils from "../../js/NotificationUtils";
import WebSocketConnection from "../../js/WebSocketConnection";
import AddAudioButton from "./AddAudioButton.vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);
import SendMessageButton from "./SendMessageButton.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ConversationDropDownMenu from "./ConversationDropDownMenu.vue";
import AddImageButton from "./AddImageButton.vue";
import IconButton from "../IconButton.vue";
import GlobalEmitter from "../../js/GlobalEmitter";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "ConversationViewer",
    components: {
        IconButton,
        AddImageButton,
        ConversationDropDownMenu,
        MaterialDesignIcon,
        SendMessageButton,
        AddAudioButton,
    },
    props: {
        myLxmfAddressHash: {
            type: String,
            required: true,
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
    emits: ["close", "reload-conversations", "update:selectedPeer"],
    data() {
        return {
            selectedPeerPath: null,
            selectedPeerLxmfStampInfo: null,
            selectedPeerSignalMetrics: null,

            lxmfMessagesRequestSequence: 0,
            chatItems: [],

            isLoadingPrevious: false,
            hasMorePrevious: true,

            newMessageDeliveryMethod: null,
            newMessageText: "",
            newMessageImage: null,
            newMessageImageUrl: null,
            newMessageAudio: null,
            newMessageTelemetry: null,
            newMessageFiles: [],
            isSendingMessage: false,
            autoScrollOnNewMessage: true,
            composeAddress: "",

            isShareContactModalOpen: false,
            contacts: [],
            contactsSearch: "",

            isRecordingAudioAttachment: false,
            audioAttachmentMicrophoneRecorder: null,
            audioAttachmentMicrophoneRecorderCodec: null,
            audioAttachmentRecordingStartedAt: null,
            audioAttachmentRecordingDuration: null,
            audioAttachmentRecordingTimer: null,
            lxmfMessageAudioAttachmentCache: {},
            isDownloadingAudio: {},
            expandedMessageInfo: null,
            imageModalUrl: null,
            isSelectedPeerBlocked: false,
            blockedDestinations: [],
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
        };
    },
    computed: {
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
        canSendMessage() {
            // can't send if empty message
            const messageText = this.newMessageText.trim();
            if (messageText == null || messageText === "") {
                return false;
            }

            // can't send if already sending
            if (this.isSendingMessage) {
                return false;
            }

            return true;
        },
        selectedPeerChatItems() {
            // get all chat items related to the selected peer
            if (this.selectedPeer) {
                return this.chatItems.filter((chatItem) => {
                    if (chatItem.type === "lxmf_message") {
                        const isFromSelectedPeer =
                            chatItem.lxmf_message.source_hash === this.selectedPeer.destination_hash;
                        const isToSelectedPeer =
                            chatItem.lxmf_message.destination_hash === this.selectedPeer.destination_hash;
                        return isFromSelectedPeer || isToSelectedPeer;
                    }

                    return false;
                });
            }

            // no peer, so no chat items!
            return [];
        },
        selectedPeerChatItemsReversed() {
            // ensure a copy of the array is returned in reverse order
            return this.selectedPeerChatItems.map((message) => message).reverse();
        },
        oldestMessageId() {
            if (this.selectedPeerChatItems.length > 0) {
                return this.selectedPeerChatItems[0].lxmf_message.id;
            }

            return null;
        },
    },
    watch: {
        selectedPeer: {
            handler() {
                this.checkIfSelectedPeerBlocked();
                this.initialLoad();
            },
            immediate: true,
        },
        async selectedPeerChatItems() {
            // chat items for selected peer changed, so lets process any available audio
            await this.processAudioForSelectedPeerChatItems();
        },
    },
    beforeUnmount() {
        // stop listening for websocket messages
        WebSocketConnection.off("message", this.onWebsocketMessage);
        GlobalEmitter.off("compose-new-message", this.onComposeNewMessageEvent);
    },
    mounted() {
        // listen for websocket messages
        WebSocketConnection.on("message", this.onWebsocketMessage);

        // listen for compose new message event
        GlobalEmitter.on("compose-new-message", this.onComposeNewMessageEvent);

        // load blocked destinations
        this.loadBlockedDestinations();
    },
    methods: {
        async loadBlockedDestinations() {
            try {
                const response = await window.axios.get("/api/v1/blocked-destinations");
                this.blockedDestinations = response.data.blocked_destinations || [];
                this.checkIfSelectedPeerBlocked();
            } catch (e) {
                console.log(e);
            }
        },
        checkIfSelectedPeerBlocked() {
            if (!this.selectedPeer) {
                this.isSelectedPeerBlocked = false;
                return;
            }
            this.isSelectedPeerBlocked = this.blockedDestinations.some(
                (b) => b.destination_hash === this.selectedPeer.destination_hash
            );
        },
        close() {
            this.$emit("close");
        },
        onMessagesScroll(event) {
            // check if messages is scrolled to bottom
            const element = event.target;
            const isAtBottom = element.scrollTop === element.scrollHeight - element.offsetHeight;

            // we want to auto scroll if user is at bottom of messages list
            this.autoScrollOnNewMessage = isAtBottom;

            // load previous when scrolling near top of page
            if (element.scrollTop <= 500) {
                this.loadPrevious();
            }
        },
        async initialLoad() {
            // reset
            this.chatItems = [];
            this.hasMorePrevious = true;
            this.selectedPeerPath = null;
            this.selectedPeerLxmfStampInfo = null;
            this.selectedPeerSignalMetrics = null;
            if (!this.selectedPeer) {
                return;
            }

            this.getPeerPath();
            this.getPeerLxmfStampInfo();
            this.getPeerSignalMetrics();

            // load 1 page of previous messages
            await this.loadPrevious();

            // scroll to bottom
            this.scrollMessagesToBottom();
        },
        async loadPrevious() {
            // do nothing if already loading
            if (this.isLoadingPrevious) {
                return;
            }

            this.isLoadingPrevious = true;

            try {
                const seq = ++this.lxmfMessagesRequestSequence;

                // fetch lxmf messages from "us to destination" and from "destination to us"
                const pageSize = 30;
                const response = await window.axios.get(
                    `/api/v1/lxmf-messages/conversation/${this.selectedPeer.destination_hash}`,
                    {
                        params: {
                            count: pageSize,
                            order: "desc",
                            after_id: this.oldestMessageId,
                        },
                    }
                );

                // do nothing if response is for a previous request
                if (seq !== this.lxmfMessagesRequestSequence) {
                    console.log("ignoring response for previous lxmf messages request");
                    return;
                }

                // convert lxmf messages to chat items
                const chatItems = [];
                const lxmfMessages = response.data.lxmf_messages;
                for (const lxmfMessage of lxmfMessages) {
                    chatItems.push({
                        type: "lxmf_message",
                        is_outbound: this.myLxmfAddressHash === lxmfMessage.source_hash,
                        lxmf_message: lxmfMessage,
                    });
                }

                // add messages to start of existing messages
                for (const chatItem of chatItems) {
                    this.chatItems.unshift(chatItem);
                }

                // no more previous to load if received items is less than expected page size
                if (chatItems.length < pageSize) {
                    this.hasMorePrevious = false;
                }
            } catch {
                // do nothing
            } finally {
                this.isLoadingPrevious = false;
            }
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
            this.onComposeSubmit();
        },
        async handleComposeAddress(destinationHash) {
            if (destinationHash.startsWith("lxmf@")) {
                destinationHash = destinationHash.replace("lxmf@", "");
            }
            if (destinationHash.length !== 32) {
                DialogUtils.alert("Invalid Address");
                return;
            }
            GlobalEmitter.emit("compose-new-message", destinationHash);
        },
        onLxmfMessageReceived(lxmfMessage) {
            // only add if it's for the current conversation
            if (lxmfMessage.source_hash !== this.selectedPeer?.destination_hash) {
                return;
            }

            // add inbound message to ui
            this.chatItems.push({
                type: "lxmf_message",
                lxmf_message: lxmfMessage,
            });

            // mark conversation as read
            const conversation = this.findConversation(this.selectedPeer.destination_hash);
            if (conversation) {
                this.markConversationAsRead(conversation);
            }

            // show notification for new messages if window is not focussed
            if (!document.hasFocus()) {
                NotificationUtils.showNewMessageNotification();
            }

            // auto scroll to bottom if we want to
            if (this.autoScrollOnNewMessage) {
                this.scrollMessagesToBottom();
            }
        },
        onLxmfMessageCreated(lxmfMessage) {
            // only add if it's for the current conversation
            if (lxmfMessage.destination_hash !== this.selectedPeer?.destination_hash) {
                return;
            }

            // add new outbound lxmf message from server
            if (!this.isLxmfMessageInUi(lxmfMessage.hash)) {
                this.chatItems.push({
                    type: "lxmf_message",
                    lxmf_message: lxmfMessage,
                    is_outbound: true,
                });
            }
        },
        onLxmfMessageUpdated(lxmfMessage) {
            // find existing chat item by lxmf message hash
            const lxmfMessageHash = lxmfMessage.hash;
            const chatItemIndex = this.chatItems.findIndex(
                (chatItem) => chatItem.lxmf_message?.hash === lxmfMessageHash
            );
            if (chatItemIndex === -1) {
                return;
            }

            // update lxmf message from server, while ensuring ui updates from nested object change
            this.chatItems[chatItemIndex].lxmf_message = lxmfMessage;
        },
        onLxmfMessageDeleted(hash) {
            if (hash) {
                // remove existing chat item by lxmf message hash
                this.chatItems = this.chatItems.filter((item) => {
                    return item.lxmf_message?.hash !== hash;
                });
            }
        },
        async getPeerPath() {
            if (this.selectedPeer) {
                try {
                    // get path to destination
                    const response = await window.axios.get(
                        `/api/v1/destination/${this.selectedPeer.destination_hash}/path`
                    );

                    // update ui
                    this.selectedPeerPath = response.data.path;
                } catch (e) {
                    console.log(e);

                    // clear previous known path
                    this.selectedPeerPath = null;
                }
            }
        },
        async getPeerLxmfStampInfo() {
            if (this.selectedPeer) {
                try {
                    // get lxmf stamp info
                    const response = await window.axios.get(
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
                    const response = await window.axios.get(
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
        scrollMessagesToBottom: function () {
            // next tick waits for the ui to have the new elements added
            this.$nextTick(() => {
                // set timeout with zero millis seems to fix issue where it doesn't scroll all the way to the bottom...
                setTimeout(() => {
                    const container = document.getElementById("messages");
                    if (container) {
                        container.scrollTop = container.scrollHeight;
                    }
                }, 0);
            });
        },
        isLxmfMessageInUi: function (hash) {
            return this.chatItems.findIndex((chatItem) => chatItem.lxmf_message?.hash === hash) !== -1;
        },
        async getCustomDisplayName() {
            if (this.selectedPeer) {
                try {
                    // get custom display name
                    const response = await window.axios.get(
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
            // do nothing if no peer selected
            if (!this.selectedPeer) {
                return;
            }

            // ask user for new display name
            const displayName = await DialogUtils.prompt("Enter a custom display name");
            if (displayName == null) {
                return;
            }

            try {
                // update display name on server
                await axios.post(
                    `/api/v1/destination/${this.selectedPeer.destination_hash}/custom-display-name/update`,
                    {
                        display_name: displayName,
                    }
                );

                // update display name in ui
                await this.getCustomDisplayName();

                // reload conversations (so conversations list updates name)
                this.$emit("reload-conversations");
            } catch (error) {
                console.log(error);
                DialogUtils.alert("Failed to update display name");
            }
        },
        async onConversationDeleted() {
            // reload conversation
            await this.initialLoad();

            // reload conversations
            this.$emit("reload-conversations");
        },
        onChatItemClick: function (chatItem) {
            if (!chatItem.is_actions_expanded) {
                chatItem.is_actions_expanded = true;
            } else {
                chatItem.is_actions_expanded = false;
            }
        },
        async downloadAndDecodeAudio(chatItem) {
            if (this.isDownloadingAudio[chatItem.lxmf_message.hash]) return;

            this.isDownloadingAudio[chatItem.lxmf_message.hash] = true;
            try {
                // fetch audio bytes from api
                const response = await window.axios.get(
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
                DialogUtils.alert("Failed to load audio attachment.");
            } finally {
                this.isDownloadingAudio[chatItem.lxmf_message.hash] = false;
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
        openImage: async function (url) {
            this.imageModalUrl = url;
        },
        closeImageModal() {
            this.imageModalUrl = null;
        },
        downloadFileFromBase64: async function (fileName, fileBytesBase64) {
            // create blob from base64 encoded file bytes
            const byteCharacters = atob(fileBytesBase64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray]);

            // create object url for blob
            const objectUrl = URL.createObjectURL(blob);

            // create link element to download blob
            const link = document.createElement("a");
            link.href = objectUrl;
            link.download = fileName;
            link.style.display = "none";
            document.body.append(link);

            // click link to download file in browser
            link.click();

            // link element is no longer needed
            link.remove();

            // revoke object url to clear memory
            setTimeout(() => URL.revokeObjectURL(objectUrl), 10000);
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
                await window.axios.delete(`/api/v1/lxmf-messages/${chatItem.lxmf_message.hash}`);

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
                const response = await window.axios.get("/api/v1/telephone/contacts");
                this.contacts = response.data;

                if (this.contacts.length === 0) {
                    ToastUtils.info("No contacts found in telephone");
                    return;
                }

                this.isShareContactModalOpen = true;
            } catch (e) {
                console.error(e);
                ToastUtils.error("Failed to load contacts");
            }
        },
        async shareContact(contact) {
            this.newMessageText = `Contact: ${contact.name} <${contact.remote_identity_hash}>`;
            this.isShareContactModalOpen = false;
            await this.sendMessage();
        },
        async sendMessage() {
            // do nothing if can't send message
            if (!this.canSendMessage) {
                return;
            }

            // do nothing if no peer selected
            if (!this.selectedPeer) {
                return;
            }

            this.isSendingMessage = true;

            try {
                // build fields
                const fields = {};

                // add telemetry if present
                if (this.newMessageTelemetry) {
                    fields["telemetry"] = this.newMessageTelemetry;
                }

                // add file attachments
                var fileAttachmentsTotalSize = 0;
                if (this.newMessageFiles.length > 0) {
                    const fileAttachments = [];
                    for (const file of this.newMessageFiles) {
                        fileAttachmentsTotalSize += file.size;
                        fileAttachments.push({
                            file_name: file.name,
                            file_bytes: Utils.arrayBufferToBase64(await file.arrayBuffer()),
                        });
                    }
                    fields["file_attachments"] = fileAttachments;
                }

                // add image attachment
                var imageTotalSize = 0;
                if (this.newMessageImage) {
                    imageTotalSize = this.newMessageImage.size;
                    fields["image"] = {
                        // Reticulum sends image type as "jpg", "png", "webp" etc and not "image/jpg" or "image/png"
                        // From memory, Sideband would not display images if the image type has the "image/" prefix
                        // https://github.com/markqvist/Sideband/blob/354fb08297835eab04ac69d15081a18baf0583ac/docs/example_plugins/view.py#L78
                        // https://github.com/markqvist/Sideband/blob/354fb08297835eab04ac69d15081a18baf0583ac/sbapp/main.py#L1900
                        // https://github.com/markqvist/Sideband/blob/354fb08297835eab04ac69d15081a18baf0583ac/sbapp/ui/messages.py#L783
                        image_type: this.newMessageImage.type.replace("image/", ""),
                        image_bytes: Utils.arrayBufferToBase64(await this.newMessageImage.arrayBuffer()),
                    };
                }

                // add audio attachment
                var audioTotalSize = 0;
                if (this.newMessageAudio) {
                    audioTotalSize = this.newMessageAudio.size;
                    fields["audio"] = {
                        audio_mode: this.newMessageAudio.audio_mode,
                        audio_bytes: Utils.arrayBufferToBase64(await this.newMessageAudio.audio_blob.arrayBuffer()),
                    };
                }

                // calculate estimated message size in bytes
                const contentSize = this.newMessageText.length;
                const totalMessageSize = contentSize + fileAttachmentsTotalSize + imageTotalSize + audioTotalSize;

                // ask user if they still want to send message if it may be rejected by sender
                if (totalMessageSize > 1000 * 900) {
                    // actual limit in LXMF Router is 1mb
                    if (
                        !(await DialogUtils.confirm(
                            `Your message exceeds 900KB (It's ${this.formatBytes(totalMessageSize)}). It may be rejected by the recipient unless they have increased their delivery limit. Do you want to try sending anyway?`
                        ))
                    ) {
                        return;
                    }
                }

                // send message to reticulum
                const response = await window.axios.post(`/api/v1/lxmf-messages/send`, {
                    delivery_method: this.newMessageDeliveryMethod,
                    lxmf_message: {
                        destination_hash: this.selectedPeer.destination_hash,
                        content: this.newMessageText,
                        fields: fields,
                    },
                });

                // add outbound message to ui
                if (!this.isLxmfMessageInUi(response.data.lxmf_message.hash)) {
                    this.chatItems.push({
                        type: "lxmf_message",
                        lxmf_message: response.data.lxmf_message,
                        is_outbound: true,
                    });
                }

                // always scroll to bottom since we just sent a message
                this.scrollMessagesToBottom();

                // clear message inputs
                this.newMessageText = "";
                this.newMessageImage = null;
                this.newMessageImageUrl = null;
                this.newMessageAudio = null;
                this.newMessageTelemetry = null;
                this.newMessageFiles = [];
                this.clearFileInput();
            } catch (e) {
                // show error
                const message = e.response?.data?.message ?? "failed to send message";
                DialogUtils.alert(message);
                console.log(e);
            } finally {
                this.isSendingMessage = false;
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
                const response = await window.axios.post(`/api/v1/lxmf-messages/${lxmfMessageHash}/cancel`);

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
            // force delete existing message
            await this.deleteChatItem(chatItem, false);

            try {
                // send message to reticulum
                const response = await window.axios.post(`/api/v1/lxmf-messages/send`, {
                    lxmf_message: {
                        destination_hash: chatItem.lxmf_message.destination_hash,
                        content: chatItem.lxmf_message.content,
                        fields: chatItem.lxmf_message.fields,
                    },
                });

                // add outbound message to ui
                if (!this.isLxmfMessageInUi(response.data.lxmf_message.hash)) {
                    this.chatItems.push({
                        type: "lxmf_message",
                        lxmf_message: response.data.lxmf_message,
                        is_outbound: true,
                    });
                }

                // always scroll to bottom since we just sent a message
                this.scrollMessagesToBottom();
            } catch (e) {
                // show error
                const message = e.response?.data?.message ?? "failed to send message";
                DialogUtils.alert(message);
                console.log(e);
            }
        },
        async shareLocation() {
            try {
                if (!navigator.geolocation) {
                    DialogUtils.alert("Geolocation is not supported by your browser");
                    return;
                }

                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        this.newMessageTelemetry = {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            altitude: position.coords.altitude || 0,
                            speed: (position.coords.speed || 0) * 3.6, // m/s to km/h to match Sideband
                            bearing: position.coords.heading || 0,
                            accuracy: position.coords.accuracy || 0,
                            last_update: Math.floor(Date.now() / 1000),
                        };
                        this.sendMessage();
                    },
                    (error) => {
                        DialogUtils.alert(`Failed to get location: ${error.message}`);
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 30000,
                        maximumAge: 0,
                    }
                );
            } catch (e) {
                console.log(e);
            }
        },
        async requestLocation() {
            try {
                if (!this.selectedPeer) return;

                // Send a telemetry request command
                await window.axios.post(`/api/v1/lxmf-messages/send`, {
                    lxmf_message: {
                        destination_hash: this.selectedPeer.destination_hash,
                        content: "",
                        fields: {
                            commands: [
                                { "0x01": Math.floor(Date.now() / 1000) }, // Sideband TELEMETRY_REQUEST
                            ],
                        },
                    },
                });

                ToastUtils.success("Location request sent");
            } catch (e) {
                console.log(e);
                ToastUtils.error("Failed to send location request");
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
        formatTimeAgo: function (datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
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
        onFileInputChange: function (event) {
            for (const file of event.target.files) {
                this.newMessageFiles.push(file);
            }
        },
        clearFileInput: function () {
            this.$refs["file-input"].value = null;
        },
        async removeImageAttachment() {
            // ask user to confirm removing image attachment
            if (!(await DialogUtils.confirm("Are you sure you want to remove this image attachment?"))) {
                return;
            }

            // remove image
            this.newMessageImage = null;
            this.newMessageImageUrl = null;
        },
        onImageSelected: function (imageBlob) {
            // update selected file
            this.newMessageImage = imageBlob;

            // update image url when file is read
            const fileReader = new FileReader();
            fileReader.onload = (event) => {
                this.newMessageImageUrl = event.target.result;
            };

            // convert image to data url
            fileReader.readAsDataURL(this.newMessageImage);
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
                        DialogUtils.alert("failed to start recording");
                    }

                    break;
                }
                case "opus": {
                    // start recording microphone
                    this.audioAttachmentMicrophoneRecorderCodec = "opus";
                    this.audioAttachmentMicrophoneRecorder = new MicrophoneRecorder();
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
                        DialogUtils.alert("failed to start recording");
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

            // do nothing if not recording
            if (!this.isRecordingAudioAttachment) {
                return;
            }

            // stop recording microphone and get audio
            this.isRecordingAudioAttachment = false;
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
            // ask user to confirm removing audio attachment
            if (!(await DialogUtils.confirm("Are you sure you want to remove this audio attachment?"))) {
                return;
            }

            // remove audio
            this.newMessageAudio = null;
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
                await window.axios.get(`/api/v1/lxmf/conversations/${conversation.destination_hash}/mark-as-read`);
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
    @apply inline-flex items-center gap-1 rounded-full border border-gray-200 dark:border-zinc-700 bg-white/90 dark:bg-zinc-900/80 px-3 py-1.5 text-xs font-semibold text-gray-800 dark:text-gray-100 shadow-sm hover:border-blue-400 dark:hover:border-blue-500 transition;
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
</style>
