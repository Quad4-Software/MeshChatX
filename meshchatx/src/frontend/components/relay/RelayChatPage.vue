<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 min-w-0 h-full bg-sem-canvas text-sem-fg">
        <div
            v-if="!rrcEnabled"
            class="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center text-sem-fg-muted"
        >
            <MaterialDesignIcon icon-name="forum-off-outline" class="size-12 opacity-40" />
            <p class="max-w-md text-sm">{{ $t("relay_chat.disabled_message") }}</p>
        </div>

        <template v-else>
            <!-- view tabs -->
            <div
                v-if="!isPopoutMode"
                class="flex items-stretch h-9 shrink-0 border-b border-sem-border bg-sem-surface-muted overflow-x-auto"
                role="tablist"
            >
                <button
                    v-for="tab in tabs"
                    :key="tab.id"
                    type="button"
                    role="tab"
                    :aria-selected="view === tab.id"
                    class="inline-flex items-center gap-1.5 px-3 sm:px-4 border-r border-sem-border text-sm transition-colors shrink-0"
                    :class="
                        view === tab.id
                            ? 'bg-sem-canvas text-sem-fg font-medium'
                            : 'text-sem-fg-muted hover:bg-sem-surface/80 dark:hover:bg-sem-surface/30'
                    "
                    @click="selectView(tab.id)"
                >
                    <MaterialDesignIcon :icon-name="tab.icon" class="size-4 shrink-0 opacity-70" />
                    <span>{{ $t(tab.label) }}</span>
                </button>
            </div>

            <!-- connect view -->
            <div v-show="view === 'chat'" class="flex flex-1 min-w-0 overflow-hidden">
                <!-- hubs + rooms sidebar -->
                <div
                    v-if="!isPopoutMode"
                    class="flex-col shrink-0 border-r border-sem-border bg-sem-canvas"
                    :class="[
                        selectedRoom ? 'hidden md:flex' : 'flex',
                        effectiveSidebarCollapsed ? 'w-16 min-w-16 max-w-16' : 'w-full md:w-72',
                    ]"
                >
                    <div
                        class="flex h-10 shrink-0 items-center border-b border-sem-border px-2"
                        :class="effectiveSidebarCollapsed ? 'justify-center' : 'justify-between gap-2'"
                    >
                        <div v-if="!effectiveSidebarCollapsed" class="flex items-center gap-2 min-w-0">
                            <MaterialDesignIcon icon-name="forum" class="size-5 shrink-0 text-sem-accent" />
                            <span class="font-semibold truncate">{{ $t("relay_chat.title") }}</span>
                        </div>
                        <button
                            type="button"
                            class="rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30 transition-colors"
                            :title="
                                effectiveSidebarCollapsed
                                    ? $t('relay_chat.expand_sidebar')
                                    : $t('relay_chat.collapse_sidebar')
                            "
                            @click="relaySidebarCollapsed = !relaySidebarCollapsed"
                        >
                            <MaterialDesignIcon
                                :icon-name="effectiveSidebarCollapsed ? 'chevron-right' : 'chevron-left'"
                                class="size-5"
                            />
                        </button>
                    </div>

                    <div v-if="effectiveSidebarCollapsed" class="flex flex-1 flex-col items-center gap-1 py-2 px-1">
                        <button
                            type="button"
                            class="rounded-xl border-2 border-dashed border-sem-border p-2 text-sem-fg-muted hover:border-sem-accent hover:text-sem-accent"
                            :title="$t('relay_chat.add_hub')"
                            @click="openAddHub"
                        >
                            <MaterialDesignIcon icon-name="plus" class="size-5" />
                        </button>
                        <button
                            v-for="hub in hubs"
                            :key="hub.hub_hash"
                            type="button"
                            class="relative rounded-xl p-2 transition-colors hover:bg-sem-surface/60"
                            :class="{ 'ring-2 ring-sem-accent': hub.hub_hash === selectedHubHash }"
                            :title="hubDisplayName(hub)"
                            @click="onCollapsedHubClick(hub)"
                        >
                            <MaterialDesignIcon
                                :icon-name="hubIconName(hub)"
                                class="size-6"
                                :class="statusIconColor(hub.status)"
                            />
                            <span
                                v-if="hubTotalUnread(hub) > 0"
                                class="absolute -top-0.5 -right-0.5 min-w-[14px] rounded-full bg-red-500 px-0.5 text-[9px] font-bold leading-tight text-white"
                            >
                                {{ formatUnreadBadge(hubTotalUnread(hub)) }}
                            </span>
                        </button>
                    </div>

                    <div
                        v-else
                        class="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1.5"
                        @contextmenu.prevent="openSidebarContextMenu($event, {})"
                    >
                        <button
                            type="button"
                            class="flex w-full items-center gap-2 rounded-xl border-2 border-dashed border-sem-border px-3 py-3 text-left text-sm text-sem-fg-muted transition-colors hover:border-sem-accent hover:bg-sem-surface/40 hover:text-sem-accent"
                            @click="openAddHub"
                        >
                            <MaterialDesignIcon icon-name="plus-circle-outline" class="size-5 shrink-0" />
                            <span class="font-medium">{{ $t("relay_chat.add_hub_card") }}</span>
                        </button>

                        <div
                            v-for="(hub, hubIndex) in hubs"
                            :key="hub.hub_hash"
                            class="overflow-hidden rounded-xl border border-sem-border bg-sem-canvas"
                            :class="{ 'opacity-60': dragHubIndex === hubIndex }"
                            draggable="true"
                            @dragstart="onHubDragStart(hubIndex, $event)"
                            @dragover.prevent="onHubDragOver(hubIndex)"
                            @drop.prevent="onHubDrop(hubIndex)"
                            @dragend="dragHubIndex = null"
                            @contextmenu.prevent="openSidebarContextMenu($event, { hub })"
                        >
                            <button
                                type="button"
                                class="flex w-full items-center gap-2 px-3 py-2.5 text-left transition-colors hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30"
                                :class="{
                                    'bg-sem-surface/70 dark:bg-sem-surface/25': hub.hub_hash === selectedHubHash,
                                }"
                                @click="toggleHub(hub.hub_hash)"
                            >
                                <MaterialDesignIcon
                                    :icon-name="isExpanded(hub.hub_hash) ? 'chevron-down' : 'chevron-right'"
                                    class="size-4 shrink-0 text-sem-fg-muted"
                                />
                                <MaterialDesignIcon
                                    :icon-name="hubIconName(hub)"
                                    class="size-5 shrink-0"
                                    :class="statusIconColor(hub.status)"
                                />
                                <div class="min-w-0 flex-1">
                                    <div class="truncate font-medium leading-tight">{{ hubDisplayName(hub) }}</div>
                                    <div class="truncate text-xs" :class="statusTextColor(hub.status)">
                                        {{ statusLabel(hub.status) }}
                                    </div>
                                </div>
                                <span
                                    v-if="hubTotalUnread(hub) > 0"
                                    class="shrink-0 min-w-[1.25rem] rounded-full bg-red-500 px-1.5 py-0.5 text-center text-xs font-bold text-white"
                                >
                                    {{ formatUnreadBadge(hubTotalUnread(hub)) }}
                                </span>
                            </button>

                            <div
                                v-show="isExpanded(hub.hub_hash)"
                                class="border-t border-sem-border px-2.5 py-2.5 space-y-2.5"
                            >
                                <div class="flex items-center gap-1.5">
                                    <button
                                        v-if="!hub.connected"
                                        type="button"
                                        :class="[btnPrimary, 'flex-1 !py-1.5 !text-xs']"
                                        @click.stop="connectHub(hub)"
                                    >
                                        <MaterialDesignIcon icon-name="lan-connect" class="size-4" />
                                        {{ $t("relay_chat.connect") }}
                                    </button>
                                    <button
                                        v-else
                                        type="button"
                                        :class="[btnSecondary, 'flex-1 !py-1.5 !text-xs']"
                                        @click.stop="disconnectHub(hub)"
                                    >
                                        <MaterialDesignIcon icon-name="lan-disconnect" class="size-4" />
                                        {{ $t("relay_chat.disconnect") }}
                                    </button>
                                    <button
                                        type="button"
                                        :class="btnIconSm"
                                        :title="$t('relay_chat.settings')"
                                        @click.stop="openSettings(hub)"
                                    >
                                        <MaterialDesignIcon icon-name="cog" class="size-4" />
                                    </button>
                                    <button
                                        type="button"
                                        :class="btnDangerSm"
                                        :title="$t('relay_chat.remove_hub')"
                                        @click.stop="removeHub(hub)"
                                    >
                                        <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                                    </button>
                                </div>

                                <ul class="space-y-0.5">
                                    <li
                                        v-for="(roomName, roomIndex) in orderedRoomsFor(hub)"
                                        :key="roomName"
                                        class="flex items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-sm cursor-pointer transition-colors hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30"
                                        :class="{
                                            'bg-sem-action-primary/15 text-sem-accent font-medium':
                                                hub.hub_hash === selectedHubHash && roomName === selectedRoom,
                                            'opacity-60':
                                                dragRoomHubHash === hub.hub_hash && dragRoomIndex === roomIndex,
                                        }"
                                        :draggable="orderedRoomsFor(hub).length > 1"
                                        @dragstart="onRoomDragStart(hub, roomIndex, $event)"
                                        @dragover.prevent="onRoomDragOver(hub, roomIndex)"
                                        @drop.prevent="onRoomDrop(hub, roomIndex)"
                                        @dragend="onRoomDragEnd"
                                        @click="selectRoom(hub.hub_hash, roomName)"
                                        @contextmenu.prevent="openSidebarContextMenu($event, { hub, room: roomName })"
                                    >
                                        <span class="flex min-w-0 items-center gap-1.5">
                                            <MaterialDesignIcon
                                                icon-name="pound"
                                                class="size-3.5 shrink-0 opacity-60"
                                            />
                                            <span class="truncate">{{ roomName }}</span>
                                        </span>
                                        <span
                                            v-if="roomUnreadCount(hub, roomName) > 0"
                                            class="shrink-0 min-w-[1.125rem] rounded-full bg-red-500 px-1 text-center text-[10px] font-bold leading-4 text-white"
                                        >
                                            {{ formatUnreadBadge(roomUnreadCount(hub, roomName)) }}
                                        </span>
                                    </li>
                                    <li
                                        v-if="orderedRoomsFor(hub).length === 0"
                                        class="px-2.5 py-1 text-xs text-sem-fg-muted"
                                    >
                                        {{ $t("relay_chat.no_rooms") }}
                                    </li>
                                </ul>

                                <form class="flex gap-1.5" @submit.prevent="joinRoom(hub)">
                                    <input
                                        v-model="joinRoomName"
                                        type="text"
                                        :placeholder="$t('relay_chat.join_room_placeholder')"
                                        class="input-field !py-1.5 !text-xs"
                                    />
                                    <button type="submit" :class="btnIconSm" :title="$t('relay_chat.join_room')">
                                        <MaterialDesignIcon icon-name="plus" class="size-4" />
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- conversation pane -->
                <div
                    class="flex min-h-0 flex-1 min-w-0 flex-col overflow-hidden bg-sem-canvas md:flex"
                    :class="selectedRoom ? 'flex' : 'hidden md:flex'"
                >
                    <div
                        v-if="selectedHub && selectedRoom"
                        class="flex items-center justify-between gap-3 px-2 py-2.5 border-b border-sem-border bg-sem-canvas sm:px-3"
                    >
                        <div class="flex min-w-0 items-center gap-2">
                            <button
                                type="button"
                                class="md:hidden rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30"
                                :title="$t('relay_chat.back')"
                                @click="selectedRoom = null"
                            >
                                <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
                            </button>
                            <MaterialDesignIcon icon-name="pound" class="size-5 shrink-0 text-sem-accent" />
                            <div class="min-w-0">
                                <div class="font-semibold truncate leading-tight">{{ selectedRoom }}</div>
                                <div class="text-xs text-sem-fg-muted truncate">{{ hubDisplayName(selectedHub) }}</div>
                            </div>
                        </div>
                        <div class="flex items-center gap-1.5 shrink-0">
                            <button
                                type="button"
                                :class="btnIcon"
                                :title="$t('relay_chat.search_messages')"
                                @click="showSearch = !showSearch"
                            >
                                <MaterialDesignIcon icon-name="magnify" class="size-5" />
                            </button>
                            <button
                                type="button"
                                :class="btnIcon"
                                :title="$t('relay_chat.popout_channel')"
                                @click="popoutChannel"
                            >
                                <MaterialDesignIcon icon-name="open-in-new" class="size-5" />
                            </button>
                            <button
                                type="button"
                                :title="showMembers ? $t('relay_chat.hide_members') : $t('relay_chat.show_members')"
                                class="inline-flex items-center gap-1 rounded-lg border px-2 py-1.5 text-sm font-medium transition"
                                :class="
                                    showMembers
                                        ? 'border-sem-action-primary bg-sem-action-primary/15 text-sem-accent'
                                        : 'border-sem-border bg-sem-canvas text-sem-fg hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30'
                                "
                                @click="showMembers = !showMembers"
                            >
                                <MaterialDesignIcon icon-name="account-group" class="size-5" />
                                <span class="text-xs font-semibold">{{ onlineMembers.length }}</span>
                            </button>
                            <button
                                type="button"
                                :class="btnIcon"
                                :title="$t('relay_chat.clear_messages')"
                                @click="clearMessages"
                            >
                                <MaterialDesignIcon icon-name="broom" class="size-5" />
                            </button>
                            <button
                                type="button"
                                :class="btnDanger"
                                :title="$t('relay_chat.leave_room')"
                                @click="leaveRoom"
                            >
                                <MaterialDesignIcon icon-name="exit-to-app" class="size-5" />
                            </button>
                        </div>
                    </div>

                    <div
                        v-if="selectedHub && selectedHub.motd && selectedRoom"
                        class="flex items-start gap-2 px-3 py-2 text-xs border-b border-sem-border bg-sem-canvas text-sem-fg-secondary"
                    >
                        <MaterialDesignIcon
                            icon-name="information-outline"
                            class="size-4 shrink-0 mt-0.5 text-sem-accent"
                        />
                        <span>{{ selectedHub.motd }}</span>
                    </div>

                    <div class="relative flex flex-1 min-h-0 overflow-hidden">
                        <!-- messages -->
                        <div class="flex flex-1 min-w-0 flex-col min-h-0">
                            <div
                                ref="messageList"
                                class="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-1.5 sm:p-4"
                            >
                                <div
                                    v-if="!selectedRoom"
                                    class="h-full flex flex-col items-center justify-center gap-2 text-center text-sem-fg-muted"
                                >
                                    <MaterialDesignIcon icon-name="chat-outline" class="size-10 opacity-40" />
                                    {{ $t("relay_chat.no_room_selected") }}
                                </div>
                                <template v-else>
                                    <template v-for="entry in messageTimeline" :key="timelineEntryKey(entry)">
                                        <div
                                            v-if="entry.type === 'dateDivider'"
                                            class="flex items-center justify-center gap-3 w-full my-3 shrink-0 px-2 select-none"
                                            role="separator"
                                            :aria-label="formatDateDividerLabel(entry.dayKey)"
                                        >
                                            <span class="h-px w-10 shrink-0 bg-sem-border sm:w-14" aria-hidden="true" />
                                            <span
                                                class="max-w-[min(100%,18rem)] text-center text-[11px] font-medium leading-snug tracking-wide text-sem-fg-muted"
                                            >
                                                {{ formatDateDividerLabel(entry.dayKey) }}
                                            </span>
                                            <span class="h-px w-10 shrink-0 bg-sem-border sm:w-14" aria-hidden="true" />
                                        </div>
                                        <template v-else-if="entry.msg">
                                            <div
                                                v-if="
                                                    entry.msg.kind === 'system' ||
                                                    entry.msg.kind === 'notice' ||
                                                    entry.msg.kind === 'error'
                                                "
                                                class="py-0.5 text-center text-xs italic"
                                                :class="
                                                    entry.msg.kind === 'error' ? 'text-sem-danger' : 'text-sem-fg-muted'
                                                "
                                                :data-msg-key="messageKey(entry.msg)"
                                            >
                                                {{ entry.msg.text }}
                                            </div>
                                            <div
                                                v-else-if="entry.msg.kind === 'action'"
                                                class="rounded-lg px-2 py-1 text-sm italic"
                                                :class="entry.msg.mention ? 'bg-sem-warning/15' : ''"
                                                :data-msg-key="messageKey(entry.msg)"
                                            >
                                                <span class="mr-1 text-xs text-sem-fg-muted">{{
                                                    formatTime(entry.msg.ts)
                                                }}</span>
                                                * {{ displayName(entry.msg) }} {{ entry.msg.text }}
                                            </div>
                                            <div
                                                v-else
                                                class="rounded-lg px-2 py-1 text-sm"
                                                :class="
                                                    entry.msg.mention
                                                        ? 'bg-sem-warning/15'
                                                        : 'hover:bg-sem-surface/40 dark:hover:bg-sem-surface/20'
                                                "
                                                :data-msg-key="messageKey(entry.msg)"
                                                @contextmenu.prevent="openMessageContextMenu($event, entry.msg)"
                                            >
                                                <span class="mr-1.5 text-xs text-sem-fg-muted">{{
                                                    formatTime(entry.msg.ts)
                                                }}</span>
                                                <span class="mr-1.5 font-semibold" :style="nameStyle(entry.msg)"
                                                    >{{ displayName(entry.msg) }}:</span
                                                >
                                                <span class="whitespace-pre-wrap break-words">{{
                                                    entry.msg.text
                                                }}</span>
                                            </div>
                                        </template>
                                    </template>
                                </template>
                            </div>

                            <form
                                v-if="selectedHub && selectedRoom"
                                class="flex items-center gap-2 p-2.5 border-t border-sem-border bg-sem-canvas"
                                @submit.prevent="sendMessage"
                            >
                                <input
                                    ref="composerInput"
                                    v-model="composer"
                                    type="text"
                                    :maxlength="selectedHub.max_msg_body_bytes || 350"
                                    :placeholder="$t('relay_chat.message_placeholder')"
                                    class="input-field"
                                />
                                <button
                                    type="submit"
                                    :class="[btnPrimary, 'shrink-0 !p-2.5']"
                                    :title="$t('relay_chat.send')"
                                    :disabled="!composer.trim() || sending"
                                >
                                    <MaterialDesignIcon icon-name="send" class="size-5" />
                                </button>
                            </form>
                        </div>

                        <!-- members panel -->
                        <div
                            v-show="showMembers && selectedRoom"
                            class="absolute inset-y-0 right-0 z-40 flex w-72 max-w-[min(18rem,100%)] min-h-0 flex-col border-l border-sem-border bg-sem-canvas shadow-xl md:static md:z-auto md:max-w-none md:w-72 md:shadow-none"
                        >
                            <div
                                class="flex shrink-0 items-center justify-between gap-2 border-b border-sem-border px-3 py-2.5"
                            >
                                <div class="flex items-center gap-1.5 font-semibold">
                                    <MaterialDesignIcon icon-name="account-group" class="size-4 text-sem-accent" />
                                    {{ $t("relay_chat.members_title") }}
                                </div>
                                <button
                                    type="button"
                                    class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30"
                                    :title="$t('relay_chat.hide_members')"
                                    @click="showMembers = false"
                                >
                                    <MaterialDesignIcon icon-name="close" class="size-4" />
                                </button>
                            </div>
                            <div class="shrink-0 border-b border-sem-border p-2">
                                <input
                                    v-model="membersSearch"
                                    type="search"
                                    :placeholder="$t('relay_chat.members_search_placeholder')"
                                    class="input-field !py-1.5 !text-xs"
                                />
                            </div>
                            <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-2 space-y-3">
                                <div>
                                    <div
                                        class="px-1 pb-1 text-xs font-semibold uppercase tracking-wide text-sem-fg-muted"
                                    >
                                        {{ $t("relay_chat.members_online") }} ({{ filteredOnlineMembers.length }})
                                    </div>
                                    <ul class="space-y-0.5">
                                        <li
                                            v-for="m in filteredOnlineMembers"
                                            :key="m.hash"
                                            class="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30"
                                            :title="m.hash"
                                            @click="insertMention(m.name)"
                                        >
                                            <span class="size-2 shrink-0 rounded-full bg-sem-success"></span>
                                            <span class="truncate" :style="{ color: colorForHash(m.hash) }">{{
                                                m.name
                                            }}</span>
                                        </li>
                                    </ul>
                                </div>
                                <div v-if="filteredOfflineMembers.length > 0">
                                    <div
                                        class="px-1 pb-1 text-xs font-semibold uppercase tracking-wide text-sem-fg-muted"
                                    >
                                        {{ $t("relay_chat.members_offline") }} ({{ filteredOfflineMembers.length }})
                                    </div>
                                    <ul class="space-y-0.5">
                                        <li
                                            v-for="m in filteredOfflineMembers"
                                            :key="m.hash"
                                            class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm opacity-60"
                                            :title="m.hash"
                                        >
                                            <span class="size-2 shrink-0 rounded-full bg-sem-fg-muted"></span>
                                            <span class="truncate">{{ m.name }}</span>
                                        </li>
                                    </ul>
                                </div>
                                <div
                                    v-if="
                                        membersSearch.trim() &&
                                        filteredOnlineMembers.length === 0 &&
                                        filteredOfflineMembers.length === 0
                                    "
                                    class="px-2 py-4 text-center text-xs text-sem-fg-muted"
                                >
                                    {{ $t("relay_chat.members_search_no_results") }}
                                </div>
                                <div
                                    v-else-if="onlineMembers.length === 0 && offlineMembers.length === 0"
                                    class="px-2 py-4 text-center text-xs text-sem-fg-muted"
                                >
                                    {{ $t("relay_chat.no_members") }}
                                </div>
                            </div>
                        </div>
                        <div
                            v-if="showMembers && selectedRoom"
                            class="absolute inset-0 z-30 bg-black/40 md:hidden"
                            @click="showMembers = false"
                        ></div>

                        <!-- search panel -->
                        <div
                            v-show="showSearch && selectedRoom"
                            class="absolute inset-y-0 right-0 z-40 flex w-80 max-w-[min(20rem,100%)] min-h-0 flex-col border-l border-sem-border bg-sem-canvas shadow-xl md:static md:z-auto md:max-w-none md:w-80 md:shadow-none"
                        >
                            <div
                                class="flex shrink-0 items-center justify-between gap-2 border-b border-sem-border px-3 py-2.5"
                            >
                                <div class="flex items-center gap-1.5 font-semibold">
                                    <MaterialDesignIcon icon-name="magnify" class="size-4 text-sem-accent" />
                                    {{ $t("relay_chat.search_messages") }}
                                </div>
                                <button
                                    type="button"
                                    class="rounded-lg p-1 text-sem-fg-muted hover:bg-sem-surface/60"
                                    @click="showSearch = false"
                                >
                                    <MaterialDesignIcon icon-name="close" class="size-4" />
                                </button>
                            </div>
                            <div class="shrink-0 border-b border-sem-border p-2">
                                <input
                                    v-model="messageSearch"
                                    type="text"
                                    :placeholder="$t('relay_chat.search_messages_placeholder')"
                                    class="input-field !py-1.5 !text-xs"
                                />
                            </div>
                            <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
                                <div
                                    v-if="!messageSearch.trim()"
                                    class="flex flex-col items-center gap-2 px-3 py-8 text-center text-xs text-sem-fg-muted"
                                >
                                    <MaterialDesignIcon icon-name="magnify" class="size-8 opacity-40" />
                                    <div class="font-medium text-sem-fg-secondary">
                                        {{ $t("relay_chat.search_empty_hint") }}
                                    </div>
                                    <div class="leading-relaxed">{{ $t("relay_chat.search_syntax_hint") }}</div>
                                </div>
                                <div
                                    v-else-if="searchResults.length === 0"
                                    class="px-2 py-4 text-center text-xs text-sem-fg-muted"
                                >
                                    {{ $t("relay_chat.search_no_results") }}
                                </div>
                                <button
                                    v-for="msg in searchResults"
                                    :key="'search-' + messageKey(msg)"
                                    type="button"
                                    class="w-full rounded-lg px-2 py-1.5 text-left text-xs hover:bg-sem-surface/60"
                                    @click="scrollToMessage(msg)"
                                >
                                    <span class="font-semibold" :style="nameStyle(msg)">{{ displayName(msg) }}</span>
                                    <span class="ml-1 text-sem-fg-muted">{{ formatTime(msg.ts) }}</span>
                                    <div class="truncate text-sem-fg-secondary">{{ msg.text }}</div>
                                </button>
                            </div>
                        </div>
                        <div
                            v-if="showSearch && selectedRoom"
                            class="absolute inset-0 z-30 bg-black/40 md:hidden"
                            @click="showSearch = false"
                        ></div>
                    </div>
                </div>
            </div>

            <!-- discovery view -->
            <div v-show="view === 'discovery'" class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                <div class="mx-auto w-full max-w-3xl space-y-4">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h2 class="text-lg font-semibold">{{ $t("relay_chat.discovery_title") }}</h2>
                            <p class="text-sm text-sem-fg-muted">{{ $t("relay_chat.discovery_subtitle") }}</p>
                        </div>
                        <button
                            type="button"
                            :class="btnSecondary"
                            :disabled="discoveryLoading"
                            @click="refreshDiscovered"
                        >
                            <MaterialDesignIcon
                                icon-name="refresh"
                                class="size-4"
                                :class="{ 'animate-spin': discoveryLoading }"
                            />
                            {{ $t("relay_chat.refresh") }}
                        </button>
                    </div>

                    <div class="relative">
                        <MaterialDesignIcon
                            icon-name="magnify"
                            class="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-sem-fg-muted"
                        />
                        <input
                            v-model="discoverySearch"
                            type="text"
                            :placeholder="$t('relay_chat.discovery_search')"
                            class="input-field !pl-9"
                            @input="onDiscoverySearch"
                        />
                    </div>

                    <div
                        v-if="discovered.length === 0"
                        class="flex flex-col items-center gap-2 rounded-xl border border-sem-border bg-sem-canvas p-8 text-center text-sm text-sem-fg-muted"
                    >
                        <MaterialDesignIcon icon-name="radar" class="size-10 opacity-40" />
                        {{ $t("relay_chat.discovery_empty") }}
                    </div>

                    <div
                        v-for="node in discovered"
                        :key="node.destination_hash"
                        class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sem-border bg-sem-canvas p-4 transition-colors hover:border-sem-border-strong"
                    >
                        <div class="min-w-0 flex-1">
                            <div class="flex items-center gap-2">
                                <MaterialDesignIcon icon-name="forum-outline" class="size-4 shrink-0 text-sem-accent" />
                                <span class="truncate font-semibold">{{ nodeName(node) }}</span>
                            </div>
                            <button
                                type="button"
                                class="mt-1 flex items-center gap-1.5 font-mono text-xs text-sem-fg-muted hover:text-sem-accent"
                                :title="$t('relay_chat.copy_hash')"
                                @click="copyHash(node.destination_hash)"
                            >
                                <MaterialDesignIcon icon-name="content-copy" class="size-3.5" />
                                <span class="truncate">{{ formatHash(node.destination_hash) }}</span>
                            </button>
                            <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-sem-fg-muted">
                                <span class="inline-flex items-center gap-1">
                                    <MaterialDesignIcon icon-name="clock-outline" class="size-3.5" />
                                    {{ $t("relay_chat.announced_ago", { time: timeAgo(node.updated_at) }) }}
                                </span>
                                <span v-if="node.hops != null" class="inline-flex items-center gap-1">
                                    <MaterialDesignIcon icon-name="transit-connection-variant" class="size-3.5" />
                                    {{ $t("relay_chat.hops_away", { count: node.hops }) }}
                                </span>
                            </div>
                        </div>
                        <button
                            v-if="isHubAdded(node.destination_hash)"
                            type="button"
                            :class="btnSecondary"
                            @click="openDiscovered(node)"
                        >
                            <MaterialDesignIcon icon-name="open-in-app" class="size-4" />
                            {{ $t("relay_chat.discovery_open") }}
                        </button>
                        <button v-else type="button" :class="btnPrimary" @click="addFromDiscovery(node)">
                            <MaterialDesignIcon icon-name="plus" class="size-4" />
                            {{ $t("relay_chat.discovery_add") }}
                        </button>
                    </div>
                </div>
            </div>

            <!-- host view -->
            <div v-show="view === 'host'" class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                <div class="mx-auto w-full max-w-3xl space-y-4">
                    <div class="flex flex-wrap items-start justify-between gap-3">
                        <div>
                            <h2 class="text-lg font-semibold">{{ $t("relay_chat.host_title") }}</h2>
                            <p class="text-sm text-sem-fg-muted">{{ $t("relay_chat.host_subtitle") }}</p>
                        </div>
                        <button type="button" :class="btnPrimary" @click="openCreateHub">
                            <MaterialDesignIcon icon-name="plus" class="size-4" />
                            {{ $t("relay_chat.create_hub") }}
                        </button>
                    </div>

                    <div
                        v-if="serverHubs.length === 0"
                        class="flex flex-col items-center gap-2 rounded-xl border border-sem-border bg-sem-canvas p-8 text-center text-sm text-sem-fg-muted"
                    >
                        <MaterialDesignIcon icon-name="server-network-off" class="size-10 opacity-40" />
                        {{ $t("relay_chat.no_hosted_hubs") }}
                    </div>

                    <div
                        v-for="hub in serverHubs"
                        :key="hub.id"
                        class="rounded-xl border border-sem-border bg-sem-canvas p-4 space-y-3"
                    >
                        <div class="flex flex-wrap items-start justify-between gap-3">
                            <div class="min-w-0 flex-1">
                                <div class="flex items-center gap-2">
                                    <span
                                        class="size-2 shrink-0 rounded-full"
                                        :class="hub.running ? 'bg-sem-success' : 'bg-sem-fg-muted'"
                                    ></span>
                                    <span class="font-semibold truncate">{{ hub.name }}</span>
                                </div>
                                <button
                                    type="button"
                                    class="mt-1 flex items-center gap-1.5 text-xs font-mono text-sem-fg-muted hover:text-sem-accent"
                                    :title="$t('relay_chat.copy_hash')"
                                    @click="copyHash(hub.dest_hash)"
                                >
                                    <MaterialDesignIcon icon-name="content-copy" class="size-3.5" />
                                    <span class="truncate">{{ formatHash(hub.dest_hash) }}</span>
                                </button>
                            </div>
                            <div class="flex shrink-0 items-center gap-1.5">
                                <button
                                    v-if="!hub.running"
                                    type="button"
                                    :class="[btnSecondary, '!px-2.5 !py-1.5 !text-xs']"
                                    @click="startServerHub(hub)"
                                >
                                    <MaterialDesignIcon icon-name="play" class="size-4" />
                                    {{ $t("relay_chat.host_start") }}
                                </button>
                                <button
                                    v-else
                                    type="button"
                                    :class="[btnSecondary, '!px-2.5 !py-1.5 !text-xs']"
                                    @click="stopServerHub(hub)"
                                >
                                    <MaterialDesignIcon icon-name="stop" class="size-4" />
                                    {{ $t("relay_chat.host_stop") }}
                                </button>
                                <button
                                    type="button"
                                    :class="btnIcon"
                                    :title="$t('relay_chat.host_announce')"
                                    :disabled="!hub.running"
                                    @click="announceServerHub(hub)"
                                >
                                    <MaterialDesignIcon icon-name="bullhorn-outline" class="size-4" />
                                </button>
                                <button
                                    type="button"
                                    :class="btnDanger"
                                    :title="$t('relay_chat.host_delete')"
                                    @click="deleteServerHub(hub)"
                                >
                                    <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                                </button>
                            </div>
                        </div>

                        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-sem-fg-muted">
                            <button
                                type="button"
                                class="inline-flex items-center gap-1 rounded-md px-1 py-0.5 transition-colors hover:bg-sem-surface/60 hover:text-sem-fg"
                                :title="$t('relay_chat.show_members')"
                                :disabled="!hub.running || hub.clients === 0"
                                @click="openHostMembers(hub)"
                            >
                                <MaterialDesignIcon icon-name="account-group" class="size-3.5" />
                                {{ hub.clients }} {{ $t("relay_chat.host_clients") }}
                            </button>
                            <button
                                type="button"
                                class="inline-flex items-center gap-1 rounded-md px-1 py-0.5 transition-colors hover:bg-sem-surface/60 hover:text-sem-fg"
                                :title="$t('relay_chat.host_manage_rooms')"
                                @click="openHostRooms(hub)"
                            >
                                <MaterialDesignIcon icon-name="pound" class="size-3.5" />
                                {{ hub.rooms.length }} {{ $t("relay_chat.host_rooms") }}
                            </button>
                        </div>

                        <button
                            type="button"
                            :class="[btnSecondary, 'w-full !py-2 !text-xs']"
                            @click="openHostRooms(hub)"
                        >
                            <MaterialDesignIcon icon-name="door-open" class="size-4" />
                            {{ $t("relay_chat.host_manage_rooms") }}
                        </button>
                    </div>
                </div>
            </div>

            <RelayHostMembersModal
                :open="hostMembersModal.open"
                :hub="hostMembersModal.hub"
                :room="hostMembersModal.room"
                @close="closeHostMembers"
                @refresh="fetchServers"
            />
            <RelayHostRoomsModal
                :open="hostRoomsModal.open"
                :hub="hostRoomsModal.hub"
                @close="closeHostRooms"
                @refresh="fetchServers"
            />

            <!-- create hub dialog -->
            <div
                v-if="showCreateHub"
                class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
                @click.self="showCreateHub = false"
            >
                <div class="w-full max-w-md rounded-2xl border border-sem-border-card bg-sem-surface p-5 shadow-xl">
                    <h2 class="mb-4 text-lg font-semibold">{{ $t("relay_chat.create_hub_title") }}</h2>
                    <form class="space-y-4" @submit.prevent="createServerHub">
                        <div class="space-y-1.5">
                            <label class="block text-sm font-semibold text-sem-fg-secondary">{{
                                $t("relay_chat.hub_name")
                            }}</label>
                            <input
                                v-model="createHubForm.name"
                                type="text"
                                :placeholder="$t('relay_chat.hub_name_placeholder')"
                                class="input-field"
                            />
                        </div>
                        <div class="space-y-1.5">
                            <label class="block text-sm font-semibold text-sem-fg-secondary">{{
                                $t("relay_chat.host_greeting")
                            }}</label>
                            <input
                                v-model="createHubForm.greeting"
                                type="text"
                                :placeholder="$t('relay_chat.host_greeting_placeholder')"
                                class="input-field"
                            />
                        </div>
                        <label class="flex items-center gap-2 text-sm">
                            <input v-model="createHubForm.announce" type="checkbox" class="size-4" />
                            {{ $t("relay_chat.host_announce_periodically") }}
                        </label>
                        <div class="flex justify-end gap-2 pt-1">
                            <button type="button" :class="btnSecondary" @click="showCreateHub = false">
                                {{ $t("common.cancel") }}
                            </button>
                            <button type="submit" :class="btnPrimary">{{ $t("relay_chat.create_hub") }}</button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- add hub dialog -->
            <div
                v-if="showAddHub"
                class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
                @click.self="showAddHub = false"
            >
                <div class="w-full max-w-md rounded-2xl border border-sem-border-card bg-sem-surface p-5 shadow-xl">
                    <h2 class="mb-4 text-lg font-semibold">{{ $t("relay_chat.add_hub_title") }}</h2>
                    <form class="space-y-4" @submit.prevent="addHub">
                        <div class="space-y-1.5">
                            <label class="block text-sm font-semibold text-sem-fg-secondary">{{
                                $t("relay_chat.hub_hash")
                            }}</label>
                            <input
                                v-model="addHubForm.hub_hash"
                                type="text"
                                :placeholder="$t('relay_chat.hub_hash_placeholder')"
                                class="input-field font-mono"
                            />
                        </div>
                        <div class="space-y-1.5">
                            <label class="block text-sm font-semibold text-sem-fg-secondary">{{
                                $t("relay_chat.hub_name")
                            }}</label>
                            <input
                                v-model="addHubForm.name"
                                type="text"
                                :placeholder="$t('relay_chat.hub_name_placeholder')"
                                class="input-field"
                            />
                        </div>
                        <div class="space-y-1.5">
                            <label class="block text-sm font-semibold text-sem-fg-secondary">{{
                                $t("relay_chat.dest_name")
                            }}</label>
                            <input
                                v-model="addHubForm.dest_name"
                                type="text"
                                placeholder="rrc.hub"
                                class="input-field font-mono"
                            />
                        </div>
                        <div class="flex justify-end gap-2 pt-1">
                            <button type="button" :class="btnSecondary" @click="showAddHub = false">
                                {{ $t("common.cancel") }}
                            </button>
                            <button type="submit" :class="btnPrimary">{{ $t("relay_chat.add_hub") }}</button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- hub settings dialog -->
            <div
                v-if="showSettings"
                class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
                @click.self="showSettings = false"
            >
                <div class="w-full max-w-md rounded-2xl border border-sem-border-card bg-sem-surface p-5 shadow-xl">
                    <h2 class="mb-4 text-lg font-semibold">{{ $t("relay_chat.settings") }}</h2>
                    <form class="space-y-4" @submit.prevent="saveSettings">
                        <div class="space-y-2">
                            <label class="block text-sm font-semibold text-sem-fg-secondary">{{
                                $t("relay_chat.hub_icon")
                            }}</label>
                            <div class="flex items-center gap-3">
                                <div
                                    class="flex size-12 shrink-0 items-center justify-center rounded-xl border border-sem-border bg-sem-canvas"
                                >
                                    <MaterialDesignIcon
                                        :icon-name="settingsHubIconPreview"
                                        class="size-7"
                                        :class="settingsHubStatusIconClass"
                                    />
                                </div>
                                <div class="flex min-w-0 flex-1 flex-wrap gap-2">
                                    <button
                                        type="button"
                                        :class="[btnSecondary, '!py-1.5 !text-xs']"
                                        @click="openIconPicker"
                                    >
                                        <MaterialDesignIcon icon-name="image-edit-outline" class="size-4" />
                                        {{ $t("relay_chat.hub_icon_choose") }}
                                    </button>
                                    <button
                                        v-if="settingsForm.hub_icon"
                                        type="button"
                                        class="text-xs text-sem-accent hover:underline"
                                        @click="settingsForm.hub_icon = null"
                                    >
                                        {{ $t("relay_chat.hub_icon_reset_default") }}
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="space-y-1.5">
                            <label class="block text-sm font-semibold text-sem-fg-secondary">{{
                                $t("relay_chat.hub_display_name")
                            }}</label>
                            <input
                                v-model="settingsForm.custom_name"
                                type="text"
                                :placeholder="settingsForm.default_name"
                                class="input-field"
                            />
                            <button
                                v-if="settingsForm.has_custom_name"
                                type="button"
                                class="text-xs text-sem-accent hover:underline"
                                @click="settingsForm.custom_name = ''"
                            >
                                {{ $t("relay_chat.revert_hub_name") }}
                            </button>
                        </div>
                        <label class="setting-toggle flex items-start gap-3">
                            <Toggle id="rrc-auto-reconnect" v-model="settingsForm.auto_reconnect" />
                            <span class="min-w-0 text-sm">
                                <span class="font-medium text-sem-fg">{{ $t("relay_chat.auto_reconnect") }}</span>
                            </span>
                        </label>
                        <label class="setting-toggle flex items-start gap-3">
                            <Toggle id="rrc-auto-list" v-model="settingsForm.auto_list" />
                            <span class="min-w-0 text-sm">
                                <span class="font-medium text-sem-fg">{{ $t("relay_chat.auto_list") }}</span>
                            </span>
                        </label>
                        <label class="setting-toggle flex items-start gap-3">
                            <Toggle id="rrc-auto-who" v-model="settingsForm.auto_who" />
                            <span class="min-w-0 text-sm">
                                <span class="font-medium text-sem-fg">{{ $t("relay_chat.auto_who") }}</span>
                            </span>
                        </label>
                        <div class="space-y-1.5">
                            <label class="block text-sm font-semibold text-sem-fg-secondary">{{
                                $t("relay_chat.nickname")
                            }}</label>
                            <input
                                v-model="settingsForm.nick"
                                type="text"
                                :placeholder="$t('relay_chat.nickname_placeholder')"
                                class="input-field"
                            />
                        </div>
                        <div class="flex justify-end gap-2 pt-1">
                            <button type="button" :class="btnSecondary" @click="showSettings = false">
                                {{ $t("common.cancel") }}
                            </button>
                            <button type="submit" :class="btnPrimary">{{ $t("relay_chat.save") }}</button>
                        </div>
                    </form>
                </div>
            </div>

            <MdiIconPickerModal
                :open="showIconPicker"
                :selected-icon="settingsForm.hub_icon"
                :preview-icon-class="settingsHubStatusIconClass"
                @close="showIconPicker = false"
                @select="onHubIconPicked"
            />

            <ContextMenuPanel :show="sidebarMenu.show" :x="sidebarMenu.x" :y="sidebarMenu.y" @click="closeSidebarMenu">
                <ContextMenuItem v-if="!sidebarMenu.hub" @click="openAddHubFromMenu">
                    {{ $t("relay_chat.ctx_add_hub") }}
                </ContextMenuItem>
                <template v-if="sidebarMenu.hub">
                    <ContextMenuItem v-if="!sidebarMenu.room" @click="focusJoinRoomFromMenu">
                        {{ $t("relay_chat.ctx_add_room") }}
                    </ContextMenuItem>
                    <ContextMenuItem v-if="!sidebarMenu.room && !sidebarMenu.hub.connected" @click="connectHubFromMenu">
                        {{ $t("relay_chat.ctx_connect_hub") }}
                    </ContextMenuItem>
                    <ContextMenuItem
                        v-if="!sidebarMenu.room && sidebarMenu.hub.connected"
                        @click="disconnectHubFromMenu"
                    >
                        {{ $t("relay_chat.ctx_disconnect_hub") }}
                    </ContextMenuItem>
                    <ContextMenuItem @click="openSettingsFromMenu">
                        {{ $t("relay_chat.ctx_hub_settings") }}
                    </ContextMenuItem>
                    <ContextMenuItem v-if="sidebarMenu.room" @click="leaveRoomFromMenu">
                        {{ $t("relay_chat.ctx_leave_room") }}
                    </ContextMenuItem>
                    <ContextMenuDivider />
                    <ContextMenuItem class="text-sem-danger" @click="removeHubFromMenu">
                        {{ $t("relay_chat.ctx_remove_hub") }}
                    </ContextMenuItem>
                </template>
            </ContextMenuPanel>

            <ContextMenuPanel :show="messageMenu.show" :x="messageMenu.x" :y="messageMenu.y" @click="closeMessageMenu">
                <ContextMenuItem
                    v-if="messageMenu.msg && canQuoteMessage(messageMenu.msg)"
                    @click="replyWithQuoteFromMenu"
                >
                    {{ $t("relay_chat.ctx_reply_quote") }}
                </ContextMenuItem>
                <ContextMenuItem
                    v-if="messageMenu.msg && canMentionMessageAuthor(messageMenu.msg)"
                    @click="mentionUserFromMenu"
                >
                    {{ $t("relay_chat.ctx_mention_user") }}
                </ContextMenuItem>
                <ContextMenuItem v-if="messageMenu.msg && messageMenu.msg.text" @click="copyMessageFromMenu">
                    {{ $t("relay_chat.ctx_copy_message") }}
                </ContextMenuItem>
                <template v-if="messageMenu.msg && canModerateSelectedHub">
                    <ContextMenuDivider />
                    <ContextMenuItem class="text-sem-danger" @click="kickUserFromMenu">
                        {{ $t("relay_chat.ctx_kick_user") }}
                    </ContextMenuItem>
                    <ContextMenuItem class="text-sem-danger" @click="banUserFromMenu">
                        {{ $t("relay_chat.ctx_ban_user") }}
                    </ContextMenuItem>
                </template>
            </ContextMenuPanel>
        </template>
    </div>
</template>

<script>
import { nextTick } from "vue";
import WebSocketConnection from "../../js/WebSocketConnection";
import GlobalState from "../../js/GlobalState";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import Utils from "../../js/Utils";
import { DEFAULT_RRC_HUB_ICON, normalizeMdiIconName } from "../../js/mdiIconNames.js";
import { countRelayMentions } from "../../js/relayMentionCount.js";
import { filterRelayMembers, filterRelayMessages } from "../../js/relayMessageSearch.js";
import { buildRelayMessageTimeline, relayMessageKey } from "../../js/relayMessageTimeline.js";
import { loadRelayLayout, saveRelayLayout } from "../../js/relayLayoutStore.js";
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import MdiIconPickerModal from "../MdiIconPickerModal.vue";
import RelayHostMembersModal from "./RelayHostMembersModal.vue";
import RelayHostRoomsModal from "./RelayHostRoomsModal.vue";
import ContextMenuPanel from "../contextmenu/ContextMenuPanel.vue";
import ContextMenuItem from "../contextmenu/ContextMenuItem.vue";
import ContextMenuDivider from "../contextmenu/ContextMenuDivider.vue";
import Toggle from "../forms/Toggle.vue";

const BTN_PRIMARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg bg-sem-action-primary px-3 py-2 text-sm font-semibold text-white transition hover:bg-sem-action-primary-hover disabled:opacity-50 disabled:cursor-not-allowed";
const BTN_SECONDARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg border border-sem-border bg-sem-surface-muted px-3 py-2 text-sm font-medium text-sem-fg transition hover:bg-sem-surface-raised disabled:opacity-50 disabled:cursor-not-allowed";
const BTN_ICON =
    "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-2 text-sem-fg transition hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30 disabled:opacity-50 disabled:cursor-not-allowed";
const BTN_ICON_SM =
    "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-1.5 text-sem-fg transition hover:bg-sem-surface/60 dark:hover:bg-sem-surface/30";
const BTN_DANGER =
    "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-2 text-sem-fg transition hover:border-sem-danger hover:text-sem-danger hover:bg-sem-danger/10 disabled:opacity-50 disabled:cursor-not-allowed";
const BTN_DANGER_SM =
    "inline-flex items-center justify-center rounded-lg border border-sem-border bg-sem-canvas p-1.5 text-sem-fg transition hover:border-sem-danger hover:text-sem-danger hover:bg-sem-danger/10";

const NAME_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6", "#3b82f6", "#8b5cf6", "#ec4899"];

export default {
    name: "RelayChatPage",
    components: {
        MaterialDesignIcon,
        MdiIconPickerModal,
        RelayHostMembersModal,
        RelayHostRoomsModal,
        ContextMenuPanel,
        ContextMenuItem,
        ContextMenuDivider,
        Toggle,
    },
    beforeRouteLeave(to, from, next) {
        this.persistRelayLayout();
        next();
    },
    props: {
        hubHash: { type: String, default: null },
        room: { type: String, default: null },
    },
    data() {
        return {
            btnPrimary: BTN_PRIMARY,
            btnSecondary: BTN_SECONDARY,
            btnIcon: BTN_ICON,
            btnIconSm: BTN_ICON_SM,
            btnDanger: BTN_DANGER,
            btnDangerSm: BTN_DANGER_SM,
            tabs: [
                { id: "chat", label: "relay_chat.tab_connect", icon: "forum" },
                { id: "discovery", label: "relay_chat.tab_discovery", icon: "radar" },
                { id: "host", label: "relay_chat.tab_host", icon: "server-network" },
            ],
            view: "chat",
            discovered: [],
            discoverySearch: "",
            discoverySearchTimer: null,
            discoveryLoading: false,
            serverHubs: [],
            roomForms: {},
            showCreateHub: false,
            createHubForm: {
                name: "",
                greeting: "",
                announce: true,
            },
            hubs: [],
            selectedHubHash: null,
            selectedRoom: null,
            expandedHubs: {},
            relaySidebarCollapsed: false,
            smUp: false,
            smMq: null,
            showMembers: false,
            showSearch: false,
            messageSearch: "",
            membersSearch: "",
            dragHubIndex: null,
            dragRoomHubHash: null,
            dragRoomIndex: null,
            sidebarMenu: {
                show: false,
                x: 0,
                y: 0,
                hub: null,
                room: null,
            },
            messageMenu: {
                show: false,
                x: 0,
                y: 0,
                msg: null,
            },
            messages: [],
            members: [],
            composer: "",
            sending: false,
            joinRoomName: "",
            showAddHub: false,
            addHubForm: {
                hub_hash: "",
                name: "",
                dest_name: "",
            },
            showSettings: false,
            showIconPicker: false,
            settingsHubHash: null,
            settingsForm: {
                auto_reconnect: true,
                auto_list: false,
                auto_who: false,
                nick: "",
                custom_name: "",
                default_name: "",
                has_custom_name: false,
                hub_icon: null,
            },
            hostMembersModal: {
                open: false,
                hub: null,
                room: null,
            },
            hostRoomsModal: {
                open: false,
                hub: null,
            },
        };
    },
    computed: {
        rrcEnabled() {
            return GlobalState.config?.rrc_enabled !== false;
        },
        isPopoutMode() {
            return Boolean(this.$route?.meta?.isPopout);
        },
        canModerateSelectedHub() {
            if (!this.selectedHub) {
                return false;
            }
            return this.serverHubs.some((s) => s.running && s.dest_hash === this.selectedHub.hub_hash);
        },
        effectiveSidebarCollapsed() {
            return this.relaySidebarCollapsed && this.smUp && !this.isPopoutMode;
        },
        selectedHub() {
            return this.hubs.find((hub) => hub.hub_hash === this.selectedHubHash) || null;
        },
        settingsHub() {
            if (!this.settingsHubHash) {
                return null;
            }
            return this.hubs.find((hub) => hub.hub_hash === this.settingsHubHash) || null;
        },
        settingsHubIconPreview() {
            return normalizeMdiIconName(this.settingsForm.hub_icon) || DEFAULT_RRC_HUB_ICON;
        },
        settingsHubStatusIconClass() {
            const status = this.settingsHub?.status ?? 0;
            return this.statusIconColor(status);
        },
        messageTimeline() {
            return buildRelayMessageTimeline(this.messages);
        },
        searchResults() {
            return filterRelayMessages(this.messages, this.messageSearch, (msg) => this.displayName(msg));
        },
        filteredOnlineMembers() {
            return filterRelayMembers(this.members, this.membersSearch);
        },
        filteredOfflineMembers() {
            return filterRelayMembers(this.offlineMembers, this.membersSearch);
        },
        onlineMembers() {
            return this.members;
        },
        offlineMembers() {
            const onlineHashes = new Set(this.members.map((m) => m.hash));
            const seen = new Map();
            for (const msg of this.messages) {
                if (!msg.src || onlineHashes.has(msg.src) || seen.has(msg.src)) {
                    continue;
                }
                seen.set(msg.src, { hash: msg.src, name: msg.nick || msg.src.slice(0, 12) });
            }
            return Array.from(seen.values()).sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
        },
    },
    watch: {
        relaySidebarCollapsed(collapsed) {
            localStorage.setItem("relayChatSidebarCollapsed", collapsed ? "1" : "0");
            this.persistRelayLayout();
        },
        selectedHubHash() {
            this.persistRelayLayout();
        },
        selectedRoom() {
            this.persistRelayLayout();
        },
        view() {
            this.persistRelayLayout();
        },
    },
    mounted() {
        WebSocketConnection.on("message", this.onWebsocketMessage);
        const saved = localStorage.getItem("relayChatSidebarCollapsed");
        if (saved === "1") {
            this.relaySidebarCollapsed = true;
        }
        this.smMq = window.matchMedia("(min-width: 640px)");
        this.smUp = this.smMq.matches;
        this.smMq.addEventListener("change", this.onSmMqChange);
        this.fetchHubs().then(() => {
            this.restoreRelayLayout();
            this.applyPopoutRoute();
            this.applyRouteQuery();
        });
        this.fetchServers();
        if (!this.isPopoutMode) {
            this.fetchDiscovered();
        }
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.onWebsocketMessage);
        if (this.discoverySearchTimer) {
            clearTimeout(this.discoverySearchTimer);
        }
        if (this.smMq) {
            this.smMq.removeEventListener("change", this.onSmMqChange);
        }
    },
    methods: {
        selectView(view) {
            this.view = view;
            this.persistRelayLayout();
            if (view === "discovery") {
                this.fetchDiscovered();
            } else if (view === "host") {
                this.fetchServers();
            }
        },
        persistRelayLayout() {
            if (this.isPopoutMode) {
                return;
            }
            saveRelayLayout({
                view: this.view,
                selectedHubHash: this.selectedHubHash,
                selectedRoom: this.selectedRoom,
                expandedHubs: { ...this.expandedHubs },
                relaySidebarCollapsed: this.relaySidebarCollapsed,
            });
        },
        restoreRelayLayout() {
            if (this.isPopoutMode) {
                return;
            }
            const saved = loadRelayLayout();
            if (!saved) {
                return;
            }
            if (saved.view === "chat" || saved.view === "discovery" || saved.view === "host") {
                this.view = saved.view;
            }
            if (typeof saved.relaySidebarCollapsed === "boolean") {
                this.relaySidebarCollapsed = saved.relaySidebarCollapsed;
            }
            if (saved.expandedHubs && typeof saved.expandedHubs === "object") {
                this.expandedHubs = { ...saved.expandedHubs };
            }
            if (saved.selectedHubHash && this.hubs.some((h) => h.hub_hash === saved.selectedHubHash)) {
                this.selectedHubHash = saved.selectedHubHash;
                this.expandedHubs[saved.selectedHubHash] = true;
                const hub = this.hubs.find((h) => h.hub_hash === saved.selectedHubHash);
                const rooms = hub ? this.orderedRoomsFor(hub) : [];
                if (saved.selectedRoom && rooms.includes(saved.selectedRoom)) {
                    this.selectRoom(saved.selectedHubHash, saved.selectedRoom, { restore: true });
                } else if (rooms.length > 0) {
                    this.selectRoom(saved.selectedHubHash, rooms[0], { restore: true });
                }
            }
        },
        orderedRoomsFor(hub) {
            if (!hub || !Array.isArray(hub.known_rooms)) {
                return [];
            }
            return hub.known_rooms;
        },
        onCollapsedHubClick(hub) {
            const rooms = this.orderedRoomsFor(hub);
            this.selectedHubHash = hub.hub_hash;
            this.expandedHubs[hub.hub_hash] = true;
            if (rooms.length > 0) {
                this.selectRoom(hub.hub_hash, rooms[0]);
            }
        },
        isExpanded(hubHash) {
            return !!this.expandedHubs[hubHash];
        },
        toggleHub(hubHash) {
            this.selectedHubHash = hubHash;
            this.expandedHubs[hubHash] = !this.expandedHubs[hubHash];
            this.persistRelayLayout();
        },
        statusLabel(status) {
            switch (status) {
                case 1:
                    return this.$t("relay_chat.status_connecting");
                case 2:
                    return this.$t("relay_chat.status_connected");
                case 3:
                    return this.$t("relay_chat.status_failed");
                default:
                    return this.$t("relay_chat.status_disconnected");
            }
        },
        statusTextColor(status) {
            if (status === 2) {
                return "text-sem-success";
            }
            if (status === 3) {
                return "text-sem-danger";
            }
            return "text-sem-fg-muted";
        },
        statusIconColor(status) {
            if (status === 2) {
                return "text-sem-success";
            }
            if (status === 1) {
                return "text-sem-warning";
            }
            return "text-sem-danger";
        },
        hubIconName(hub) {
            if (!hub) {
                return DEFAULT_RRC_HUB_ICON;
            }
            return normalizeMdiIconName(hub.hub_icon) || DEFAULT_RRC_HUB_ICON;
        },
        hubDisplayName(hub) {
            if (!hub) {
                return "";
            }
            if (hub.display_name) {
                return hub.display_name;
            }
            return hub.name || "";
        },
        formatUnreadBadge(count) {
            const n = Number(count) || 0;
            if (n <= 0) {
                return "";
            }
            if (n >= 1000) {
                return "999+";
            }
            return String(n);
        },
        hubTotalUnread(hub) {
            if (typeof hub.total_unread === "number") {
                return hub.total_unread;
            }
            const counts = hub.unread_counts;
            if (counts && typeof counts === "object") {
                return Object.values(counts).reduce((a, b) => a + (Number(b) || 0), 0);
            }
            return hub.unread_rooms ? hub.unread_rooms.length : 0;
        },
        roomUnreadCount(hub, room) {
            const counts = hub.unread_counts;
            if (counts && typeof counts === "object" && counts[room] != null) {
                return Number(counts[room]) || 0;
            }
            if (hub.unread_rooms && hub.unread_rooms.includes(room)) {
                return 1;
            }
            return 0;
        },
        updateUnreadBadge() {
            GlobalState.relayChatUnreadCount = countRelayMentions(this.hubs);
        },
        onSmMqChange() {
            this.smUp = this.smMq.matches;
        },
        onHubDragStart(index, event) {
            this.dragHubIndex = index;
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", String(index));
            }
        },
        onHubDragOver(index) {
            if (this.dragHubIndex === null || this.dragHubIndex === index) {
                return;
            }
            const hubs = [...this.hubs];
            const [moved] = hubs.splice(this.dragHubIndex, 1);
            hubs.splice(index, 0, moved);
            this.hubs = hubs;
            this.dragHubIndex = index;
        },
        async onHubDrop() {
            this.dragHubIndex = null;
            try {
                await window.api.put("/api/v1/rrc/hubs/order", {
                    hub_hashes: this.hubs.map((h) => h.hub_hash),
                });
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
                await this.fetchHubs();
            }
        },
        onRoomDragStart(hub, roomIndex, event) {
            if (this.orderedRoomsFor(hub).length <= 1) {
                return;
            }
            this.dragRoomHubHash = hub.hub_hash;
            this.dragRoomIndex = roomIndex;
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", String(roomIndex));
            }
        },
        onRoomDragOver(hub, roomIndex) {
            if (this.dragRoomHubHash !== hub.hub_hash || this.dragRoomIndex === null) {
                return;
            }
            if (this.dragRoomIndex === roomIndex) {
                return;
            }
            const rooms = [...this.orderedRoomsFor(hub)];
            const [moved] = rooms.splice(this.dragRoomIndex, 1);
            rooms.splice(roomIndex, 0, moved);
            hub.known_rooms = rooms;
            this.dragRoomIndex = roomIndex;
        },
        async onRoomDrop(hub) {
            if (this.dragRoomHubHash !== hub.hub_hash) {
                return;
            }
            this.onRoomDragEnd();
            try {
                await window.api.put(`/api/v1/rrc/hubs/${hub.hub_hash}/rooms/order`, {
                    room_names: this.orderedRoomsFor(hub),
                });
                await this.fetchHubs();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
                await this.fetchHubs();
            }
        },
        onRoomDragEnd() {
            this.dragRoomHubHash = null;
            this.dragRoomIndex = null;
        },
        openSidebarContextMenu(event, { hub = null, room = null }) {
            this.sidebarMenu = {
                show: true,
                x: event.clientX,
                y: event.clientY,
                hub,
                room,
            };
            this.closeMessageMenu();
        },
        closeSidebarMenu() {
            this.sidebarMenu.show = false;
        },
        openMessageContextMenu(event, msg) {
            if (!msg || msg.kind === "system" || msg.kind === "notice" || msg.kind === "error") {
                return;
            }
            this.messageMenu = {
                show: true,
                x: event.clientX,
                y: event.clientY,
                msg,
            };
            this.closeSidebarMenu();
        },
        closeMessageMenu() {
            this.messageMenu.show = false;
        },
        openAddHubFromMenu() {
            this.closeSidebarMenu();
            this.openAddHub();
        },
        focusJoinRoomFromMenu() {
            const hub = this.sidebarMenu.hub;
            this.closeSidebarMenu();
            if (!hub) {
                return;
            }
            this.selectedHubHash = hub.hub_hash;
            this.expandedHubs[hub.hub_hash] = true;
            nextTick(() => {
                const inputs = this.$el?.querySelectorAll?.("input.input-field");
                if (inputs && inputs.length > 0) {
                    inputs[inputs.length - 1].focus();
                }
            });
        },
        connectHubFromMenu() {
            const hub = this.sidebarMenu.hub;
            this.closeSidebarMenu();
            if (hub) {
                this.connectHub(hub);
            }
        },
        disconnectHubFromMenu() {
            const hub = this.sidebarMenu.hub;
            this.closeSidebarMenu();
            if (hub) {
                this.disconnectHub(hub);
            }
        },
        openSettingsFromMenu() {
            const hub = this.sidebarMenu.hub;
            this.closeSidebarMenu();
            if (hub) {
                this.openSettings(hub);
            }
        },
        async leaveRoomFromMenu() {
            const hub = this.sidebarMenu.hub;
            const room = this.sidebarMenu.room;
            this.closeSidebarMenu();
            if (!hub || !room) {
                return;
            }
            if (this.selectedHubHash === hub.hub_hash && this.selectedRoom === room) {
                await this.leaveRoom();
                return;
            }
            const confirmed = await DialogUtils.confirm(this.$t("relay_chat.leave_room_confirm"));
            if (!confirmed) {
                return;
            }
            try {
                await window.api.delete(`/api/v1/rrc/hubs/${hub.hub_hash}/rooms/${this.encodeRoom(room)}`);
                ToastUtils.success(this.$t("relay_chat.left_room"));
                await this.fetchHubs();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        removeHubFromMenu() {
            const hub = this.sidebarMenu.hub;
            this.closeSidebarMenu();
            if (hub) {
                this.removeHub(hub);
            }
        },
        canQuoteMessage(msg) {
            return Boolean(msg && typeof msg.text === "string" && msg.text.trim());
        },
        canMentionMessageAuthor(msg) {
            if (!msg || !this.selectedHub) {
                return false;
            }
            const name = this.displayName(msg);
            return Boolean(name && msg.kind === "msg");
        },
        replyWithQuoteFromMenu() {
            const msg = this.messageMenu.msg;
            this.closeMessageMenu();
            if (!msg) {
                return;
            }
            const author = this.displayName(msg);
            const prefix = `> ${author}: ${msg.text}\n\n`;
            const cur = this.composer || "";
            this.composer = cur + (cur && !cur.endsWith("\n") ? "\n" : "") + prefix;
            nextTick(() => this.$refs.composerInput?.focus?.());
        },
        mentionUserFromMenu() {
            const msg = this.messageMenu.msg;
            this.closeMessageMenu();
            if (msg) {
                this.insertMention(this.displayName(msg));
            }
        },
        copyMessageFromMenu() {
            const msg = this.messageMenu.msg;
            this.closeMessageMenu();
            if (!msg?.text) {
                return;
            }
            try {
                navigator.clipboard.writeText(msg.text);
                ToastUtils.success(this.$t("common.copied"));
            } catch {
                ToastUtils.error(this.$t("common.failed_to_copy"));
            }
        },
        async sendModerationCommand(template, msg) {
            if (!this.selectedHub || !this.selectedRoom || !msg) {
                return;
            }
            const target = this.displayName(msg);
            const room = this.selectedRoom;
            const text = template.replace("{room}", room).replace("{target}", target);
            try {
                await window.api.post(`/api/v1/rrc/hubs/${this.selectedHubHash}/command`, {
                    text,
                    room,
                });
                ToastUtils.success(this.$t("common.success"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        kickUserFromMenu() {
            const msg = this.messageMenu.msg;
            this.closeMessageMenu();
            this.sendModerationCommand("/kick {room} {target}", msg);
        },
        banUserFromMenu() {
            const msg = this.messageMenu.msg;
            this.closeMessageMenu();
            this.sendModerationCommand("/ban {room} add {target}", msg);
        },
        insertMention(name) {
            if (!name) {
                return;
            }
            const mention = "@" + name.replace(/\s/g, "") + " ";
            const cur = this.composer || "";
            this.composer = cur + (cur && !cur.endsWith(" ") ? " " : "") + mention;
            nextTick(() => {
                const el = this.$refs.composerInput;
                if (el && typeof el.focus === "function") {
                    el.focus();
                }
            });
        },
        popoutChannel() {
            if (!this.selectedHubHash || !this.selectedRoom) {
                return;
            }
            const hub = encodeURIComponent(this.selectedHubHash);
            const roomPath = encodeURIComponent(this.selectedRoom);
            const url = `${window.location.origin}${window.location.pathname}#/popout/relay-chat/${hub}/${roomPath}`;
            window.open(url, "_blank", "width=900,height=700,noopener");
        },
        applyPopoutRoute() {
            const hubHash = this.hubHash || this.$route?.params?.hubHash;
            const routeRoom = this.room || this.$route?.params?.room;
            if (!hubHash) {
                return;
            }
            this.view = "chat";
            this.selectedHubHash = decodeURIComponent(hubHash);
            this.expandedHubs[this.selectedHubHash] = true;
            if (routeRoom) {
                this.selectRoom(this.selectedHubHash, decodeURIComponent(routeRoom));
            }
        },
        applyRouteQuery() {
            const hubHash = this.$route?.query?.hub;
            const routeRoom = this.$route?.query?.room;
            if (!hubHash || typeof hubHash !== "string") {
                return;
            }
            this.view = "chat";
            this.selectedHubHash = hubHash;
            this.expandedHubs[hubHash] = true;
            if (routeRoom && typeof routeRoom === "string") {
                this.selectRoom(hubHash, routeRoom);
            }
        },
        messageKey(msg) {
            return relayMessageKey(msg);
        },
        timelineEntryKey(entry) {
            if (entry.type === "dateDivider") {
                return `date-${entry.dayKey}`;
            }
            return this.messageKey(entry.msg);
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
        scrollToMessage(msg) {
            if (!msg) {
                return;
            }
            this.showSearch = false;
            const key = this.messageKey(msg);
            nextTick(() => {
                const el = this.$refs.messageList?.querySelector(`[data-msg-key="${key}"]`);
                el?.scrollIntoView({ block: "center", behavior: "smooth" });
            });
        },
        displayName(msg) {
            if (msg.nick) {
                return msg.nick;
            }
            if (msg.src) {
                return msg.src.slice(0, 12);
            }
            return this.$t("relay_chat.system");
        },
        colorForHash(hash) {
            if (!hash) {
                return "inherit";
            }
            let sum = 0;
            for (let i = 0; i < hash.length; i++) {
                sum = (sum + hash.charCodeAt(i)) % NAME_COLORS.length;
            }
            return NAME_COLORS[sum];
        },
        nameStyle(msg) {
            return { color: this.colorForHash(msg.src) };
        },
        formatTime(ts) {
            if (!ts) {
                return "";
            }
            try {
                return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            } catch {
                return "";
            }
        },
        formatHash(hash) {
            if (!hash) {
                return "-";
            }
            return Utils.formatDestinationHash(hash);
        },
        timeAgo(datetime) {
            return Utils.formatTimeAgoForI18n(datetime);
        },
        encodeRoom(room) {
            return encodeURIComponent(room);
        },
        async fetchHubs() {
            try {
                const response = await window.api.get("/api/v1/rrc/hubs");
                this.hubs = response.data?.hubs || [];
                if (!this.selectedHubHash && this.hubs.length > 0) {
                    this.selectedHubHash = this.hubs[0].hub_hash;
                    this.expandedHubs[this.hubs[0].hub_hash] = true;
                }
                this.updateUnreadBadge();
            } catch {
                // relay chat may be unavailable for this identity
            }
        },
        selectHub(hubHash) {
            this.selectedHubHash = hubHash;
        },
        async selectRoom(hubHash, room, options = {}) {
            this.selectedHubHash = hubHash;
            this.selectedRoom = room;
            this.expandedHubs[hubHash] = true;
            try {
                const response = await window.api.get(
                    `/api/v1/rrc/hubs/${hubHash}/rooms/${this.encodeRoom(room)}/messages`
                );
                this.messages = response.data?.messages || [];
                this.members = response.data?.members || [];
                this.scrollToBottom();
                if (!options.restore) {
                    await this.fetchHubs();
                }
                this.persistRelayLayout();
            } catch {
                this.messages = [];
                this.members = [];
            }
        },
        async refreshMembers() {
            if (!this.selectedHubHash || !this.selectedRoom) {
                return;
            }
            try {
                const response = await window.api.get(
                    `/api/v1/rrc/hubs/${this.selectedHubHash}/rooms/${this.encodeRoom(this.selectedRoom)}/messages`
                );
                this.members = response.data?.members || [];
            } catch {
                // ignore member refresh failures
            }
        },
        scrollToBottom() {
            nextTick(() => {
                const el = this.$refs.messageList;
                if (el) {
                    el.scrollTop = el.scrollHeight;
                }
            });
        },
        async sendMessage() {
            const text = this.composer.trim();
            if (!text || !this.selectedHub || !this.selectedRoom) {
                return;
            }
            const isAction = text.startsWith("/me ");
            const payload = isAction ? { text: text.slice(4), action: true } : { text };
            this.sending = true;
            try {
                await window.api.post(
                    `/api/v1/rrc/hubs/${this.selectedHubHash}/rooms/${this.encodeRoom(this.selectedRoom)}/messages`,
                    payload
                );
                this.composer = "";
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.send_failed"));
            } finally {
                this.sending = false;
            }
        },
        async joinRoom(hub) {
            const room = this.joinRoomName.trim();
            if (!room) {
                ToastUtils.warning(this.$t("relay_chat.room_required"));
                return;
            }
            try {
                await window.api.post(`/api/v1/rrc/hubs/${hub.hub_hash}/rooms`, { room });
                this.joinRoomName = "";
                ToastUtils.success(this.$t("relay_chat.joined_room"));
                await this.fetchHubs();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async leaveRoom() {
            if (!this.selectedHub || !this.selectedRoom) {
                return;
            }
            const confirmed = await DialogUtils.confirm(this.$t("relay_chat.leave_room_confirm"));
            if (!confirmed) {
                return;
            }
            const room = this.selectedRoom;
            try {
                await window.api.delete(`/api/v1/rrc/hubs/${this.selectedHubHash}/rooms/${this.encodeRoom(room)}`);
                this.selectedRoom = null;
                this.messages = [];
                this.members = [];
                ToastUtils.success(this.$t("relay_chat.left_room"));
                await this.fetchHubs();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async clearMessages() {
            if (!this.selectedHub || !this.selectedRoom) {
                return;
            }
            const confirmed = await DialogUtils.confirm(this.$t("relay_chat.clear_messages_confirm"));
            if (!confirmed) {
                return;
            }
            try {
                await window.api.delete(
                    `/api/v1/rrc/hubs/${this.selectedHubHash}/rooms/${this.encodeRoom(this.selectedRoom)}/messages`
                );
                this.messages = [];
                ToastUtils.success(this.$t("relay_chat.messages_cleared"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async connectHub(hub) {
            try {
                await window.api.post(`/api/v1/rrc/hubs/${hub.hub_hash}/connect`);
                await this.fetchHubs();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async disconnectHub(hub) {
            try {
                await window.api.post(`/api/v1/rrc/hubs/${hub.hub_hash}/disconnect`);
                await this.fetchHubs();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        openAddHub() {
            this.addHubForm = { hub_hash: "", name: "", dest_name: "" };
            this.showAddHub = true;
        },
        async addHub() {
            const hubHash = this.addHubForm.hub_hash.trim();
            if (!hubHash) {
                ToastUtils.warning(this.$t("relay_chat.invalid_hub_hash"));
                return;
            }
            try {
                const response = await window.api.post("/api/v1/rrc/hubs", {
                    hub_hash: hubHash,
                    name: this.addHubForm.name.trim() || undefined,
                    dest_name: this.addHubForm.dest_name.trim() || undefined,
                    connect: true,
                });
                this.showAddHub = false;
                ToastUtils.success(this.$t("relay_chat.hub_added"));
                await this.fetchHubs();
                const added = response.data?.hub;
                if (added) {
                    this.selectedHubHash = added.hub_hash;
                    this.expandedHubs[added.hub_hash] = true;
                }
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.invalid_hub_hash"));
            }
        },
        async removeHub(hub) {
            const confirmed = await DialogUtils.confirm(this.$t("relay_chat.remove_hub_confirm"));
            if (!confirmed) {
                return;
            }
            try {
                await window.api.delete(`/api/v1/rrc/hubs/${hub.hub_hash}`);
                if (this.selectedHubHash === hub.hub_hash) {
                    this.selectedHubHash = null;
                    this.selectedRoom = null;
                    this.messages = [];
                    this.members = [];
                }
                ToastUtils.success(this.$t("relay_chat.hub_removed"));
                await this.fetchHubs();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        openSettings(hub) {
            this.settingsHubHash = hub.hub_hash;
            const defaultName = hub.hub_name_announced || hub.name || "";
            this.settingsForm = {
                auto_reconnect: hub.auto_reconnect !== false,
                auto_list: !!hub.auto_list,
                auto_who: !!hub.auto_who,
                nick: hub.nick_override || "",
                custom_name: hub.custom_name || "",
                default_name: defaultName,
                has_custom_name: Boolean(hub.custom_name),
                hub_icon: normalizeMdiIconName(hub.hub_icon),
            };
            this.showSettings = true;
        },
        openIconPicker() {
            this.showIconPicker = true;
        },
        onHubIconPicked(iconName) {
            this.settingsForm.hub_icon = normalizeMdiIconName(iconName);
        },
        async saveSettings() {
            try {
                const payload = {
                    auto_reconnect: this.settingsForm.auto_reconnect,
                    auto_list: this.settingsForm.auto_list,
                    auto_who: this.settingsForm.auto_who,
                    nick: this.settingsForm.nick,
                };
                const trimmed = (this.settingsForm.custom_name || "").trim();
                if (!trimmed && this.settingsForm.has_custom_name) {
                    payload.revert_custom_name = true;
                } else if (trimmed) {
                    payload.custom_name = trimmed;
                }
                const icon = normalizeMdiIconName(this.settingsForm.hub_icon);
                const hadIcon = Boolean(this.settingsHub?.hub_icon);
                if (!icon && hadIcon) {
                    payload.revert_hub_icon = true;
                } else if (icon) {
                    payload.hub_icon = icon;
                }
                await window.api.patch(`/api/v1/rrc/hubs/${this.settingsHubHash}`, payload);
                this.showSettings = false;
                ToastUtils.success(this.$t("relay_chat.settings_saved"));
                await this.fetchHubs();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        isHubAdded(destinationHash) {
            return this.hubs.some((hub) => hub.hub_hash === destinationHash);
        },
        nodeName(node) {
            if (node.custom_display_name) {
                return node.custom_display_name;
            }
            if (node.display_name && node.display_name !== "Anonymous Peer") {
                return node.display_name;
            }
            return this.formatHash(node.destination_hash);
        },
        async fetchDiscovered() {
            try {
                const response = await window.api.get("/api/v1/announces", {
                    params: {
                        aspect: "rrc.hub",
                        limit: 200,
                        search: this.discoverySearch || undefined,
                    },
                });
                this.discovered = response.data?.announces || [];
            } catch {
                this.discovered = [];
            }
        },
        async refreshDiscovered() {
            this.discoveryLoading = true;
            try {
                await this.fetchDiscovered();
                ToastUtils.info(this.$t("relay_chat.discovery_refreshed") + " (" + this.discovered.length + ")");
            } finally {
                this.discoveryLoading = false;
            }
        },
        onDiscoverySearch() {
            if (this.discoverySearchTimer) {
                clearTimeout(this.discoverySearchTimer);
            }
            this.discoverySearchTimer = setTimeout(() => {
                this.fetchDiscovered();
            }, 300);
        },
        upsertDiscovered(announce) {
            const index = this.discovered.findIndex((n) => n.destination_hash === announce.destination_hash);
            if (index >= 0) {
                this.discovered.splice(index, 1, announce);
            } else {
                this.discovered.unshift(announce);
            }
        },
        async addFromDiscovery(node) {
            try {
                const response = await window.api.post("/api/v1/rrc/hubs", {
                    hub_hash: node.destination_hash,
                    name: this.nodeName(node),
                    dest_name: "rrc.hub",
                    connect: true,
                });
                ToastUtils.success(this.$t("relay_chat.discovery_added"));
                await this.fetchHubs();
                const added = response.data?.hub;
                if (added) {
                    this.selectedHubHash = added.hub_hash;
                    this.expandedHubs[added.hub_hash] = true;
                }
                this.view = "chat";
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        openDiscovered(node) {
            this.selectedHubHash = node.destination_hash;
            this.expandedHubs[node.destination_hash] = true;
            this.view = "chat";
        },
        selectHostView() {
            this.view = "host";
            this.fetchServers();
        },
        async fetchServers() {
            try {
                const response = await window.api.get("/api/v1/rrc/servers");
                const hubs = response.data?.hubs || [];
                for (const hub of hubs) {
                    if (!this.roomForms[hub.id]) {
                        this.roomForms[hub.id] = { name: "", topic: "", private: false };
                    }
                }
                this.serverHubs = hubs;
            } catch {
                // relay chat hosting may be unavailable for this identity
            }
        },
        openCreateHub() {
            this.createHubForm = { name: "", greeting: "", announce: true };
            this.showCreateHub = true;
        },
        async createServerHub() {
            try {
                await window.api.post("/api/v1/rrc/servers", {
                    name: this.createHubForm.name.trim() || undefined,
                    greeting: this.createHubForm.greeting.trim() || undefined,
                    announce: this.createHubForm.announce,
                });
                this.showCreateHub = false;
                ToastUtils.success(this.$t("relay_chat.host_hub_created"));
                await this.fetchServers();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async deleteServerHub(hub) {
            const confirmed = await DialogUtils.confirm(this.$t("relay_chat.host_delete_hub_confirm"));
            if (!confirmed) {
                return;
            }
            try {
                await window.api.delete(`/api/v1/rrc/servers/${hub.id}`);
                ToastUtils.success(this.$t("relay_chat.host_hub_deleted"));
                await this.fetchServers();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async startServerHub(hub) {
            try {
                await window.api.post(`/api/v1/rrc/servers/${hub.id}/start`);
                await this.fetchServers();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async stopServerHub(hub) {
            try {
                await window.api.post(`/api/v1/rrc/servers/${hub.id}/stop`);
                await this.fetchServers();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async announceServerHub(hub) {
            try {
                await window.api.post(`/api/v1/rrc/servers/${hub.id}/announce`);
                ToastUtils.success(this.$t("relay_chat.host_announced"));
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async createRoom(hub) {
            const form = this.roomForms[hub.id] || {};
            const name = (form.name || "").trim();
            if (!name) {
                ToastUtils.warning(this.$t("relay_chat.room_required"));
                return;
            }
            try {
                await window.api.post(`/api/v1/rrc/servers/${hub.id}/rooms`, {
                    name,
                    topic: (form.topic || "").trim() || undefined,
                    private: !!form.private,
                });
                this.roomForms[hub.id] = { name: "", topic: "", private: false };
                ToastUtils.success(this.$t("relay_chat.host_room_created"));
                await this.fetchServers();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        async deleteRoom(hub, room) {
            const confirmed = await DialogUtils.confirm(this.$t("relay_chat.host_delete_room_confirm"));
            if (!confirmed) {
                return;
            }
            try {
                await window.api.delete(`/api/v1/rrc/servers/${hub.id}/rooms/${this.encodeRoom(room)}`);
                ToastUtils.success(this.$t("relay_chat.host_room_deleted"));
                await this.fetchServers();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        openHostMembers(hub, room = null) {
            this.hostMembersModal = {
                open: true,
                hub,
                room: room || null,
            };
        },
        closeHostMembers() {
            this.hostMembersModal.open = false;
        },
        openHostRooms(hub) {
            this.hostRoomsModal = {
                open: true,
                hub,
            };
        },
        closeHostRooms() {
            this.hostRoomsModal.open = false;
        },
        copyHash(hash) {
            if (!hash) {
                return;
            }
            try {
                navigator.clipboard.writeText(hash);
                ToastUtils.success(this.$t("relay_chat.hash_copied"));
            } catch {
                // clipboard may be unavailable
            }
        },
        onWebsocketMessage(message) {
            let json;
            try {
                json = JSON.parse(message.data);
            } catch {
                return;
            }
            if (json.type === "rrc.change") {
                this.fetchHubs();
            } else if (json.type === "rrc.message") {
                if (json.hub_hash === this.selectedHubHash && json.room === this.selectedRoom && json.message) {
                    this.messages.push(json.message);
                    this.scrollToBottom();
                    if (json.message.kind === "system" || json.message.kind === "notice") {
                        this.refreshMembers();
                    }
                } else if (json.message && json.message.kind === "msg") {
                    const onRelayPage = this.$route?.name === "relay-chat" || this.$route?.name === "relay-chat-popout";
                    if (!onRelayPage || json.hub_hash !== this.selectedHubHash || json.room !== this.selectedRoom) {
                        ToastUtils.info(this.$t("relay_chat.new_message_toast", { room: json.room || "" }));
                    }
                }
                this.fetchHubs();
            } else if (json.type === "rrc.server.change") {
                this.fetchServers();
            } else if (json.type === "announce" && json.announce && json.announce.aspect === "rrc.hub") {
                this.upsertDiscovered(json.announce);
            }
        },
    },
};
</script>
