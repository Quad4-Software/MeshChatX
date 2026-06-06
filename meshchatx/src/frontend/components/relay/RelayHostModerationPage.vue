<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex min-h-0 flex-1 flex-col overflow-hidden bg-sem-canvas text-sem-fg">
        <div :class="RELAY_HOST_PAGE_HEADER">
            <button type="button" :class="RELAY_HOST_ICON_BTN" :title="$t('relay_chat.back')" @click="$emit('back')">
                <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
            </button>
            <div class="min-w-0 flex-1">
                <h2 class="truncate text-lg font-semibold text-sem-fg">{{ pageTitle }}</h2>
                <p v-if="hub" class="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-sem-fg-muted">
                    <span class="inline-flex items-center gap-1.5">
                        <span
                            class="inline-block size-2 shrink-0 rounded-full"
                            :class="hub.running ? 'bg-sem-success' : 'bg-sem-fg-muted'"
                        ></span>
                        {{ hub.running ? $t("relay_chat.host_status_running") : $t("relay_chat.host_status_stopped") }}
                    </span>
                    <template v-if="hub.running && liveUptimeSeconds > 0">
                        <span class="text-sem-border-strong" aria-hidden="true">·</span>
                        <span>{{
                            $t("relay_chat.host_moderation_uptime", { time: formatUptime(liveUptimeSeconds) })
                        }}</span>
                    </template>
                    <template v-if="navbarMemberCount != null">
                        <span class="text-sem-border-strong" aria-hidden="true">·</span>
                        <span>{{ $t("relay_chat.host_moderation_members", { count: navbarMemberCount }) }}</span>
                    </template>
                </p>
            </div>
        </div>

        <div :class="RELAY_HOST_PAGE_TABS" role="tablist">
            <button
                type="button"
                role="tab"
                :aria-selected="tab === 'rooms'"
                :class="[RELAY_HOST_PAGE_TAB, tab === 'rooms' ? RELAY_HOST_PAGE_TAB_ACTIVE : RELAY_HOST_PAGE_TAB_IDLE]"
                @click="setTab('rooms')"
            >
                <MaterialDesignIcon icon-name="pound" class="size-4" />
                {{ $t("relay_chat.host_moderation_tab_rooms") }}
            </button>
            <button
                type="button"
                role="tab"
                :aria-selected="tab === 'members'"
                :class="[
                    RELAY_HOST_PAGE_TAB,
                    tab === 'members' ? RELAY_HOST_PAGE_TAB_ACTIVE : RELAY_HOST_PAGE_TAB_IDLE,
                ]"
                @click="setTab('members')"
            >
                <MaterialDesignIcon icon-name="account-group" class="size-4" />
                {{ $t("relay_chat.host_moderation_tab_members") }}
            </button>
        </div>

        <div v-if="!hub" class="flex flex-1 items-center justify-center p-6 text-sm text-sem-fg-muted">
            {{ $t("relay_chat.host_moderation_hub_missing") }}
        </div>

        <div v-else-if="tab === 'rooms'" :class="RELAY_HOST_PAGE_BODY">
            <div :class="[RELAY_HOST_PAGE_LIST, isNarrow && selectedRoom ? 'hidden' : 'flex flex-1 lg:flex-none']">
                <div class="shrink-0 space-y-3 border-b border-sem-border p-3 sm:p-4">
                    <div class="relative">
                        <input
                            v-model="roomsSearch"
                            type="search"
                            :placeholder="$t('relay_chat.host_rooms_search')"
                            class="input-field !py-2.5 pl-10 pr-3"
                        />
                        <MaterialDesignIcon
                            icon-name="magnify"
                            class="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-sem-fg-muted"
                        />
                    </div>
                    <button
                        v-if="!showAddRoomForm"
                        type="button"
                        class="flex w-full items-center gap-2 rounded-xl border-2 border-dashed border-sem-border px-3 py-3 text-left text-sm text-sem-fg-muted transition-colors hover:border-sem-accent hover:bg-sem-surface/40 hover:text-sem-accent"
                        @click="showAddRoomForm = true"
                    >
                        <MaterialDesignIcon icon-name="plus-circle-outline" class="size-5 shrink-0" />
                        <span class="font-medium">{{ $t("relay_chat.host_add_room") }}</span>
                    </button>
                    <form
                        v-else
                        class="space-y-2.5 rounded-xl border border-sem-border bg-sem-surface-raised/40 p-3"
                        @submit.prevent="createRoom"
                    >
                        <input
                            v-model="newRoom.name"
                            type="text"
                            :placeholder="$t('relay_chat.host_room_name')"
                            class="input-field w-full !py-2.5 !text-sm"
                            autofocus
                        />
                        <input
                            v-model="newRoom.topic"
                            type="text"
                            :placeholder="$t('relay_chat.host_room_topic')"
                            class="input-field w-full !py-2.5 !text-sm"
                        />
                        <div class="flex gap-2 pt-0.5">
                            <button
                                type="submit"
                                :class="[btnPrimary, 'flex-1 !py-2.5 !text-sm']"
                                :disabled="creatingRoom"
                            >
                                <MaterialDesignIcon icon-name="plus" class="size-4" />
                                {{ $t("relay_chat.host_add_room") }}
                            </button>
                            <button
                                type="button"
                                :class="[btnSecondary, '!py-2.5 !text-sm']"
                                :disabled="creatingRoom"
                                @click="cancelAddRoom"
                            >
                                {{ $t("common.cancel") }}
                            </button>
                        </div>
                    </form>
                </div>
                <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                    <div v-if="roomsLoading" class="py-12 text-center text-sm text-sem-fg-muted">
                        {{ $t("common.loading") }}
                    </div>
                    <div v-else-if="filteredRooms.length === 0" class="py-12 text-center text-sm text-sem-fg-muted">
                        {{
                            roomsSearch.trim()
                                ? $t("relay_chat.host_rooms_search_empty")
                                : $t("relay_chat.host_no_rooms")
                        }}
                    </div>
                    <ul v-else class="space-y-1.5">
                        <li
                            v-for="room in filteredRooms"
                            :key="room.name"
                            class="cursor-pointer px-3 py-2.5"
                            :class="[
                                RELAY_HOST_LIST_ITEM,
                                selectedRoom === room.name ? RELAY_HOST_LIST_ITEM_SELECTED : RELAY_HOST_LIST_ITEM_IDLE,
                            ]"
                            @click="selectedRoom = room.name"
                        >
                            <div class="flex items-start justify-between gap-2">
                                <div class="min-w-0">
                                    <div class="font-medium text-sem-fg">#{{ room.name }}</div>
                                    <div v-if="room.topic" class="truncate text-xs text-sem-fg-muted">
                                        {{ room.topic }}
                                    </div>
                                    <div class="mt-1 flex flex-wrap gap-x-3 text-xs text-sem-fg-muted">
                                        <span>{{ room.members }} {{ $t("relay_chat.host_clients") }}</span>
                                        <span>{{ room.message_count || 0 }} msgs</span>
                                    </div>
                                </div>
                                <button
                                    v-if="room.registered"
                                    type="button"
                                    class="shrink-0 rounded-lg p-1.5 text-sem-fg-muted hover:text-sem-danger"
                                    :title="$t('relay_chat.host_delete_room')"
                                    @click.stop="deleteRoom(room.name)"
                                >
                                    <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                                </button>
                            </div>
                        </li>
                    </ul>
                </div>
            </div>

            <div :class="[RELAY_HOST_PAGE_DETAIL, isNarrow && !selectedRoom ? 'hidden' : 'flex']">
                <div
                    v-if="isNarrow && selectedRoom"
                    class="flex shrink-0 items-center gap-2 border-b border-sem-border px-3 py-2 lg:hidden"
                >
                    <button type="button" :class="RELAY_HOST_ICON_BTN" @click="selectedRoom = null">
                        <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
                    </button>
                    <span class="font-semibold text-sem-fg">#{{ selectedRoom }}</span>
                </div>
                <div
                    v-if="!selectedRoom"
                    class="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-sem-fg-muted"
                >
                    <MaterialDesignIcon icon-name="pound" class="size-10 opacity-40" />
                    {{ $t("relay_chat.host_rooms_select") }}
                </div>
                <template v-else>
                    <div :class="[RELAY_HOST_DETAIL_HEADER, 'hidden lg:block']">
                        <div class="font-semibold text-sem-fg">#{{ selectedRoom }}</div>
                        <div class="text-xs text-sem-fg-muted">{{ $t("relay_chat.host_room_activity") }}</div>
                    </div>
                    <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                        <ul v-if="roomMessages.length > 0" class="space-y-2">
                            <li v-for="(msg, idx) in roomMessages" :key="idx" :class="RELAY_HOST_MESSAGE">
                                <div class="flex flex-wrap items-center gap-x-2 text-xs text-sem-fg-muted">
                                    <span :style="{ color: colorForHash(msg.peer) }">{{
                                        msg.nick || formatHash(msg.peer)
                                    }}</span>
                                    <span>{{ formatTime(msg.ts) }}</span>
                                </div>
                                <div class="mt-1 whitespace-pre-wrap break-words">{{ msg.text }}</div>
                            </li>
                        </ul>
                        <div v-else class="py-8 text-center text-sm text-sem-fg-muted">
                            {{ $t("relay_chat.host_no_activity") }}
                        </div>
                    </div>
                </template>
            </div>
        </div>

        <div v-else :class="RELAY_HOST_PAGE_BODY">
            <div :class="[RELAY_HOST_PAGE_LIST, isNarrow && selectedMember ? 'hidden' : 'flex flex-1 lg:flex-none']">
                <div class="shrink-0 border-b border-sem-border p-3 sm:p-4">
                    <div class="relative">
                        <input
                            v-model="membersSearch"
                            type="search"
                            :placeholder="$t('relay_chat.host_members_search')"
                            class="input-field !py-2.5 pl-10 pr-3"
                        />
                        <MaterialDesignIcon
                            icon-name="magnify"
                            class="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-sem-fg-muted"
                        />
                    </div>
                </div>
                <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                    <div v-if="membersLoading" class="py-12 text-center text-sm text-sem-fg-muted">
                        {{ $t("common.loading") }}
                    </div>
                    <div v-else-if="filteredMembers.length === 0" class="py-12 text-center text-sm text-sem-fg-muted">
                        {{ $t("relay_chat.no_members") }}
                    </div>
                    <ul v-else class="space-y-1.5">
                        <li
                            v-for="member in filteredMembers"
                            :key="member.hash"
                            class="cursor-pointer px-3 py-2.5"
                            :class="[
                                RELAY_HOST_LIST_ITEM,
                                selectedMember?.hash === member.hash
                                    ? RELAY_HOST_LIST_ITEM_SELECTED
                                    : RELAY_HOST_LIST_ITEM_IDLE,
                            ]"
                            @click="selectMember(member)"
                        >
                            <div class="flex items-start gap-2">
                                <span class="mt-1.5 size-2 shrink-0 rounded-full bg-sem-success"></span>
                                <div class="min-w-0 flex-1">
                                    <div class="truncate font-medium" :style="{ color: colorForHash(member.hash) }">
                                        {{ member.name }}
                                    </div>
                                    <div class="truncate font-mono text-xs text-sem-fg-muted">
                                        {{ formatHash(member.hash) }}
                                    </div>
                                    <div
                                        v-if="!roomFilter && member.rooms?.length"
                                        class="mt-1 truncate text-xs text-sem-fg-muted"
                                    >
                                        {{ member.rooms.map((r) => "#" + r).join(", ") }}
                                    </div>
                                </div>
                                <div class="flex shrink-0 items-center gap-0.5">
                                    <button
                                        type="button"
                                        class="rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-warning/15 hover:text-sem-warning"
                                        :title="$t('relay_chat.ctx_kick_user')"
                                        @click.stop="moderate(member, 'kick')"
                                    >
                                        <MaterialDesignIcon icon-name="account-remove" class="size-4" />
                                    </button>
                                    <button
                                        type="button"
                                        class="rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-danger/15 hover:text-sem-danger"
                                        :title="$t('relay_chat.host_ban_hub')"
                                        @click.stop="moderate(member, roomFilter ? 'room_ban' : 'ban')"
                                    >
                                        <MaterialDesignIcon icon-name="block-helper" class="size-4" />
                                    </button>
                                </div>
                            </div>
                        </li>
                    </ul>
                </div>
            </div>

            <div :class="[RELAY_HOST_PAGE_DETAIL, isNarrow && !selectedMember ? 'hidden' : 'flex']">
                <div
                    v-if="isNarrow && selectedMember"
                    class="flex shrink-0 items-center gap-2 border-b border-sem-border px-3 py-2 lg:hidden"
                >
                    <button type="button" :class="RELAY_HOST_ICON_BTN" @click="selectedMember = null">
                        <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
                    </button>
                    <span class="truncate font-semibold" :style="{ color: colorForHash(selectedMember.hash) }">
                        {{ selectedMember.name }}
                    </span>
                </div>
                <div
                    v-if="!selectedMember"
                    class="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-sem-fg-muted"
                >
                    <MaterialDesignIcon icon-name="account-search" class="size-10 opacity-40" />
                    {{ $t("relay_chat.host_members_select") }}
                </div>
                <template v-else>
                    <div :class="[RELAY_HOST_DETAIL_HEADER, 'hidden lg:block']">
                        <div class="font-semibold" :style="{ color: colorForHash(selectedMember.hash) }">
                            {{ selectedMember.name }}
                        </div>
                        <button
                            type="button"
                            class="mt-0.5 font-mono text-xs text-sem-fg-muted hover:text-sem-accent"
                            @click="copyHash(selectedMember.hash)"
                        >
                            {{ formatHash(selectedMember.hash) }}
                        </button>
                    </div>
                    <div class="min-h-0 flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                        <div v-if="messagesLoading" class="py-8 text-center text-sm text-sem-fg-muted">
                            {{ $t("common.loading") }}
                        </div>
                        <div v-else-if="memberMessages.length === 0" class="py-8 text-center text-sm text-sem-fg-muted">
                            {{ $t("relay_chat.host_no_messages") }}
                        </div>
                        <ul v-else class="space-y-2">
                            <li v-for="(msg, idx) in memberMessages" :key="idx" :class="RELAY_HOST_MESSAGE">
                                <div class="flex flex-wrap items-center gap-x-2 text-xs text-sem-fg-muted">
                                    <span>#{{ msg.room }}</span>
                                    <span>{{ formatTime(msg.ts) }}</span>
                                    <span v-if="msg.kind === 'action'" class="italic">action</span>
                                </div>
                                <div class="mt-1 whitespace-pre-wrap break-words">{{ msg.text }}</div>
                            </li>
                        </ul>
                    </div>
                </template>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";
import {
    RELAY_HOST_DETAIL_HEADER,
    RELAY_HOST_ICON_BTN,
    RELAY_HOST_LIST_ITEM,
    RELAY_HOST_LIST_ITEM_IDLE,
    RELAY_HOST_LIST_ITEM_SELECTED,
    RELAY_HOST_MESSAGE,
    RELAY_HOST_PAGE_BODY,
    RELAY_HOST_PAGE_DETAIL,
    RELAY_HOST_PAGE_HEADER,
    RELAY_HOST_PAGE_LIST,
    RELAY_HOST_PAGE_TAB,
    RELAY_HOST_PAGE_TAB_ACTIVE,
    RELAY_HOST_PAGE_TAB_IDLE,
    RELAY_HOST_PAGE_TABS,
} from "../../js/relayHostModerationClasses.js";

const BTN_PRIMARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg bg-sem-action-primary px-3 py-2 text-sm font-semibold text-white transition hover:bg-sem-action-primary-hover disabled:opacity-50";
const BTN_SECONDARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg border border-sem-border bg-sem-surface-raised px-3 py-2 text-sm font-medium text-sem-fg transition hover:bg-sem-surface-muted disabled:opacity-50";
const NAME_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6", "#3b82f6", "#8b5cf6", "#ec4899"];

export default {
    name: "RelayHostModerationPage",
    components: { MaterialDesignIcon },
    props: {
        hub: { type: Object, default: null },
        initialTab: { type: String, default: "rooms" },
        roomFilter: { type: String, default: null },
    },
    emits: ["back", "refresh"],
    data() {
        return {
            RELAY_HOST_PAGE_HEADER,
            RELAY_HOST_PAGE_TABS,
            RELAY_HOST_PAGE_TAB,
            RELAY_HOST_PAGE_TAB_ACTIVE,
            RELAY_HOST_PAGE_TAB_IDLE,
            RELAY_HOST_PAGE_BODY,
            RELAY_HOST_PAGE_LIST,
            RELAY_HOST_PAGE_DETAIL,
            RELAY_HOST_ICON_BTN,
            RELAY_HOST_LIST_ITEM,
            RELAY_HOST_LIST_ITEM_SELECTED,
            RELAY_HOST_LIST_ITEM_IDLE,
            RELAY_HOST_DETAIL_HEADER,
            RELAY_HOST_MESSAGE,
            btnPrimary: BTN_PRIMARY,
            btnSecondary: BTN_SECONDARY,
            tab: "rooms",
            isNarrow: false,
            mq: null,
            roomsLoading: false,
            membersLoading: false,
            creatingRoom: false,
            messagesLoading: false,
            showAddRoomForm: false,
            rooms: [],
            recent: [],
            members: [],
            roomsSearch: "",
            membersSearch: "",
            selectedRoom: null,
            selectedMember: null,
            memberMessages: [],
            newRoom: { name: "", topic: "" },
            localIdentityHash: "",
            uptimeTick: 0,
            uptimeAnchorMs: 0,
            uptimeTimer: null,
        };
    },
    computed: {
        liveUptimeSeconds() {
            void this.uptimeTick;
            if (!this.hub?.running) {
                return 0;
            }
            const base = Number(this.hub.uptime_seconds) || 0;
            if (!this.uptimeAnchorMs) {
                return base;
            }
            return base + Math.floor((Date.now() - this.uptimeAnchorMs) / 1000);
        },
        navbarMemberCount() {
            if (this.roomFilter) {
                if (this.membersLoading) {
                    return null;
                }
                return this.members.length;
            }
            if (this.hub?.clients != null) {
                return this.hub.clients;
            }
            if (!this.membersLoading) {
                return this.members.length;
            }
            return null;
        },
        filteredRooms() {
            const q = this.roomsSearch.trim().toLowerCase();
            if (!q) {
                return this.rooms;
            }
            return this.rooms.filter((room) => {
                const name = (room.name || "").toLowerCase();
                const topic = (room.topic || "").toLowerCase();
                return name.includes(q) || topic.includes(q);
            });
        },
        pageTitle() {
            if (!this.hub?.name) {
                return this.$t("relay_chat.host_moderation_title");
            }
            if (this.roomFilter) {
                return this.$t("relay_chat.host_moderation_title_room", {
                    hub: this.hub.name,
                    room: this.roomFilter,
                });
            }
            return this.$t("relay_chat.host_moderation_title_hub", { hub: this.hub.name });
        },
        roomMessages() {
            if (!this.selectedRoom) {
                return [];
            }
            return this.recent.filter((m) => m.room === this.selectedRoom);
        },
        filteredMembers() {
            const q = this.membersSearch.trim().toLowerCase();
            if (!q) {
                return this.members;
            }
            return this.members.filter((m) => {
                const name = (m.name || "").toLowerCase();
                const hash = (m.hash || "").toLowerCase();
                const rooms = (m.rooms || []).join(" ").toLowerCase();
                return name.includes(q) || hash.includes(q) || rooms.includes(q);
            });
        },
    },
    watch: {
        hub: {
            immediate: true,
            handler() {
                this.uptimeAnchorMs = Date.now();
                this.reload();
            },
        },
        initialTab: {
            immediate: true,
            handler(val) {
                this.tab = val === "members" ? "members" : "rooms";
            },
        },
        tab(val) {
            if (val === "rooms") {
                this.fetchActivity();
            } else {
                this.fetchMembers();
            }
        },
    },
    mounted() {
        this.mq = window.matchMedia("(max-width: 1023px)");
        this.isNarrow = this.mq.matches;
        this.mq.addEventListener("change", this.onMq);
        this.tab = this.initialTab === "members" ? "members" : "rooms";
        this.ensureLocalIdentity();
        this.uptimeAnchorMs = Date.now();
        this.uptimeTimer = window.setInterval(() => {
            if (this.hub?.running) {
                this.uptimeTick += 1;
            }
        }, 1000);
        if (this.hub?.id) {
            this.reload();
        }
    },
    beforeUnmount() {
        if (this.mq) {
            this.mq.removeEventListener("change", this.onMq);
        }
        if (this.uptimeTimer) {
            clearInterval(this.uptimeTimer);
        }
    },
    methods: {
        onMq() {
            this.isNarrow = this.mq.matches;
        },
        setTab(next) {
            this.tab = next;
            if (next === "rooms") {
                this.selectedMember = null;
            } else {
                this.selectedRoom = null;
            }
        },
        reload() {
            this.selectedRoom = null;
            this.selectedMember = null;
            this.memberMessages = [];
            this.newRoom = { name: "", topic: "" };
            this.showAddRoomForm = false;
            this.roomsSearch = "";
            if (this.hub?.running) {
                this.fetchMembers();
            } else {
                this.members = [];
            }
            if (this.tab === "rooms") {
                this.fetchActivity();
            }
        },
        cancelAddRoom() {
            this.showAddRoomForm = false;
            this.newRoom = { name: "", topic: "" };
        },
        async fetchActivity() {
            if (!this.hub?.id) {
                return;
            }
            this.roomsLoading = true;
            try {
                const response = await window.api.get(`/api/v1/rrc/servers/${this.hub.id}/activity`);
                this.rooms = response.data?.rooms || [];
                this.recent = response.data?.recent || [];
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            } finally {
                this.roomsLoading = false;
            }
        },
        async fetchMembers() {
            if (!this.hub?.id) {
                return;
            }
            this.membersLoading = true;
            try {
                const params = this.roomFilter ? { params: { room: this.roomFilter } } : {};
                const response = await window.api.get(`/api/v1/rrc/servers/${this.hub.id}/members`, params);
                this.members = response.data?.members || [];
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            } finally {
                this.membersLoading = false;
            }
        },
        async createRoom() {
            const name = (this.newRoom.name || "").trim();
            if (!name || !this.hub?.id) {
                ToastUtils.warning(this.$t("relay_chat.room_required"));
                return;
            }
            this.creatingRoom = true;
            try {
                await window.api.post(`/api/v1/rrc/servers/${this.hub.id}/rooms`, {
                    name,
                    topic: (this.newRoom.topic || "").trim() || undefined,
                });
                this.newRoom = { name: "", topic: "" };
                this.showAddRoomForm = false;
                ToastUtils.success(this.$t("relay_chat.host_room_created"));
                this.$emit("refresh");
                await this.fetchActivity();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            } finally {
                this.creatingRoom = false;
            }
        },
        async deleteRoom(room) {
            const confirmed = await DialogUtils.confirm(this.$t("relay_chat.host_delete_room_confirm"));
            if (!confirmed || !this.hub?.id) {
                return;
            }
            try {
                await window.api.delete(`/api/v1/rrc/servers/${this.hub.id}/rooms/${encodeURIComponent(room)}`);
                ToastUtils.success(this.$t("relay_chat.host_room_deleted"));
                if (this.selectedRoom === room) {
                    this.selectedRoom = null;
                }
                this.$emit("refresh");
                await this.fetchActivity();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        selectMember(member) {
            this.selectedMember = member;
            this.loadMemberMessages();
        },
        async loadMemberMessages() {
            if (!this.selectedMember || !this.hub?.id) {
                return;
            }
            this.messagesLoading = true;
            try {
                const params = { peer: this.selectedMember.hash, limit: 200 };
                if (this.roomFilter) {
                    params.room = this.roomFilter;
                }
                const response = await window.api.get(`/api/v1/rrc/servers/${this.hub.id}/messages`, {
                    params,
                });
                this.memberMessages = response.data?.messages || [];
            } catch {
                this.memberMessages = [];
            } finally {
                this.messagesLoading = false;
            }
        },
        async ensureLocalIdentity() {
            if (this.localIdentityHash) {
                return;
            }
            try {
                const response = await window.api.get("/api/v1/config");
                const hash = response.data?.identity_hash;
                if (typeof hash === "string" && hash.trim()) {
                    this.localIdentityHash = hash.trim().toLowerCase();
                }
            } catch {
                // config may be unavailable in tests
            }
        },
        async resolveModerationRoom(member, action) {
            if (this.roomFilter) {
                return this.roomFilter;
            }
            const needsRoom = action === "kick" || action === "room_ban";
            if (!needsRoom) {
                return null;
            }
            const rooms = (member.rooms || []).filter((r) => typeof r === "string" && r.trim());
            if (rooms.length === 0) {
                ToastUtils.warning(this.$t("relay_chat.host_kick_no_room"));
                return null;
            }
            if (rooms.length === 1) {
                return rooms[0];
            }
            const entered = await DialogUtils.prompt(
                this.$t("relay_chat.host_kick_pick_room", {
                    name: member.name,
                    rooms: rooms.map((r) => "#" + r).join(", "),
                })
            );
            if (!entered) {
                return null;
            }
            const norm = entered.trim().replace(/^#/, "");
            const match = rooms.find((r) => r.toLowerCase() === norm.toLowerCase());
            if (!match) {
                ToastUtils.warning(this.$t("relay_chat.host_kick_room_invalid"));
                return null;
            }
            return match;
        },
        async moderate(member, action) {
            if (!this.hub?.id || !member?.hash) {
                return;
            }
            await this.ensureLocalIdentity();
            if (this.localIdentityHash && member.hash.toLowerCase() === this.localIdentityHash) {
                ToastUtils.warning(this.$t("relay_chat.host_cannot_moderate_self"));
                return;
            }
            const room = await this.resolveModerationRoom(member, action);
            if ((action === "kick" || action === "room_ban") && !room) {
                return;
            }
            const labels = {
                kick: this.$t("relay_chat.host_kick_confirm", { name: member.name, room }),
                ban: this.$t("relay_chat.host_ban_confirm", { name: member.name }),
                room_ban: this.$t("relay_chat.host_room_ban_confirm", {
                    name: member.name,
                    room,
                }),
            };
            const confirmed = await DialogUtils.confirm(labels[action] || "");
            if (!confirmed) {
                return;
            }
            try {
                await window.api.post(`/api/v1/rrc/servers/${this.hub.id}/moderate`, {
                    action,
                    peer: member.hash,
                    room: room || undefined,
                });
                ToastUtils.success(this.$t("common.success"));
                this.$emit("refresh");
                await this.fetchMembers();
                if (this.selectedMember?.hash === member.hash) {
                    this.selectedMember = null;
                    this.memberMessages = [];
                }
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            }
        },
        colorForHash(hash) {
            if (!hash) {
                return undefined;
            }
            let n = 0;
            for (let i = 0; i < hash.length; i++) {
                n = (n + hash.charCodeAt(i)) % NAME_COLORS.length;
            }
            return NAME_COLORS[n];
        },
        formatHash(hash) {
            if (!hash || hash.length < 16) {
                return hash || "";
            }
            return hash.slice(0, 8) + "..." + hash.slice(-8);
        },
        formatTime(ts) {
            if (!ts) {
                return "";
            }
            return new Date(ts).toLocaleString();
        },
        formatUptime(seconds) {
            if (seconds == null || seconds < 0) {
                return "—";
            }
            let s = Math.floor(seconds);
            if (s < 60) {
                return `${s}s`;
            }
            if (s < 3600) {
                return `${Math.floor(s / 60)}m`;
            }
            if (s < 86400) {
                return `${Math.floor(s / 3600)}h`;
            }
            if (s < 30 * 86400) {
                return `${Math.floor(s / 86400)}d`;
            }
            const yearSec = 365 * 86400;
            const monthSec = 30 * 86400;
            const years = Math.floor(s / yearSec);
            s -= years * yearSec;
            const months = Math.floor(s / monthSec);
            s -= months * monthSec;
            const days = Math.floor(s / 86400);
            const parts = [];
            if (years) {
                parts.push(`${years}y`);
            }
            if (months) {
                parts.push(`${months}mo`);
            }
            if (days) {
                parts.push(`${days}d`);
            }
            return parts.length ? parts.join(" ") : "0d";
        },
        copyHash(hash) {
            if (!hash) {
                return;
            }
            try {
                navigator.clipboard.writeText(hash);
                ToastUtils.success(this.$t("relay_chat.hash_copied"));
            } catch {
                ToastUtils.error(this.$t("common.failed_to_copy"));
            }
        },
    },
};
</script>
