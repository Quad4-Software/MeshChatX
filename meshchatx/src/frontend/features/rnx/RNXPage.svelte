<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { onMount, tick } from "svelte";
    import { fade } from "svelte/transition";
    import MaterialDesignIcon from "../../ui/svelte/MaterialDesignIcon.svelte";
    import ToolsPageHeader from "../../ui/svelte/ToolsPageHeader.svelte";
    import ToastUtils from "../../js/ToastUtils.js";
    import GlobalEmitter from "../../js/GlobalEmitter.js";
    import { t } from "../../js/i18n.js";
    import { loadRnxLayout, saveRnxLayout } from "../../js/browserLayoutStore.js";
    import { onWsEvent, offWsEvent } from "../../js/registries/wsEventRegistry.js";
    import RemoteShellTerminal from "../remote-shell/components/RemoteShellTerminal.svelte";
    import RemoteShellFullscreenDialog from "../remote-shell/components/RemoteShellFullscreenDialog.svelte";
    import { NARROW_BREAKPOINT_PX } from "../remote-shell/lib/constants.js";
    import {
        appendSessionOutput,
        formatTerminalOutput,
        ingestSessionOutput,
    } from "../remote-shell/lib/sessionOutput.js";
    import RNXSessionsList from "./components/RNXSessionsList.svelte";
    import RNXExecuteTab from "./components/RNXExecuteTab.svelte";
    import RNXListenTab from "./components/RNXListenTab.svelte";
    import { DEFAULT_RNX_EXECUTE_FORM, DEFAULT_RNX_LISTEN_FORM, RNX_VIEW_TABS } from "./lib/constants.js";
    import {
        buildRnxExecutePayload,
        buildRnxListenPayload,
        clearRnxSessionOutput,
        createRnxSession,
        fetchRnxSessions,
        removeRnxSession,
        sendRnxSessionInput,
        startRnxSession,
        stopRnxSession,
    } from "./lib/rnxApi.js";
    import type { RnxExecuteForm, RnxListenForm, RnxSession, RnxTabId } from "./lib/types.js";

    let activeTab = $state<RnxTabId>("sessions");
    let sessions = $state<RnxSession[]>([]);
    let outputsBySession = $state<Record<string, string>>({});
    let selectedSessionId = $state<string | null>(null);
    let commandInput = $state("");
    let executeForm = $state<RnxExecuteForm>({ ...DEFAULT_RNX_EXECUTE_FORM });
    let listenForm = $state<RnxListenForm>({ ...DEFAULT_RNX_LISTEN_FORM });
    let isNarrowScreen = $state(false);
    let mobileSessionsOpen = $state(false);
    let sessionFullscreen = $state(false);

    let sessionTerminal = $state<ReturnType<typeof RemoteShellTerminal> | null>(null);
    let fullscreenTerminal = $state<ReturnType<typeof RemoteShellFullscreenDialog> | null>(null);

    function isReducedMotion(): boolean {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
            return false;
        }
        return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    const tabFadeMs = $derived(isReducedMotion() ? 0 : 120);

    const selectedSession = $derived(sessions.find((session) => session.id === selectedSessionId) || null);

    const selectedOutput = $derived(
        formatTerminalOutput(
            selectedSessionId,
            selectedSessionId ? outputsBySession[selectedSessionId] : undefined,
            t("rnx.select_or_create_session"),
            t("rnx.no_output_yet")
        )
    );

    const selectedListenAddress = $derived(
        selectedSession && selectedSession.mode === "listen" ? selectedSession.listen_address || "" : ""
    );

    const headerDescription = $derived(isNarrowScreen ? "" : t("rnx.description"));

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
        const state = loadRnxLayout();
        if (state && typeof state === "object") {
            selectedSessionId = state.selectedSessionId || null;
        }
    }

    function persistLayout(): void {
        saveRnxLayout({
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

    function ingestSession(session: RnxSession): void {
        ingestSessionOutput(session, outputsBySession);
        outputsBySession = { ...outputsBySession };
    }

    async function loadSessions(): Promise<void> {
        try {
            const fetched = await fetchRnxSessions();
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
            ToastUtils.error(error?.response?.data?.message || t("rnx.failed_to_load_sessions"));
        }
    }

    async function createExecuteSession(): Promise<void> {
        const payload = buildRnxExecutePayload(executeForm);
        if (!payload.destination) {
            ToastUtils.warning(t("rnx.destination_required"));
            return;
        }
        if (payload.mode !== "interactive" && !payload.remote_command) {
            ToastUtils.warning(t("rnx.command_required"));
            return;
        }
        try {
            const created = await createRnxSession(payload);
            if (created?.id) {
                outputsBySession[created.id] = "";
                outputsBySession = { ...outputsBySession };
                ingestSession(created);
                await loadSessions();
                selectSession(created.id);
                activeTab = "sessions";
                ToastUtils.success(t("rnx.session_created"));
            }
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnx.failed_to_create_session"));
        }
    }

    async function createListenSession(): Promise<void> {
        const payload = buildRnxListenPayload(listenForm);
        try {
            const created = await createRnxSession(payload);
            if (created?.id) {
                outputsBySession[created.id] = "";
                outputsBySession = { ...outputsBySession };
                ingestSession(created);
                await loadSessions();
                selectSession(created.id);
                activeTab = "sessions";
                ToastUtils.success(t("rnx.session_created"));
            }
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnx.failed_to_create_session"));
        }
    }

    async function startSelected(): Promise<void> {
        if (!selectedSession) return;
        try {
            await startRnxSession(selectedSession.id);
            ToastUtils.success(t("rnx.session_started"));
            await loadSessions();
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnx.failed_to_start_session"));
        }
    }

    async function stopSelected(): Promise<void> {
        if (!selectedSession) return;
        try {
            await stopRnxSession(selectedSession.id);
            ToastUtils.success(t("rnx.session_stopped"));
            await loadSessions();
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnx.failed_to_stop_session"));
        }
    }

    async function removeSelected(): Promise<void> {
        if (!selectedSession) return;
        const sessionId = selectedSession.id;
        try {
            await removeRnxSession(sessionId);
            delete outputsBySession[sessionId];
            outputsBySession = { ...outputsBySession };
            ToastUtils.success(t("rnx.session_removed"));
            await loadSessions();
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnx.failed_to_remove_session"));
        }
    }

    async function clearSelectedOutput(): Promise<void> {
        if (!selectedSession) return;
        try {
            const session = await clearRnxSessionOutput(selectedSession.id);
            if (session?.id) {
                outputsBySession[session.id] = "";
                outputsBySession = { ...outputsBySession };
            }
            ToastUtils.success(t("rnx.output_cleared"));
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnx.failed_to_clear_output"));
        }
    }

    async function copyListenAddress(): Promise<void> {
        const address = selectedListenAddress;
        if (!address) return;
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(address);
            }
            ToastUtils.success(t("rnx.address_copied"));
        } catch {
            ToastUtils.error(t("rnx.failed_to_copy_address"));
        }
    }

    async function sendCommand(): Promise<void> {
        if (!selectedSession || !commandInput.trim()) return;
        const text = commandInput;
        commandInput = "";
        try {
            await sendRnxSessionInput(selectedSession.id, text);
        } catch (error: any) {
            ToastUtils.error(error?.response?.data?.message || t("rnx.failed_to_send_input"));
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

        onWsEvent("rnx.session.change", onSessionChange);
        onWsEvent("rnx.output", onOutputEvent);
        GlobalEmitter.on("identity-switched", onIdentitySwitched);
        GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected);

        return () => {
            window.removeEventListener("resize", handleResize);
            window.removeEventListener("keydown", handleFullscreenKeydown);
            document.body.style.overflow = "";
            offWsEvent("rnx.session.change", onSessionChange);
            offWsEvent("rnx.output", onOutputEvent);
            GlobalEmitter.off("identity-switched", onIdentitySwitched);
            GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected);
        };
    });
</script>

<div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-sem-canvas">
    {#if !sessionFullscreen}
        <ToolsPageHeader
            icon="console"
            title={t("rnx.title")}
            description={headerDescription}
            eyebrow={t("rnx.remote_exec")}
            accent="teal"
        />
        <div
            class="flex items-stretch h-9 shrink-0 border-b border-sem-border bg-sem-surface-muted overflow-x-auto"
            role="tablist"
        >
            {#each RNX_VIEW_TABS as tab (tab.id)}
                <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    class="inline-flex items-center gap-1 px-2.5 sm:px-4 border-r border-sem-border text-xs sm:text-sm transition-colors shrink-0 {activeTab ===
                    tab.id
                        ? 'bg-sem-surface text-gray-900 dark:text-gray-100 font-medium'
                        : 'text-sem-fg-muted hover:bg-sem-surface-muted'}"
                    onclick={() => (activeTab = tab.id as RnxTabId)}
                >
                    <MaterialDesignIcon iconName={tab.icon} class="size-4 shrink-0 opacity-70" />
                    <span class="lg:hidden">{t(tab.shortLabel || tab.label)}</span>
                    <span class="hidden lg:inline">{t(tab.label)}</span>
                </button>
            {/each}
        </div>

        <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
            {#if activeTab === "sessions"}
                <div class="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden" in:fade={{ duration: tabFadeMs }}>
                    <aside
                        class="flex flex-col min-h-0 shrink-0 border-sem-border px-2 sm:px-3 md:px-4 py-2 sm:py-3 gap-2 sm:gap-3 {sessionsAsideClass}"
                    >
                        <RNXSessionsList
                            {sessions}
                            {selectedSessionId}
                            onselect={selectSession}
                            onrefresh={() => void loadSessions()}
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
                            i18nPrefix="rnx"
                            onupdateCommandInput={(val) => (commandInput = val)}
                            onsend={() => void sendCommand()}
                            onstart={() => void startSelected()}
                            onstop={() => void stopSelected()}
                            onclear={() => void clearSelectedOutput()}
                            onremove={() => void removeSelected()}
                            oncopyAddress={() => void copyListenAddress()}
                            ontoggleFullscreen={toggleSessionFullscreen}
                            ontoggleSessions={toggleMobileSessions}
                        />
                    </section>
                </div>
            {:else if activeTab === "execute"}
                <div class="flex-1 flex flex-col min-h-0 overflow-hidden" in:fade={{ duration: tabFadeMs }}>
                    <RNXExecuteTab bind:form={executeForm} onsubmit={createExecuteSession} />
                </div>
            {:else if activeTab === "listen"}
                <div class="flex-1 flex flex-col min-h-0 overflow-hidden" in:fade={{ duration: tabFadeMs }}>
                    <RNXListenTab bind:form={listenForm} onsubmit={createListenSession} />
                </div>
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
            i18nPrefix="rnx"
            onupdateCommandInput={(val) => (commandInput = val)}
            onsend={() => void sendCommand()}
            onstart={() => void startSelected()}
            onstop={() => void stopSelected()}
            onclear={() => void clearSelectedOutput()}
            onremove={() => void removeSelected()}
            oncopyAddress={() => void copyListenAddress()}
            ontoggleFullscreen={toggleSessionFullscreen}
            ontoggleSessions={toggleMobileSessions}
        />
    {/if}
</div>
