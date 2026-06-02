<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <ToolsPageHeader
            icon="console-network-outline"
            :title="$t('rnsh.title')"
            :description="$t('rnsh.description')"
            :eyebrow="$t('rnsh.remote_shell')"
            accent="indigo"
        />
        <div
            class="flex items-stretch h-9 shrink-0 border-b border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900 overflow-x-auto"
            role="tablist"
        >
            <button
                v-for="tab in viewTabs"
                :key="tab.id"
                type="button"
                role="tab"
                :aria-selected="activeTab === tab.id"
                class="inline-flex items-center gap-1.5 px-3 sm:px-4 border-r border-gray-200 dark:border-zinc-800 text-sm transition-colors shrink-0"
                :class="
                    activeTab === tab.id
                        ? 'bg-white dark:bg-zinc-950 text-gray-900 dark:text-gray-100 font-medium'
                        : 'text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                "
                @click="activeTab = tab.id"
            >
                <MaterialDesignIcon :icon-name="tab.icon" class="size-4 shrink-0 opacity-70" />
                <span>{{ $t(tab.label) }}</span>
            </button>
        </div>

        <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div v-show="activeTab === 'sessions'" class="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
                <aside
                    class="flex flex-col min-h-0 max-h-[40vh] lg:max-h-none lg:w-80 xl:w-96 shrink-0 border-b lg:border-b-0 lg:border-r border-gray-200 dark:border-zinc-800 px-3 md:px-4 py-3 gap-3"
                >
                    <div class="flex items-center justify-between gap-2">
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">
                            {{ $t("rnsh.sessions") }}
                        </div>
                        <button type="button" class="secondary-chip text-xs px-2 py-1.5" @click="loadSessions">
                            <MaterialDesignIcon icon-name="refresh" class="size-4" />
                            {{ $t("rnsh.refresh") }}
                        </button>
                    </div>

                    <div class="flex-1 min-h-0 space-y-1.5 overflow-y-auto custom-scrollbar pr-1">
                        <button
                            v-for="session in sessions"
                            :key="session.id"
                            type="button"
                            class="w-full text-left rounded-lg px-3 py-2 transition-colors"
                            :class="
                                session.id === selectedSessionId
                                    ? 'bg-indigo-100 dark:bg-indigo-900/35 text-indigo-950 dark:text-indigo-100'
                                    : 'text-gray-900 dark:text-zinc-100 hover:bg-gray-100 dark:hover:bg-zinc-800/70'
                            "
                            @click="selectSession(session.id)"
                        >
                            <div class="flex items-center justify-between gap-2">
                                <div class="font-medium text-sm text-gray-900 dark:text-zinc-100 truncate">
                                    {{ session.name || $t("rnsh.unnamed_session") }}
                                </div>
                                <span
                                    class="text-[11px] font-semibold uppercase tracking-wide shrink-0"
                                    :class="statusClass(session)"
                                >
                                    {{ statusLabel(session) }}
                                </span>
                            </div>
                            <div class="font-mono text-xs text-gray-500 dark:text-zinc-400 truncate mt-1">
                                {{ session.mode === "listen" ? $t("rnsh.listen_mode") : session.destination || "-" }}
                            </div>
                        </button>
                        <div v-if="sessions.length === 0" class="text-xs text-gray-500 dark:text-zinc-400">
                            {{ $t("rnsh.no_sessions") }}
                        </div>
                    </div>
                </aside>

                <section class="flex-1 min-w-0 min-h-0 flex flex-col">
                    <div
                        class="shrink-0 flex flex-wrap items-center justify-between gap-2 px-3 md:px-4 py-2.5 border-b border-gray-200 dark:border-zinc-800"
                    >
                        <div class="min-w-0">
                            <div class="text-sm font-semibold text-gray-900 dark:text-zinc-100 truncate">
                                {{ selectedSession?.name || $t("rnsh.session_output") }}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-zinc-400 font-mono truncate">
                                {{ selectedSession?.last_command || $t("rnsh.no_command_yet") }}
                            </div>
                        </div>
                        <div class="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                class="secondary-chip text-xs px-2 py-1.5"
                                :disabled="!selectedSession"
                                @click="startSelected"
                            >
                                <MaterialDesignIcon icon-name="play" class="size-4" />
                                {{ $t("rnsh.start") }}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip text-xs px-2 py-1.5 text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/40"
                                :disabled="!selectedSession"
                                @click="stopSelected"
                            >
                                <MaterialDesignIcon icon-name="stop" class="size-4" />
                                {{ $t("rnsh.stop") }}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip text-xs px-2 py-1.5"
                                :disabled="!selectedSession"
                                @click="clearSelectedOutput"
                            >
                                <MaterialDesignIcon icon-name="broom" class="size-4" />
                                {{ $t("rnsh.clear") }}
                            </button>
                            <button
                                type="button"
                                class="secondary-chip text-xs px-2 py-1.5 text-red-600 dark:text-red-300 border-red-200 dark:border-red-500/40"
                                :disabled="!selectedSession"
                                @click="removeSelected"
                            >
                                <MaterialDesignIcon icon-name="trash-can-outline" class="size-4" />
                                {{ $t("rnsh.remove") }}
                            </button>
                        </div>
                    </div>

                    <div
                        ref="outputBox"
                        class="flex-1 min-h-0 bg-zinc-950 dark:bg-black text-zinc-100 font-mono text-xs px-3 md:px-4 py-3 whitespace-pre-wrap break-words overflow-auto custom-scrollbar"
                    >
                        {{ selectedOutput }}
                    </div>

                    <form
                        class="shrink-0 flex flex-wrap gap-2 px-3 md:px-4 py-2.5 border-t border-gray-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-950"
                        @submit.prevent="sendCommand"
                    >
                        <input
                            v-model="commandInput"
                            type="text"
                            class="input-field flex-1 min-w-52 font-mono text-xs"
                            :placeholder="$t('rnsh.command_input_placeholder')"
                            :disabled="!selectedSession"
                        />
                        <button
                            type="submit"
                            class="primary-chip px-3 py-2 text-xs"
                            :disabled="!selectedSession || !commandInput.trim()"
                        >
                            <MaterialDesignIcon icon-name="send" class="size-4" />
                            {{ $t("rnsh.send_line") }}
                        </button>
                    </form>
                </section>
            </div>

            <div
                v-show="activeTab === 'connect'"
                class="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-4 md:px-5 lg:px-8 py-4 space-y-4"
            >
                <p class="text-xs text-gray-500 dark:text-zinc-500 leading-relaxed">
                    {{ $t("rnsh.usage_hint") }}
                </p>
                <div class="grid lg:grid-cols-2 gap-4">
                    <div>
                        <label class="glass-label">{{ $t("rnsh.name") }}</label>
                        <input
                            v-model="connectForm.name"
                            type="text"
                            class="input-field"
                            :placeholder="$t('rnsh.name_placeholder')"
                        />
                    </div>
                    <div>
                        <label class="glass-label">{{ $t("rnsh.destination_hash") }}</label>
                        <input
                            v-model="connectForm.destination"
                            type="text"
                            class="input-field font-mono"
                            :placeholder="$t('rnsh.destination_placeholder')"
                        />
                    </div>
                </div>
                <div>
                    <label class="glass-label">{{ $t("rnsh.remote_command") }}</label>
                    <input
                        v-model="connectForm.command"
                        type="text"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnsh.command_placeholder')"
                    />
                </div>
                <div class="flex flex-wrap items-center gap-4">
                    <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="connectForm.mirror" type="checkbox" class="rounded-sm" />
                        {{ $t("rnsh.mirror_exit_code") }}
                    </label>
                    <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="connectForm.no_id" type="checkbox" class="rounded-sm" />
                        {{ $t("rnsh.no_id") }}
                    </label>
                </div>
                <button type="button" class="primary-chip px-4 py-2 text-sm" @click="createConnectSession">
                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                    {{ $t("rnsh.create_and_start") }}
                </button>
            </div>

            <div
                v-show="activeTab === 'listen'"
                class="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-4 md:px-5 lg:px-8 py-4 space-y-4"
            >
                <p class="text-xs text-gray-500 dark:text-zinc-500 leading-relaxed">
                    {{ $t("rnsh.usage_hint") }}
                </p>
                <div>
                    <label class="glass-label">{{ $t("rnsh.name") }}</label>
                    <input
                        v-model="listenForm.name"
                        type="text"
                        class="input-field"
                        :placeholder="$t('rnsh.name_placeholder')"
                    />
                </div>
                <div>
                    <label class="glass-label">{{ $t("rnsh.allowed_hashes") }}</label>
                    <textarea
                        v-model="listenForm.allowed_hashes_text"
                        rows="4"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnsh.allowed_hashes_placeholder')"
                    ></textarea>
                </div>
                <div>
                    <label class="glass-label">{{ $t("rnsh.default_command") }}</label>
                    <input
                        v-model="listenForm.command"
                        type="text"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnsh.command_placeholder')"
                    />
                </div>
                <button type="button" class="primary-chip px-4 py-2 text-sm" @click="createListenSession">
                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                    {{ $t("rnsh.create_and_start") }}
                </button>
            </div>
        </div>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToolsPageHeader from "./ToolsPageHeader.vue";
import ToastUtils from "../../js/ToastUtils";
import WebSocketConnection from "../../js/WebSocketConnection";
import { loadRnshLayout, saveRnshLayout } from "../../js/browserLayoutStore";

const EMPTY_LAYOUT = {
    selectedSessionId: null,
};

export default {
    name: "RNSHManagerPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
    },
    data() {
        return {
            viewTabs: [
                { id: "sessions", label: "rnsh.tab_sessions", icon: "console-line" },
                { id: "connect", label: "rnsh.tab_connect", icon: "lan-connect" },
                { id: "listen", label: "rnsh.tab_listen", icon: "access-point-network" },
            ],
            activeTab: "sessions",
            sessions: [],
            outputsBySession: {},
            selectedSessionId: null,
            commandInput: "",
            connectForm: {
                name: "",
                destination: "",
                command: "",
                mirror: false,
                no_id: false,
            },
            listenForm: {
                name: "",
                allowed_hashes_text: "",
                command: "",
            },
        };
    },
    computed: {
        selectedSession() {
            return this.sessions.find((session) => session.id === this.selectedSessionId) || null;
        },
        selectedOutput() {
            if (!this.selectedSessionId) {
                return this.$t("rnsh.select_or_create_session");
            }
            const output = this.outputsBySession[this.selectedSessionId];
            if (typeof output === "string") {
                return output;
            }
            return this.$t("rnsh.no_output_yet");
        },
    },
    async mounted() {
        this.restoreLayout();
        await this.loadSessions();
        WebSocketConnection.on("message", this.onWebsocketMessage);
    },
    beforeUnmount() {
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    methods: {
        statusClass(session) {
            if (!session) return "text-gray-500";
            if (session.status === "running") return "text-emerald-600 dark:text-emerald-400";
            if (session.status === "failed") return "text-red-600 dark:text-red-400";
            return "text-gray-500 dark:text-zinc-400";
        },
        statusLabel(session) {
            if (!session) return "-";
            return this.$t(`rnsh.status_${session.status}`);
        },
        restoreLayout() {
            const state = loadRnshLayout();
            const safe = state && typeof state === "object" ? state : EMPTY_LAYOUT;
            this.selectedSessionId = safe.selectedSessionId || null;
        },
        persistLayout() {
            saveRnshLayout({
                selectedSessionId: this.selectedSessionId || null,
            });
        },
        selectSession(sessionId) {
            this.selectedSessionId = sessionId;
            this.persistLayout();
            this.$nextTick(() => {
                this.scrollOutputToBottom();
            });
        },
        ingestSession(session) {
            if (!session || !session.id) {
                return;
            }
            const chunks = Array.isArray(session.output_chunks) ? session.output_chunks : [];
            if (chunks.length > 0) {
                this.outputsBySession[session.id] = chunks.map((chunk) => chunk.text || "").join("");
            } else if (typeof session.output_text === "string") {
                this.outputsBySession[session.id] = session.output_text;
            } else if (!this.outputsBySession[session.id]) {
                this.outputsBySession[session.id] = "";
            }
        },
        async loadSessions() {
            try {
                const response = await window.api.get("/api/v1/rnsh/sessions");
                this.sessions = Array.isArray(response.data?.sessions) ? response.data.sessions : [];
                this.sessions.forEach((session) => this.ingestSession(session));
                if (!this.selectedSessionId && this.sessions.length > 0) {
                    this.selectedSessionId = this.sessions[0].id;
                }
                if (this.selectedSessionId && !this.sessions.find((session) => session.id === this.selectedSessionId)) {
                    this.selectedSessionId = this.sessions[0]?.id || null;
                }
                this.persistLayout();
                this.$nextTick(() => {
                    this.scrollOutputToBottom();
                });
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnsh.failed_to_load_sessions"));
            }
        },
        buildConnectPayload() {
            return {
                name: this.connectForm.name || undefined,
                mode: "connect",
                destination: (this.connectForm.destination || "").trim(),
                remote_command: (this.connectForm.command || "").trim() || undefined,
                mirror: !!this.connectForm.mirror,
                no_id: !!this.connectForm.no_id,
                autostart: true,
            };
        },
        buildListenPayload() {
            return {
                name: this.listenForm.name || undefined,
                mode: "listen",
                allowed_hashes: (this.listenForm.allowed_hashes_text || "")
                    .split("\n")
                    .map((value) => value.trim())
                    .filter((value) => value.length > 0),
                default_command: (this.listenForm.command || "").trim() || undefined,
                autostart: true,
            };
        },
        async createSessionFromPayload(payload) {
            try {
                const response = await window.api.post("/api/v1/rnsh/sessions", payload);
                const session = response.data?.session;
                if (session?.id) {
                    this.outputsBySession[session.id] = "";
                    this.ingestSession(session);
                    await this.loadSessions();
                    this.selectSession(session.id);
                    this.activeTab = "sessions";
                    ToastUtils.success(this.$t("rnsh.session_created"));
                }
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnsh.failed_to_create_session"));
            }
        },
        async createConnectSession() {
            const payload = this.buildConnectPayload();
            if (!payload.destination) {
                ToastUtils.warning(this.$t("rnsh.destination_required"));
                return;
            }
            await this.createSessionFromPayload(payload);
        },
        async createListenSession() {
            await this.createSessionFromPayload(this.buildListenPayload());
        },
        async startSelected() {
            if (!this.selectedSession) return;
            try {
                await window.api.post(`/api/v1/rnsh/sessions/${this.selectedSession.id}/start`, {});
                ToastUtils.success(this.$t("rnsh.session_started"));
                await this.loadSessions();
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnsh.failed_to_start_session"));
            }
        },
        async stopSelected() {
            if (!this.selectedSession) return;
            try {
                await window.api.post(`/api/v1/rnsh/sessions/${this.selectedSession.id}/stop`, {});
                ToastUtils.success(this.$t("rnsh.session_stopped"));
                await this.loadSessions();
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnsh.failed_to_stop_session"));
            }
        },
        async removeSelected() {
            if (!this.selectedSession) return;
            const sessionId = this.selectedSession.id;
            try {
                await window.api.delete(`/api/v1/rnsh/sessions/${sessionId}`);
                delete this.outputsBySession[sessionId];
                ToastUtils.success(this.$t("rnsh.session_removed"));
                await this.loadSessions();
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnsh.failed_to_remove_session"));
            }
        },
        async clearSelectedOutput() {
            if (!this.selectedSession) return;
            try {
                const response = await window.api.post(`/api/v1/rnsh/sessions/${this.selectedSession.id}/clear`, {});
                const session = response.data?.session;
                if (session?.id) {
                    this.outputsBySession[session.id] = "";
                }
                ToastUtils.success(this.$t("rnsh.output_cleared"));
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnsh.failed_to_clear_output"));
            }
        },
        async sendCommand() {
            if (!this.selectedSession || !this.commandInput.trim()) {
                return;
            }
            const text = this.commandInput;
            this.commandInput = "";
            try {
                await window.api.post(`/api/v1/rnsh/sessions/${this.selectedSession.id}/input`, {
                    text,
                    newline: true,
                });
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnsh.failed_to_send_input"));
            }
        },
        appendOutput(sessionId, text) {
            if (!sessionId || typeof text !== "string" || !text.length) {
                return;
            }
            const existing = this.outputsBySession[sessionId] || "";
            const merged = existing + text;
            this.outputsBySession[sessionId] = merged.length > 250000 ? merged.slice(-250000) : merged;
            if (sessionId === this.selectedSessionId) {
                this.$nextTick(() => {
                    this.scrollOutputToBottom();
                });
            }
        },
        onWebsocketMessage(event) {
            let payload = null;
            try {
                payload = JSON.parse(event.data);
            } catch {
                return;
            }
            if (!payload || typeof payload !== "object") {
                return;
            }
            if (payload.type === "rnsh.session.change") {
                void this.loadSessions();
                return;
            }
            if (payload.type === "rnsh.output") {
                this.appendOutput(payload.session_id, payload.chunk?.text);
            }
        },
        scrollOutputToBottom() {
            const target = this.$refs.outputBox;
            if (!target) {
                return;
            }
            target.scrollTop = target.scrollHeight;
        },
    },
};
</script>
