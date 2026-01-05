<template>
    <div class="flex flex-col w-full sm:w-80 sm:min-w-80">
        <!-- tabs -->
        <div class="bg-transparent border-b border-r border-gray-200/70 dark:border-zinc-700/80 backdrop-blur">
            <div class="-mb-px flex">
                <div
                    class="w-full border-b-2 py-3 px-1 text-center text-sm font-semibold tracking-wide uppercase cursor-pointer transition"
                    :class="[
                        tab === 'conversations'
                            ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-300'
                            : 'border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:hover:border-zinc-600 hover:text-gray-700 dark:hover:text-gray-200',
                    ]"
                    @click="tab = 'conversations'"
                >
                    {{ $t("messages.conversations") }}
                </div>
                <div
                    class="w-full border-b-2 py-3 px-1 text-center text-sm font-semibold tracking-wide uppercase cursor-pointer transition"
                    :class="[
                        tab === 'announces'
                            ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-300'
                            : 'border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:hover:border-zinc-600 hover:text-gray-700 dark:hover:text-gray-200',
                    ]"
                    @click="tab = 'announces'"
                >
                    {{ $t("messages.announces") }}
                </div>
            </div>
        </div>

        <!-- conversations -->
        <div
            v-if="tab === 'conversations'"
            class="flex-1 flex flex-col bg-white dark:bg-zinc-950 border-r border-gray-200 dark:border-zinc-700 overflow-hidden min-h-0"
        >
            <!-- Folders Section -->
            <div class="border-b border-gray-200 dark:border-zinc-700 bg-gray-50/50 dark:bg-zinc-900/50">
                <div
                    class="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors"
                    @click="foldersExpanded = !foldersExpanded"
                >
                    <div class="flex items-center gap-2">
                        <MaterialDesignIcon
                            :icon-name="foldersExpanded ? 'chevron-down' : 'chevron-right'"
                            class="size-4 text-gray-400"
                        />
                        <span class="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-zinc-500">
                            Folders
                        </span>
                    </div>
                    <div class="flex gap-1" @click.stop>
                        <button
                            type="button"
                            class="p-1 text-gray-400 hover:text-blue-500 hover:bg-gray-200/50 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                            title="Create Folder"
                            @click="createFolder"
                        >
                            <MaterialDesignIcon icon-name="folder-plus-outline" class="size-4" />
                        </button>
                        <div class="relative">
                            <button
                                type="button"
                                class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-zinc-300 hover:bg-gray-200/50 dark:hover:bg-zinc-800 rounded-lg transition-colors"
                                @click="folderMenu.show = !folderMenu.show"
                            >
                                <MaterialDesignIcon icon-name="dots-vertical" class="size-4" />
                            </button>
                            <div
                                v-if="folderMenu.show"
                                v-click-outside="{ handler: () => (folderMenu.show = false), capture: true }"
                                class="absolute right-0 top-full mt-1 z-[60] min-w-[160px] bg-white dark:bg-zinc-800 rounded-xl shadow-xl border border-gray-200 dark:border-zinc-700 py-1 overflow-hidden animate-in fade-in zoom-in duration-100"
                            >
                                <button
                                    type="button"
                                    class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                                    @click="
                                        $emit('export-folders');
                                        folderMenu.show = false;
                                    "
                                >
                                    <MaterialDesignIcon icon-name="export" class="size-4" />
                                    <span>Export Folders</span>
                                </button>
                                <button
                                    type="button"
                                    class="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                                    @click="
                                        $emit('import-folders');
                                        folderMenu.show = false;
                                    "
                                >
                                    <MaterialDesignIcon icon-name="import" class="size-4" />
                                    <span>Import Folders</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div v-if="foldersExpanded" class="flex flex-col max-h-48 overflow-y-auto pb-1">
                    <div
                        class="px-3 py-1.5 flex items-center gap-2 cursor-pointer transition-colors text-sm"
                        :class="[
                            selectedFolderId === null
                                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 font-semibold'
                                : 'text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800',
                            dragOverFolderId === 'all'
                                ? 'ring-2 ring-blue-500 ring-inset bg-blue-50 dark:bg-blue-900/20'
                                : '',
                        ]"
                        @click="$emit('folder-click', null)"
                        @dragover="onDragOver($event, 'all')"
                        @dragleave="onDragLeave"
                        @drop="onDropOnFolder($event, null)"
                    >
                        <MaterialDesignIcon icon-name="inbox-outline" class="size-4" />
                        <span class="truncate flex-1">All Messages</span>
                    </div>
                    <div
                        class="px-3 py-1.5 flex items-center gap-2 cursor-pointer transition-colors text-sm"
                        :class="[
                            selectedFolderId === 0
                                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 font-semibold'
                                : 'text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800',
                            dragOverFolderId === 0
                                ? 'ring-2 ring-blue-500 ring-inset bg-blue-50 dark:bg-blue-900/20'
                                : '',
                        ]"
                        @click="$emit('folder-click', 0)"
                        @dragover="onDragOver($event, 0)"
                        @dragleave="onDragLeave"
                        @drop="onDropOnFolder($event, 0)"
                    >
                        <MaterialDesignIcon icon-name="folder-outline" class="size-4" />
                        <span class="truncate flex-1">Uncategorized</span>
                    </div>
                    <div
                        v-for="folder in folders"
                        :key="folder.id"
                        class="group px-3 py-1.5 flex items-center gap-2 cursor-pointer transition-colors text-sm"
                        :class="[
                            selectedFolderId === folder.id
                                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400 font-semibold'
                                : 'text-gray-600 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800',
                            dragOverFolderId === folder.id
                                ? 'ring-2 ring-blue-500 ring-inset bg-blue-50 dark:bg-blue-900/20'
                                : '',
                        ]"
                        @click="$emit('folder-click', folder.id)"
                        @dragover="onDragOver($event, folder.id)"
                        @dragleave="onDragLeave"
                        @drop="onDropOnFolder($event, folder.id)"
                    >
                        <MaterialDesignIcon icon-name="folder" class="size-4" />
                        <span class="truncate flex-1">{{ folder.name }}</span>
                        <div class="hidden group-hover:flex items-center gap-0.5">
                            <button
                                type="button"
                                class="p-1 hover:text-blue-500 hover:bg-white dark:hover:bg-zinc-700 rounded-lg transition-colors"
                                @click.stop="renameFolder(folder)"
                            >
                                <MaterialDesignIcon icon-name="pencil-outline" class="size-3.5" />
                            </button>
                            <button
                                type="button"
                                class="p-1 hover:text-red-500 hover:bg-white dark:hover:bg-zinc-700 rounded-lg transition-colors"
                                @click.stop="deleteFolder(folder)"
                            >
                                <MaterialDesignIcon icon-name="trash-can-outline" class="size-3.5" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- search + filters -->
            <div
                v-if="conversations.length > 0 || isFilterActive"
                class="p-1 border-b border-gray-300 dark:border-zinc-700 space-y-2"
            >
                <div class="flex gap-1">
                    <input
                        :value="conversationSearchTerm"
                        type="text"
                        :placeholder="$t('messages.search_placeholder', { count: conversations.length })"
                        class="input-field flex-1"
                        @input="onConversationSearchInput"
                    />
                    <button
                        type="button"
                        class="p-2 bg-gray-100 dark:bg-zinc-800 text-gray-500 dark:text-gray-400 rounded-lg hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
                        title="Selection Mode"
                        :class="{ 'text-blue-500 bg-blue-50 dark:bg-blue-900/20': selectionMode }"
                        @click="toggleSelectionMode"
                    >
                        <MaterialDesignIcon icon-name="checkbox-multiple-marked-outline" class="size-5" />
                    </button>
                    <button
                        type="button"
                        class="p-2 bg-gray-100 dark:bg-zinc-800 text-gray-500 dark:text-gray-400 rounded-lg hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors"
                        title="Ingest Paper Message"
                        @click="openIngestPaperMessageModal"
                    >
                        <MaterialDesignIcon icon-name="qrcode-scan" class="size-5" />
                    </button>
                </div>
                <div
                    v-if="selectionMode"
                    class="flex items-center justify-between px-2 py-1 bg-blue-50 dark:bg-blue-900/10 rounded-lg"
                >
                    <div class="flex items-center gap-2">
                        <input
                            type="checkbox"
                            :checked="allSelected"
                            class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            @change="toggleSelectAll"
                        />
                        <span class="text-xs font-semibold text-blue-700 dark:text-blue-400">
                            {{ selectedHashes.size }} selected
                        </span>
                    </div>
                    <div class="flex gap-2">
                        <button
                            type="button"
                            class="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline"
                            @click="bulkMarkAsRead"
                        >
                            Mark as read
                        </button>
                        <button
                            type="button"
                            class="text-xs font-bold text-red-600 dark:text-red-400 hover:underline"
                            @click="bulkDelete"
                        >
                            Delete
                        </button>
                        <div class="relative">
                            <button
                                type="button"
                                class="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline"
                                @click="moveMenu.show = !moveMenu.show"
                            >
                                Move to
                            </button>
                            <div
                                v-if="moveMenu.show"
                                v-click-outside="{ handler: () => (moveMenu.show = false), capture: true }"
                                class="absolute right-0 top-full mt-1 z-[60] min-w-[160px] bg-white dark:bg-zinc-800 rounded-xl shadow-xl border border-gray-200 dark:border-zinc-700 py-1 overflow-hidden animate-in fade-in zoom-in duration-100"
                            >
                                <button
                                    type="button"
                                    class="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                                    @click="moveSelectedToFolder(null)"
                                >
                                    Uncategorized
                                </button>
                                <button
                                    v-for="folder in folders"
                                    :key="folder.id"
                                    type="button"
                                    class="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-colors"
                                    @click="moveSelectedToFolder(folder.id)"
                                >
                                    {{ folder.name }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="flex flex-wrap gap-1">
                    <button type="button" :class="filterChipClasses(filterUnreadOnly)" @click="toggleFilter('unread')">
                        {{ $t("messages.unread") }}
                    </button>
                    <button type="button" :class="filterChipClasses(filterFailedOnly)" @click="toggleFilter('failed')">
                        {{ $t("messages.failed") }}
                    </button>
                    <button
                        type="button"
                        :class="filterChipClasses(filterHasAttachmentsOnly)"
                        @click="toggleFilter('attachments')"
                    >
                        {{ $t("messages.attachments") }}
                    </button>
                </div>
            </div>

            <!-- conversations -->
            <div class="flex h-full overflow-y-auto" @scroll="onConversationsScroll">
                <div v-if="isLoading" class="w-full divide-y divide-gray-100 dark:divide-zinc-800">
                    <div v-for="i in 6" :key="i" class="p-3 animate-pulse">
                        <div class="flex gap-3">
                            <div class="size-10 rounded bg-gray-200 dark:bg-zinc-800"></div>
                            <div class="flex-1 space-y-2 py-1">
                                <div class="h-2 bg-gray-200 dark:bg-zinc-800 rounded w-3/4"></div>
                                <div class="h-2 bg-gray-200 dark:bg-zinc-800 rounded w-1/2"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div v-else-if="displayedConversations.length > 0" class="w-full">
                    <div
                        v-for="conversation of displayedConversations"
                        :key="conversation.destination_hash"
                        v-memo="[
                            conversation.destination_hash,
                            conversation.updated_at,
                            conversation.is_unread,
                            conversation.failed_messages_count,
                            selectedDestinationHash === conversation.destination_hash,
                            GlobalState.config.banished_effect_enabled && isBlocked(conversation.destination_hash),
                            selectionMode,
                            selectedHashes.has(conversation.destination_hash),
                        ]"
                        class="flex cursor-pointer p-2 border-l-2 relative group conversation-item"
                        :class="[
                            conversation.destination_hash === selectedDestinationHash
                                ? 'bg-gray-100 dark:bg-zinc-700 border-blue-500 dark:border-blue-400'
                                : 'bg-white dark:bg-zinc-950 border-transparent hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-gray-200 dark:hover:border-zinc-600',
                            selectedHashes.has(conversation.destination_hash)
                                ? 'bg-blue-50/50 dark:bg-blue-900/10'
                                : '',
                        ]"
                        draggable="true"
                        @click="
                            selectionMode
                                ? toggleSelectConversation(conversation.destination_hash)
                                : onConversationClick(conversation)
                        "
                        @contextmenu="onRightClick($event, conversation.destination_hash)"
                        @dragstart="onDragStart($event, conversation.destination_hash)"
                    >
                        <!-- Selection Checkbox -->
                        <div v-if="selectionMode" class="my-auto mr-3 px-1">
                            <input
                                type="checkbox"
                                :checked="selectedHashes.has(conversation.destination_hash)"
                                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                @click.stop
                                @change="toggleSelectConversation(conversation.destination_hash)"
                            />
                        </div>

                        <!-- banished overlay -->
                        <div
                            v-if="
                                GlobalState.config.banished_effect_enabled && isBlocked(conversation.destination_hash)
                            "
                            class="banished-overlay"
                            :style="{ background: GlobalState.config.banished_color + '33' }"
                        >
                            <span
                                class="banished-text !text-[10px] !opacity-100 !tracking-widest !border !px-1 !py-0.5 !text-white !shadow-lg"
                                :style="{ 'background-color': GlobalState.config.banished_color }"
                                >{{ GlobalState.config.banished_text }}</span
                            >
                        </div>

                        <div class="my-auto mr-2">
                            <LxmfUserIcon
                                :custom-image="conversation.contact_image"
                                :icon-name="conversation.lxmf_user_icon ? conversation.lxmf_user_icon.icon_name : ''"
                                :icon-foreground-colour="
                                    conversation.lxmf_user_icon ? conversation.lxmf_user_icon.foreground_colour : ''
                                "
                                :icon-background-colour="
                                    conversation.lxmf_user_icon ? conversation.lxmf_user_icon.background_colour : ''
                                "
                                icon-class="size-7"
                            />
                        </div>
                        <div class="mr-auto w-full pr-2 min-w-0">
                            <div class="flex justify-between gap-2 min-w-0">
                                <div
                                    class="text-gray-900 dark:text-gray-100 truncate min-w-0"
                                    :title="conversation.custom_display_name ?? conversation.display_name"
                                    :class="{
                                        'font-semibold':
                                            (conversation.is_unread &&
                                                conversation.destination_hash !== selectedDestinationHash) ||
                                            conversation.failed_messages_count > 0,
                                    }"
                                >
                                    {{ conversation.custom_display_name ?? conversation.display_name }}
                                </div>
                                <div class="text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap flex-shrink-0">
                                    {{ formatTimeAgo(conversation.updated_at) }}
                                </div>
                            </div>
                            <div class="text-gray-600 dark:text-gray-400 text-xs mt-0.5 truncate">
                                {{
                                    conversation.latest_message_preview ??
                                    conversation.latest_message_title ??
                                    "No messages yet"
                                }}
                            </div>
                        </div>
                        <div class="flex items-center space-x-1">
                            <div v-if="conversation.has_attachments" class="text-gray-500 dark:text-gray-300">
                                <MaterialDesignIcon icon-name="paperclip" class="w-4 h-4" />
                            </div>
                            <div
                                v-if="
                                    conversation.is_unread && conversation.destination_hash !== selectedDestinationHash
                                "
                                class="my-auto ml-1"
                            >
                                <div class="bg-blue-500 dark:bg-blue-400 rounded-full p-1"></div>
                            </div>
                            <div v-else-if="conversation.failed_messages_count" class="my-auto ml-1">
                                <div class="bg-red-500 dark:bg-red-400 rounded-full p-1"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Context Menu -->
                    <div
                        v-if="contextMenu.show"
                        v-click-outside="{ handler: () => (contextMenu.show = false), capture: true }"
                        class="fixed z-[100] min-w-[200px] bg-white dark:bg-zinc-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-zinc-700 py-1.5 overflow-hidden animate-in fade-in zoom-in duration-100"
                        :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
                    >
                        <button
                            type="button"
                            class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-zinc-300 hover:bg-gray-100 dark:hover:bg-zinc-700 transition-all active:scale-95"
                            @click="bulkMarkAsRead"
                        >
                            <MaterialDesignIcon icon-name="email-open-outline" class="size-4 text-gray-400" />
                            <span class="font-medium">Mark as Read</span>
                        </button>
                        <div class="border-t border-gray-100 dark:border-zinc-700 my-1.5 mx-2"></div>
                        <div
                            class="px-4 py-1.5 text-[10px] font-black text-gray-400 dark:text-zinc-500 uppercase tracking-widest"
                        >
                            Move to Folder
                        </div>
                        <button
                            type="button"
                            class="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 dark:hover:text-blue-400 transition-all active:scale-95"
                            @click="moveSelectedToFolder(null)"
                        >
                            <MaterialDesignIcon icon-name="inbox-arrow-down" class="size-4 opacity-70" />
                            <span>Uncategorized</span>
                        </button>
                        <div class="max-h-[200px] overflow-y-auto custom-scrollbar">
                            <button
                                v-for="folder in folders"
                                :key="folder.id"
                                type="button"
                                class="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 dark:text-zinc-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 dark:hover:text-blue-400 transition-all active:scale-95"
                                @click="moveSelectedToFolder(folder.id)"
                            >
                                <MaterialDesignIcon icon-name="folder" class="size-4 opacity-70" />
                                <span class="truncate">{{ folder.name }}</span>
                            </button>
                        </div>
                        <div class="border-t border-gray-100 dark:border-zinc-700 my-1.5 mx-2"></div>
                        <button
                            type="button"
                            class="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all active:scale-95"
                            @click="bulkDelete"
                        >
                            <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                            <span class="font-bold">Delete</span>
                        </button>
                    </div>

                    <!-- loading more spinner -->
                    <div v-if="isLoadingMore" class="p-4 text-center">
                        <MaterialDesignIcon icon-name="loading" class="size-6 animate-spin text-gray-400" />
                    </div>
                </div>
                <div v-else class="mx-auto my-auto text-center leading-5">
                    <div v-if="isLoading" class="flex flex-col text-gray-900 dark:text-gray-100">
                        <div class="mx-auto mb-1 text-gray-500">
                            <MaterialDesignIcon icon-name="loading" class="size-6 animate-spin" />
                        </div>
                        <div class="font-semibold">{{ $t("messages.loading_conversations") }}</div>
                    </div>

                    <!-- no conversations at all -->
                    <div
                        v-else-if="conversations.length === 0 && !isFilterActive"
                        class="flex flex-col text-gray-900 dark:text-gray-100"
                    >
                        <div class="mx-auto mb-1 text-gray-500">
                            <MaterialDesignIcon icon-name="tray-remove" class="size-6" />
                        </div>
                        <div class="font-semibold">No Conversations</div>
                        <div>Discover peers on the Announces tab</div>
                    </div>

                    <!-- is searching or filtering, but no results -->
                    <div v-else-if="isFilterActive" class="flex flex-col text-gray-900 dark:text-gray-100">
                        <div class="mx-auto mb-1 text-gray-500">
                            <MaterialDesignIcon icon-name="magnify-close" class="size-6" />
                        </div>
                        <div class="font-semibold">{{ $t("messages.no_search_results") }}</div>
                        <div>{{ $t("messages.no_search_results_conversations") }}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- discover -->
        <div
            v-if="tab === 'announces'"
            class="flex-1 flex flex-col bg-white dark:bg-zinc-950 border-r border-gray-200 dark:border-zinc-700 overflow-hidden min-h-0"
        >
            <!-- search -->
            <div class="p-1 border-b border-gray-300 dark:border-zinc-700">
                <input
                    :value="peersSearchTerm"
                    type="text"
                    :placeholder="$t('messages.search_placeholder_announces', { count: totalPeersCount })"
                    class="input-field"
                    @input="onPeersSearchInput"
                />
            </div>

            <!-- peers -->
            <div class="flex h-full overflow-y-auto" @scroll="onPeersScroll">
                <div v-if="searchedPeers.length > 0" class="w-full">
                    <div
                        v-for="peer of searchedPeers"
                        :key="peer.destination_hash"
                        v-memo="[
                            peer.destination_hash,
                            peer.updated_at,
                            peer.hops,
                            peer.snr,
                            selectedDestinationHash === peer.destination_hash,
                            GlobalState.config.banished_effect_enabled && isBlocked(peer.destination_hash),
                        ]"
                        class="flex cursor-pointer p-2 border-l-2 relative"
                        :class="[
                            peer.destination_hash === selectedDestinationHash
                                ? 'bg-gray-100 dark:bg-zinc-700 border-blue-500 dark:border-blue-400'
                                : 'bg-white dark:bg-zinc-950 border-transparent hover:bg-gray-50 dark:hover:bg-zinc-700 hover:border-gray-200 dark:hover:border-zinc-600',
                        ]"
                        @click="onPeerClick(peer)"
                    >
                        <!-- banished overlay -->
                        <div
                            v-if="GlobalState.config.banished_effect_enabled && isBlocked(peer.destination_hash)"
                            class="banished-overlay"
                            :style="{ background: GlobalState.config.banished_color + '33' }"
                        >
                            <span
                                class="banished-text !text-[10px] !opacity-100 !tracking-widest !border !px-1 !py-0.5 !text-white !shadow-lg"
                                :style="{ 'background-color': GlobalState.config.banished_color }"
                                >{{ GlobalState.config.banished_text }}</span
                            >
                        </div>

                        <div class="my-auto mr-2">
                            <LxmfUserIcon
                                :custom-image="peer.contact_image"
                                :icon-name="peer.lxmf_user_icon?.icon_name"
                                :icon-foreground-colour="peer.lxmf_user_icon?.foreground_colour"
                                :icon-background-colour="peer.lxmf_user_icon?.background_colour"
                                icon-class="size-7"
                            />
                        </div>
                        <div class="min-w-0 flex-1">
                            <div
                                class="text-gray-900 dark:text-gray-100 truncate"
                                :title="peer.custom_display_name ?? peer.display_name"
                            >
                                {{ peer.custom_display_name ?? peer.display_name }}
                            </div>
                            <div class="flex space-x-1 text-gray-500 dark:text-gray-400 text-sm">
                                <!-- time ago -->
                                <span class="flex my-auto space-x-1">
                                    {{ formatTimeAgo(peer.updated_at) }}
                                </span>

                                <!-- hops away -->
                                <span
                                    v-if="peer.hops != null && peer.hops !== 128"
                                    class="flex my-auto text-sm text-gray-500 space-x-1"
                                >
                                    <span>•</span>
                                    <span v-if="peer.hops === 0 || peer.hops === 1">{{ $t("messages.direct") }}</span>
                                    <span v-else>{{ $t("messages.hops", { count: peer.hops }) }}</span>
                                </span>

                                <!-- snr -->
                                <span v-if="peer.snr != null" class="flex my-auto space-x-1">
                                    <span>•</span>
                                    <span>{{ $t("messages.snr", { snr: peer.snr }) }}</span>
                                </span>
                            </div>
                        </div>
                    </div>

                    <!-- loading more spinner -->
                    <div v-if="isLoadingMoreAnnounces" class="p-4 text-center">
                        <MaterialDesignIcon icon-name="loading" class="size-6 animate-spin text-gray-400" />
                    </div>
                </div>
                <div v-else class="mx-auto my-auto text-center leading-5">
                    <!-- no peers at all -->
                    <div v-if="peersCount === 0" class="flex flex-col text-gray-900 dark:text-gray-100">
                        <div class="mx-auto mb-1 text-gray-500">
                            <MaterialDesignIcon icon-name="account-search-outline" class="size-6" />
                        </div>
                        <div class="font-semibold">{{ $t("messages.no_peers_discovered") }}</div>
                        <div>{{ $t("messages.waiting_for_announce") }}</div>
                    </div>

                    <!-- is searching, but no results -->
                    <div
                        v-if="peersSearchTerm !== '' && peersCount > 0"
                        class="flex flex-col text-gray-900 dark:text-gray-100"
                    >
                        <div class="mx-auto mb-1 text-gray-500">
                            <MaterialDesignIcon icon-name="account-off-outline" class="size-6" />
                        </div>
                        <div class="font-semibold">{{ $t("messages.no_search_results") }}</div>
                        <div>{{ $t("messages.no_search_results_peers") }}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import DialogUtils from "../../js/DialogUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import GlobalState from "../../js/GlobalState";

export default {
    name: "MessagesSidebar",
    components: { MaterialDesignIcon, LxmfUserIcon },
    props: {
        peers: {
            type: Object,
            required: true,
        },
        conversations: {
            type: Array,
            required: true,
        },
        folders: {
            type: Array,
            default: () => [],
        },
        selectedFolderId: {
            type: [Number, String],
            default: null,
        },
        selectedDestinationHash: {
            type: String,
            required: true,
        },
        conversationSearchTerm: {
            type: String,
            default: "",
        },
        filterUnreadOnly: {
            type: Boolean,
            default: false,
        },
        filterFailedOnly: {
            type: Boolean,
            default: false,
        },
        filterHasAttachmentsOnly: {
            type: Boolean,
            default: false,
        },
        isLoading: {
            type: Boolean,
            default: false,
        },
        isLoadingMore: {
            type: Boolean,
            default: false,
        },
        hasMoreConversations: {
            type: Boolean,
            default: false,
        },
        isLoadingMoreAnnounces: {
            type: Boolean,
            default: false,
        },
        hasMoreAnnounces: {
            type: Boolean,
            default: false,
        },
        peersSearchTerm: {
            type: String,
            default: "",
        },
        totalPeersCount: {
            type: Number,
            default: 0,
        },
    },
    emits: [
        "conversation-click",
        "peer-click",
        "conversation-search-changed",
        "conversation-filter-changed",
        "peers-search-changed",
        "ingest-paper-message",
        "load-more",
        "load-more-announces",
        "folder-click",
        "create-folder",
        "rename-folder",
        "delete-folder",
        "move-to-folder",
        "bulk-mark-as-read",
        "bulk-delete",
        "export-folders",
        "import-folders",
    ],
    data() {
        let foldersExpanded = true;
        try {
            if (typeof localStorage !== "undefined") {
                foldersExpanded = localStorage.getItem("meshchatx_folders_expanded") !== "false";
            }
        } catch {
            // ignore
        }
        return {
            GlobalState,
            tab: "conversations",
            foldersExpanded,
            selectionMode: false,
            selectedHashes: new Set(),
            folderMenu: {
                show: false,
            },
            moveMenu: {
                show: false,
            },
            contextMenu: {
                show: false,
                x: 0,
                y: 0,
                targetHash: null,
            },
            draggedHash: null,
            dragOverFolderId: null,
        };
    },
    computed: {
        isFilterActive() {
            return (
                this.conversationSearchTerm !== "" ||
                this.filterUnreadOnly ||
                this.filterFailedOnly ||
                this.filterHasAttachmentsOnly
            );
        },
        blockedDestinations() {
            return GlobalState.blockedDestinations;
        },
        displayedConversations() {
            return this.conversations;
        },
        peersCount() {
            return Object.keys(this.peers).length;
        },
        peersOrderedByLatestAnnounce() {
            const peers = Object.values(this.peers);
            // Pre-parse timestamps for sorting performance
            const timedPeers = peers.map((p) => ({
                p,
                t: p._updated_at_ts || (p._updated_at_ts = new Date(p.updated_at).getTime()),
            }));
            timedPeers.sort((a, b) => b.t - a.t);
            return timedPeers.map((tp) => tp.p);
        },
        searchedPeers() {
            return this.peersOrderedByLatestAnnounce.filter((peer) => {
                const search = this.peersSearchTerm.toLowerCase();
                const matchesDisplayName = peer.display_name.toLowerCase().includes(search);
                const matchesCustomDisplayName = peer.custom_display_name?.toLowerCase()?.includes(search) === true;
                const matchesDestinationHash = peer.destination_hash.toLowerCase().includes(search);
                return matchesDisplayName || matchesCustomDisplayName || matchesDestinationHash;
            });
        },
        hasUnreadConversations() {
            return this.conversations.some((c) => c.is_unread);
        },
        allSelected() {
            return this.conversations.length > 0 && this.selectedHashes.size === this.conversations.length;
        },
    },
    watch: {
        foldersExpanded(newVal) {
            try {
                if (typeof localStorage !== "undefined") {
                    localStorage.setItem("meshchatx_folders_expanded", newVal);
                }
            } catch {
                // ignore
            }
        },
    },
    methods: {
        toggleSelectionMode() {
            this.selectionMode = !this.selectionMode;
            if (!this.selectionMode) {
                this.selectedHashes.clear();
            }
        },
        toggleSelectAll() {
            if (this.allSelected) {
                this.selectedHashes.clear();
            } else {
                this.conversations.forEach((c) => this.selectedHashes.add(c.destination_hash));
            }
        },
        toggleSelectConversation(hash) {
            if (this.selectedHashes.has(hash)) {
                this.selectedHashes.delete(hash);
            } else {
                this.selectedHashes.add(hash);
            }
        },
        onRightClick(event, hash) {
            event.preventDefault();
            if (this.selectionMode && !this.selectedHashes.has(hash)) {
                this.selectedHashes.add(hash);
            }
            this.contextMenu.x = event.clientX;
            this.contextMenu.y = event.clientY;
            this.contextMenu.targetHash = hash;
            this.contextMenu.show = true;
        },
        onFolderContextMenu(event) {
            event.preventDefault();
            // Show folder management menu
        },
        onDragStart(event, hash) {
            this.draggedHash = hash;
            event.dataTransfer.setData("text/plain", hash);
            event.dataTransfer.effectAllowed = "move";
        },
        onDragOver(event, folderId) {
            event.preventDefault();
            this.dragOverFolderId = folderId;
            event.dataTransfer.dropEffect = "move";
        },
        onDragLeave() {
            this.dragOverFolderId = null;
        },
        onDropOnFolder(event, folderId) {
            event.preventDefault();
            this.dragOverFolderId = null;
            const hash = event.dataTransfer.getData("text/plain");
            if (hash) {
                this.$emit("move-to-folder", {
                    peer_hashes: [hash],
                    folder_id: folderId,
                });
            }
            this.draggedHash = null;
        },
        async createFolder() {
            const name = await DialogUtils.prompt("Enter folder name", "New Folder");
            if (name) {
                this.$emit("create-folder", name);
            }
        },
        async renameFolder(folder) {
            const name = await DialogUtils.prompt("Rename folder", folder.name);
            if (name && name !== folder.name) {
                this.$emit("rename-folder", { id: folder.id, name });
            }
        },
        async deleteFolder(folder) {
            const confirmed = await DialogUtils.confirm(
                `Are you sure you want to delete the folder "${folder.name}"? Conversations will be moved to Uncategorized.`,
                "Delete Folder"
            );
            if (confirmed) {
                this.$emit("delete-folder", folder.id);
            }
        },
        bulkMarkAsRead() {
            const hashes = this.selectionMode ? Array.from(this.selectedHashes) : [this.contextMenu.targetHash];
            this.$emit("bulk-mark-as-read", hashes);
            this.contextMenu.show = false;
            this.moveMenu.show = false;
            this.folderMenu.show = false;
            if (this.selectionMode) this.toggleSelectionMode();
        },
        bulkDelete() {
            const hashes = this.selectionMode ? Array.from(this.selectedHashes) : [this.contextMenu.targetHash];
            this.$emit("bulk-delete", hashes);
            this.contextMenu.show = false;
            this.moveMenu.show = false;
            this.folderMenu.show = false;
            if (this.selectionMode) this.toggleSelectionMode();
        },
        moveSelectedToFolder(folderId) {
            const hashes = this.selectionMode ? Array.from(this.selectedHashes) : [this.contextMenu.targetHash];
            this.$emit("move-to-folder", { peer_hashes: hashes, folder_id: folderId });
            this.contextMenu.show = false;
            this.moveMenu.show = false;
            this.folderMenu.show = false;
            if (this.selectionMode) this.toggleSelectionMode();
        },
        isBlocked(destinationHash) {
            return this.blockedDestinations.some((b) => b.destination_hash === destinationHash);
        },
        openIngestPaperMessageModal() {
            this.$emit("ingest-paper-message");
        },
        onConversationClick(conversation) {
            if (this.isBlocked(conversation.destination_hash)) {
                return;
            }
            this.$emit("conversation-click", conversation);
        },
        onPeerClick(peer) {
            if (this.isBlocked(peer.destination_hash)) {
                return;
            }
            this.$emit("peer-click", peer);
        },
        formatTimeAgo: function (datetimeString) {
            return Utils.formatTimeAgo(datetimeString);
        },
        onConversationSearchInput(event) {
            this.$emit("conversation-search-changed", event.target.value);
        },
        toggleFilter(filterKey) {
            this.$emit("conversation-filter-changed", filterKey);
        },
        onConversationsScroll(event) {
            const element = event.target;
            // if scrolled near bottom (within 200px)
            if (element.scrollHeight - element.scrollTop - element.clientHeight < 200) {
                if (this.hasMoreConversations && !this.isLoadingMore && !this.isLoading) {
                    this.$emit("load-more");
                }
            }
        },
        onPeersScroll(event) {
            const element = event.target;
            // if scrolled near bottom (within 200px)
            if (element.scrollHeight - element.scrollTop - element.clientHeight < 200) {
                if (this.hasMoreAnnounces && !this.isLoadingMoreAnnounces) {
                    this.$emit("load-more-announces");
                }
            }
        },
        onPeersSearchInput(event) {
            this.$emit("peers-search-changed", event.target.value);
        },
        filterChipClasses(isActive) {
            const base = "px-2 py-1 rounded-full text-xs font-semibold transition-colors";
            if (isActive) {
                return `${base} bg-blue-600 text-white dark:bg-blue-500`;
            }
            return `${base} bg-gray-100 text-gray-700 dark:bg-zinc-800 dark:text-zinc-200`;
        },
    },
};
</script>
