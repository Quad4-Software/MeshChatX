<!-- SPDX-License-Identifier: 0BSD -->

<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
        <ToolsPageHeader
            v-show="!sessionFullscreen"
            icon="console"
            :title="$t('rnx.title')"
            :description="headerDescription"
            :eyebrow="$t('rnx.remote_exec')"
            accent="teal"
        />
        <div
            v-show="!sessionFullscreen"
            class="flex items-stretch h-9 shrink-0 border-b border-sem-border bg-sem-surface-muted overflow-x-auto"
            role="tablist"
        >
            <button
                v-for="tab in viewTabs"
                :key="tab.id"
                type="button"
                role="tab"
                :aria-selected="activeTab === tab.id"
                class="inline-flex items-center gap-1 px-2.5 sm:px-4 border-r border-sem-border text-xs sm:text-sm transition-colors shrink-0"
                :class="
                    activeTab === tab.id
                        ? 'bg-sem-surface text-gray-900 dark:text-gray-100 font-medium'
                        : 'text-sem-fg-muted hover:bg-sem-surface-muted'
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
                    class="flex flex-col min-h-0 shrink-0 border-sem-border px-2 sm:px-3 md:px-4 py-2 sm:py-3 gap-2 sm:gap-3"
                    :class="sessionsAsideClass"
                >
                    <div class="flex items-center justify-between gap-2">
                        <div class="text-xs sm:text-sm font-semibold text-sem-fg">
                            {{ $t("rnx.sessions") }}
                        </div>
                        <button type="button" class="secondary-chip text-xs px-2 py-1.5" @click="loadSessions">
                            <MaterialDesignIcon icon-name="refresh" class="size-4" />
                            <span class="hidden sm:inline">{{ $t("rnx.refresh") }}</span>
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
                                    : 'text-sem-fg hover:bg-sem-surface-muted/70'
                            "
                            @click="selectSession(session.id)"
                        >
                            <div class="flex items-center justify-between gap-2">
                                <div class="font-medium text-xs sm:text-sm text-sem-fg truncate">
                                    {{ session.name || $t("rnx.unnamed_session") }}
                                </div>
                                <span
                                    class="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wide shrink-0"
                                    :class="statusClass(session)"
                                >
                                    {{ statusLabel(session) }}
                                </span>
                            </div>
                            <div class="font-mono text-[10px] sm:text-xs text-sem-fg-muted truncate mt-0.5">
                                {{ sessionSubtitle(session) }}
                            </div>
                        </button>
                        <div v-if="sessions.length === 0" class="text-xs text-sem-fg-muted px-1">
                            {{ $t("rnx.no_sessions") }}
                        </div>
                    </div>
                </aside>

                <section class="flex-1 min-w-0 min-h-0 flex flex-col" :class="terminalSectionClass">
                    <RNSHSessionTerminal
                        ref="sessionTerminal"
                        i18n-prefix="rnx"
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
                v-show="activeTab === 'execute'"
                class="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-3 sm:px-4 md:px-5 lg:px-8 py-3 sm:py-4 space-y-3 sm:space-y-4"
            >
                <p class="text-xs text-sem-fg-muted leading-relaxed">
                    {{ $t("rnx.usage_hint") }}
                </p>
                <div class="grid gap-3 sm:gap-4 lg:grid-cols-2">
                    <div>
                        <label class="glass-label">{{ $t("rnx.name") }}</label>
                        <input
                            v-model="executeForm.name"
                            type="text"
                            class="input-field"
                            :placeholder="$t('rnx.name_placeholder')"
                        />
                    </div>
                    <div>
                        <label class="glass-label">{{ $t("rnx.destination_hash") }}</label>
                        <input
                            v-model="executeForm.destination"
                            type="text"
                            class="input-field font-mono text-xs"
                            :placeholder="$t('rnx.destination_placeholder')"
                        />
                    </div>
                </div>
                <div v-if="!executeForm.interactive">
                    <label class="glass-label">{{ $t("rnx.remote_command") }}</label>
                    <input
                        v-model="executeForm.command"
                        type="text"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnx.command_placeholder')"
                    />
                </div>
                <div>
                    <label class="glass-label">{{ $t("rnx.config_dir") }}</label>
                    <input
                        v-model="executeForm.config_path"
                        type="text"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnx.config_dir_placeholder')"
                    />
                    <p class="mt-1 text-[10px] sm:text-xs text-sem-fg-muted">
                        {{ $t("rnx.config_dir_hint") }}
                    </p>
                </div>
                <div class="flex flex-wrap items-center gap-3 sm:gap-4">
                    <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="executeForm.mirror" type="checkbox" class="rounded-sm" />
                        {{ $t("rnx.mirror_exit_code") }}
                    </label>
                    <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="executeForm.no_id" type="checkbox" class="rounded-sm" />
                        {{ $t("rnx.no_id") }}
                    </label>
                    <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="executeForm.detailed" type="checkbox" class="rounded-sm" />
                        {{ $t("rnx.detailed") }}
                    </label>
                    <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="executeForm.interactive" type="checkbox" class="rounded-sm" />
                        {{ $t("rnx.interactive") }}
                    </label>
                </div>
                <div class="grid gap-3 sm:gap-4 lg:grid-cols-2">
                    <div>
                        <label class="glass-label">{{ $t("rnx.timeout") }}</label>
                        <input
                            v-model="executeForm.timeout"
                            type="number"
                            min="1"
                            step="1"
                            class="input-field font-mono text-xs"
                        />
                    </div>
                    <div>
                        <label class="glass-label">{{ $t("rnx.result_timeout") }}</label>
                        <input
                            v-model="executeForm.result_timeout"
                            type="number"
                            min="1"
                            step="1"
                            class="input-field font-mono text-xs"
                        />
                    </div>
                    <div>
                        <label class="glass-label">{{ $t("rnx.stdout_limit") }}</label>
                        <input
                            v-model="executeForm.stdout_limit"
                            type="number"
                            min="1"
                            step="1"
                            class="input-field font-mono text-xs"
                        />
                    </div>
                    <div>
                        <label class="glass-label">{{ $t("rnx.stderr_limit") }}</label>
                        <input
                            v-model="executeForm.stderr_limit"
                            type="number"
                            min="1"
                            step="1"
                            class="input-field font-mono text-xs"
                        />
                    </div>
                </div>
                <button
                    type="button"
                    class="primary-chip px-4 py-2 text-sm w-full sm:w-auto"
                    @click="createExecuteSession"
                >
                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                    {{ $t("rnx.create_and_start") }}
                </button>
            </div>

            <div
                v-show="activeTab === 'listen'"
                class="flex-1 min-h-0 overflow-y-auto custom-scrollbar px-3 sm:px-4 md:px-5 lg:px-8 py-3 sm:py-4 space-y-3 sm:space-y-4"
            >
                <p class="text-xs text-sem-fg-muted leading-relaxed">
                    {{ $t("rnx.usage_hint") }}
                </p>
                <div>
                    <label class="glass-label">{{ $t("rnx.name") }}</label>
                    <input
                        v-model="listenForm.name"
                        type="text"
                        class="input-field"
                        :placeholder="$t('rnx.name_placeholder')"
                    />
                </div>
                <div>
                    <label class="glass-label">{{ $t("rnx.allowed_hashes") }}</label>
                    <textarea
                        v-model="listenForm.allowed_hashes_text"
                        rows="4"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnx.allowed_hashes_placeholder')"
                    ></textarea>
                </div>
                <div>
                    <label class="glass-label">{{ $t("rnx.config_dir") }}</label>
                    <input
                        v-model="listenForm.config_path"
                        type="text"
                        class="input-field font-mono text-xs"
                        :placeholder="$t('rnx.config_dir_placeholder')"
                    />
                    <p class="mt-1 text-[10px] sm:text-xs text-sem-fg-muted">
                        {{ $t("rnx.config_dir_hint") }}
                    </p>
                </div>
                <div class="flex flex-wrap items-center gap-3 sm:gap-4">
                    <label class="flex items-center gap-2 text-xs sm:text-sm text-gray-700 dark:text-gray-300">
                        <input v-model="listenForm.no_auth" type="checkbox" class="rounded-sm" />
                        {{ $t("rnx.no_auth") }}
                    </label>
                </div>
                <button
                    type="button"
                    class="primary-chip px-4 py-2 text-sm w-full sm:w-auto"
                    @click="createListenSession"
                >
                    <MaterialDesignIcon icon-name="plus" class="size-4" />
                    {{ $t("rnx.create_and_start") }}
                </button>
            </div>
        </div>

        <Teleport to="body">
            <div
                v-if="sessionFullscreen"
                class="fixed inset-0 z-[220] flex flex-col bg-zinc-950"
                role="dialog"
                aria-modal="true"
                :aria-label="$t('rnx.session_output')"
            >
                <RNSHSessionTerminal
                    ref="fullscreenTerminal"
                    i18n-prefix="rnx"
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
import { loadRnxLayout, saveRnxLayout } from "../../js/browserLayoutStore";
import { renderTerminalOutput } from "../../js/terminalRender";
import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
import GlobalEmitter from "../../js/GlobalEmitter";

const EMPTY_LAYOUT = {
    selectedSessionId: null,
};

const NARROW_BREAKPOINT_PX = 1024;

export default {
    name: "RNXManagerPage",
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
                    label: "rnx.tab_sessions",
                    shortLabel: "rnx.tab_sessions_short",
                    icon: "console-line",
                },
                { id: "execute", label: "rnx.tab_execute", shortLabel: "rnx.tab_execute_short", icon: "lan-connect" },
                {
                    id: "listen",
                    label: "rnx.tab_listen",
                    shortLabel: "rnx.tab_listen_short",
                    icon: "access-point-network",
                },
            ],
            activeTab: "sessions",
            sessions: [],
            outputsBySession: {},
            selectedSessionId: null,
            commandInput: "",
            executeForm: {
                name: "",
                destination: "",
                command: "",
                config_path: "",
                mirror: false,
                no_id: false,
                detailed: true,
                interactive: false,
                timeout: "",
                result_timeout: "",
                stdout_limit: "",
                stderr_limit: "",
            },
            listenForm: {
                name: "",
                allowed_hashes_text: "",
                config_path: "",
                no_auth: false,
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
                return this.$t("rnx.select_or_create_session");
            }
            const output = this.outputsBySession[this.selectedSessionId];
            if (typeof output === "string" && output.length > 0) {
                return renderTerminalOutput(output);
            }
            return this.$t("rnx.no_output_yet");
        },
        selectedListenAddress() {
            const session = this.selectedSession;
            if (!session || session.mode !== "listen") {
                return "";
            }
            return session.listen_address || "";
        },
        headerDescription() {
            return this.isNarrowScreen ? "" : this.$t("rnx.description");
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
        onWsEvent("rnx.session.change", this.onSessionChange);
        onWsEvent("rnx.output", this.onOutputEvent);
        GlobalEmitter.on("websocket-reconnected", this.onWebsocketReconnected);
    },
    beforeUnmount() {
        if (this.onWindowResize) {
            window.removeEventListener("resize", this.onWindowResize);
        }
        if (this.onFullscreenKeydown) {
            window.removeEventListener("keydown", this.onFullscreenKeydown);
        }
        document.body.style.overflow = "";
        offWsEvent("rnx.session.change", this.onSessionChange);
        offWsEvent("rnx.output", this.onOutputEvent);
        GlobalEmitter.off("websocket-reconnected", this.onWebsocketReconnected);
    },
    methods: {
        onWebsocketReconnected() {
            void this.loadSessions();
        },
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
            return "text-sem-fg-muted";
        },
        statusLabel(session) {
            if (!session) return "-";
            return this.$t(`rnx.status_${session.status}`);
        },
        sessionSubtitle(session) {
            if (!session) return "-";
            if (session.mode === "listen") {
                return session.listen_address || this.$t("rnx.listen_mode");
            }
            return session.destination || "-";
        },
        restoreLayout() {
            const state = loadRnxLayout();
            const safe = state && typeof state === "object" ? state : EMPTY_LAYOUT;
            this.selectedSessionId = safe.selectedSessionId || null;
        },
        persistLayout() {
            saveRnxLayout({
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
            const existing = this.outputsBySession[session.id] || "";
            const chunks = Array.isArray(session.output_chunks) ? session.output_chunks : [];
            const fromChunks = chunks.length > 0 ? chunks.map((chunk) => chunk.text || "").join("") : "";
            const fromText = typeof session.output_text === "string" ? session.output_text : "";
            // Prefer the longer server buffer so a short chunk tail cannot hide output_text.
            const incoming = fromText.length >= fromChunks.length ? fromText : fromChunks;
            if (!incoming) {
                if (!Object.prototype.hasOwnProperty.call(this.outputsBySession, session.id)) {
                    this.outputsBySession[session.id] = "";
                }
                return;
            }
            // Keep a longer live WebSocket buffer when a reload returns a truncated tail.
            if (existing.length > incoming.length) {
                if (
                    existing.endsWith(incoming) ||
                    (fromChunks && existing.endsWith(fromChunks)) ||
                    (fromChunks && existing.includes(fromChunks))
                ) {
                    return;
                }
            }
            this.outputsBySession[session.id] = incoming;
        },
        async loadSessions() {
            try {
                const response = await window.api.get("/api/v1/rnx/sessions");
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
                ToastUtils.error(error?.response?.data?.message || this.$t("rnx.failed_to_load_sessions"));
            }
        },
        buildExecutePayload() {
            const interactive = !!this.executeForm.interactive;
            return {
                name: this.executeForm.name || undefined,
                mode: interactive ? "interactive" : "execute",
                destination: (this.executeForm.destination || "").trim(),
                remote_command: interactive ? undefined : (this.executeForm.command || "").trim() || undefined,
                config_path: (this.executeForm.config_path || "").trim() || undefined,
                mirror: !!this.executeForm.mirror,
                no_id: !!this.executeForm.no_id,
                detailed: !!this.executeForm.detailed,
                timeout: (this.executeForm.timeout || "").toString().trim() || undefined,
                result_timeout: (this.executeForm.result_timeout || "").toString().trim() || undefined,
                stdout_limit: (this.executeForm.stdout_limit || "").toString().trim() || undefined,
                stderr_limit: (this.executeForm.stderr_limit || "").toString().trim() || undefined,
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
                config_path: (this.listenForm.config_path || "").trim() || undefined,
                no_auth: !!this.listenForm.no_auth,
                autostart: true,
            };
        },
        async createSessionFromPayload(payload) {
            try {
                const response = await window.api.post("/api/v1/rnx/sessions", payload);
                const session = response.data?.session;
                if (session?.id) {
                    this.outputsBySession[session.id] = "";
                    this.ingestSession(session);
                    await this.loadSessions();
                    this.selectSession(session.id);
                    this.activeTab = "sessions";
                    ToastUtils.success(this.$t("rnx.session_created"));
                }
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnx.failed_to_create_session"));
            }
        },
        async createExecuteSession() {
            const payload = this.buildExecutePayload();
            if (!payload.destination) {
                ToastUtils.warning(this.$t("rnx.destination_required"));
                return;
            }
            if (payload.mode !== "interactive" && !payload.remote_command) {
                ToastUtils.warning(this.$t("rnx.command_required"));
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
                await window.api.post(`/api/v1/rnx/sessions/${this.selectedSession.id}/start`, {});
                ToastUtils.success(this.$t("rnx.session_started"));
                await this.loadSessions();
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnx.failed_to_start_session"));
            }
        },
        async stopSelected() {
            if (!this.selectedSession) return;
            try {
                await window.api.post(`/api/v1/rnx/sessions/${this.selectedSession.id}/stop`, {});
                ToastUtils.success(this.$t("rnx.session_stopped"));
                await this.loadSessions();
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnx.failed_to_stop_session"));
            }
        },
        async removeSelected() {
            if (!this.selectedSession) return;
            const sessionId = this.selectedSession.id;
            try {
                await window.api.delete(`/api/v1/rnx/sessions/${sessionId}`);
                delete this.outputsBySession[sessionId];
                ToastUtils.success(this.$t("rnx.session_removed"));
                await this.loadSessions();
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnx.failed_to_remove_session"));
            }
        },
        async clearSelectedOutput() {
            if (!this.selectedSession) return;
            try {
                const response = await window.api.post(`/api/v1/rnx/sessions/${this.selectedSession.id}/clear`, {});
                const session = response.data?.session;
                if (session?.id) {
                    this.outputsBySession[session.id] = "";
                }
                ToastUtils.success(this.$t("rnx.output_cleared"));
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnx.failed_to_clear_output"));
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
                ToastUtils.success(this.$t("rnx.address_copied"));
            } catch {
                ToastUtils.error(this.$t("rnx.failed_to_copy_address"));
            }
        },
        async sendCommand() {
            if (!this.selectedSession || !this.commandInput.trim()) {
                return;
            }
            const text = this.commandInput;
            this.commandInput = "";
            try {
                await window.api.post(`/api/v1/rnx/sessions/${this.selectedSession.id}/input`, {
                    text,
                    newline: true,
                });
            } catch (error) {
                ToastUtils.error(error?.response?.data?.message || this.$t("rnx.failed_to_send_input"));
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
        onSessionChange() {
            void this.loadSessions();
        },
        onOutputEvent(payload) {
            this.appendOutput(payload.session_id, payload.chunk?.text);
        },
        onWebsocketMessage(message) {
            let json;
            try {
                if (
                    message &&
                    typeof message === "object" &&
                    typeof message.type === "string" &&
                    message.data === undefined
                ) {
                    json = message;
                } else {
                    const raw = typeof message === "string" ? message : message?.data;
                    json = typeof raw === "string" ? JSON.parse(raw) : message;
                }
            } catch {
                return;
            }
            if (!json || typeof json !== "object" || typeof json.type !== "string") {
                return;
            }
            if (json.type === "rnx.session.change") {
                return this.onSessionChange(json);
            }
            if (json.type === "rnx.output") {
                return this.onOutputEvent(json);
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
