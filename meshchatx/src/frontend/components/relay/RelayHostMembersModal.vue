<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        @click.self="$emit('close')"
    >
        <div
            class="flex h-[min(100dvh-2rem,900px)] w-full max-w-6xl flex-col rounded-2xl border border-sem-border-card bg-sem-surface shadow-xl"
            role="dialog"
            :aria-label="title"
        >
            <div class="flex shrink-0 items-center gap-2 border-b border-sem-border px-4 py-3 sm:px-5 sm:py-4">
                <button
                    v-if="selectedMember && isNarrow"
                    type="button"
                    class="rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-surface/60"
                    @click="selectedMember = null"
                >
                    <MaterialDesignIcon icon-name="arrow-left" class="size-5" />
                </button>
                <h2 class="min-w-0 flex-1 text-lg font-semibold truncate">{{ title }}</h2>
                <button
                    type="button"
                    class="rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-surface/60"
                    :title="$t('common.close')"
                    @click="$emit('close')"
                >
                    <MaterialDesignIcon icon-name="close" class="size-5" />
                </button>
            </div>

            <div class="shrink-0 border-b border-sem-border px-4 py-2.5 sm:px-5">
                <div class="relative">
                    <input
                        v-model="search"
                        type="search"
                        :placeholder="$t('relay_chat.host_members_search')"
                        class="input-field !py-2.5 pr-10"
                    />
                    <MaterialDesignIcon
                        icon-name="magnify"
                        class="pointer-events-none absolute right-3 top-1/2 size-5 -translate-y-1/2 text-sem-fg-muted"
                    />
                </div>
            </div>

            <div class="flex min-h-0 flex-1 flex-col lg:flex-row">
                <div
                    class="flex min-h-0 flex-col border-sem-border lg:w-80 lg:shrink-0 lg:border-r"
                    :class="isNarrow && selectedMember ? 'hidden' : 'flex-1 lg:flex-none'"
                >
                    <div class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                        <div v-if="loading" class="py-12 text-center text-sm text-sem-fg-muted">
                            {{ $t("common.loading") }}
                        </div>
                        <div
                            v-else-if="filteredMembers.length === 0"
                            class="py-12 text-center text-sm text-sem-fg-muted"
                        >
                            {{ $t("relay_chat.no_members") }}
                        </div>
                        <ul v-else class="space-y-1.5">
                            <li
                                v-for="member in filteredMembers"
                                :key="member.hash"
                                class="rounded-xl border px-3 py-2.5 transition-colors cursor-pointer"
                                :class="
                                    selectedMember?.hash === member.hash
                                        ? 'border-sem-accent bg-sem-accent/10'
                                        : 'border-sem-border hover:bg-sem-surface/50'
                                "
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
                                            v-if="!room && member.rooms?.length"
                                            class="mt-1 text-xs text-sem-fg-muted truncate"
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
                                            @click.stop="moderate(member, room ? 'room_ban' : 'ban')"
                                        >
                                            <MaterialDesignIcon icon-name="block-helper" class="size-4" />
                                        </button>
                                    </div>
                                </div>
                            </li>
                        </ul>
                    </div>
                </div>

                <div
                    class="flex min-h-0 min-w-0 flex-1 flex-col"
                    :class="isNarrow && !selectedMember ? 'hidden' : 'flex'"
                >
                    <div
                        v-if="!selectedMember"
                        class="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-sem-fg-muted"
                    >
                        <MaterialDesignIcon icon-name="account-search" class="size-10 opacity-40" />
                        {{ $t("relay_chat.host_members_select") }}
                    </div>
                    <template v-else>
                        <div class="shrink-0 border-b border-sem-border px-4 py-3 sm:px-5">
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
                        <div class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                            <div v-if="messagesLoading" class="py-8 text-center text-sm text-sem-fg-muted">
                                {{ $t("common.loading") }}
                            </div>
                            <div
                                v-else-if="memberMessages.length === 0"
                                class="py-8 text-center text-sm text-sem-fg-muted"
                            >
                                {{ $t("relay_chat.host_no_messages") }}
                            </div>
                            <ul v-else class="space-y-2">
                                <li
                                    v-for="(msg, idx) in memberMessages"
                                    :key="idx"
                                    class="rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm"
                                >
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
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";

const NAME_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6", "#3b82f6", "#8b5cf6", "#ec4899"];

export default {
    name: "RelayHostMembersModal",
    components: { MaterialDesignIcon },
    props: {
        open: { type: Boolean, default: false },
        hub: { type: Object, default: null },
        room: { type: String, default: null },
    },
    emits: ["close", "refresh"],
    data() {
        return {
            loading: false,
            members: [],
            search: "",
            selectedMember: null,
            memberMessages: [],
            messagesLoading: false,
            isNarrow: false,
            mq: null,
            localIdentityHash: "",
        };
    },
    computed: {
        title() {
            const hubName = this.hub?.name || "";
            if (this.room) {
                return this.$t("relay_chat.host_members_room_title", { hub: hubName, room: this.room });
            }
            return this.$t("relay_chat.host_members_all_title", { hub: hubName });
        },
        filteredMembers() {
            const q = this.search.trim().toLowerCase();
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
        open(val) {
            if (val) {
                this.search = "";
                this.selectedMember = null;
                this.memberMessages = [];
                this.ensureLocalIdentity();
                this.fetchMembers();
            }
        },
    },
    mounted() {
        this.mq = window.matchMedia("(max-width: 1023px)");
        this.isNarrow = this.mq.matches;
        this.mq.addEventListener("change", this.onMq);
    },
    beforeUnmount() {
        if (this.mq) {
            this.mq.removeEventListener("change", this.onMq);
        }
    },
    methods: {
        onMq() {
            this.isNarrow = this.mq.matches;
        },
        async fetchMembers() {
            if (!this.hub?.id) {
                return;
            }
            this.loading = true;
            try {
                const params = this.room ? { params: { room: this.room } } : {};
                const response = await window.api.get(`/api/v1/rrc/servers/${this.hub.id}/members`, params);
                this.members = response.data?.members || [];
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
                this.$emit("close");
            } finally {
                this.loading = false;
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
                if (this.room) {
                    params.room = this.room;
                }
                const response = await window.api.get(`/api/v1/rrc/servers/${this.hub.id}/messages`, { params });
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
            if (this.room) {
                return this.room;
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
            const d = new Date(ts);
            return d.toLocaleString();
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
