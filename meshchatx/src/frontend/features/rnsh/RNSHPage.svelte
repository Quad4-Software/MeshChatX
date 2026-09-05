<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, tick } from "svelte";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import { loadRnshLayout, saveRnshLayout } from "../../js/browserLayoutStore.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import RemoteShellTerminal from "../remote-shell/components/RemoteShellTerminal.svelte";
    import RemoteShellFullscreenDialog from "../remote-shell/components/RemoteShellFullscreenDialog.svelte";
    import { NARROW_BREAKPOINT_PX } from "../remote-shell/lib/constants.js";
    import {
        appendSessionOutput,
        formatTerminalOutput,
        ingestSessionOutput,
    } from "../remote-shell/lib/sessionOutput.js";
    import RNSHSessionsList from "./components/RNSHSessionsList.svelte";
    import RNSHConnectTab from "./components/RNSHConnectTab.svelte";
    import RNSHListenTab from "./components/RNSHListenTab.svelte";
    import { DEFAULT_RNSH_CONNECT_FORM, DEFAULT_RNSH_LISTEN_FORM, RNSH_VIEW_TABS } from "./lib/constants.js";
    import {
        buildRnshConnectPayload,
        buildRnshListenPayload,
        clearRnshSessionOutput,
        createRnshSession,
        fetchRnshSessions,
        removeRnshSession,
        sendRnshSessionInput,
        startRnshSession,
        stopRnshSession,
    } from "./lib/rnshApi.js";
    import type { RnshConnectForm, RnshListenForm, RnshSession, RnshTabId } from "./lib/types.js";

    let activeTab = $state<RnshTabId>("sessions");
    let sessions = $state<RnshSession[]>([]);
    let outputsBySession = $state<Record<string, string>>({});
    let selectedSessionId = $state<string | null>(null);
    let commandInput = $state("");
    let connectForm = $state<RnshConnectForm>({ ...DEFAULT_RNSH_CONNECT_FORM });
    let listenForm = $state<RnshListenForm>({ ...DEFAULT_RNSH_LISTEN_FORM });
    let isNarrowScreen = $state(false);
    let mobileSessionsOpen = $state(false);
    let sessionFullscreen = $state(false);

    let sessionTerminal = $state<ReturnType<typeof RemoteShellTerminal> | null>(null);
    let fullscreenTerminal = $state<ReturnType<typeof RemoteShellFullscreenDialog> | null>(null);

    const selectedSession = $derived(sessions.find((session) => session.id === selectedSessionId) || null);

    const selectedOutput = $derived(
        formatTerminalOutput(
            selectedSessionId,
            selectedSessionId ? outputsBySession[selectedSessionId] : undefined,
            t("rnsh.select_or_create_session"),
            t("rnsh.no_output_yet")
        )
    );

    const selectedListenAddress = $derived(
        selectedSession && selectedSession.mode === "listen" ? selectedSession.listen_address || "" : ""
    );

    const headerDescription = $derived(isNarrowScreen ? "" : t("rnsh.description"));

    const sessionsAsideClass = $derived(
        !isNarrowScreen
            ? "lg:w-80 xl:w-96 border-b lg:border-b-0 lg:border-r max-h-[36vh] lg:max-h-none"
            : mobileSessionsOpen
              ? "flex-1 min-h-0 border-b"
              : "hidden"
    );

    const terminalSectionClass = $derived(isNarrowScreen && mobileSessionsOpen ? "hidden" : "");

    function updateViewport(): void {
        const narrow = typeof window !== "undefined" && window.innerWidth < NARROW_BREAKPOINT_PX;
        isNarrowScreen = narrow;
        if (!narrow) {
            mobileSessionsOpen = false;
        }
    }

    function toggleMobileSessions(): void {
        mobileSessionsOpen = !mobileSessionsOpen;
    }

    function toggleSessionFullscreen(): void {
        sessionFullscreen = !sessionFullscreen;
        if (sessionFullscreen && isNarrowScreen) {
            mobileSessionsOpen = false;
        }
    }

    function restoreLayout(): void {
        const state = loadRnshLayout();
        if (state && typeof state === "object") {
            selectedSessionId = state.selectedSessionId || null;
        }
    }

    function persistLayout(): void {
        saveRnshLayout({
            selectedSessionId: selectedSessionId || null,
        });
    }

    function scrollOutputToBottom(): void {
        if (sessionFullscreen && fullscreenTerminal) {
            fullscreenTerminal.scrollToBottom();
        } else if (sessionTerminal) {
            sessionTerminal.scrollToBottom();
        }
    }

    function selectSession(sessionId: string): void {
        selectedSessionId = sessionId;
        persistLayout();
        if (isNarrowScreen) {
            mobileSessionsOpen = false;
        }
        void tick().then(() => {
            scrollOutputToBottom();
        });
    }

    function ingestSession(session: RnshSession): void {
        ingestSessionOutput(session, outputsBySession);
        outputsBySession = { ...outputsBySession };
    }

    async function loadSessions(): Promise<void> {
        try {
            const fetched = await fetchRnshSessions();
            sessions = fetched;
            sessions.forEach((session) => ingestSession(session));
            if (!selectedSessionId && sessions.length > 0) {
                selectedSessionId = sessions[0].id;
            }
            if (selectedSessionId && !sessions.find((session) => session.id === selectedSessionId)) {
                selectedSessionId = sessions[0]?.id || null;
            }
            persistLayout();
            void tick().then(() => {
                scrollOutputToBottom();
            });
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnsh.failed_to_load_sessions"));
        }
    }

    async function createConnectSession(): Promise<void> {
        const payload = buildRnshConnectPayload(connectForm);
        if (!payload.destination) {
            ToastUtils.warning(t("rnsh.destination_required"));
            return;
        }
        try {
            const created = await createRnshSession(payload);
            if (created?.id) {
                outputsBySession[created.id] = "";
                outputsBySession = { ...outputsBySession };
                ingestSession(created);
                await loadSessions();
                selectSession(created.id);
                activeTab = "sessions";
                ToastUtils.success(t("rnsh.session_created"));
            }
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnsh.failed_to_create_session"));
        }
    }

    async function createListenSession(): Promise<void> {
        const payload = buildRnshListenPayload(listenForm);
        try {
            const created = await createRnshSession(payload);
            if (created?.id) {
                outputsBySession[created.id] = "";
                outputsBySession = { ...outputsBySession };
                ingestSession(created);
                await loadSessions();
                selectSession(created.id);
                activeTab = "sessions";
                ToastUtils.success(t("rnsh.session_created"));
            }
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnsh.failed_to_create_session"));
        }
    }

    async function startSelected(): Promise<void> {
        if (!selectedSession) return;
        try {
            await startRnshSession(selectedSession.id);
            ToastUtils.success(t("rnsh.session_started"));
            await loadSessions();
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnsh.failed_to_start_session"));
        }
    }

    async function stopSelected(): Promise<void> {
        if (!selectedSession) return;
        try {
            await stopRnshSession(selectedSession.id);
            ToastUtils.success(t("rnsh.session_stopped"));
            await loadSessions();
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnsh.failed_to_stop_session"));
        }
    }

    async function removeSelected(): Promise<void> {
        if (!selectedSession) return;
        const sessionId = selectedSession.id;
        try {
            await removeRnshSession(sessionId);
            delete outputsBySession[sessionId];
            outputsBySession = { ...outputsBySession };
            ToastUtils.success(t("rnsh.session_removed"));
            await loadSessions();
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnsh.failed_to_remove_session"));
        }
    }

    async function clearSelectedOutput(): Promise<void> {
        if (!selectedSession) return;
        try {
            const session = await clearRnshSessionOutput(selectedSession.id);
            if (session?.id) {
                outputsBySession[session.id] = "";
                outputsBySession = { ...outputsBySession };
            }
            ToastUtils.success(t("rnsh.output_cleared"));
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnsh.failed_to_clear_output"));
        }
    }

    async function copyListenAddress(): Promise<void> {
        const address = selectedListenAddress;
        if (!address) return;
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(address);
            }
            ToastUtils.success(t("rnsh.address_copied"));
        } catch {
            ToastUtils.error(t("rnsh.failed_to_copy_address"));
        }
    }

    async function sendCommand(): Promise<void> {
        if (!selectedSession || !commandInput.trim()) return;
        const text = commandInput;
        commandInput = "";
        try {
            await sendRnshSessionInput(selectedSession.id, text);
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnsh.failed_to_send_input"));
        }
    }

    function appendOutput(sessionId: string, text: string): void {
        appendSessionOutput(sessionId, text, outputsBySession);
        outputsBySession = { ...outputsBySession };
        if (sessionId === selectedSessionId) {
            void tick().then(() => {
                scrollOutputToBottom();
            });
        }
    }

    function onSessionChange(): void {
        void loadSessions();
    }

    function onOutputEvent(payload: any): void {
        appendOutput(payload?.session_id, payload?.chunk?.text);
    }

    function onIdentitySwitched(): void {
        sessions = [];
        outputsBySession = {};
        selectedSessionId = null;
        sessionFullscreen = false;
        void loadSessions();
    }

    function onWebsocketReconnected(): void {
        void loadSessions();
    }

    $effect(() => {
        if (typeof document === "undefined") {
            return;
        }
        document.body.style.overflow = sessionFullscreen ? "hidden" : "";
        if (sessionFullscreen) {
            void tick().then(() => {
                scrollOutputToBottom();
            });
        }
        return () => {
            document.body.style.overflow = "";
        };
    });

    onMount(() => {
        updateViewport();
        const handleResize = () => updateViewport();
        window.addEventListener("resize", handleResize, { passive: true });

        const handleFullscreenKeydown = (event: KeyboardEvent) => {
            if (event.key === "Escape" && sessionFullscreen) {
                sessionFullscreen = false;
            }
        };
        window.addEventListener("keydown", handleFullscreenKeydown);

        restoreLayout();
        void loadSessions();

        onWsEvent("rnsh.session.change", onSessionChange);
        onWsEvent("rnsh.output", onOutputEvent);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);

        return () => {
            window.removeEventListener("resize", handleResize);
            window.removeEventListener("keydown", handleFullscreenKeydown);
            document.body.style.overflow = "";
            offWsEvent("rnsh.session.change", onSessionChange);
            offWsEvent("rnsh.output", onOutputEvent);
            GlobalEmitter.off("identity-switched", onIdentitySwitched);
            GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    {#if !sessionFullscreen}
        <ToolsPageHeader
            icon="console-network-outline"
            title={t("rnsh.title")}
            description={headerDescription}
            eyebrow={t("rnsh.remote_shell")}
            accent="indigo"
        />
        <div
            class="flex items-stretch h-9 shrink-0 border-b border-sem-border bg-sem-surface-muted overflow-x-auto"
            role="tablist"
        >
            {#each RNSH_VIEW_TABS as tab (tab.id)}
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    class="inline-flex items-center gap-1 px-2.5 sm:px-4 border-r border-sem-border text-xs sm:text-sm transition-colors shrink-0 {activeTab ===
                    tab.id
                        ? 'bg-sem-surface text-gray-900 dark:text-gray-100 font-medium'
                        : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                    onclick={() => (activeTab = tab.id as RnshTabId)}
                >
                    <MaterialDesignIcon iconName={tab.icon} class="size-4 shrink-0 opacity-70" />
                    <span class="lg:hidden">{t(tab.shortLabel || tab.label)}</span>
                    <span class="hidden lg:inline">{t(tab.label)}</span>
                </button>
            {/each}
        </div>

        <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
            {#if activeTab === "sessions"}
                <div class="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden">
                    <aside
                        class="flex flex-col min-h-0 shrink-0 border-sem-border px-2 sm:px-3 md:px-4 py-2 sm:py-3 gap-2 sm:gap-3 {sessionsAsideClass}"
                    >
                        <RNSHSessionsList
                            {sessions}
                            {selectedSessionId}
                            onselect={selectSession}
                            onrefresh={loadSessions}
                        />
                    </aside>

                    <section class="flex-1 min-w-0 min-h-0 flex flex-col {terminalSectionClass}">
                        <RemoteShellTerminal
                            bind:this={sessionTerminal}
                            session={selectedSession}
                            output={selectedOutput}
                            {commandInput}
                            listenAddress={selectedListenAddress}
                            showSessionsToggle={isNarrowScreen}
                            sessionsOpen={mobileSessionsOpen}
                            compactHeader={isNarrowScreen}
                            i18nPrefix="rnsh"
                            onupdateCommandInput={(val) => (commandInput = val)}
                            onsend={sendCommand}
                            onstart={startSelected}
                            onstop={stopSelected}
                            onclear={clearSelectedOutput}
                            onremove={removeSelected}
                            oncopyAddress={copyListenAddress}
                            ontoggleFullscreen={toggleSessionFullscreen}
                            ontoggleSessions={toggleMobileSessions}
                        />
                    </section>
                </div>
            {:else if activeTab === "connect"}
                <RNSHConnectTab bind:form={connectForm} onsubmit={createConnectSession} />
            {:else if activeTab === "listen"}
                <RNSHListenTab bind:form={listenForm} onsubmit={createListenSession} />
            {/if}
        </div>
    {/if}

    {#if sessionFullscreen}
        <RemoteShellFullscreenDialog
            bind:this={fullscreenTerminal}
            session={selectedSession}
            output={selectedOutput}
            {commandInput}
            listenAddress={selectedListenAddress}
            showSessionsToggle={isNarrowScreen}
            sessionsOpen={mobileSessionsOpen}
            i18nPrefix="rnsh"
            onupdateCommandInput={(val) => (commandInput = val)}
            onsend={sendCommand}
            onstart={startSelected}
            onstop={stopSelected}
            onclear={clearSelectedOutput}
            onremove={removeSelected}
            oncopyAddress={copyListenAddress}
            ontoggleFullscreen={toggleSessionFullscreen}
            ontoggleSessions={toggleMobileSessions}
        />
    {/if}
</div>
