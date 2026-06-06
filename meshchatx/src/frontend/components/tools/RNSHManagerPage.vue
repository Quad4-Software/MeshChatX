<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <ToolsPageHeader
            v-show="!sessionFullscreen"
            icon="console-network-outline"
            :title="$t('rnsh.title')"
            :description="headerDescription"
            :eyebrow="$t('rnsh.remote_shell')"
            accent="indigo"
        />
        <div
            v-show="!sessionFullscreen"
            class="flex items-stretch h-9 shrink-0 border-b border-gray-200 dark:border-zinc-800 bg-gray-50 dark:bg-zinc-900 overflow-x-auto"
            role="tablist"
        >
            <button
                v-for="tab in viewTabs"
                :key="tab.id"
                type="button"
                role="tab"
                :aria-selected="activeTab === tab.id"
                class="inline-flex items-center gap-1 px-2.5 sm:px-4 border-r border-gray-200 dark:border-zinc-800 text-xs sm:text-sm transition-colors shrink-0"
                :class="
                    activeTab === tab.id
                        ? 'bg-white dark:bg-zinc-950 text-gray-900 dark:text-gray-100 font-medium'
                        : 'text-gray-500 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-800'
                "
                @click="activeTab = tab.id"
            >
                <MaterialDesignIcon :icon-name="tab.icon" class="size-4 shrink-0 opacity-70" />
                <span class="lg:hidden">{{ $t(tab.shortLabel || tab.label) }}</span>
                <span class="hidden lg:inline">{{ $t(tab.label) }}</span>
            </button>
        </div>

        <div v-show="!sessionFullscreen" class="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div v-show="activeTab === 'sessions'" class="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
                <aside
                    class="flex flex-col min-h-0 shrink-0 border-gray-200 dark:border-zinc-800 px-2 sm:px-3 md:px-4 py-2 sm:py-3 gap-2 sm:gap-3"
                    :class="sessionsAsideClass"
                >
                    <div class="flex items-center justify-between gap-2">
                        <div class="text-xs sm:text-sm font-semibold text-gray-900 dark:text-white">
                            {{ $t("rnsh.sessions") }}
                        </div>
                        <button type="button" class="secondary-chip text-xs px-2 py-1.5" @click="loadSessions">
                            <MaterialDesignIcon icon-name="refresh" class="size-4" />
                            <span class="hidden sm:inline">{{ $t("rnsh.refresh") }}</span>
                        </button>
                    </div>

                    <div class="flex-1 min-h-0 space-y-1 overflow-y-auto custom-scrollbar pr-0.5">
                        <button
                            v-for="session in sessions"
                            :key="session.id"
                            type="button"
                            class="w-full text-left rounded-lg px-2.5 sm:px-3 py-1.5 sm:py-2 transition-colors"
                            :class="
                                session.id === selectedSessionId
                                    ? 'bg-indigo-100 dark:bg-indigo-900/35 text-indigo-950 dark:text-indigo-100'
                                    : 'text-gray-900 dark:text-zinc-100 hover:bg-gray-100 dark:hover:bg-zinc-800/70'
                            "
                            @click="selectSession(session.id)"
                        >
                            <div class="flex items-center justify-between gap-2">
                                <div class="font-medium text-xs sm:text-sm text-gray-900 dark:text-zinc-100 truncate">
                                    {{ session.name || $t("rnsh.unnamed_session") }}
                                </div>
                                <span
                                    class="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wide shrink-0"
                                    :class="statusClass(session)"
                                >
                                    {{ statusLabel(session) }}
                                </span>
                            </div>
                            <div
                                class="font-mono text-[10px] sm:text-xs text-gray-500 dark:text-zinc-400 truncate mt-0.5"
                            >
                                {{ sessionSubtitle(session) }}
                            </div>
                        </button>
                        <div v-if="sessions.length === 0" class="text-xs text-gray-500 dark:text-zinc-400 px-1">
                            {{ $t("rnsh.no_sessions") }}
                        </div>
                    </div>
                </aside>

                <section class="flex-1 min-w-0 min-h-0 flex flex-col" :class="terminalSectionClass">
                    <RNSHSessionTerminal
                        ref="sessionTerminal"
                        :session="selectedSession"
                        :output="selectedOutput"
                        :command-input="commandInput"
                        :listen-address="selectedListenAddress"
                        :show-sessions-toggle="isNarrowScreen"
                        :sessions-open="mobileSessionsOpen"
                        :compact-header="isNarrowScreen"
                        @update:command-input="commandInput = $event"
                        @send="sendCommand"
                        @start="startSelected"
                        @stop="stopSelected"
                        @clear="clearSelectedOutput"
                        @remove="removeSelected"
                        @copy-address="copyListenAddress"
                        @toggle-fullscreen="toggleSessionFullscreen"
                        @toggle-sessions="toggleMobileSessions"
                    />
                </section>
            </div>

            <div
                v-show="activeTab === 'connect'"
                class="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-3 sm:px-4 md:px-5 lg:px-8 py-3 sm:py-4 space-y-3 sm:space-y-4"
            >
                <p class="text-xs text-gray-500 dark:text-zinc-500 leading-relaxed">
                    {{ $t("rnsh.usage_hint") }}
                </p>
                <div class="grid gap-3 sm:gap-4 lg:grid-cols-2">
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
                            class="input-field font-mono text-xs"
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
                <div>
                    <label class="glass-label">{{ $t("rnsh.config_dir") }}</label>
                    <input
                        v-model="connectForm.config_path"
                        type="text"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnsh.config_dir_placeholder')"
                    />
                    <p class="mt-1 text-[10px] sm:text-xs text-gray-500 dark:text-zinc-500">
                        {{ $t("rnsh.config_dir_hint") }}
                    </p>
                </div>
                <div class="flex flex-wrap items-center gap-3 sm:gap-4">
                    <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="connectForm.mirror" type="checkbox" class="rounded-sm" />
                        {{ $t("rnsh.mirror_exit_code") }}
                    </label>
                    <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="connectForm.no_id" type="checkbox" class="rounded-sm" />
                        {{ $t("rnsh.no_id") }}
                    </label>
                </div>
                <button
                    type="button"
                    class="primary-chip px-4 py-2 text-sm w-full sm:w-auto"
                    @click="createConnectSession"
                >
                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                    {{ $t("rnsh.create_and_start") }}
                </button>
            </div>

            <div
                v-show="activeTab === 'listen'"
                class="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-3 sm:px-4 md:px-5 lg:px-8 py-3 sm:py-4 space-y-3 sm:space-y-4"
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
                <div>
                    <label class="glass-label">{{ $t("rnsh.config_dir") }}</label>
                    <input
                        v-model="listenForm.config_path"
                        type="text"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnsh.config_dir_placeholder')"
                    />
                    <p class="mt-1 text-[10px] sm:text-xs text-gray-500 dark:text-zinc-500">
                        {{ $t("rnsh.config_dir_hint") }}
                    </p>
                </div>
                <button
                    type="button"
                    class="primary-chip px-4 py-2 text-sm w-full sm:w-auto"
                    @click="createListenSession"
                >
                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                    {{ $t("rnsh.create_and_start") }}
                </button>
            </div>
        </div>

        <Teleport to="body">
            <div
                v-if="sessionFullscreen"
                class="fixed inset-0 z-[220] flex flex-col bg-zinc-950"
                role="dialog"
                aria-modal="true"
                :aria-label="$t('rnsh.session_output')"
            >
                <RNSHSessionTerminal
                    ref="fullscreenTerminal"
                    :session="selectedSession"
                    :output="selectedOutput"
                    :command-input="commandInput"
                    :listen-address="selectedListenAddress"
                    fullscreen
                    :show-sessions-toggle="isNarrowScreen"
                    :sessions-open="mobileSessionsOpen"
                    compact-header
                    @update:command-input="commandInput = $event"
                    @send="sendCommand"
                    @start="startSelected"
                    @stop="stopSelected"
                    @clear="clearSelectedOutput"
                    @remove="removeSelected"
                    @copy-address="copyListenAddress"
                    @toggle-fullscreen="toggleSessionFullscreen"
                    @toggle-sessions="toggleMobileSessions"
                />
            </div>
        </Teleport>
    </div>
</template>

<script>
import MaterialDesignIcon from "../MaterialDesignIcon.vue";
import ToolsPageHeader from "./ToolsPageHeader.vue";
import RNSHSessionTerminal from "./RNSHSessionTerminal.vue";
import ToastUtils from "../../js/ToastUtils";
import WebSocketConnection from "../../js/WebSocketConnection";
import { loadRnshLayout, saveRnshLayout } from "../../js/browserLayoutStore";
import { renderTerminalOutput } from "../../js/terminalRender";

const EMPTY_LAYOUT = {
    selectedSessionId: null,
};

const NARROW_BREAKPOINT_PX = 1024;

export default {
    name: "RNSHManagerPage",
    components: {
        MaterialDesignIcon,
        ToolsPageHeader,
        RNSHSessionTerminal,
    },
    data() {
        return {
            viewTabs: [
                {
                    id: "sessions",
                    label: "rnsh.tab_sessions",
                    shortLabel: "rnsh.tab_sessions_short",
                    icon: "console-line",
                },
                { id: "connect", label: "rnsh.tab_connect", shortLabel: "rnsh.tab_connect_short", icon: "lan-connect" },
                {
                    id: "listen",
                    label: "rnsh.tab_listen",
                    shortLabel: "rnsh.tab_listen_short",
                    icon: "access-point-network",
                },
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
                config_path: "",
                mirror: false,
                no_id: false,
            },
            listenForm: {
                name: "",
                allowed_hashes_text: "",
                command: "",
                config_path: "",
            },
            isNarrowScreen: false,
            mobileSessionsOpen: false,
            sessionFullscreen: false,
            onWindowResize: null,
            onFullscreenKeydown: null,
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
            if (typeof output === "string" && output.length > 0) {
                return renderTerminalOutput(output);
            }
            return this.$t("rnsh.no_output_yet");
        },
        selectedListenAddress() {
            const session = this.selectedSession;
            if (!session || session.mode !== "listen") {
                return "";
            }
            return session.listen_address || "";
        },
        headerDescription() {
            return this.isNarrowScreen ? "" : this.$t("rnsh.description");
        },
        sessionsAsideClass() {
            if (!this.isNarrowScreen) {
                return "lg:w-80 xl:w-96 border-b lg:border-b-0 lg:border-r max-h-[36vh] lg:max-h-none";
            }
            if (this.mobileSessionsOpen) {
                return "flex-1 min-h-0 border-b";
            }
            return "hidden";
        },
        terminalSectionClass() {
            if (this.isNarrowScreen && this.mobileSessionsOpen) {
                return "hidden";
            }
            return "";
        },
    },
    watch: {
        sessionFullscreen(active) {
            if (typeof document === "undefined") {
                return;
            }
            document.body.style.overflow = active ? "hidden" : "";
            if (active) {
                this.$nextTick(() => this.scrollOutputToBottom());
            }
        },
    },
    async mounted() {
        this.updateViewport();
        this.onWindowResize = () => this.updateViewport();
        window.addEventListener("resize", this.onWindowResize, { passive: true });
        this.onFullscreenKeydown = (event) => {
            if (event.key === "Escape" && this.sessionFullscreen) {
                this.sessionFullscreen = false;
            }
        };
        window.addEventListener("keydown", this.onFullscreenKeydown);
        this.restoreLayout();
        await this.loadSessions();
        WebSocketConnection.on("message", this.onWebsocketMessage);
    },
    beforeUnmount() {
        if (this.onWindowResize) {
            window.removeEventListener("resize", this.onWindowResize);
        }
        if (this.onFullscreenKeydown) {
            window.removeEventListener("keydown", this.onFullscreenKeydown);
        }
        document.body.style.overflow = "";
        WebSocketConnection.off("message", this.onWebsocketMessage);
    },
    methods: {
        updateViewport() {
            const narrow = typeof window !== "undefined" && window.innerWidth < NARROW_BREAKPOINT_PX;
            this.isNarrowScreen = narrow;
            if (!narrow) {
                this.mobileSessionsOpen = false;
            }
        },
        toggleMobileSessions() {
            this.mobileSessionsOpen = !this.mobileSessionsOpen;
        },
        toggleSessionFullscreen() {
            this.sessionFullscreen = !this.sessionFullscreen;
            if (this.sessionFullscreen && this.isNarrowScreen) {
                this.mobileSessionsOpen = false;
            }
        },
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
        sessionSubtitle(session) {
            if (!session) return "-";
            if (session.mode === "listen") {
                return session.listen_address || this.$t("rnsh.listen_mode");
            }
            return session.destination || "-";
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
            if (this.isNarrowScreen) {
                this.mobileSessionsOpen = false;
            }
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
                config_path: (this.connectForm.config_path || "").trim() || undefined,
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
                config_path: (this.listenForm.config_path || "").trim() || undefined,
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
        async copyListenAddress() {
            const address = this.selectedListenAddress;
            if (!address) {
                return;
            }
            try {
                if (navigator.clipboard?.writeText) {
                    await navigator.clipboard.writeText(address);
                }
                ToastUtils.success(this.$t("rnsh.address_copied"));
            } catch {
                ToastUtils.error(this.$t("rnsh.failed_to_copy_address"));
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
            const inline = this.$refs.sessionTerminal;
            const full = this.$refs.fullscreenTerminal;
            if (this.sessionFullscreen && full?.scrollToBottom) {
                full.scrollToBottom();
            } else if (inline?.scrollToBottom) {
                inline.scrollToBottom();
            }
        },
    },
};
</script>
