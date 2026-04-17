<!-- SPDX-License-Identifier: 0BSD AND MIT -->

<template>
    <div :class="sidebarRootClass">
        <div
            v-if="effectiveCollapsed"
            :class="[
                'flex flex-col h-full min-h-0 bg-white dark:bg-zinc-950 border-gray-200 dark:border-zinc-800',
                edgeBorderClass,
            ]"
        >
            <div
                class="hidden sm:flex h-12 shrink-0 items-center border-b border-gray-200 dark:border-zinc-800 px-2"
                :class="collapsedHeaderJustifyClass"
            >
                <button
                    type="button"
                    class="p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors"
                    @click="$emit('toggle-collapse')"
                >
                    <MaterialDesignIcon :icon-name="collapsedStripChevronIcon" class="size-5" />
                </button>
            </div>
            <div class="flex flex-col items-center gap-1 py-2 px-1 border-b border-gray-200 dark:border-zinc-800">
                <button
                    type="button"
                    class="p-2 rounded-xl transition-colors"
                    :class="
                        tab === 'conversations'
                            ? 'bg-indigo-600 text-white dark:bg-indigo-500'
                            : 'text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
                    "
                    @click="tab = 'conversations'"
                >
                    <MaterialDesignIcon icon-name="message-text" class="size-6" />
                </button>
                <button
                    type="button"
                    class="p-2 rounded-xl transition-colors"
                    :class="
                        tab === 'announces'
                            ? 'bg-indigo-600 text-white dark:bg-indigo-500'
                            : 'text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800'
                    "
                    @click="tab = 'announces'"
                >
                    <MaterialDesignIcon icon-name="account-search-outline" class="size-6" />
                </button>
            </div>
            <div
                v-if="tab === 'conversations'"
                class="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden flex flex-col items-center gap-1 py-1 px-0.5"
            >
                <button
                    v-for="c in collapsedSidebarConversations"
                    :key="c.destination_hash"
                    type="button"
                    class="shrink-0 p-0.5 rounded-xl transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                    :class="
                        selectedDestinationHash === c.destination_hash
                            ? 'ring-2 ring-indigo-500 ring-offset-1 ring-offset-white dark:ring-offset-zinc-950'
                            : 'hover:bg-white/10'
                    "
                    :title="c.custom_display_name ?? c.display_name"
                    @click="onConversationClick(c)"
                >
                    <LxmfUserIcon
                        :custom-image="c.contact_image"
                        :icon-name="c.lxmf_user_icon ? c.lxmf_user_icon.icon_name : ''"
                        :icon-foreground-colour="c.lxmf_user_icon ? c.lxmf_user_icon.foreground_colour : ''"
                        :icon-background-colour="c.lxmf_user_icon ? c.lxmf_user_icon.background_colour : ''"
                        icon-class="size-9 shrink-0"
                        :icon-style="collapsedConversationIconStyle"
                    />
                </button>
            </div>
        </div>
        <template v-else>
            <!-- tabs (h-12 matches App.vue main sidebar collapse row) -->
            <div :class="['bg-white dark:bg-zinc-950 border-b border-gray-200 dark:border-zinc-800', edgeBorderClass]">
                <div class="-mb-px flex h-12 min-w-0 items-stretch" :class="{ 'flex-row-reverse': isRightSidebar }">
                    <div class="flex min-w-0 flex-1">
                        <div
                            class="flex w-full cursor-pointer items-center justify-center border-b-2 px-1 text-center text-sm font-semibold uppercase tracking-wide transition"
                            :class="[
                                tab === 'conversations'
                                    ? 'border-indigo-500 text-indigo-600 dark:border-indigo-400 dark:text-indigo-300'
                                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:hover:border-zinc-600 hover:text-gray-700 dark:hover:text-gray-200',
                            ]"
                            @click="tab = 'conversations'"
                        >
                            {{ $t("messages.conversations") }}
                        </div>
                        <div
                            class="flex w-full cursor-pointer items-center justify-center border-b-2 px-1 text-center text-sm font-semibold uppercase tracking-wide transition"
                            :class="[
                                tab === 'announces'
                                    ? 'border-indigo-500 text-indigo-600 dark:border-indigo-400 dark:text-indigo-300'
                                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:hover:border-zinc-600 hover:text-gray-700 dark:hover:text-gray-200',
                            ]"
                            @click="tab = 'announces'"
                        >
                            {{ $t("messages.announces") }}
                        </div>
                    </div>
                    <button
                        type="button"
                        class="hidden sm:flex shrink-0 items-center border-b-2 border-transparent px-1.5 text-gray-500 hover:bg-gray-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors"
                        @click="$emit('toggle-collapse')"
                    >
                        <MaterialDesignIcon :icon-name="expandedTabBarChevronIcon" class="size-5" />
                    </button>
                </div>
            </div>

            <!-- conversations -->
            <div
                v-if="tab === 'conversations'"
                :class="[
                    'flex-1 flex flex-col bg-white dark:bg-zinc-950 border-gray-200 dark:border-zinc-800 overflow-hidden min-h-0',
                    edgeBorderClass,
                ]"
            >
                <!-- Folders Section -->
                <div class="border-b border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
                    <div
                        class="flex cursor-pointer items-center justify-between px-3 py-2 transition-colors hover:bg-gray-100 dark:hover:bg-zinc-800/80"
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
                                class="p-1 text-gray-400 hover:text-indigo-500 hover:bg-gray-200/50 dark:hover:bg-zinc-800 rounded-lg transition-colors"
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
                    class="p-1 border-b border-gray-300 dark:border-zinc-700 space-y-1.5"
                >
                    <div class="flex gap-2">
                        <input
                            :value="conversationSearchTerm"
                            type="text"
                            :placeholder="$t('messages.search_placeholder', { count: conversations.length })"
                            class="input-field flex-1 w-full rounded-none"
                            @input="onConversationSearchInput"
                        />
                    </div>
                    <div class="flex items-center justify-end gap-1 px-1 text-gray-500 dark:text-gray-400">
                        <button
                            type="button"
                            class="p-1 rounded-lg hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
                            title="Selection Mode"
                            :class="{ 'text-blue-500 dark:text-blue-400': selectionMode }"
                            @click="toggleSelectionMode"
                        >
                            <MaterialDesignIcon icon-name="checkbox-multiple-marked-outline" class="size-5" />
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
                        <button
                            type="button"
                            :class="filterChipClasses(filterUnreadOnly)"
                            @click="toggleFilter('unread')"
                        >
                            {{ $t("messages.unread") }}
                        </button>
                        <button
                            type="button"
                            :class="filterChipClasses(filterFailedOnly)"
                            @click="toggleFilter('failed')"
                        >
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
                                <div class="rounded bg-gray-200 dark:bg-zinc-800" :style="messageIconStyle"></div>
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
                                pinnedSet.has(conversation.destination_hash),
                                timeAgoTick,
                                isRightSidebar,
                            ]"
                            :class="[
                                'flex cursor-pointer p-2 relative group conversation-item',
                                selectionEdgeBorderClass,
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
                                    GlobalState.config.banished_effect_enabled &&
                                    isBlocked(conversation.destination_hash)
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
                                    :icon-name="
                                        conversation.lxmf_user_icon ? conversation.lxmf_user_icon.icon_name : ''
                                    "
                                    :icon-foreground-colour="
                                        conversation.lxmf_user_icon ? conversation.lxmf_user_icon.foreground_colour : ''
                                    "
                                    :icon-background-colour="
                                        conversation.lxmf_user_icon ? conversation.lxmf_user_icon.background_colour : ''
                                    "
                                    icon-class="shrink-0"
                                    :icon-style="messageIconStyle"
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
                                    <div
                                        class="text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap flex-shrink-0"
                                    >
                                        {{ formatTimeAgo(conversation.updated_at) }}
                                    </div>
                                </div>
                                <div class="text-gray-600 dark:text-gray-400 text-xs mt-0.5 truncate">
                                    {{
                                        stripMarkdown(
                                            conversation.latest_message_preview ?? conversation.latest_message_title
                                        ) ?? "No messages yet"
                                    }}
                                </div>
                            </div>
                            <div class="flex flex-col items-center justify-between ml-1 py-1 shrink-0">
                                <div class="flex items-center space-x-1">
                                    <div
                                        v-if="pinnedSet.has(conversation.destination_hash)"
                                        class="text-blue-500 dark:text-blue-400"
                                        title="Pinned"
                                    >
                                        <MaterialDesignIcon icon-name="pin" class="w-4 h-4" />
                                    </div>
                                    <div v-if="conversation.has_attachments" class="text-gray-500 dark:text-gray-300">
                                        <MaterialDesignIcon icon-name="paperclip" class="w-4 h-4" />
                                    </div>
                                    <div
                                        v-if="
                                            conversation.is_unread &&
                                            conversation.destination_hash !== selectedDestinationHash
                                        "
                                        class="my-auto ml-1"
                                    >
                                        <div class="bg-blue-500 dark:bg-blue-400 rounded-full p-1"></div>
                                    </div>
                                    <div v-else-if="conversation.failed_messages_count" class="my-auto ml-1">
                                        <div class="bg-red-500 dark:bg-red-400 rounded-full p-1"></div>
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    class="p-1 opacity-0 group-hover:opacity-100 hover:bg-gray-200 dark:hover:bg-zinc-800 rounded-lg transition-all"
                                    @click.stop="onRightClick($event, conversation.destination_hash)"
                                >
                                    <MaterialDesignIcon icon-name="dots-vertical" class="size-4 text-gray-400" />
                                </button>
                            </div>
                        </div>

                        <!-- Context Menu -->
                        <ContextMenuPanel
                            v-click-outside="{ handler: () => (contextMenu.show = false), capture: true }"
                            :show="contextMenu.show"
                            :x="contextMenu.x"
                            :y="contextMenu.y"
                            panel-class="z-[100]"
                        >
                            <ContextMenuItem @click="bulkMarkAsRead">
                                <MaterialDesignIcon icon-name="email-open-outline" class="size-4 text-gray-400" />
                                Mark as Read
                            </ContextMenuItem>
                            <ContextMenuItem v-if="contextMenu.targetHash" @click="togglePinFromContextMenu">
                                <MaterialDesignIcon
                                    :icon-name="isContextTargetPinned ? 'pin-off' : 'pin'"
                                    class="size-4 text-gray-400"
                                />
                                {{
                                    isContextTargetPinned
                                        ? $t("messages.unpin_conversation")
                                        : $t("messages.pin_conversation")
                                }}
                            </ContextMenuItem>
                            <ContextMenuItem @click="contextMenuIngestPaperMessage">
                                <MaterialDesignIcon icon-name="qrcode-scan" class="size-4 text-gray-400" />
                                {{ $t("messages.ingest_paper_message") }}
                            </ContextMenuItem>
                            <ContextMenuItem
                                v-if="contextMenu.targetHash && isBlocked(contextMenu.targetHash)"
                                item-class="text-emerald-600 dark:text-emerald-400"
                                @click="liftBanishmentFromConversationMenu"
                            >
                                <MaterialDesignIcon icon-name="check-circle" class="size-4" />
                                {{ $t("banishment.lift_banishment") }}
                            </ContextMenuItem>
                            <ContextMenuDivider />
                            <ContextMenuItem
                                v-if="GlobalState.config.telemetry_enabled"
                                @click="toggleTelemetryTrust(contextMenu.targetHash)"
                            >
                                <MaterialDesignIcon
                                    :icon-name="
                                        contextMenu.targetContact?.is_telemetry_trusted
                                            ? 'shield-check'
                                            : 'shield-outline'
                                    "
                                    :class="
                                        contextMenu.targetContact?.is_telemetry_trusted
                                            ? 'size-4 text-blue-500'
                                            : 'size-4 text-gray-400'
                                    "
                                />
                                {{
                                    contextMenu.targetContact?.is_telemetry_trusted
                                        ? "Revoke Telemetry Trust"
                                        : "Trust for Telemetry"
                                }}
                            </ContextMenuItem>
                            <ContextMenuDivider v-if="GlobalState.config.telemetry_enabled" />
                            <ContextMenuSectionLabel>Move to Folder</ContextMenuSectionLabel>
                            <ContextMenuItem @click="moveSelectedToFolder(null)">
                                <MaterialDesignIcon icon-name="inbox-arrow-down" class="size-4 opacity-70" />
                                Uncategorized
                            </ContextMenuItem>
                            <div class="max-h-[200px] overflow-y-auto custom-scrollbar">
                                <ContextMenuItem
                                    v-for="folder in folders"
                                    :key="folder.id"
                                    @click="moveSelectedToFolder(folder.id)"
                                >
                                    <MaterialDesignIcon icon-name="folder" class="size-4 opacity-70" />
                                    <span class="truncate">{{ folder.name }}</span>
                                </ContextMenuItem>
                            </div>
                            <ContextMenuDivider />
                            <ContextMenuItem item-class="text-red-600 dark:text-red-400" @click="bulkDelete">
                                <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                                Delete
                            </ContextMenuItem>
                        </ContextMenuPanel>

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
                :class="[
                    'flex-1 flex flex-col bg-white dark:bg-zinc-950 border-gray-200 dark:border-zinc-800 overflow-hidden min-h-0',
                    edgeBorderClass,
                ]"
            >
                <!-- search -->
                <div class="p-1 border-b border-gray-200 dark:border-zinc-800">
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
                                timeAgoTick,
                                isRightSidebar,
                            ]"
                            :class="[
                                'flex cursor-pointer p-2 relative',
                                selectionEdgeBorderClass,
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
                                    icon-class="shrink-0"
                                    :icon-style="messageIconStyle"
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
                                        <span v-if="peer.hops === 0 || peer.hops === 1">{{
                                            $t("messages.direct")
                                        }}</span>
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
        </template>
    </div>
</template>

<script>
import Utils from "../../js/Utils";
import DialogUtils from "../../js/DialogUtils";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import LxmfUserIcon from "../LxmfUserIcon.vue";
import ContextMenuDivider from "../contextmenu/ContextMenuDivider.vue";
import ContextMenuItem from "../contextmenu/ContextMenuItem.vue";
import ContextMenuPanel from "../contextmenu/ContextMenuPanel.vue";
import ContextMenuSectionLabel from "../contextmenu/ContextMenuSectionLabel.vue";
import GlobalState from "../../js/GlobalState";
import GlobalEmitter from "../../js/GlobalEmitter";
import MarkdownRenderer from "../../js/MarkdownRenderer";

export default {
    name: "MessagesSidebar",
    components: {
        MaterialDesignIcon,
        LxmfUserIcon,
        ContextMenuDivider,
        ContextMenuItem,
        ContextMenuPanel,
        ContextMenuSectionLabel,
    },
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
        pinnedPeerHashes: {
            type: Array,
            default: () => [],
        },
        collapsed: {
            type: Boolean,
            default: false,
        },
        sidebarPosition: {
            type: String,
            default: "left",
            validator: (v) => v === "left" || v === "right",
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
        "toggle-conversation-pin",
        "toggle-collapse",
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
            timeAgoTick: 0,
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
                targetContact: null,
            },
            draggedHash: null,
            dragOverFolderId: null,
            smUp: typeof window !== "undefined" ? window.innerWidth >= 640 : true,
        };
    },
    computed: {
        effectiveCollapsed() {
            return this.collapsed && this.smUp;
        },
        collapsedSidebarConversations() {
            return this.displayedConversations.slice(0, 5);
        },
        isRightSidebar() {
            return this.sidebarPosition === "right";
        },
        edgeBorderClass() {
            return this.isRightSidebar ? "border-l" : "border-r";
        },
        selectionEdgeBorderClass() {
            return this.isRightSidebar ? "border-r-2" : "border-l-2";
        },
        collapsedHeaderJustifyClass() {
            return this.isRightSidebar ? "justify-start" : "justify-end";
        },
        collapsedStripChevronIcon() {
            return this.isRightSidebar ? "chevron-left" : "chevron-right";
        },
        expandedTabBarChevronIcon() {
            return this.isRightSidebar ? "chevron-right" : "chevron-left";
        },
        collapsedConversationIconStyle() {
            return { width: "36px", height: "36px" };
        },
        sidebarRootClass() {
            if (this.effectiveCollapsed) {
                return "flex flex-col w-16 min-w-16 max-w-16 h-full min-h-0";
            }
            return "flex flex-col w-full sm:w-80 sm:min-w-80 md:max-lg:w-64 md:max-lg:min-w-64 lg:w-80 lg:min-w-80 min-h-0";
        },
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
        pinnedSet() {
            return new Set(this.pinnedPeerHashes || []);
        },
        isContextTargetPinned() {
            return Boolean(this.contextMenu.targetHash && this.pinnedSet.has(this.contextMenu.targetHash));
        },
        displayedConversations() {
            const list = [...this.conversations];
            const pinned = this.pinnedSet;
            const idx = new Map(list.map((c, i) => [c.destination_hash, i]));
            list.sort((a, b) => {
                const ap = pinned.has(a.destination_hash);
                const bp = pinned.has(b.destination_hash);
                if (ap !== bp) {
                    return ap ? -1 : 1;
                }
                return idx.get(a.destination_hash) - idx.get(b.destination_hash);
            });
            return list;
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
            return (
                this.displayedConversations.length > 0 &&
                this.selectedHashes.size === this.displayedConversations.length
            );
        },
        messageIconStyle() {
            const size = GlobalState.config?.message_icon_size || 28;
            return { width: `${size}px`, height: `${size}px` };
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
    mounted() {
        GlobalEmitter.on("contact-updated", this.onContactUpdated);
        const tickMs = 60 * 1000;
        this._timeAgoInterval = setInterval(() => {
            this.timeAgoTick = Date.now();
        }, tickMs);
        this._smUpMql = window.matchMedia("(min-width: 640px)");
        this._smUpResize = () => {
            this.smUp = this._smUpMql.matches;
        };
        this._smUpResize();
        this._smUpMql.addEventListener("change", this._smUpResize);
    },
    unmounted() {
        GlobalEmitter.off("contact-updated", this.onContactUpdated);
        if (this._smUpMql && this._smUpResize) {
            this._smUpMql.removeEventListener("change", this._smUpResize);
        }
        if (this._timeAgoInterval) clearInterval(this._timeAgoInterval);
    },
    methods: {
        onContactUpdated(data) {
            // update local contact info if context menu is showing this peer
            if (this.contextMenu.show && this.contextMenu.targetHash === data.remote_identity_hash) {
                this.fetchContactForContextMenu(data.remote_identity_hash);
            }
        },
        async fetchContactForContextMenu(hash) {
            try {
                const response = await window.api.get(`/api/v1/telephone/contacts/check/${hash}`);
                if (response.data.is_contact) {
                    this.contextMenu.targetContact = response.data.contact;
                } else {
                    this.contextMenu.targetContact = null;
                }
            } catch (e) {
                console.error("Failed to fetch contact for context menu", e);
            }
        },
        stripMarkdown(text) {
            return MarkdownRenderer.strip(text);
        },
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
                this.displayedConversations.forEach((c) => this.selectedHashes.add(c.destination_hash));
            }
        },
        toggleSelectConversation(hash) {
            if (this.selectedHashes.has(hash)) {
                this.selectedHashes.delete(hash);
            } else {
                this.selectedHashes.add(hash);
            }
        },
        async onRightClick(event, hash) {
            event.preventDefault();
            if (this.selectionMode && !this.selectedHashes.has(hash)) {
                this.selectedHashes.add(hash);
            }
            this.contextMenu.x = event.clientX;
            this.contextMenu.y = event.clientY;
            this.contextMenu.targetHash = hash;
            this.contextMenu.show = true;
            this.contextMenu.targetContact = null;

            // fetch contact info for trust status
            await this.fetchContactForContextMenu(hash);
        },
        togglePinFromContextMenu() {
            const h = this.contextMenu.targetHash;
            if (!h) {
                return;
            }
            this.$emit("toggle-conversation-pin", h);
            this.contextMenu.show = false;
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
            const name = await DialogUtils.prompt(
                this.$t("messages.enter_folder_name"),
                this.$t("messages.new_folder")
            );
            if (name) {
                this.$emit("create-folder", name);
            }
        },
        async renameFolder(folder) {
            const name = await DialogUtils.prompt(this.$t("messages.rename_folder"), folder.name);
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
        async toggleTelemetryTrust(hash) {
            const contact = this.contextMenu.targetContact;
            const newStatus = !contact?.is_telemetry_trusted;
            try {
                if (!contact) {
                    // find display name from conversations
                    const conv = this.conversations.find((c) => c.destination_hash === hash);
                    await window.api.post("/api/v1/telephone/contacts", {
                        name: conv?.display_name || hash.substring(0, 8),
                        remote_identity_hash: hash,
                        is_telemetry_trusted: true,
                    });
                } else {
                    await window.api.patch(`/api/v1/telephone/contacts/${contact.id}`, {
                        is_telemetry_trusted: newStatus,
                    });
                }
                GlobalEmitter.emit("contact-updated", {
                    remote_identity_hash: hash,
                    is_telemetry_trusted: newStatus,
                });
                this.contextMenu.show = false;
                DialogUtils.alert(
                    newStatus
                        ? this.$t("app.telemetry_trust_granted_alert")
                        : this.$t("app.telemetry_trust_revoked_alert")
                );
            } catch (e) {
                DialogUtils.alert(this.$t("app.telemetry_trust_failed"));
                console.error(e);
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
        contextMenuIngestPaperMessage() {
            this.contextMenu.show = false;
            this.$emit("ingest-paper-message");
        },
        async liftBanishmentFromConversationMenu() {
            const hash = this.contextMenu.targetHash;
            if (!hash) {
                this.contextMenu.show = false;
                return;
            }
            try {
                await window.api.delete(`/api/v1/blocked-destinations/${hash}`);
                GlobalEmitter.emit("block-status-changed");
                DialogUtils.alert(this.$t("banishment.banishment_lifted"));
            } catch (e) {
                DialogUtils.alert(this.$t("banishment.failed_lift_banishment"));
                console.error(e);
            }
            this.contextMenu.show = false;
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
