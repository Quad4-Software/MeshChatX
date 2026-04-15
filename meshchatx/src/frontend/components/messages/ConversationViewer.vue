<template>
    <!-- peer selected -->
    <div
        v-if="selectedPeer"
        class="flex flex-col h-full bg-white dark:bg-zinc-950 overflow-hidden transition-all relative"
    >
        <!-- banished overlay -->
        <div
            v-if="GlobalState?.config?.banished_effect_enabled && isSelectedPeerBlocked"
            class="banished-overlay"
            :style="{ background: (GlobalState?.config?.banished_color || '#dc2626') + '33' }"
        >
            <span
                class="banished-text !opacity-100 !text-white !shadow-lg !bg-red-600 !px-4 !py-2 !rounded-xl !border-2 !tracking-widest"
                :style="{
                    'background-color': GlobalState?.config?.banished_color || '#dc2626',
                    'border-color': GlobalState?.config?.banished_color || '#dc2626',
                }"
                >{{ GlobalState?.config?.banished_text || "BANISHED" }}</span
            >
        </div>

        <!-- header -->
        <div
            ref="conversationPeerHeader"
            class="relative z-20 flex flex-wrap items-center gap-y-2 px-3 sm:px-4 py-3 border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950"
        >
            <!-- peer icon -->
            <div class="flex-shrink-0 mr-3">
                <LxmfUserIcon
                    :custom-image="selectedPeer.contact_image"
                    :icon-name="selectedPeer.lxmf_user_icon ? selectedPeer.lxmf_user_icon.icon_name : ''"
                    :icon-foreground-colour="
                        selectedPeer.lxmf_user_icon ? selectedPeer.lxmf_user_icon.foreground_colour : ''
                    "
                    :icon-background-colour="
                        selectedPeer.lxmf_user_icon ? selectedPeer.lxmf_user_icon.background_colour : ''
                    "
                    icon-class="shrink-0"
                    :icon-style="messageIconStyle"
                />
            </div>

            <!-- peer info -->
            <div class="min-w-0 flex-1">
                <div class="flex items-center cursor-pointer min-w-0 group" @click="updateCustomDisplayName">
                    <div
                        v-if="selectedPeer.custom_display_name != null"
                        class="mr-1.5 text-gray-500 dark:text-zinc-400 group-hover:text-gray-700 dark:group-hover:text-zinc-200 transition-colors"
                        :title="$t('messages.custom_display_name')"
                    >
                        <MaterialDesignIcon icon-name="tag-outline" class="size-4" />
                    </div>
                    <div
                        class="font-semibold text-gray-900 dark:text-zinc-100 truncate max-w-[120px] sm:max-w-sm text-base"
                        :title="selectedPeer.custom_display_name ?? selectedPeer.display_name"
                    >
                        {{ selectedPeer.custom_display_name ?? selectedPeer.display_name }}
                    </div>
                </div>
                <div class="text-xs text-gray-500 dark:text-zinc-400 mt-0.5 flex items-center gap-2 min-w-0">
                    <!-- destination hash -->
                    <div
                        class="cursor-pointer hover:text-blue-500 transition-colors truncate max-w-[120px] sm:max-w-none shrink-0"
                        :title="selectedPeer.destination_hash"
                        @click="copyHash(selectedPeer.destination_hash)"
                    >
                        {{ formatDestinationHash(selectedPeer.destination_hash) }}
                    </div>

                    <div
                        v-if="
                            selectedPeerPath ||
                            selectedPeerSignalMetrics?.snr != null ||
                            selectedPeerLxmfStampInfo?.stamp_cost
                        "
                        class="flex items-center gap-2 min-w-0"
                    >
                        <span class="text-gray-300 dark:text-zinc-700 shrink-0">•</span>

                        <div class="flex items-center gap-2 truncate">
                            <!-- hops away -->
                            <span
                                v-if="selectedPeerPath"
                                class="flex items-center cursor-pointer hover:text-gray-700 dark:hover:text-zinc-200 shrink-0"
                                title="Path information"
                                @click="onDestinationPathClick(selectedPeerPath)"
                            >
                                <span v-if="selectedPeerPath.hops === 0 || selectedPeerPath.hops === 1">{{
                                    $t("messages.direct")
                                }}</span>
                                <span v-else>{{ $t("messages.hops_away", { count: selectedPeerPath.hops }) }}</span>
                            </span>

                            <!-- snr -->
                            <span
                                v-if="selectedPeerSignalMetrics?.snr != null"
                                class="flex items-center gap-2 shrink-0"
                            >
                                <span class="text-gray-300 dark:text-zinc-700 opacity-50">•</span>
                                <span
                                    class="cursor-pointer hover:text-gray-700 dark:hover:text-zinc-200"
                                    title="Signal quality"
                                    @click="onSignalMetricsClick(selectedPeerSignalMetrics)"
                                    >{{ $t("messages.snr", { snr: selectedPeerSignalMetrics.snr }) }}</span
                                >
                            </span>

                            <!-- stamp cost -->
                            <span v-if="selectedPeerLxmfStampInfo?.stamp_cost" class="flex items-center gap-2 shrink-0">
                                <span class="text-gray-300 dark:text-zinc-700 opacity-50">•</span>
                                <span
                                    class="cursor-pointer hover:text-gray-700 dark:hover:text-zinc-200"
                                    title="LXMF stamp requirement"
                                    @click="onStampInfoClick(selectedPeerLxmfStampInfo)"
                                    >{{
                                        $t("messages.stamp_cost", { cost: selectedPeerLxmfStampInfo.stamp_cost })
                                    }}</span
                                >
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- dropdown menu -->
            <div class="ml-auto flex items-center gap-0.5 sm:gap-1.5 min-w-0 shrink-0">
                <ConversationDropDownMenu
                    v-if="selectedPeer"
                    :peer="selectedPeer"
                    :compact="compactPeerActions"
                    :has-failed-messages="hasFailedOrCancelledMessages"
                    @conversation-deleted="onConversationDeleted"
                    @set-custom-display-name="updateCustomDisplayName"
                    @popout="openConversationPopout"
                    @retry-failed="retryAllFailedOrCancelledMessages"
                    @open-telemetry-history="isTelemetryHistoryModalOpen = true"
                    @start-call="onStartCall"
                    @share-contact="openShareContactModal"
                />

                <IconButton title="Close" class="shrink-0" @click="close">
                    <MaterialDesignIcon icon-name="close" class="size-6 sm:size-7" />
                </IconButton>
            </div>
        </div>

        <!-- Telemetry History Modal -->
        <div
            v-if="isTelemetryHistoryModalOpen"
            class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            @click.self="isTelemetryHistoryModalOpen = false"
        >
            <div
                class="w-full max-w-lg bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
            >
                <div class="px-6 py-4 border-b border-gray-100 dark:border-zinc-800 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <MaterialDesignIcon icon-name="satellite-variant" class="size-6 text-blue-500" />
                        <h3 class="text-lg font-bold text-gray-900 dark:text-white">Telemetry History</h3>
                    </div>
                    <button
                        type="button"
                        class="text-gray-400 hover:text-gray-500 dark:hover:text-zinc-300 transition-colors"
                        @click="isTelemetryHistoryModalOpen = false"
                    >
                        <MaterialDesignIcon icon-name="close" class="size-6" />
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto p-4 space-y-3">
                    <div v-if="selectedPeerTelemetryItems.length === 0" class="text-center py-8 text-gray-400">
                        No telemetry history found for this peer.
                    </div>
                    <div
                        v-for="item in selectedPeerTelemetryItems"
                        :key="item.lxmf_message.hash"
                        class="p-3 rounded-xl border border-gray-100 dark:border-zinc-800 bg-gray-50/50 dark:bg-zinc-900/30"
                    >
                        <div class="flex justify-between items-start mb-2">
                            <span
                                class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-gray-200 dark:bg-zinc-800 text-gray-600 dark:text-zinc-400"
                            >
                                {{ item.is_outbound ? "Sent" : "Received" }}
                            </span>
                            <span class="text-[10px] text-gray-400">{{
                                formatTimeAgo(item.lxmf_message.created_at)
                            }}</span>
                        </div>

                        <!-- location -->
                        <div v-if="item.lxmf_message.fields?.telemetry?.location" class="flex items-center gap-2 mb-2">
                            <button
                                type="button"
                                class="flex items-center gap-2 text-xs font-mono text-blue-600 dark:text-blue-400 hover:underline"
                                @click="viewLocationOnMap(item.lxmf_message.fields.telemetry.location)"
                            >
                                <MaterialDesignIcon icon-name="map-marker" class="size-4" />
                                {{ item.lxmf_message.fields.telemetry.location.latitude.toFixed(6) }},
                                {{ item.lxmf_message.fields.telemetry.location.longitude.toFixed(6) }}
                            </button>
                        </div>

                        <!-- sensors -->
                        <div
                            v-if="item.lxmf_message.fields?.telemetry"
                            class="flex flex-wrap gap-3 text-[10px] text-gray-500"
                        >
                            <span v-if="item.lxmf_message.fields.telemetry.battery" class="flex items-center gap-1">
                                <MaterialDesignIcon icon-name="battery" class="size-3" />
                                Battery: {{ item.lxmf_message.fields.telemetry.battery.charge_percent }}%
                            </span>
                            <span
                                v-if="item.lxmf_message.fields.telemetry.physical_link"
                                class="flex items-center gap-1"
                            >
                                <MaterialDesignIcon icon-name="antenna" class="size-3" />
                                SNR: {{ item.lxmf_message.fields.telemetry.physical_link.snr }}dB
                            </span>
                        </div>

                        <!-- commands -->
                        <div
                            v-if="item.lxmf_message.fields?.commands?.some((c) => c['0x01'])"
                            class="flex items-center gap-2 text-[10px] text-emerald-600 dark:text-emerald-400 mt-1"
                        >
                            <MaterialDesignIcon icon-name="crosshairs-question" class="size-3" />
                            <span>Location Request</span>
                        </div>
                    </div>
                </div>
                <div
                    class="px-6 py-4 border-t border-gray-100 dark:border-zinc-800 bg-gray-50/30 dark:bg-zinc-900/20 flex flex-col gap-4"
                >
                    <div v-if="telemetryBatteryHistory.length > 1" class="space-y-2">
                        <div class="flex items-center justify-between">
                            <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest"
                                >Battery Level (%)</span
                            >
                            <span class="text-[10px] text-gray-500"
                                >{{ telemetryBatteryHistory[0].y }}% →
                                {{ telemetryBatteryHistory[telemetryBatteryHistory.length - 1].y }}%</span
                            >
                        </div>
                        <svg class="w-full h-12 overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
                            <path
                                :d="batterySparklinePath"
                                fill="none"
                                stroke="#3b82f6"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <circle
                                :cx="100"
                                :cy="100 - telemetryBatteryHistory[telemetryBatteryHistory.length - 1].y"
                                r="3"
                                fill="#3b82f6"
                            />
                        </svg>
                    </div>

                    <div class="flex justify-between items-center w-full">
                        <label class="flex items-center gap-2 cursor-pointer group">
                            <input
                                v-model="showTelemetryInChat"
                                type="checkbox"
                                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span
                                class="text-xs font-medium text-gray-600 dark:text-zinc-400 group-hover:text-gray-900 dark:group-hover:text-zinc-200"
                                >Show telemetry in main chat</span
                            >
                        </label>
                        <button
                            type="button"
                            class="px-4 py-2 bg-blue-600 text-white text-xs font-bold rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
                            @click="isTelemetryHistoryModalOpen = false"
                        >
                            Done
                        </button>
                    </div>
                </div>
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
                class="pointer-events-none absolute inset-0 z-[5] border-2 border-dashed border-blue-400/70 bg-blue-500/[0.06] dark:bg-blue-400/[0.08]"
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
                    class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0"
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
            <div
                id="messages"
                class="flex-1 min-h-0 overflow-y-scroll bg-white dark:bg-zinc-950"
                @scroll="onMessagesScroll"
            >
                <div v-if="selectedPeerChatItems.length > 0" class="flex flex-col flex-col-reverse px-4 py-6 min-w-0">
                    <template v-for="entry in selectedPeerChatDisplayGroups" :key="entry.key">
                        <div
                            v-if="entry.type === 'imageGroup'"
                            class="flex flex-col max-w-[85%] sm:max-w-[75%] md:max-lg:max-w-[70%] lg:max-w-[65%] mb-4 group min-w-0"
                            :class="{
                                'ml-auto items-end': entry.items[0].is_outbound,
                                'mr-auto items-start': !entry.items[0].is_outbound,
                            }"
                            @contextmenu.prevent="onMessageContextMenu($event, entry.items[0])"
                        >
                            <div
                                class="relative w-full max-w-[min(280px,85vw)] rounded-2xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 shadow-md mb-1.5"
                                :class="entry.items[0].is_outbound ? 'ml-auto' : 'mr-auto'"
                                @click.stop="onChatItemClick(entry.items[0])"
                            >
                                <button
                                    type="button"
                                    class="absolute top-1 right-1 z-10 p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity text-white hover:bg-white/20"
                                    :title="$t('messages.message_actions')"
                                    @click.stop="onMessageContextMenu($event, entry.items[0])"
                                >
                                    <MaterialDesignIcon icon-name="dots-vertical" class="size-4" />
                                </button>
                                <div
                                    v-if="imageGroupSortedChron(entry.items).length === 2"
                                    class="grid grid-cols-2 gap-0.5 bg-black/5 dark:bg-white/5"
                                >
                                    <button
                                        v-for="imgItem in imageGroupSortedChron(entry.items)"
                                        :id="`message-${imgItem.lxmf_message.hash}`"
                                        :key="imgItem.lxmf_message.hash"
                                        type="button"
                                        class="relative aspect-square min-h-[96px] max-h-[220px] min-w-0 overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                                        @click.stop="
                                            openImage(
                                                lxmfImageUrl(imgItem.lxmf_message.hash),
                                                imageGroupGalleryUrls(entry.items)
                                            )
                                        "
                                    >
                                        <img
                                            :src="lxmfImageUrl(imgItem.lxmf_message.hash)"
                                            loading="lazy"
                                            decoding="async"
                                            class="h-full w-full object-cover object-center transition-transform hover:scale-[1.02]"
                                            alt=""
                                        />
                                    </button>
                                </div>
                                <div
                                    v-else-if="imageGroupSortedChron(entry.items).length === 3"
                                    class="grid grid-cols-2 gap-0.5 bg-black/5 dark:bg-white/5"
                                >
                                    <button
                                        v-for="imgItem in imageGroupSortedChron(entry.items).slice(0, 2)"
                                        :id="`message-${imgItem.lxmf_message.hash}`"
                                        :key="imgItem.lxmf_message.hash"
                                        type="button"
                                        class="relative aspect-square min-h-[96px] max-h-[220px] min-w-0 overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                                        @click.stop="
                                            openImage(
                                                lxmfImageUrl(imgItem.lxmf_message.hash),
                                                imageGroupGalleryUrls(entry.items)
                                            )
                                        "
                                    >
                                        <img
                                            :src="lxmfImageUrl(imgItem.lxmf_message.hash)"
                                            loading="lazy"
                                            decoding="async"
                                            class="h-full w-full object-cover object-center transition-transform hover:scale-[1.02]"
                                            alt=""
                                        />
                                    </button>
                                    <button
                                        :id="`message-${imageGroupSortedChron(entry.items)[2].lxmf_message.hash}`"
                                        type="button"
                                        class="relative col-span-2 aspect-[2/1] max-h-52 min-h-[80px] w-full overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                                        @click.stop="
                                            openImage(
                                                lxmfImageUrl(imageGroupSortedChron(entry.items)[2].lxmf_message.hash),
                                                imageGroupGalleryUrls(entry.items)
                                            )
                                        "
                                    >
                                        <img
                                            :src="lxmfImageUrl(imageGroupSortedChron(entry.items)[2].lxmf_message.hash)"
                                            loading="lazy"
                                            decoding="async"
                                            class="h-full w-full object-cover object-center transition-transform hover:scale-[1.02]"
                                            alt=""
                                        />
                                    </button>
                                </div>
                                <div v-else class="grid grid-cols-2 gap-0.5 bg-black/5 dark:bg-white/5">
                                    <button
                                        v-for="(cell, idx) in imageGroupSortedChron(entry.items).slice(0, 4)"
                                        :id="`message-${cell.lxmf_message.hash}`"
                                        :key="cell.lxmf_message.hash"
                                        type="button"
                                        class="relative aspect-square min-h-[96px] max-h-[220px] min-w-0 overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80"
                                        @click.stop="
                                            openImage(
                                                lxmfImageUrl(cell.lxmf_message.hash),
                                                imageGroupGalleryUrls(entry.items)
                                            )
                                        "
                                    >
                                        <img
                                            :src="lxmfImageUrl(cell.lxmf_message.hash)"
                                            loading="lazy"
                                            decoding="async"
                                            class="h-full w-full object-cover object-center transition-transform hover:scale-[1.02]"
                                            alt=""
                                        />
                                        <div
                                            v-if="idx === 3 && imageGroupSortedChron(entry.items).length > 4"
                                            class="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/55 text-white text-3xl font-bold"
                                        >
                                            +{{ imageGroupSortedChron(entry.items).length - 4 }}
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
                                          : isOutboundWaitingBubble(entry.items[0])
                                            ? 'shadow-sm'
                                            : entry.items[0].is_outbound
                                              ? outboundBubbleSurfaceClass(entry.items[0])
                                              : 'bg-white dark:bg-zinc-900 text-gray-900 dark:text-zinc-100 border border-gray-200/60 dark:border-zinc-800/60 shadow-sm',
                                ]"
                                :style="bubbleStyles(entry.items[0])"
                            >
                                <div class="flex items-center justify-end gap-1.5 select-none h-3">
                                    <span
                                        class="text-[9px] opacity-80 font-medium"
                                        :class="outboundBubbleFooterTimeClass(entry.items[0])"
                                        :title="
                                            getMessageInfoLines(
                                                entry.items[0].lxmf_message,
                                                entry.items[0].is_outbound
                                            ).join('\n')
                                        "
                                    >
                                        {{ formatTimeAgo(entry.items[0].lxmf_message.created_at) }}
                                    </span>
                                    <div v-if="entry.items[0].is_outbound" class="flex items-center gap-1">
                                        <span
                                            v-if="isOpportunisticDeferredDelivery(entry.items[0].lxmf_message)"
                                            class="text-[9px] font-bold uppercase tracking-wider"
                                            :class="
                                                isThemeOutboundBubble(entry.items[0])
                                                    ? 'text-amber-800 dark:text-amber-300'
                                                    : 'text-amber-200'
                                            "
                                        >
                                            {{ $t("messages.opportunistic_deferred_label") }}
                                        </span>
                                        <span
                                            v-else-if="
                                                ['failed', 'cancelled', 'rejected'].includes(
                                                    entry.items[0].lxmf_message.state
                                                )
                                            "
                                            class="text-[9px] font-bold uppercase tracking-wider text-white"
                                        >
                                            {{
                                                entry.items[0].lxmf_message.state === "rejected" ? "Rejected" : "Failed"
                                            }}
                                        </span>
                                        <button
                                            v-if="['failed', 'cancelled'].includes(entry.items[0].lxmf_message.state)"
                                            type="button"
                                            class="ml-0.5 p-0.5 rounded hover:bg-white/20 transition-colors"
                                            title="Retry sending"
                                            @click.stop="retrySendingMessage(entry.items[0])"
                                        >
                                            <MaterialDesignIcon icon-name="refresh" class="size-3 text-white" />
                                        </button>
                                        <MaterialDesignIcon
                                            v-if="entry.items[0].lxmf_message.state === 'delivered'"
                                            icon-name="check-all"
                                            class="size-3"
                                            :class="outboundBubbleDeliveredIconClass(entry.items[0])"
                                            title="Delivered"
                                        />
                                        <MaterialDesignIcon
                                            v-else-if="
                                                ['sent', 'propagated', 'unknown'].includes(
                                                    entry.items[0].lxmf_message.state
                                                )
                                            "
                                            icon-name="check"
                                            class="size-3"
                                            :class="outboundBubbleSentCheckIconClass(entry.items[0])"
                                            :title="
                                                entry.items[0].lxmf_message.state === 'propagated'
                                                    ? 'Sent to propagation node'
                                                    : 'Sent'
                                            "
                                        />
                                        <svg
                                            v-else-if="
                                                showRichOutboundPendingUi(entry.items[0]) &&
                                                isOutboundPendingForUi(entry.items[0])
                                            "
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            class="animate-spin size-3.5 shrink-0"
                                            :class="outboundSendingStatusIconClass(entry.items[0])"
                                            :title="outboundBubbleStatusHoverTitle(entry.items[0].lxmf_message)"
                                        >
                                            <title>
                                                {{ outboundBubbleStatusHoverTitle(entry.items[0].lxmf_message) }}
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
                                            v-else-if="isOutboundPendingForUi(entry.items[0])"
                                            icon-name="check"
                                            class="size-3"
                                            :class="outboundBubblePendingCheckIconClass(entry.items[0])"
                                            :title="$t('messages.sending_ellipsis')"
                                        />
                                        <div
                                            v-else-if="isOpportunisticDeferredDelivery(entry.items[0].lxmf_message)"
                                            class="relative flex size-3.5 shrink-0 items-center justify-center rounded-full border border-dashed border-amber-200/85"
                                            :title="$t('messages.opportunistic_deferred_tooltip')"
                                        >
                                            <MaterialDesignIcon
                                                icon-name="clock-outline"
                                                class="size-2.5 text-amber-200/95"
                                            />
                                        </div>
                                        <MaterialDesignIcon
                                            v-else-if="
                                                ['failed', 'cancelled', 'rejected'].includes(
                                                    entry.items[0].lxmf_message.state
                                                )
                                            "
                                            icon-name="alert-circle-outline"
                                            class="size-3 text-white"
                                            :title="outboundBubbleFailedTitle(entry.items[0].lxmf_message)"
                                        />
                                    </div>
                                </div>
                            </div>
                            <div
                                v-if="entry.items[0].is_actions_expanded"
                                class="border-t px-4 py-2.5 rounded-b-2xl rounded-t-md w-full max-w-[min(280px,85vw)]"
                                :class="outboundExpandedActionsShellClass(entry.items[0])"
                            >
                                <div class="flex items-center gap-2">
                                    <button
                                        type="button"
                                        class="inline-flex items-center gap-x-1.5 rounded-lg bg-blue-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-600 transition-colors"
                                        @click.stop="replyToMessage(entry.items[0])"
                                    >
                                        {{ $t("messages.reply") }}
                                    </button>
                                    <button
                                        type="button"
                                        class="inline-flex items-center gap-x-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-red-600 transition-colors"
                                        @click.stop="deleteChatItem(entry.items[0])"
                                    >
                                        Delete
                                    </button>
                                    <button
                                        type="button"
                                        class="inline-flex items-center gap-x-1.5 rounded-lg bg-gray-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-gray-700 transition-colors"
                                        @click.stop="showRawMessage(entry.items[0])"
                                    >
                                        Raw LXM
                                    </button>
                                </div>
                            </div>
                            <div
                                v-if="expandedMessageInfo === entry.items[0].lxmf_message.hash"
                                class="mt-2 px-1 text-xs text-gray-500 dark:text-zinc-400 space-y-0.5"
                                :class="entry.items[0].is_outbound ? 'self-end' : 'self-start'"
                            >
                                <div
                                    v-for="(line, index) in getMessageInfoLines(
                                        entry.items[0].lxmf_message,
                                        entry.items[0].is_outbound
                                    )"
                                    :key="index"
                                    class="break-all"
                                >
                                    {{ line }}
                                </div>
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
                            @contextmenu.prevent="onMessageContextMenu($event, chatItem)"
                        >
                            <!-- standalone image (outside bubble) -->
                            <div
                                v-if="chatItem.lxmf_message.fields?.image"
                                class="relative group w-full max-w-[min(280px,85vw)] rounded-2xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 shadow-md mb-1.5"
                                :class="chatItem.is_outbound ? 'ml-auto' : 'mr-auto'"
                            >
                                <img
                                    :src="pendingOutboundImageSrc(chatItem)"
                                    loading="lazy"
                                    decoding="async"
                                    class="max-h-[min(320px,55vh)] w-full cursor-pointer object-cover object-center transition-transform hover:scale-[1.01]"
                                    alt=""
                                    @click.stop="openImage(pendingOutboundImageSrc(chatItem))"
                                />
                                <div
                                    class="pointer-events-none absolute bottom-2 left-2 rounded-lg bg-black/60 px-2.5 py-1 text-xs text-white opacity-0 backdrop-blur-sm transition-opacity group-hover:opacity-100 sm:opacity-100"
                                >
                                    <span>{{
                                        (chatItem.lxmf_message.fields.image.image_type ?? "image").toUpperCase()
                                    }}</span>
                                    <span class="mx-1">·</span>
                                    <span>{{ formatAttachmentSize(chatItem.lxmf_message.fields.image, "image") }}</span>
                                </div>
                            </div>
                            <!-- image-only: inline timestamp overlay (no bubble) -->
                            <div
                                v-if="isImageOnlyMessage(chatItem)"
                                class="flex items-center gap-1.5 select-none mt-0.5"
                                :class="chatItem.is_outbound ? 'justify-end' : 'justify-start'"
                            >
                                <span class="text-[9px] opacity-50 font-medium">
                                    {{ formatTimeAgo(chatItem.lxmf_message.created_at) }}
                                </span>
                                <template v-if="chatItem.is_outbound">
                                    <MaterialDesignIcon
                                        v-if="chatItem.lxmf_message.state === 'delivered'"
                                        icon-name="check-all"
                                        class="size-3 opacity-50"
                                    />
                                    <MaterialDesignIcon
                                        v-else-if="
                                            ['sent', 'propagated', 'unknown'].includes(chatItem.lxmf_message.state)
                                        "
                                        icon-name="check"
                                        class="size-3 opacity-50"
                                    />
                                    <span
                                        v-else-if="
                                            ['failed', 'cancelled', 'rejected'].includes(chatItem.lxmf_message.state)
                                        "
                                        class="text-[9px] font-bold uppercase tracking-wider text-red-500"
                                    >
                                        {{ chatItem.lxmf_message.state === "rejected" ? "Rejected" : "Failed" }}
                                    </span>
                                </template>
                            </div>

                            <!-- message content -->
                            <div
                                v-if="!isImageOnlyMessage(chatItem)"
                                class="relative rounded-2xl overflow-hidden transition-all duration-200 hover:shadow-md min-w-0"
                                :class="[
                                    ['cancelled', 'failed'].includes(chatItem.lxmf_message.state)
                                        ? 'shadow-sm'
                                        : chatItem.lxmf_message.is_spam
                                          ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-900 dark:text-yellow-100 border border-yellow-300 dark:border-yellow-700 shadow-sm'
                                          : isOutboundWaitingBubble(chatItem)
                                            ? 'shadow-sm'
                                            : chatItem.is_outbound
                                              ? outboundBubbleSurfaceClass(chatItem)
                                              : 'bg-white dark:bg-zinc-900 text-gray-900 dark:text-zinc-100 border border-gray-200/60 dark:border-zinc-800/60 shadow-sm',
                                ]"
                                :style="bubbleStyles(chatItem)"
                                @click="onChatItemClick(chatItem)"
                            >
                                <button
                                    type="button"
                                    class="absolute top-1 right-1 p-1 rounded-lg opacity-0 group-hover:opacity-100 hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300 dark:text-zinc-500"
                                    :class="outboundMessageMenuButtonHoverClass(chatItem)"
                                    :title="$t('messages.message_actions')"
                                    @click.stop="onMessageContextMenu($event, chatItem)"
                                >
                                    <MaterialDesignIcon icon-name="dots-vertical" class="size-4" />
                                </button>
                                <div class="w-full space-y-1 px-4 py-2.5 min-w-0">
                                    <!-- reply snippet -->
                                    <div
                                        v-if="chatItem.lxmf_message.reply_to_hash"
                                        class="mb-2 p-2 rounded-lg bg-black/5 dark:bg-white/5 border-l-2 border-blue-500/50 cursor-pointer hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
                                        @click.stop="scrollToMessage(chatItem.lxmf_message.reply_to_hash)"
                                    >
                                        <div
                                            class="flex items-center gap-1 text-[10px] font-bold uppercase tracking-tight mb-0.5"
                                            :class="outboundReplySnippetTitleClass(chatItem)"
                                        >
                                            <MaterialDesignIcon icon-name="reply" class="size-3" />
                                            {{ $t("messages.replying_to") }}
                                        </div>
                                        <div class="text-xs opacity-70 truncate line-clamp-1 italic">
                                            {{
                                                chatItem.lxmf_message.fields?.reply_quoted_content ||
                                                getRepliedMessage(chatItem.lxmf_message.reply_to_hash)?.content ||
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
                                                ? isThemeOutboundBubble(chatItem)
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
                                            !getParsedItems(chatItem)?.isOnlyPaperMessage &&
                                            !shouldHideAutoImageCaption(chatItem)
                                        "
                                        class="leading-relaxed break-words [word-break:break-word] min-w-0 markdown-content"
                                        :class="{
                                            'markdown-content--outbound-theme':
                                                chatItem.is_outbound && isThemeOutboundBubble(chatItem),
                                            'markdown-content--outbound-solid':
                                                chatItem.is_outbound && !isThemeOutboundBubble(chatItem),
                                            'markdown-content--inbound': !chatItem.is_outbound,
                                            'markdown-content--single-emoji': messageMarkdownSingleEmoji(chatItem),
                                        }"
                                        :style="{
                                            'font-family': 'inherit',
                                            'font-size': messageMarkdownFontSizePx(chatItem) + 'px',
                                        }"
                                        @click="handleMessageClick"
                                        v-html="renderMarkdown(chatItem.lxmf_message.content)"
                                    ></div>
                                    <!-- eslint-enable vue/no-v-html -->

                                    <!-- telemetry placeholder for empty content messages -->
                                    <div
                                        v-if="!chatItem.lxmf_message.content && chatItem.lxmf_message.fields?.telemetry"
                                        class="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100/20"
                                    >
                                        <MaterialDesignIcon icon-name="satellite-variant" class="size-4 opacity-60" />
                                        <span class="text-[10px] font-bold uppercase tracking-wider opacity-60">
                                            {{
                                                chatItem.is_outbound
                                                    ? "Telemetry update sent"
                                                    : "Telemetry update received"
                                            }}
                                        </span>
                                    </div>

                                    <div
                                        v-if="
                                            !chatItem.lxmf_message.content &&
                                            chatItem.lxmf_message.fields?.telemetry_stream
                                        "
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
                                            chatItem.lxmf_message.fields?.commands?.some(
                                                (c) => c['0x01'] || c['1'] || c['0x1']
                                            )
                                        "
                                        class="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100/20"
                                    >
                                        <MaterialDesignIcon icon-name="crosshairs-question" class="size-4 opacity-60" />
                                        <span class="text-[10px] font-bold uppercase tracking-wider opacity-60">
                                            {{
                                                chatItem.is_outbound
                                                    ? "Location Request Sent"
                                                    : "Location Request Received"
                                            }}
                                        </span>
                                    </div>

                                    <!-- parsed items (contacts / paper messages) -->
                                    <div v-if="getParsedItems(chatItem)" class="mt-2 space-y-2">
                                        <!-- contact -->
                                        <div
                                            v-if="getParsedItems(chatItem).contact && !chatItem.is_outbound"
                                            class="flex flex-col gap-2 p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/30"
                                        >
                                            <div class="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                                                <MaterialDesignIcon icon-name="account-plus-outline" class="size-5" />
                                                <span class="text-sm font-bold">Contact Shared</span>
                                            </div>
                                            <div class="flex items-center gap-3">
                                                <LxmfUserIcon
                                                    :custom-image="getParsedItems(chatItem).contact.custom_image"
                                                    :icon-name="
                                                        getParsedItems(chatItem).contact.lxmf_user_icon?.icon_name
                                                    "
                                                    :icon-foreground-colour="
                                                        getParsedItems(chatItem).contact.lxmf_user_icon
                                                            ?.foreground_colour
                                                    "
                                                    :icon-background-colour="
                                                        getParsedItems(chatItem).contact.lxmf_user_icon
                                                            ?.background_colour
                                                    "
                                                    icon-class="size-10"
                                                />
                                                <div class="flex-1 min-w-0">
                                                    <div
                                                        class="text-sm font-bold text-gray-900 dark:text-white truncate"
                                                    >
                                                        {{ getParsedItems(chatItem).contact.name }}
                                                    </div>
                                                    <div
                                                        class="text-[10px] font-mono text-gray-500 dark:text-zinc-400 truncate"
                                                    >
                                                        {{ getParsedItems(chatItem).contact.hash }}
                                                    </div>
                                                    <div
                                                        v-if="getParsedItems(chatItem).contact.lxmf_address"
                                                        class="text-[9px] font-mono text-gray-400 dark:text-zinc-500 truncate"
                                                    >
                                                        LXMF: {{ getParsedItems(chatItem).contact.lxmf_address }}
                                                    </div>
                                                    <div
                                                        v-if="getParsedItems(chatItem).contact.lxst_address"
                                                        class="text-[9px] font-mono text-gray-400 dark:text-zinc-500 truncate"
                                                    >
                                                        LXST: {{ getParsedItems(chatItem).contact.lxst_address }}
                                                    </div>
                                                </div>
                                            </div>
                                            <button
                                                type="button"
                                                class="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
                                                @click="
                                                    addContact(
                                                        getParsedItems(chatItem).contact.name,
                                                        getParsedItems(chatItem).contact.hash,
                                                        getParsedItems(chatItem).contact.lxmf_address,
                                                        getParsedItems(chatItem).contact.lxst_address
                                                    )
                                                "
                                            >
                                                Add to Contacts
                                            </button>
                                        </div>

                                        <!-- paper message auto-conversion -->
                                        <div
                                            v-if="getParsedItems(chatItem).paperMessage && !chatItem.is_outbound"
                                            class="flex flex-col gap-2 p-3 rounded-xl bg-emerald-50 dark:bg-black/60 border border-emerald-100 dark:border-zinc-700/50"
                                        >
                                            <div class="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                                                <MaterialDesignIcon icon-name="qrcode-scan" class="size-5" />
                                                <span class="text-sm font-bold">Paper Message detected</span>
                                            </div>
                                            <p class="text-xs text-emerald-600/80 dark:text-zinc-400 leading-relaxed">
                                                This message contains a signed LXMF URI that can be ingested into your
                                                conversations.
                                            </p>
                                            <button
                                                type="button"
                                                class="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
                                                @click="ingestPaperMessage(getParsedItems(chatItem).paperMessage)"
                                            >
                                                Ingest Message
                                            </button>
                                        </div>
                                    </div>

                                    <!-- audio field -->
                                    <div v-if="chatItem.lxmf_message.fields?.audio" class="pb-1">
                                        <!-- audio is loaded -->
                                        <AudioWaveformPlayer
                                            v-if="lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash]"
                                            :src="lxmfMessageAudioAttachmentCache[chatItem.lxmf_message.hash]"
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
                                                <span
                                                    class="text-[10px] font-bold text-gray-400 uppercase tracking-wider"
                                                    >{{ $t("messages.downloading") }}</span
                                                >
                                            </div>
                                        </div>

                                        <div
                                            class="text-[10px] mt-1 text-right opacity-60"
                                            :class="outboundAttachmentCaptionClass(chatItem)"
                                        >
                                            Voice Note •
                                            {{ formatAttachmentSize(chatItem.lxmf_message.fields.audio, "audio") }}
                                        </div>
                                    </div>

                                    <!-- file attachment fields -->
                                    <div v-if="chatItem.lxmf_message.fields?.file_attachments" class="space-y-2 mt-1">
                                        <a
                                            v-for="(file_attachment, index) of chatItem.lxmf_message.fields
                                                ?.file_attachments ?? []"
                                            :key="file_attachment.file_name"
                                            target="_blank"
                                            :download="file_attachment.file_name"
                                            :href="`/api/v1/lxmf-messages/attachment/${chatItem.lxmf_message.hash}/file?file_index=${index}`"
                                            class="flex items-center gap-3 border rounded-lg px-3 py-2 text-sm font-medium cursor-pointer transition-colors"
                                            :class="
                                                chatItem.is_outbound
                                                    ? outboundEmbeddedCardClass(chatItem)
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
                                                            ? outboundEmbeddedSecondaryTextClass(chatItem)
                                                            : 'text-gray-500 dark:text-zinc-400'
                                                    "
                                                >
                                                    {{ formatAttachmentSize(file_attachment, "file") }}
                                                </div>
                                            </div>
                                            <div class="my-auto">
                                                <MaterialDesignIcon icon-name="download" class="size-5" />
                                            </div>
                                        </a>
                                    </div>

                                    <!-- commands -->
                                    <div v-if="chatItem.lxmf_message.fields?.commands" class="space-y-2 mt-1">
                                        <div
                                            v-for="(command, index) in chatItem.lxmf_message.fields.commands"
                                            :key="index"
                                        >
                                            <div
                                                v-if="command['0x01'] || command['1'] || command['0x1']"
                                                class="flex items-center gap-2 border border-gray-200/60 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                                                :class="
                                                    chatItem.is_outbound
                                                        ? outboundEmbeddedCardClass(chatItem)
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
                                                        ? outboundEmbeddedCardClass(chatItem)
                                                        : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300'
                                                "
                                                @click="
                                                    viewLocationOnMap(chatItem.lxmf_message.fields.telemetry.location)
                                                "
                                            >
                                                <MaterialDesignIcon icon-name="map-marker" class="size-5" />
                                                <div class="text-left">
                                                    <div
                                                        class="font-bold text-[10px] uppercase tracking-wider opacity-80"
                                                    >
                                                        Location
                                                    </div>
                                                    <div class="text-[9px] font-mono opacity-70">
                                                        {{
                                                            chatItem.lxmf_message.fields.telemetry.location.latitude.toFixed(
                                                                6
                                                            )
                                                        }},
                                                        {{
                                                            chatItem.lxmf_message.fields.telemetry.location.longitude.toFixed(
                                                                6
                                                            )
                                                        }}
                                                    </div>
                                                </div>
                                            </button>

                                            <!-- Live Track Toggle Button (only for incoming) -->
                                            <button
                                                v-if="!chatItem.is_outbound"
                                                type="button"
                                                class="flex items-center gap-2 border border-gray-200/60 dark:border-zinc-700 hover:bg-gray-50 dark:hover:bg-zinc-800 rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                                                :class="[
                                                    selectedPeer?.is_tracking
                                                        ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30 shadow-inner'
                                                        : 'bg-gray-50 dark:bg-zinc-800/50 text-gray-700 dark:text-zinc-300',
                                                ]"
                                                @click="toggleTracking()"
                                            >
                                                <MaterialDesignIcon
                                                    :icon-name="selectedPeer?.is_tracking ? 'radar' : 'crosshairs'"
                                                    class="size-5"
                                                    :class="{
                                                        'animate-pulse text-blue-500': selectedPeer?.is_tracking,
                                                    }"
                                                />
                                                <div class="text-left">
                                                    <div
                                                        class="font-bold text-[10px] uppercase tracking-wider opacity-80"
                                                    >
                                                        {{
                                                            selectedPeer?.is_tracking ? "Tracking Active" : "Live Track"
                                                        }}
                                                    </div>
                                                    <div class="text-[9px] opacity-70">
                                                        {{
                                                            selectedPeer?.is_tracking
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
                                                <span
                                                    >{{
                                                        chatItem.lxmf_message.fields.telemetry.battery.charge_percent
                                                    }}%</span
                                                >
                                            </div>
                                            <div
                                                v-if="chatItem.lxmf_message.fields.telemetry.physical_link"
                                                class="flex items-center gap-1 opacity-60 text-[10px]"
                                            >
                                                <MaterialDesignIcon icon-name="antenna" class="size-3" />
                                                <span
                                                    >SNR:
                                                    {{
                                                        chatItem.lxmf_message.fields.telemetry.physical_link.snr
                                                    }}dB</span
                                                >
                                            </div>
                                        </div>
                                    </div>

                                    <!-- message footer: timestamp and status icons -->
                                    <div class="flex items-center justify-end gap-1.5 mt-1.5 select-none h-3">
                                        <span
                                            class="text-[9px] opacity-80 font-medium"
                                            :class="outboundBubbleFooterTimeClass(chatItem)"
                                            :title="
                                                getMessageInfoLines(chatItem.lxmf_message, chatItem.is_outbound).join(
                                                    '\n'
                                                )
                                            "
                                        >
                                            {{ formatTimeAgo(chatItem.lxmf_message.created_at) }}
                                        </span>

                                        <!-- outbound status icons -->
                                        <div v-if="chatItem.is_outbound" class="flex items-center gap-1">
                                            <span
                                                v-if="isOpportunisticDeferredDelivery(chatItem.lxmf_message)"
                                                class="text-[9px] font-bold uppercase tracking-wider"
                                                :class="
                                                    isThemeOutboundBubble(chatItem)
                                                        ? 'text-amber-800 dark:text-amber-300'
                                                        : 'text-amber-200'
                                                "
                                            >
                                                {{ $t("messages.opportunistic_deferred_label") }}
                                            </span>
                                            <span
                                                v-else-if="
                                                    ['failed', 'cancelled', 'rejected'].includes(
                                                        chatItem.lxmf_message.state
                                                    )
                                                "
                                                class="text-[9px] font-bold uppercase tracking-wider text-white"
                                            >
                                                {{ chatItem.lxmf_message.state === "rejected" ? "Rejected" : "Failed" }}
                                            </span>
                                            <button
                                                v-if="['failed', 'cancelled'].includes(chatItem.lxmf_message.state)"
                                                type="button"
                                                class="ml-0.5 p-0.5 rounded hover:bg-white/20 transition-colors"
                                                title="Retry sending"
                                                @click.stop="retrySendingMessage(chatItem)"
                                            >
                                                <MaterialDesignIcon icon-name="refresh" class="size-3 text-white" />
                                            </button>

                                            <!-- delivered: double check -->
                                            <MaterialDesignIcon
                                                v-if="chatItem.lxmf_message.state === 'delivered'"
                                                icon-name="check-all"
                                                class="size-3"
                                                :class="outboundBubbleDeliveredIconClass(chatItem)"
                                                title="Delivered"
                                            />
                                            <!-- sent: single check (include unknown for initial outbound when server confirmed creation) -->
                                            <MaterialDesignIcon
                                                v-else-if="
                                                    ['sent', 'propagated', 'unknown'].includes(
                                                        chatItem.lxmf_message.state
                                                    )
                                                "
                                                icon-name="check"
                                                class="size-3"
                                                :class="outboundBubbleSentCheckIconClass(chatItem)"
                                                :title="
                                                    chatItem.lxmf_message.state === 'propagated'
                                                        ? 'Sent to propagation node'
                                                        : 'Sent'
                                                "
                                            />
                                            <svg
                                                v-else-if="
                                                    showRichOutboundPendingUi(chatItem) &&
                                                    isOutboundPendingForUi(chatItem)
                                                "
                                                xmlns="http://www.w3.org/2000/svg"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                class="animate-spin size-3.5 shrink-0"
                                                :class="outboundSendingStatusIconClass(chatItem)"
                                                :title="outboundBubbleStatusHoverTitle(chatItem.lxmf_message)"
                                            >
                                                <title>
                                                    {{ outboundBubbleStatusHoverTitle(chatItem.lxmf_message) }}
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
                                                v-else-if="isOutboundPendingForUi(chatItem)"
                                                icon-name="check"
                                                class="size-3"
                                                :class="outboundBubblePendingCheckIconClass(chatItem)"
                                                :title="$t('messages.sending_ellipsis')"
                                            />
                                            <div
                                                v-else-if="isOpportunisticDeferredDelivery(chatItem.lxmf_message)"
                                                class="relative flex size-3.5 shrink-0 items-center justify-center rounded-full border border-dashed border-amber-200/85"
                                                :title="$t('messages.opportunistic_deferred_tooltip')"
                                            >
                                                <MaterialDesignIcon
                                                    icon-name="clock-outline"
                                                    class="size-2.5 text-amber-200/95"
                                                />
                                            </div>
                                            <!-- failed/cancelled/rejected: alert -->
                                            <MaterialDesignIcon
                                                v-else-if="
                                                    ['failed', 'cancelled', 'rejected'].includes(
                                                        chatItem.lxmf_message.state
                                                    )
                                                "
                                                icon-name="alert-circle-outline"
                                                class="size-3 text-white"
                                                :title="outboundBubbleFailedTitle(chatItem.lxmf_message)"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <!-- actions (expanded) -->
                                <div
                                    v-if="chatItem.is_actions_expanded"
                                    class="border-t px-4 py-2.5"
                                    :class="outboundExpandedActionsShellClass(chatItem)"
                                >
                                    <div class="flex items-center gap-2">
                                        <button
                                            type="button"
                                            class="inline-flex items-center gap-x-1.5 rounded-lg bg-blue-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-600 transition-colors"
                                            @click.stop="replyToMessage(chatItem)"
                                        >
                                            {{ $t("messages.reply") }}
                                        </button>
                                        <button
                                            type="button"
                                            class="inline-flex items-center gap-x-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-red-600 transition-colors"
                                            @click.stop="deleteChatItem(chatItem)"
                                        >
                                            Delete
                                        </button>
                                        <button
                                            type="button"
                                            class="inline-flex items-center gap-x-1.5 rounded-lg bg-gray-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-gray-700 transition-colors"
                                            @click.stop="showRawMessage(chatItem)"
                                        >
                                            Raw LXM
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <div
                                v-if="chatItem.lxmf_message.reactions?.length"
                                class="mt-1 flex w-full flex-wrap justify-end gap-0.5 px-0.5"
                            >
                                <span
                                    v-for="(r, ridx) in chatItem.lxmf_message.reactions"
                                    :key="r.reactionHash || ridx"
                                    class="inline-flex min-h-[1.35rem] min-w-[1.35rem] cursor-default select-none items-center justify-center rounded-full border border-gray-200/90 bg-white px-1.5 py-0.5 text-sm leading-none shadow-sm dark:border-zinc-600/90 dark:bg-zinc-900"
                                    :title="reactionReactorLabel(r.sender)"
                                    >{{ r.emoji }}</span
                                >
                            </div>

                            <!-- expanded message details -->
                            <div
                                v-if="expandedMessageInfo === chatItem.lxmf_message.hash"
                                class="mt-2 px-1 text-xs text-gray-500 dark:text-zinc-400 space-y-0.5"
                            >
                                <div
                                    v-for="(line, index) in getMessageInfoLines(
                                        chatItem.lxmf_message,
                                        chatItem.is_outbound
                                    )"
                                    :key="index"
                                    class="break-all"
                                >
                                    {{ line }}
                                </div>
                            </div>
                        </div>
                    </template>

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
                            class="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0"
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
                                class="w-full max-w-[min(280px,100%)] rounded-xl overflow-hidden ring-1 ring-black/10 dark:ring-white/10 shadow-sm bg-black/5 dark:bg-white/5"
                            >
                                <div v-if="newMessageImages.length === 1" class="relative group">
                                    <button
                                        type="button"
                                        class="block w-full overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60"
                                        @click.stop="openImage(newMessageImageUrls[0], newMessageImageUrls)"
                                    >
                                        <img
                                            v-if="newMessageImageUrls[0]"
                                            :src="newMessageImageUrls[0]"
                                            class="max-h-52 w-full object-cover object-center"
                                        />
                                    </button>
                                    <button
                                        type="button"
                                        class="absolute -top-1 -right-1 inline-flex items-center justify-center w-6 h-6 rounded-full bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-600 dark:text-gray-200 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/40 shadow-md"
                                        @click.stop="removeImageAttachment(0)"
                                    >
                                        <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <div v-else-if="newMessageImages.length === 2" class="grid grid-cols-2 gap-0.5">
                                    <div v-for="(image, index) in newMessageImages" :key="index" class="relative group">
                                        <button
                                            type="button"
                                            class="relative block aspect-square min-h-[88px] w-full overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60"
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
                                            class="absolute top-1 right-1 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
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
                                            class="relative block aspect-square min-h-[88px] w-full overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60"
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
                                            class="absolute top-1 right-1 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
                                            @click.stop="removeImageAttachment(index)"
                                        >
                                            <MaterialDesignIcon icon-name="close" class="w-3.5 h-3.5" />
                                        </button>
                                    </div>
                                    <div class="relative group col-span-2">
                                        <button
                                            type="button"
                                            class="relative block aspect-[2/1] max-h-44 w-full min-h-[72px] overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60"
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
                                            class="absolute top-1 right-1 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
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
                                            class="relative block aspect-square min-h-[88px] w-full overflow-hidden focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60"
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
                                            class="absolute top-1 right-1 inline-flex items-center justify-center w-6 h-6 rounded-full bg-black/55 text-white hover:bg-black/70 shadow-md"
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
                                    class="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-sm rounded-xl focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 block w-full min-w-0 pl-3 sm:pl-4 pr-11 py-2.5 resize-none shadow-sm transition-all placeholder:text-gray-400 dark:placeholder:text-zinc-500 min-h-[44px] max-h-[200px] overflow-y-auto leading-snug"
                                    rows="1"
                                    spellcheck="true"
                                    :placeholder="$t('messages.send_placeholder')"
                                    @keydown.enter.exact.prevent="onEnterPressed"
                                    @keydown.enter.shift.exact.prevent="onShiftEnterPressed"
                                    @paste="onMessagePaste"
                                ></textarea>
                                <button
                                    type="button"
                                    class="absolute right-1.5 top-1/2 -translate-y-1/2 inline-flex items-center justify-center rounded-lg p-1.5 text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800 hover:text-gray-800 dark:hover:text-zinc-100"
                                    :title="$t('stickers.picker_tooltip')"
                                    @click.stop="toggleStickerPicker"
                                >
                                    <MaterialDesignIcon icon-name="emoticon-outline" class="w-5 h-5" />
                                </button>
                                <div
                                    v-if="isStickerPickerOpen"
                                    class="absolute bottom-full right-0 mb-2 z-50 w-[min(320px,85vw)] max-h-[min(420px,70vh)] flex flex-col rounded-2xl border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-xl overflow-hidden"
                                    :class="{
                                        'ring-2 ring-blue-500/50 ring-offset-2 ring-offset-white dark:ring-offset-zinc-900':
                                            stickerDropActive && emojiStickerTab === 'stickers',
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
                                            accept="image/png,image/jpeg,image/gif,image/webp,image/bmp,.png,.jpg,.jpeg,.gif,.webp,.bmp"
                                            multiple
                                            class="hidden"
                                            @change="onStickerUploadInputChange"
                                        />
                                        <div v-if="userStickers.length > 0" class="grid grid-cols-4 gap-2 mb-2">
                                            <button
                                                v-for="s in userStickers"
                                                :key="s.id"
                                                type="button"
                                                class="aspect-square rounded-lg overflow-hidden border border-gray-200 dark:border-zinc-700 hover:ring-2 hover:ring-blue-500/50"
                                                :title="s.name || 'Sticker'"
                                                @click="addStickerFromLibrary(s)"
                                            >
                                                <img
                                                    :src="stickerImageUrl(s.id)"
                                                    class="w-full h-full object-contain bg-gray-50 dark:bg-zinc-800"
                                                    alt=""
                                                />
                                            </button>
                                        </div>
                                        <div
                                            v-if="userStickers.length === 0"
                                            class="text-center text-sm text-gray-500 dark:text-zinc-400 mb-2 px-1"
                                        >
                                            {{ $t("stickers.empty_library") }}
                                        </div>
                                        <button
                                            type="button"
                                            class="w-full rounded-xl border-2 border-dashed border-gray-300 dark:border-zinc-600 px-3 py-3 text-left transition-colors hover:border-blue-400 hover:bg-blue-50/60 dark:hover:bg-blue-950/30"
                                            :class="
                                                stickerDropActive
                                                    ? 'border-blue-500 bg-blue-50/70 dark:bg-blue-950/40'
                                                    : ''
                                            "
                                            :disabled="isStickerUploading"
                                            @click="triggerStickerUploadInput"
                                        >
                                            <div class="flex items-start gap-2">
                                                <MaterialDesignIcon
                                                    icon-name="upload"
                                                    class="size-5 shrink-0 text-blue-500 mt-0.5"
                                                />
                                                <div class="min-w-0">
                                                    <div class="text-xs font-medium text-gray-800 dark:text-zinc-100">
                                                        {{
                                                            userStickers.length > 0
                                                                ? $t("stickers.add_more_hint")
                                                                : $t("stickers.drop_or_click_hint")
                                                        }}
                                                    </div>
                                                    <div
                                                        v-if="isStickerUploading"
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
                                    :delivery-method="newMessageDeliveryMethod"
                                    :compact="compactSendLayout"
                                    :sending-tooltip="sendMessagePathfindingTooltip"
                                    @send="sendMessage"
                                    @delivery-method-changed="newMessageDeliveryMethod = $event"
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

                        <!-- action button -->
                        <div class="flex flex-wrap gap-2 items-center mt-2">
                            <button type="button" class="attachment-action-button" @click="addFilesToMessage">
                                <MaterialDesignIcon icon-name="paperclip-plus" class="w-4 h-4" />
                                <span class="hidden sm:inline">{{ $t("messages.add_files") }}</span>
                            </button>
                            <button
                                type="button"
                                class="attachment-action-button"
                                :title="$t('messages.paste_from_clipboard')"
                                @click="pasteFromClipboard"
                            >
                                <MaterialDesignIcon icon-name="content-paste" class="w-4 h-4" />
                                <span class="hidden sm:inline">Paste</span>
                            </button>
                            <AddImageButton @add-image="onImageSelected" />
                            <AddAudioButton
                                :is-recording-audio-attachment="isRecordingAudioAttachment"
                                @start-recording="startRecordingAudioAttachment($event)"
                                @stop-recording="stopRecordingAudioAttachment"
                            >
                                <span>{{
                                    $t("messages.recording", { duration: audioAttachmentRecordingDuration })
                                }}</span>
                            </AddAudioButton>
                            <button
                                type="button"
                                class="attachment-action-button"
                                :title="$t('messages.share_location')"
                                @click="shareLocation"
                            >
                                <MaterialDesignIcon icon-name="map-marker" class="w-4 h-4" />
                                <span class="hidden sm:inline">{{ $t("messages.location") }}</span>
                            </button>
                            <button
                                type="button"
                                class="attachment-action-button"
                                :title="$t('messages.request_location')"
                                @click="requestLocation"
                            >
                                <MaterialDesignIcon icon-name="crosshairs-question" class="w-4 h-4" />
                                <span class="hidden sm:inline">{{ $t("messages.request") }}</span>
                            </button>
                            <button
                                type="button"
                                class="attachment-action-button"
                                :title="$t('messages.generate_paper_message')"
                                :disabled="!canSendMessage || isGeneratingPaperMessage"
                                @click="generatePaperMessageFromComposition"
                            >
                                <template v-if="isGeneratingPaperMessage">
                                    <div
                                        class="size-4 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"
                                    ></div>
                                    <span class="hidden sm:inline">Generating...</span>
                                </template>
                                <template v-else>
                                    <MaterialDesignIcon icon-name="qrcode-plus" class="w-4 h-4" />
                                    <span class="hidden sm:inline">LXM</span>
                                </template>
                            </button>
                            <button
                                v-if="hasTranslator && newMessageText"
                                type="button"
                                class="attachment-action-button"
                                :title="$t('translator.translate')"
                                @click="translateMessage"
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
                panel-class="z-[200]"
            >
                <ContextMenuItem @click="replyToMessage(messageContextMenu.chatItem)">
                    <MaterialDesignIcon icon-name="reply" class="size-4 text-indigo-500" />
                    Reply
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
                            v-for="(emo, emi) in columbaReactionEmojis"
                            :key="emi"
                            type="button"
                            class="text-lg leading-none px-1.5 py-0.5 rounded-lg hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                            :title="emo"
                            @click="sendReactionEmojiFromMenu(messageContextMenu.chatItem, emo)"
                        >
                            {{ emo }}
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
                        <div class="flex-shrink-0">
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
                        class="w-full bg-white dark:bg-zinc-900 border-2 border-gray-100 dark:border-zinc-800 text-gray-900 dark:text-zinc-100 text-base rounded-3xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 pl-12 pr-4 py-4 shadow-sm transition-all placeholder:text-gray-400 dark:placeholder:text-zinc-600 font-medium"
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
            class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 dark:bg-black/90 backdrop-blur-sm p-4 outline-none"
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
            class="fixed inset-0 z-[150] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
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
                <div class="p-0 overflow-y-auto bg-gray-50 dark:bg-zinc-950 flex-grow">
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
                                class="text-sm font-mono break-all text-gray-900 dark:text-zinc-200 bg-white dark:bg-zinc-900 p-2 rounded border border-gray-100 dark:border-zinc-800"
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
                                class="text-xs font-mono bg-white dark:bg-zinc-900 p-3 rounded border border-gray-100 dark:border-zinc-800 whitespace-pre-wrap break-all text-gray-800 dark:text-zinc-300"
                            >
                                {{ rawMessageData.content }}
                            </div>
                        </div>

                        <div v-if="rawMessageData.raw_uri" class="space-y-1">
                            <label
                                class="text-[10px] font-bold uppercase tracking-wider text-gray-400 dark:text-zinc-500"
                                >Raw LXMF URI</label
                            >
                            <div
                                class="text-[10px] font-mono bg-white dark:bg-zinc-900 p-2 rounded border border-gray-100 dark:border-zinc-800 break-all text-gray-600 dark:text-zinc-400"
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
                                    JSON.stringify(rawMessageData, null, 2)
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
import DialogUtils from "../../js/DialogUtils";
import MicrophoneRecorder from "../../js/MicrophoneRecorder";
import WebSocketConnection from "../../js/WebSocketConnection";
import AddAudioButton from "./AddAudioButton.vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);
import SendMessageButton from "./SendMessageButton.vue";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ContextMenuDivider from "../contextmenu/ContextMenuDivider.vue";
import ContextMenuItem from "../contextmenu/ContextMenuItem.vue";
import ContextMenuPanel from "../contextmenu/ContextMenuPanel.vue";
import ConversationDropDownMenu from "./ConversationDropDownMenu.vue";
import AddImageButton from "./AddImageButton.vue";
import AudioWaveformPlayer from "./AudioWaveformPlayer.vue";
import IconButton from "../IconButton.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import GlobalEmitter from "../../js/GlobalEmitter";
import ToastUtils from "../../js/ToastUtils";
import PaperMessageModal from "./PaperMessageModal.vue";
import GlobalState from "../../js/GlobalState";
import MarkdownRenderer from "../../js/MarkdownRenderer";
import { COLUMBA_REACTION_EMOJIS, mergeLxmfReactionRowsIntoMessages } from "../../js/lxmfReactions";
import { createOutboundQueue } from "../../js/outboundSendQueue";
import emojiPickerEnDataUrl from "emoji-picker-element-data/en/emojibase/data.json?url";
import "emoji-picker-element";

export default {
    name: "ConversationViewer",
    components: {
        IconButton,
        AddImageButton,
        ContextMenuDivider,
        ContextMenuItem,
        ContextMenuPanel,
        ConversationDropDownMenu,
        MaterialDesignIcon,
        SendMessageButton,
        AddAudioButton,
        AudioWaveformPlayer,
        PaperMessageModal,
        LxmfUserIcon,
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
            },
            columbaReactionEmojis: COLUMBA_REACTION_EMOJIS,
            userStickers: [],
            isStickerPickerOpen: false,
            emojiStickerTab: "emoji",
            emojiPickerDataUrl: emojiPickerEnDataUrl,
            stickerDropActive: false,
            composerImageDropActive: false,
            isStickerUploading: false,
            now: Date.now(),
            updateTimer: null,
            sendStatusUiMs: Date.now(),
            sendStatusTickInterval: null,
            windowWidth: typeof window !== "undefined" ? window.innerWidth : 1024,
            peerHeaderCompact: false,
            peerHeaderResizeObserver: null,
        };
    },
    computed: {
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
        usesThemeOutboundBubbleColor() {
            const c = GlobalState?.config?.message_outbound_bubble_color;
            if (c == null || String(c).trim() === "") {
                return true;
            }
            return String(c).trim().toLowerCase() === "#4f46e5";
        },
        bubbleStyles() {
            void GlobalState.detailedOutboundSendStatus;
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
                return "Finding path to peer (Reticulum is resolving a route). Your message sends as soon as the route is ready. Hover status icons in the bubble for details.";
            }
            return this.$t("messages.sending_ellipsis");
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
                return this.chatItems.filter((chatItem) => {
                    if (chatItem.type === "lxmf_message") {
                        const isFromSelectedPeer =
                            chatItem.lxmf_message.source_hash === this.selectedPeer.destination_hash;
                        const isToSelectedPeer =
                            chatItem.lxmf_message.destination_hash === this.selectedPeer.destination_hash;

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
            return this.chatItems
                .filter((chatItem) => {
                    if (chatItem.type === "lxmf_message") {
                        const isFromSelectedPeer =
                            chatItem.lxmf_message.source_hash === this.selectedPeer.destination_hash;
                        const isToSelectedPeer =
                            chatItem.lxmf_message.destination_hash === this.selectedPeer.destination_hash;

                        if (!(isFromSelectedPeer || isToSelectedPeer)) return false;

                        return this.isTelemetryOnly(chatItem.lxmf_message);
                    }
                    return false;
                })
                .reverse();
        },
        selectedPeerChatItemsReversed() {
            // ensure a copy of the array is returned in reverse order
            return this.selectedPeerChatItems.map((message) => message).reverse();
        },
        selectedPeerChatDisplayGroups() {
            const reversed = this.selectedPeerChatItemsReversed;
            const groups = [];
            let i = 0;
            while (i < reversed.length) {
                const item = reversed[i];
                if (this.canMergeImageIntoImageStrip(item)) {
                    const run = [item];
                    let j = i + 1;
                    while (j < reversed.length && run.length < 12) {
                        const next = reversed[j];
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
                        i = j;
                        continue;
                    }
                }
                groups.push({
                    type: "single",
                    chatItem: item,
                    key: item.lxmf_message.hash,
                });
                i++;
            }
            return groups;
        },
        oldestMessageId() {
            if (this.selectedPeerChatItems.length > 0) {
                return this.selectedPeerChatItems[0].lxmf_message.id;
            }

            return null;
        },
        hasFailedOrCancelledMessages() {
            return this.selectedPeerChatItems.some(
                (item) => item.is_outbound && ["failed", "cancelled"].includes(item.lxmf_message?.state)
            );
        },
        telemetryBatteryHistory() {
            return this.selectedPeerTelemetryItems
                .filter((item) => item.lxmf_message.fields?.telemetry?.battery)
                .map((item) => ({
                    x: item.lxmf_message.timestamp,
                    y: item.lxmf_message.fields.telemetry.battery.charge_percent,
                }))
                .sort((a, b) => a.x - b.x);
        },
        batterySparklinePath() {
            const history = this.telemetryBatteryHistory;
            if (history.length < 2) return "";

            const minX = history[0].x;
            const maxX = history[history.length - 1].x;
            const rangeX = maxX - minX || 1;

            return history
                .map((p, i) => {
                    const x = ((p.x - minX) / rangeX) * 100;
                    const y = 100 - p.y; // SVG y is top-down
                    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
                })
                .join(" ");
        },
    },
    watch: {
        selectedPeer: {
            handler(newPeer, oldPeer) {
                if (oldPeer) {
                    this.saveDraft(oldPeer.destination_hash);
                }
                this.teardownPeerHeaderResizeObserver();
                if (!newPeer) {
                    this.peerHeaderCompact = false;
                }
                this.checkIfSelectedPeerBlocked();
                this.strangerBannerDismissed = false;
                this.checkIfStrangerPeer();
                this.initialLoad();
                if (newPeer) {
                    this.loadDraft(newPeer.destination_hash);
                    this.$nextTick(() => this.setupPeerHeaderResizeObserver());
                }
            },
            immediate: true,
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
    },
    beforeUnmount() {
        this.teardownPeerHeaderResizeObserver();
        if (this.selectedPeer) {
            this.saveDraft(this.selectedPeer.destination_hash);
        }
        if (this._onWindowResize) {
            window.removeEventListener("resize", this._onWindowResize);
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
    },
    methods: {
        setupPeerHeaderResizeObserver() {
            this.teardownPeerHeaderResizeObserver();
            const el = this.$refs.conversationPeerHeader;
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
            if (this.getParsedItems(chatItem)?.isOnlyPaperMessage) {
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
        handleMessageClick(event) {
            const nomadnetLink = event.target.closest(".nomadnet-link");
            if (nomadnetLink) {
                event.preventDefault();
                const url = nomadnetLink.getAttribute("data-nomadnet-url");
                if (url) {
                    const [hash, ...pathParts] = url.split(":");
                    const path = pathParts.join(":");
                    const routeName = this.$route.meta.isPopout ? "nomadnetwork-popout" : "nomadnetwork";
                    this.$router.push({
                        name: routeName,
                        params: { destinationHash: hash },
                        query: { path: path },
                    });
                }
            }

            const lxmfLink = event.target.closest(".lxmf-link");
            if (lxmfLink) {
                event.preventDefault();
                const address = lxmfLink.getAttribute("data-lxmf-address");
                if (address) {
                    this.$router.push({
                        name: "messages",
                        params: { destinationHash: address },
                    });
                }
            }
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
            try {
                await navigator.clipboard.writeText(this.myLxmfAddressHash);
                ToastUtils.success(this.$t("messages.address_copied"));
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("messages.failed_copy_address"));
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
            if (!this.config?.translator_enabled) {
                this.hasTranslator = false;
                return;
            }
            try {
                const response = await window.api.get("/api/v1/translator/languages");
                this.translatorLanguages = response.data.languages || [];
                this.hasTranslator = this.translatorLanguages.length > 0;
            } catch (e) {
                console.log("Failed to check translator:", e);
                this.hasTranslator = false;
            }
        },
        async translateMessage() {
            if (!this.newMessageText || this.isTranslatingMessage) return;

            try {
                this.isTranslatingMessage = true;
                const targetLang = this.$i18n.locale || "en";
                const response = await window.api.post("/api/v1/translator/translate", {
                    text: this.newMessageText,
                    source_lang: "auto",
                    target_lang: targetLang,
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
            } finally {
                this.isTranslatingMessage = false;
            }
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
                        remote_identity_hash: this.selectedPeer.destination_hash,
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
            this.warmPathToPeer();

            // mark as read
            this.markConversationAsRead(this.selectedPeer);

            // load 1 page of previous messages
            await this.loadPrevious();

            // scroll to bottom
            this.scrollMessagesToBottom();

            // auto load audio
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

                // do nothing if response is for a previous request
                if (seq !== this.lxmfMessagesRequestSequence) {
                    console.log("ignoring response for previous lxmf messages request");
                    return;
                }

                // convert lxmf messages to chat items
                const chatItems = [];
                const lxmfMessages = mergeLxmfReactionRowsIntoMessages(response.data.lxmf_messages);
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
            if (destinationHash.startsWith("lxmf@")) {
                destinationHash = destinationHash.replace("lxmf@", "");
            }
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
        onLxmfMessageReceived(lxmfMessage) {
            if (lxmfMessage.source_hash !== this.selectedPeer?.destination_hash) {
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
            if (lxmfMessage.destination_hash !== this.selectedPeer?.destination_hash) {
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
            const chatItemIndex = this.chatItems.findIndex(
                (chatItem) => chatItem.lxmf_message?.hash === lxmfMessageHash
            );
            if (chatItemIndex === -1) {
                return;
            }

            this.chatItems[chatItemIndex].lxmf_message = {
                ...this.chatItems[chatItemIndex].lxmf_message,
                ...lxmfMessage,
            };
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
                    const response = await window.api.get(
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
            if (index !== -1) {
                const el = document.getElementById(`message-${hash}`);
                if (el) {
                    el.scrollIntoView({ behavior: "smooth", block: "center" });
                    // briefly highlight
                    el.classList.add("ring-2", "ring-blue-500", "ring-offset-2");
                    setTimeout(() => {
                        el.classList.remove("ring-2", "ring-blue-500", "ring-offset-2");
                    }, 2000);
                }
            } else {
                DialogUtils.alert(this.$t("messages.message_not_found_in_cache"));
            }
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
        onMessageContextMenu(event, chatItem) {
            this.messageContextMenu.chatItem = chatItem;
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
            try {
                // we'll try to get the URI first as it contains the raw signed message
                const response = await window.api.get(`/api/v1/lxmf-messages/${chatItem.lxmf_message.hash}/uri`);
                this.rawMessageData = {
                    ...chatItem.lxmf_message,
                    raw_uri: response.data.uri,
                };
            } catch {
                // if URI is not available (message no longer in router), we show what we have
                this.rawMessageData = { ...chatItem.lxmf_message };
            }
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
        pendingOutboundImageSrc(chatItem) {
            const prev = chatItem.lxmf_message?.fields?.image?._preview_url;
            if (prev) {
                return prev;
            }
            return this.lxmfImageUrl(chatItem.lxmf_message.hash);
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
                return "Finding path: Reticulum is resolving a route to this peer. Your message sends when the route is ready.";
            }
            if (lxmfMessage.state === "generating") {
                return "Preparing message…";
            }
            if (lxmfMessage.state === "sending" && (lxmfMessage.progress ?? 0) > 0) {
                return `Sending… ${Number(lxmfMessage.progress).toFixed(0)}%`;
            }
            if (lxmfMessage.state === "sending") {
                return "Sending…";
            }
            return "Pending";
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
                return "shadow-sm";
            }
            return "shadow-sm bg-sky-100 text-slate-900 border border-sky-200/90 dark:bg-sky-950/45 dark:text-sky-50 dark:border-sky-800/55";
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
            return "text-white/90";
        },
        outboundSendingStatusIconClass(chatItem) {
            if (this.isOutboundWaitingBubble(chatItem)) {
                return "text-gray-600 dark:text-zinc-400";
            }
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-700 dark:text-sky-300";
            }
            return "text-white/90";
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
            return "text-white/90";
        },
        outboundBubblePendingCheckIconClass(chatItem) {
            if (this.isThemeOutboundBubble(chatItem)) {
                return "text-sky-700 dark:text-sky-300 opacity-50";
            }
            return "text-white/90 opacity-50";
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
                return "Finding path";
            }
            if (lxmfMessage.state === "generating") {
                return "Preparing message";
            }
            if (lxmfMessage.state === "sending" && (lxmfMessage.progress ?? 0) > 0) {
                return `Sending ${Number(lxmfMessage.progress).toFixed(0)}%`;
            }
            if (lxmfMessage.state === "sending") {
                return "Sending";
            }
            if (lxmfMessage.state === "outbound") {
                return "Outbound";
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
            return "Failed";
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
                await window.api.post(`/api/v1/destination/${this.selectedPeer.destination_hash}/request-path`);
            } catch (e) {
                console.log(e);
            }
        },
        imageGroupGalleryUrls(items) {
            return this.imageGroupSortedChron(items).map((it) => this.lxmfImageUrl(it.lxmf_message.hash));
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
                audioTotalSize = this.newMessageAudio.size;
                fields["audio"] = {
                    audio_mode: this.newMessageAudio.audio_mode,
                    audio_size: this.newMessageAudio.size,
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
                    const pendingHash = `pending-${crypto.randomUUID()}`;
                    job.pendingHash = pendingHash;
                    const pendingFields = {};
                    if (job.images.length > 0) {
                        pendingFields.image = {
                            image_type: job.images[0].image_type,
                            image_size: job.images[0].image_size,
                            _preview_url: job.imagePreviewUrls[0],
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
        isTelemetryOnly(msg) {
            const hasContent = msg.content && msg.content.trim() !== "";
            const hasAttachments = msg.fields?.image || msg.fields?.audio || msg.fields?.file_attachments;
            const hasTelemetry = msg.fields?.telemetry || msg.fields?.telemetry_stream;
            const hasCommands = msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"]);

            return !hasContent && !hasAttachments && (hasTelemetry || hasCommands);
        },
        hasRenderableContent(msg) {
            if (msg.content && msg.content.trim() !== "") return true;
            if (msg.fields?.image) return true;
            if (msg.fields?.audio) return true;
            if (msg.fields?.file_attachments) return true;
            if (msg.fields?.telemetry || msg.fields?.telemetry_stream) return true;
            if (msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"] || c["1"] || c["0x1"])) return true;
            return false;
        },
        isImageOnlyMessage(chatItem) {
            const msg = chatItem.lxmf_message;
            if (!msg.fields?.image) return false;
            if (msg.fields?.audio || msg.fields?.file_attachments) return false;
            const content = (msg.content || "").trim();
            if (content && !this.shouldHideAutoImageCaption(chatItem)) return false;
            if (msg.reply_to_hash) return false;
            if (msg.fields?.telemetry || msg.fields?.telemetry_stream) return false;
            if (msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"] || c["1"] || c["0x1"])) return false;
            return true;
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
        formatDestinationHash(hash) {
            return Utils.formatDestinationHash(hash);
        },
        async copyHash(hash) {
            try {
                await navigator.clipboard.writeText(hash);
                ToastUtils.success(this.$t("messages.hash_copied"));
            } catch (e) {
                console.error(e);
                ToastUtils.error(this.$t("messages.failed_to_copy_hash"));
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
            if (!dt) {
                return [];
            }
            const out = [];
            const seen = new Set();
            const pushIfImage = (f) => {
                if (!f?.type?.startsWith("image/")) {
                    return;
                }
                const k = `${f.name}:${f.size}:${f.lastModified}`;
                if (seen.has(k)) {
                    return;
                }
                seen.add(k);
                out.push(f);
            };
            if (dt.files?.length) {
                for (let i = 0; i < dt.files.length; i++) {
                    pushIfImage(dt.files[i]);
                }
                if (out.length > 0) {
                    return out;
                }
            }
            if (dt.items?.length) {
                for (let i = 0; i < dt.items.length; i++) {
                    const item = dt.items[i];
                    if (item.kind === "file" && item.type?.startsWith("image/")) {
                        const f = item.getAsFile();
                        pushIfImage(f);
                    }
                }
            }
            return out;
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
            const cd = event.clipboardData;
            if (!cd?.items?.length) {
                return;
            }
            const imageBlobs = [];
            for (let i = 0; i < cd.items.length; i++) {
                const item = cd.items[i];
                if (item.kind === "file" && item.type.startsWith("image/")) {
                    const f = item.getAsFile();
                    if (f) {
                        imageBlobs.push(f);
                    }
                }
            }
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
            try {
                const text = await navigator.clipboard.readText();
                if (text) {
                    const input = this.$refs["message-input"];
                    const start = input.selectionStart;
                    const end = input.selectionEnd;
                    const currentText = this.newMessageText || "";
                    this.newMessageText = currentText.substring(0, start) + text + currentText.substring(end);

                    this.$nextTick(() => {
                        input.focus();
                        const newCursorPos = start + text.length;
                        input.setSelectionRange(newCursorPos, newCursorPos);
                        // adjust height
                        input.style.height = "auto";
                        input.style.height = Math.min(input.scrollHeight, 200) + "px";
                    });
                }
            } catch (err) {
                console.error("Failed to read clipboard contents: ", err);
                ToastUtils.error(this.$t("messages.failed_read_clipboard"));
            }
        },
        onFileInputChange: function (event) {
            for (const file of event.target.files) {
                this.newMessageFiles.push(file);
            }
        },
        clearFileInput: function () {
            this.$refs["file-input"].value = null;
        },
        async removeImageAttachment(index) {
            // ask user to confirm removing image attachment
            if (!(await DialogUtils.confirm(this.$t("messages.remove_image_confirm")))) {
                return;
            }

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
            };
            if (map[m]) {
                return map[m];
            }
            const ext = (name.split(".").pop() || "").toLowerCase();
            const extMap = { png: "png", jpg: "jpeg", jpeg: "jpeg", gif: "gif", webp: "webp", bmp: "bmp" };
            return extMap[ext] || null;
        },
        async uploadStickerImageFiles(fileList) {
            const maxBytes = 512 * 1024;
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
                    if (file.size > maxBytes) {
                        ToastUtils.error(this.$t("stickers.file_too_large"));
                        failed++;
                        continue;
                    }
                    const imageType = this.mimeToStickerType(file.type, file.name);
                    if (!imageType) {
                        ToastUtils.error(this.$t("stickers.unsupported_type"));
                        failed++;
                        continue;
                    }
                    try {
                        const buf = await file.arrayBuffer();
                        const imageBytes = Utils.arrayBufferToBase64(buf);
                        await window.api.post("/api/v1/stickers", {
                            image_bytes: imageBytes,
                            image_type: imageType,
                            name: null,
                        });
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
                        DialogUtils.alert(this.$t("messages.failed_start_recording"));
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
                        DialogUtils.alert(this.$t("messages.failed_start_recording"));
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
            if (!(await DialogUtils.confirm(this.$t("messages.remove_audio_confirm")))) {
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
    @apply inline-flex items-center gap-1 rounded-full border border-gray-200 px-3 py-1.5 text-xs font-bold text-gray-700 bg-white shadow-sm transition-all !important;
}
.attachment-action-button:hover {
    @apply bg-gray-50 text-gray-900 border-blue-400 !important;
}
.dark .attachment-action-button {
    @apply border-zinc-700 text-zinc-100 bg-zinc-900 !important;
}
.dark .attachment-action-button:hover {
    @apply bg-zinc-800 text-white border-blue-500 !important;
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
</style>
