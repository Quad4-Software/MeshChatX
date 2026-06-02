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
                    v-if="selectedRoom && isNarrow"
                    type="button"
                    class="rounded-lg p-1.5 text-sem-fg-muted hover:bg-sem-surface/60"
                    @click="selectedRoom = null"
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

            <div class="flex min-h-0 flex-1 flex-col lg:flex-row">
                <div
                    class="flex min-h-0 flex-col border-sem-border lg:w-96 lg:shrink-0 lg:border-r"
                    :class="isNarrow && selectedRoom ? 'hidden' : 'flex-1 lg:flex-none'"
                >
                    <div class="shrink-0 border-b border-sem-border p-3 sm:p-4 space-y-2">
                        <form class="flex flex-wrap gap-2" @submit.prevent="createRoom">
                            <input
                                v-model="newRoom.name"
                                type="text"
                                :placeholder="$t('relay_chat.host_room_name')"
                                class="input-field !py-2 !text-xs flex-1 min-w-[8rem]"
                            />
                            <input
                                v-model="newRoom.topic"
                                type="text"
                                :placeholder="$t('relay_chat.host_room_topic')"
                                class="input-field !py-2 !text-xs flex-1 min-w-[8rem]"
                            />
                            <button type="submit" :class="[btnPrimary, '!px-3 !py-2 !text-xs']" :disabled="creating">
                                <MaterialDesignIcon icon-name="plus" class="size-4" />
                                {{ $t("relay_chat.host_add_room") }}
                            </button>
                        </form>
                    </div>
                    <div class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                        <div v-if="loading" class="py-12 text-center text-sm text-sem-fg-muted">
                            {{ $t("common.loading") }}
                        </div>
                        <ul v-else class="space-y-1.5">
                            <li
                                v-for="room in rooms"
                                :key="room.name"
                                class="rounded-xl border px-3 py-2.5 cursor-pointer transition-colors"
                                :class="
                                    selectedRoom === room.name
                                        ? 'border-sem-accent bg-sem-accent/10'
                                        : 'border-sem-border hover:bg-sem-surface/50'
                                "
                                @click="selectRoom(room.name)"
                            >
                                <div class="flex items-start justify-between gap-2">
                                    <div class="min-w-0">
                                        <div class="font-medium">#{{ room.name }}</div>
                                        <div v-if="room.topic" class="truncate text-xs text-sem-fg-muted">
                                            {{ room.topic }}
                                        </div>
                                        <div class="mt-1 flex flex-wrap gap-x-3 text-xs text-sem-fg-muted">
                                            <span>{{ room.members }} {{ $t("relay_chat.host_clients") }}</span>
                                            <span>{{ room.message_count || 0 }} msgs</span>
                                        </div>
                                        <div v-if="room.last_activity_ts" class="text-xs text-sem-fg-muted">
                                            {{ formatTime(room.last_activity_ts) }}
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

                <div
                    class="flex min-h-0 min-w-0 flex-1 flex-col"
                    :class="isNarrow && !selectedRoom ? 'hidden' : 'flex'"
                >
                    <div
                        v-if="!selectedRoom"
                        class="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-sm text-sem-fg-muted"
                    >
                        <MaterialDesignIcon icon-name="pound" class="size-10 opacity-40" />
                        {{ $t("relay_chat.host_rooms_select") }}
                    </div>
                    <template v-else>
                        <div class="shrink-0 border-b border-sem-border px-4 py-3 sm:px-5">
                            <div class="font-semibold">#{{ selectedRoom }}</div>
                            <div class="text-xs text-sem-fg-muted">{{ $t("relay_chat.host_room_activity") }}</div>
                        </div>
                        <div class="flex-1 overflow-y-auto custom-scrollbar p-3 sm:p-4">
                            <ul v-if="roomMessages.length > 0" class="space-y-2">
                                <li
                                    v-for="(msg, idx) in roomMessages"
                                    :key="idx"
                                    class="rounded-lg border border-sem-border bg-sem-canvas px-3 py-2 text-sm"
                                >
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
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import DialogUtils from "../../js/DialogUtils";
import ToastUtils from "../../js/ToastUtils";

const BTN_PRIMARY =
    "inline-flex items-center justify-center gap-1.5 rounded-lg bg-sem-action-primary px-3 py-2 text-sm font-semibold text-white transition hover:bg-sem-action-primary-hover disabled:opacity-50";
const NAME_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6", "#3b82f6", "#8b5cf6", "#ec4899"];

export default {
    name: "RelayHostRoomsModal",
    components: { MaterialDesignIcon },
    props: {
        open: { type: Boolean, default: false },
        hub: { type: Object, default: null },
    },
    emits: ["close", "refresh"],
    data() {
        return {
            loading: false,
            creating: false,
            rooms: [],
            recent: [],
            selectedRoom: null,
            newRoom: { name: "", topic: "" },
            isNarrow: false,
            mq: null,
            btnPrimary: BTN_PRIMARY,
        };
    },
    computed: {
        title() {
            return this.$t("relay_chat.host_rooms_modal_title", { hub: this.hub?.name || "" });
        },
        roomMessages() {
            if (!this.selectedRoom) {
                return [];
            }
            return this.recent.filter((m) => m.room === this.selectedRoom);
        },
    },
    watch: {
        open(val) {
            if (val) {
                this.selectedRoom = null;
                this.newRoom = { name: "", topic: "" };
                this.fetchActivity();
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
        async fetchActivity() {
            if (!this.hub?.id) {
                return;
            }
            this.loading = true;
            try {
                const response = await window.api.get(`/api/v1/rrc/servers/${this.hub.id}/activity`);
                this.rooms = response.data?.rooms || [];
                this.recent = response.data?.recent || [];
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
                this.$emit("close");
            } finally {
                this.loading = false;
            }
        },
        selectRoom(name) {
            this.selectedRoom = name;
        },
        async createRoom() {
            const name = (this.newRoom.name || "").trim();
            if (!name || !this.hub?.id) {
                ToastUtils.warning(this.$t("relay_chat.room_required"));
                return;
            }
            this.creating = true;
            try {
                await window.api.post(`/api/v1/rrc/servers/${this.hub.id}/rooms`, {
                    name,
                    topic: (this.newRoom.topic || "").trim() || undefined,
                });
                this.newRoom = { name: "", topic: "" };
                ToastUtils.success(this.$t("relay_chat.host_room_created"));
                this.$emit("refresh");
                await this.fetchActivity();
            } catch (e) {
                ToastUtils.error(e.response?.data?.message || this.$t("relay_chat.action_failed"));
            } finally {
                this.creating = false;
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
    },
};
</script>
