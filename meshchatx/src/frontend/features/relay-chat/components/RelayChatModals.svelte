<!-- SPDX-License-Identifier: 0BSD -->

<script lang="ts">
    import { tick } from "svelte";
    import MaterialDesignIcon from "../../../ui/svelte/MaterialDesignIcon.svelte";
    import Toggle from "../../../ui/svelte/Toggle.svelte";
    import RelayAddHubModal from "./RelayAddHubModal.svelte";
    import RelayHubSettingsModal from "./RelayHubSettingsModal.svelte";
    import { t } from "../../../js/i18n.js";
    import { RELAY_HOST_MODAL_OVERLAY, RELAY_HOST_MODAL_PANEL_COMPACT } from "../../../js/relayHostModalClasses.js";
    import {
        ANNOUNCE_SLIDER_POS_MAX,
        announceMinutesToSliderPos,
        announceSliderPosToMinutes,
        formatAnnounceIntervalMinutes,
        parseAnnounceIntervalMinutes,
    } from "../../../js/announceIntervalSliderMap.js";
    import { clampFloatingToViewport } from "../../../js/clampFloatingToViewport.js";
    import { computeCaret, type ContextMenuCaret } from "../../../js/contextMenuCaret.js";
    import {
        ANNOUNCE_INTERVAL_MAX_MINUTES,
        ANNOUNCE_INTERVAL_MIN_MINUTES,
        BTN_PRIMARY,
        BTN_SECONDARY,
        DEFAULT_ANNOUNCE_INTERVAL_SECONDS,
    } from "../lib/constants.js";
    import { isHubConnected } from "../lib/relayFormatters.js";
    import type { RrcHostedHub, RrcHub, RrcIgnoredPeer, RrcMessage } from "../lib/types.js";

    interface SidebarMenuState {
        show: boolean;
        x: number;
        y: number;
        hub: RrcHub | null;
        room: string | null;
    }

    interface MessageMenuState {
        show: boolean;
        x: number;
        y: number;
        msg: RrcMessage | null;
    }

    interface Props {
        showAddHub?: boolean;
        showCreateHub?: boolean;
        showHostHubSettings?: boolean;
        showHubSettings?: boolean;
        showChatPrefs?: boolean;
        sidebarMenu?: SidebarMenuState;
        messageMenu?: MessageMenuState;
        settingsHub?: RrcHub | null;
        hostSettingsHub?: RrcHostedHub | null;
        canModerateSelectedHub?: boolean;
        hideJoinPart?: boolean;
        highlightWords?: string[];
        ignoredPeers?: RrcIgnoredPeer[];
        applyingOptionsToAllHubs?: boolean;
        canQuoteMessage?: (msg: RrcMessage | null | undefined) => boolean;
        canMentionMessageAuthor?: (msg: RrcMessage | null | undefined) => boolean;
        canIgnoreMessageAuthor?: (msg: RrcMessage | null | undefined) => boolean;
        isIgnoredAuthor?: (msg: RrcMessage | null | undefined) => boolean;
        canTranslateRelayMessage?: (msg: RrcMessage | null | undefined) => boolean;
        oncloseaddhub?: () => void;
        onsubmitaddhub?: (payload: { hub_hash: string; name?: string; dest_name?: string }) => void;
        onclosecreatehub?: () => void;
        onsubmitcreatehub?: (payload: {
            name: string;
            greeting: string;
            announce: boolean;
            announce_interval_seconds: number;
        }) => void;
        onclosehosthubsettings?: () => void;
        onsubmithosthubsettings?: (payload: {
            name: string;
            announce: boolean;
            announce_interval_seconds: number;
        }) => void;
        onclosehubsettings?: () => void;
        onsubmithubsettings?: (payload: Record<string, unknown>) => void;
        onapplyoptionsall?: (options: { auto_reconnect: boolean; auto_list: boolean; auto_who: boolean }) => void;
        onclosechatprefs?: () => void;
        onsethidejoinpart?: (value: boolean) => void;
        onaddhighlightword?: (word: string) => boolean | void;
        onremovehighlightword?: (word: string) => void;
        onremoveignoredpeer?: (peer: RrcIgnoredPeer) => void;
        onclosesidebarmenu?: () => void;
        onclosemessagemenu?: () => void;
        onopenaddhubmenu?: () => void;
        onaddroommenu?: () => void;
        onconnecthubmenu?: () => void;
        ondisconnecthubmenu?: () => void;
        onopensettingsmenu?: () => void;
        oncopyhubaddressmenu?: () => void;
        onsharehubmenu?: () => void;
        onleaveroommenu?: () => void;
        onremovehubmenu?: () => void;
        onreplyquote?: () => void;
        onmentionuser?: () => void;
        oncopymessage?: () => void;
        ontoggleignore?: () => void;
        ontranslatemessage?: () => void;
        onkickuser?: () => void;
        onbanuser?: () => void;
    }

    let {
        showAddHub = false,
        showCreateHub = false,
        showHostHubSettings = false,
        showHubSettings = false,
        showChatPrefs = false,
        sidebarMenu = { show: false, x: 0, y: 0, hub: null, room: null },
        messageMenu = { show: false, x: 0, y: 0, msg: null },
        settingsHub = null,
        hostSettingsHub = null,
        canModerateSelectedHub = false,
        hideJoinPart = false,
        highlightWords = [],
        ignoredPeers = [],
        applyingOptionsToAllHubs = false,
        canQuoteMessage = () => false,
        canMentionMessageAuthor = () => false,
        canIgnoreMessageAuthor = () => false,
        isIgnoredAuthor = () => false,
        canTranslateRelayMessage = () => false,
        oncloseaddhub,
        onsubmitaddhub,
        onclosecreatehub,
        onsubmitcreatehub,
        onclosehosthubsettings,
        onsubmithosthubsettings,
        onclosehubsettings,
        onsubmithubsettings,
        onapplyoptionsall,
        onclosechatprefs,
        onsethidejoinpart,
        onaddhighlightword,
        onremovehighlightword,
        onremoveignoredpeer,
        onclosesidebarmenu,
        onclosemessagemenu,
        onopenaddhubmenu,
        onaddroommenu,
        onconnecthubmenu,
        ondisconnecthubmenu,
        onopensettingsmenu,
        oncopyhubaddressmenu,
        onsharehubmenu,
        onleaveroommenu,
        onremovehubmenu,
        onreplyquote,
        onmentionuser,
        oncopymessage,
        ontoggleignore,
        ontranslatemessage,
        onkickuser,
        onbanuser,
    }: Props = $props();

    // --- create hub form --------------------------------------------------------

    let createName = $state("");
    let createGreeting = $state("");
    let createAnnounce = $state(true);
    let createIntervalSeconds = $state(DEFAULT_ANNOUNCE_INTERVAL_SECONDS);
    let createIntervalDraft = $state<string | null>(null);

    function resolveIntervalSeconds(seconds: unknown): number {
        const raw = Number(seconds);
        if (!Number.isFinite(raw) || raw <= 0) {
            return DEFAULT_ANNOUNCE_INTERVAL_SECONDS;
        }
        return Math.round(raw);
    }

    function clampIntervalMinutes(value: number | null | undefined): number {
        const raw = Number(value);
        const minutes = Number.isFinite(raw) ? Math.round(raw as number) : ANNOUNCE_INTERVAL_MIN_MINUTES;
        return Math.max(ANNOUNCE_INTERVAL_MIN_MINUTES, Math.min(ANNOUNCE_INTERVAL_MAX_MINUTES, minutes));
    }

    const createIntervalMinutes = $derived(Math.round(resolveIntervalSeconds(createIntervalSeconds) / 60));
    const createIntervalSliderPos = $derived(announceMinutesToSliderPos(createIntervalMinutes));
    const createIntervalShown = $derived(createIntervalDraft ?? formatAnnounceIntervalMinutes(createIntervalMinutes));
    const createIntervalLabel = $derived(formatAnnounceIntervalMinutes(createIntervalMinutes));

    function onCreateIntervalSlider(event: Event) {
        const minutes = announceSliderPosToMinutes(Number((event?.target as HTMLInputElement | null)?.value));
        createIntervalSeconds = minutes * 60;
        createIntervalDraft = null;
    }

    function onCreateIntervalFocus() {
        createIntervalDraft = formatAnnounceIntervalMinutes(createIntervalMinutes);
    }

    function onCreateIntervalInput(event: Event) {
        const raw = String((event?.target as HTMLInputElement | null)?.value ?? "");
        createIntervalDraft = raw;
        if (raw.trim() === "") {
            return;
        }
        const minutes = parseAnnounceIntervalMinutes(raw);
        if (minutes != null) {
            createIntervalSeconds = clampIntervalMinutes(minutes) * 60;
        }
    }

    function onCreateIntervalBlur() {
        const parsed = parseAnnounceIntervalMinutes(createIntervalDraft);
        createIntervalSeconds = clampIntervalMinutes(parsed ?? createIntervalMinutes) * 60;
        createIntervalDraft = null;
    }

    function submitCreateHub() {
        onsubmitcreatehub?.({
            name: createName,
            greeting: createGreeting,
            announce: createAnnounce,
            announce_interval_seconds: createIntervalSeconds,
        });
        createName = "";
        createGreeting = "";
        createAnnounce = true;
        createIntervalSeconds = DEFAULT_ANNOUNCE_INTERVAL_SECONDS;
        createIntervalDraft = null;
    }

    // --- host hub settings form ---------------------------------------------------

    let hostName = $state("");
    let hostAnnounce = $state(true);
    let hostIntervalSeconds = $state(DEFAULT_ANNOUNCE_INTERVAL_SECONDS);
    let hostIntervalDraft = $state<string | null>(null);

    const hostIntervalMinutes = $derived(Math.round(resolveIntervalSeconds(hostIntervalSeconds) / 60));
    const hostIntervalSliderPos = $derived(announceMinutesToSliderPos(hostIntervalMinutes));
    const hostIntervalShown = $derived(hostIntervalDraft ?? formatAnnounceIntervalMinutes(hostIntervalMinutes));
    const hostIntervalLabel = $derived(formatAnnounceIntervalMinutes(hostIntervalMinutes));

    $effect(() => {
        if (showHostHubSettings && hostSettingsHub) {
            hostName = hostSettingsHub.name || "";
            hostAnnounce = hostSettingsHub.announce !== false;
            hostIntervalSeconds = resolveIntervalSeconds(hostSettingsHub.announce_interval_seconds);
            hostIntervalDraft = null;
        }
    });

    function onHostIntervalSlider(event: Event) {
        const minutes = announceSliderPosToMinutes(Number((event?.target as HTMLInputElement | null)?.value));
        hostIntervalSeconds = minutes * 60;
        hostIntervalDraft = null;
    }

    function onHostIntervalFocus() {
        hostIntervalDraft = formatAnnounceIntervalMinutes(hostIntervalMinutes);
    }

    function onHostIntervalInput(event: Event) {
        const raw = String((event?.target as HTMLInputElement | null)?.value ?? "");
        hostIntervalDraft = raw;
        if (raw.trim() === "") {
            return;
        }
        const minutes = parseAnnounceIntervalMinutes(raw);
        if (minutes != null) {
            hostIntervalSeconds = clampIntervalMinutes(minutes) * 60;
        }
    }

    function onHostIntervalBlur() {
        const parsed = parseAnnounceIntervalMinutes(hostIntervalDraft);
        hostIntervalSeconds = clampIntervalMinutes(parsed ?? hostIntervalMinutes) * 60;
        hostIntervalDraft = null;
    }

    function submitHostHubSettings() {
        onsubmithosthubsettings?.({
            name: hostName,
            announce: hostAnnounce,
            announce_interval_seconds: hostIntervalSeconds,
        });
    }

    // --- chat prefs ------------------------------------------------------------

    let highlightWordDraft = $state("");

    function addHighlightWord() {
        const word = highlightWordDraft.trim();
        if (!word) {
            return;
        }
        const added = onaddhighlightword?.(word);
        if (added !== false) {
            highlightWordDraft = "";
        }
    }

    // --- context menu positioning -------------------------------------------------

    let sidebarMenuPanel = $state<HTMLDivElement | null>(null);
    let messageMenuPanel = $state<HTMLDivElement | null>(null);
    let sidebarMenuPos = $state({ left: 0, top: 0, maxHeight: null as number | null });
    let messageMenuPos = $state({ left: 0, top: 0, maxHeight: null as number | null });
    let sidebarMenuCaret: ContextMenuCaret | null = $state(null);
    let messageMenuCaret: ContextMenuCaret | null = $state(null);

    async function updateMenuPositions() {
        await tick();
        if (sidebarMenu.show && sidebarMenuPanel) {
            const rect = sidebarMenuPanel.getBoundingClientRect();
            const result = clampFloatingToViewport(sidebarMenu.x, sidebarMenu.y, rect.width, rect.height);
            sidebarMenuPos = { left: result.left, top: result.top, maxHeight: result.maxHeight };
            sidebarMenuCaret = computeCaret(
                sidebarMenu.x,
                sidebarMenu.y,
                result.left,
                result.top,
                rect.width,
                rect.height
            );
        }
        if (messageMenu.show && messageMenuPanel) {
            const rect = messageMenuPanel.getBoundingClientRect();
            const result = clampFloatingToViewport(messageMenu.x, messageMenu.y, rect.width, rect.height);
            messageMenuPos = { left: result.left, top: result.top, maxHeight: result.maxHeight };
            messageMenuCaret = computeCaret(
                messageMenu.x,
                messageMenu.y,
                result.left,
                result.top,
                rect.width,
                rect.height
            );
        }
    }

    $effect(() => {
        if (sidebarMenu.show) {
            sidebarMenuPos = { left: sidebarMenu.x, top: sidebarMenu.y, maxHeight: null };
            sidebarMenuCaret = null;
        }
        if (messageMenu.show) {
            messageMenuPos = { left: messageMenu.x, top: messageMenu.y, maxHeight: null };
            messageMenuCaret = null;
        }
        void updateMenuPositions();
    });
</script>

<svelte:window
    onclick={() => {
        if (sidebarMenu.show) onclosesidebarmenu?.();
        if (messageMenu.show) onclosemessagemenu?.();
    }}
/>

<RelayAddHubModal show={showAddHub} onclose={oncloseaddhub} onsubmit={onsubmitaddhub} />

<RelayHubSettingsModal
    show={showHubSettings}
    hub={settingsHub}
    {applyingOptionsToAllHubs}
    onclose={onclosehubsettings}
    onsubmit={onsubmithubsettings}
    {onapplyoptionsall}
/>

{#if showCreateHub}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class={RELAY_HOST_MODAL_OVERLAY}
        onclick={(e) => {
            if (e.target === e.currentTarget) onclosecreatehub?.();
        }}
    >
        <div class={RELAY_HOST_MODAL_PANEL_COMPACT} onclick={(e) => e.stopPropagation()}>
            <h2 class="mb-4 text-lg font-semibold text-sem-fg">{t("relay_chat.create_hub_title")}</h2>
            <form
                class="space-y-4"
                onsubmit={(e) => {
                    e.preventDefault();
                    submitCreateHub();
                }}
            >
                <div class="space-y-1.5">
                    <label class="block text-sm font-semibold text-sem-fg-secondary" for="rrc-create-name">
                        {t("relay_chat.hub_name")}
                    </label>
                    <input
                        id="rrc-create-name"
                        bind:value={createName}
                        type="text"
                        placeholder={t("relay_chat.hub_name_placeholder")}
                        class="input-field"
                    />
                </div>
                <div class="space-y-1.5">
                    <label class="block text-sm font-semibold text-sem-fg-secondary" for="rrc-create-greeting">
                        {t("relay_chat.host_greeting")}
                    </label>
                    <input
                        id="rrc-create-greeting"
                        bind:value={createGreeting}
                        type="text"
                        placeholder={t("relay_chat.host_greeting_placeholder")}
                        class="input-field"
                    />
                </div>
                <label class="setting-toggle flex items-start gap-3 cursor-pointer">
                    <Toggle id="rrc-create-announce" bind:checked={createAnnounce} />
                    <span class="min-w-0 text-sm">
                        <span class="font-medium text-sem-fg">{t("relay_chat.host_announce_periodically")}</span>
                    </span>
                </label>
                {#if createAnnounce}
                    <div class="space-y-2">
                        <div class="flex items-center justify-between gap-2">
                            <label
                                for="rrc-create-announce-interval"
                                class="text-sm font-semibold text-sem-fg-secondary"
                            >
                                {t("relay_chat.host_announce_interval")}
                            </label>
                            <input
                                id="rrc-create-announce-interval-input"
                                type="text"
                                inputmode="text"
                                autocomplete="off"
                                maxlength="12"
                                class="w-20 shrink-0 rounded-lg border border-sem-border bg-sem-canvas px-1.5 py-1 text-center text-xs font-bold text-sem-accent tabular-nums shadow-xs focus:border-sem-accent focus:outline-hidden focus:ring-1 focus:ring-sem-accent/40"
                                value={createIntervalShown}
                                aria-label={t("relay_chat.host_announce_interval")}
                                onfocus={onCreateIntervalFocus}
                                oninput={onCreateIntervalInput}
                                onblur={onCreateIntervalBlur}
                            />
                        </div>
                        <input
                            id="rrc-create-announce-interval"
                            type="range"
                            min="0"
                            max={ANNOUNCE_SLIDER_POS_MAX}
                            step="1"
                            value={createIntervalSliderPos}
                            class="w-full h-2 rounded-lg appearance-none cursor-pointer bg-sem-surface-muted accent-sem-accent"
                            oninput={onCreateIntervalSlider}
                        />
                        <p class="text-xs text-sem-fg-muted">
                            {t("relay_chat.host_announce_interval_hint", { interval: createIntervalLabel })}
                        </p>
                    </div>
                {/if}
                <div class="flex justify-end gap-2 pt-1">
                    <button type="button" class={BTN_SECONDARY} onclick={() => onclosecreatehub?.()}>
                        {t("common.cancel")}
                    </button>
                    <button type="submit" class={BTN_PRIMARY}>{t("relay_chat.create_hub")}</button>
                </div>
            </form>
        </div>
    </div>
{/if}

{#if showHostHubSettings}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class={RELAY_HOST_MODAL_OVERLAY}
        onclick={(e) => {
            if (e.target === e.currentTarget) onclosehosthubsettings?.();
        }}
    >
        <div class={RELAY_HOST_MODAL_PANEL_COMPACT} onclick={(e) => e.stopPropagation()}>
            <h2 class="mb-4 text-lg font-semibold text-sem-fg">{t("relay_chat.host_hub_settings")}</h2>
            <form
                class="space-y-4"
                onsubmit={(e) => {
                    e.preventDefault();
                    submitHostHubSettings();
                }}
            >
                <div class="space-y-1.5">
                    <label class="block text-sm font-semibold text-sem-fg-secondary" for="rrc-host-name">
                        {t("relay_chat.hub_name")}
                    </label>
                    <input
                        id="rrc-host-name"
                        bind:value={hostName}
                        type="text"
                        placeholder={t("relay_chat.hub_name_placeholder")}
                        class="input-field"
                    />
                </div>
                <label class="setting-toggle flex items-start gap-3 cursor-pointer">
                    <Toggle id="rrc-host-announce" bind:checked={hostAnnounce} />
                    <span class="min-w-0 text-sm">
                        <span class="font-medium text-sem-fg">{t("relay_chat.host_announce_periodically")}</span>
                    </span>
                </label>
                {#if hostAnnounce}
                    <div class="space-y-2">
                        <div class="flex items-center justify-between gap-2">
                            <label for="rrc-host-announce-interval" class="text-sm font-semibold text-sem-fg-secondary">
                                {t("relay_chat.host_announce_interval")}
                            </label>
                            <input
                                id="rrc-host-announce-interval-input"
                                type="text"
                                inputmode="text"
                                autocomplete="off"
                                maxlength="12"
                                class="w-20 shrink-0 rounded-lg border border-sem-border bg-sem-canvas px-1.5 py-1 text-center text-xs font-bold text-sem-accent tabular-nums shadow-xs focus:border-sem-accent focus:outline-hidden focus:ring-1 focus:ring-sem-accent/40"
                                value={hostIntervalShown}
                                aria-label={t("relay_chat.host_announce_interval")}
                                onfocus={onHostIntervalFocus}
                                oninput={onHostIntervalInput}
                                onblur={onHostIntervalBlur}
                            />
                        </div>
                        <input
                            id="rrc-host-announce-interval"
                            type="range"
                            min="0"
                            max={ANNOUNCE_SLIDER_POS_MAX}
                            step="1"
                            value={hostIntervalSliderPos}
                            class="w-full h-2 rounded-lg appearance-none cursor-pointer bg-sem-surface-muted accent-sem-accent"
                            oninput={onHostIntervalSlider}
                        />
                        <p class="text-xs text-sem-fg-muted">
                            {t("relay_chat.host_announce_interval_hint", { interval: hostIntervalLabel })}
                        </p>
                    </div>
                {/if}
                <div class="flex justify-end gap-2 pt-1">
                    <button type="button" class={BTN_SECONDARY} onclick={() => onclosehosthubsettings?.()}>
                        {t("common.cancel")}
                    </button>
                    <button type="submit" class={BTN_PRIMARY}>{t("relay_chat.save")}</button>
                </div>
            </form>
        </div>
    </div>
{/if}

{#if showChatPrefs}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        onclick={(e) => {
            if (e.target === e.currentTarget) onclosechatprefs?.();
        }}
    >
        <div class="w-full max-w-md rounded-2xl border border-sem-border-card bg-sem-surface p-5 shadow-xl text-sem-fg">
            <h2 class="mb-4 text-lg font-semibold">{t("relay_chat.chat_prefs")}</h2>
            <div class="space-y-5">
                <label class="setting-toggle flex items-start gap-3 cursor-pointer">
                    <Toggle id="rrc-hide-join-part" checked={hideJoinPart} onchange={(v) => onsethidejoinpart?.(v)} />
                    <span class="min-w-0 text-sm">
                        <span class="font-medium text-sem-fg">{t("relay_chat.prefs_hide_join_part")}</span>
                        <span class="block text-xs text-sem-fg-muted">{t("relay_chat.prefs_hide_join_part_hint")}</span>
                    </span>
                </label>
                <div class="space-y-2">
                    <span class="block text-sm font-semibold text-sem-fg-secondary"
                        >{t("relay_chat.prefs_highlight_words")}</span
                    >
                    <p class="text-xs text-sem-fg-muted">{t("relay_chat.prefs_highlight_hint")}</p>
                    <div class="flex gap-2">
                        <input
                            bind:value={highlightWordDraft}
                            type="text"
                            placeholder={t("relay_chat.prefs_highlight_placeholder")}
                            class="input-field"
                            onkeydown={(e) => {
                                if (e.key === "Enter") {
                                    e.preventDefault();
                                    addHighlightWord();
                                }
                            }}
                        />
                        <button
                            type="button"
                            class="{BTN_SECONDARY} shrink-0"
                            disabled={!highlightWordDraft.trim()}
                            onclick={addHighlightWord}
                        >
                            {t("common.add")}
                        </button>
                    </div>
                    {#if highlightWords.length}
                        <div class="flex flex-wrap gap-1.5 pt-1">
                            {#each highlightWords as w (w)}
                                <span
                                    class="inline-flex items-center gap-1 rounded-full border border-sem-border bg-sem-canvas px-2.5 py-1 text-xs font-medium text-sem-fg"
                                >
                                    {w}
                                    <button
                                        type="button"
                                        class="text-sem-fg-muted hover:text-sem-danger cursor-pointer"
                                        title={t("common.delete")}
                                        onclick={() => onremovehighlightword?.(w)}
                                    >
                                        <MaterialDesignIcon iconName="close" class="size-3.5" />
                                    </button>
                                </span>
                            {/each}
                        </div>
                    {/if}
                </div>
                <div class="space-y-2">
                    <span class="block text-sm font-semibold text-sem-fg-secondary"
                        >{t("relay_chat.prefs_ignored")}</span
                    >
                    <p class="text-xs text-sem-fg-muted">{t("relay_chat.prefs_ignored_hint")}</p>
                    {#if ignoredPeers.length === 0}
                        <div
                            class="rounded-lg border border-dashed border-sem-border px-3 py-4 text-center text-xs text-sem-fg-muted"
                        >
                            {t("relay_chat.prefs_ignored_empty")}
                        </div>
                    {:else}
                        <ul class="max-h-48 space-y-1 overflow-y-auto custom-scrollbar pr-1">
                            {#each ignoredPeers as peer (peer.hash || peer.name)}
                                <li
                                    class="flex items-center gap-2 rounded-lg border border-sem-border bg-sem-canvas px-2.5 py-1.5"
                                >
                                    <span class="min-w-0 flex-1 truncate text-sm font-medium text-sem-fg">
                                        {peer.name || peer.hash}
                                    </span>
                                    <button
                                        type="button"
                                        class="shrink-0 rounded-md px-2 py-0.5 text-xs font-medium text-sem-accent hover:bg-sem-surface/60 cursor-pointer"
                                        onclick={() => onremoveignoredpeer?.(peer)}
                                    >
                                        {t("relay_chat.unignore")}
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
            </div>
            <div class="flex justify-end gap-2 pt-4">
                <button type="button" class={BTN_SECONDARY} onclick={() => onclosechatprefs?.()}>
                    {t("common.close")}
                </button>
            </div>
        </div>
    </div>
{/if}

{#if sidebarMenu.show}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        bind:this={sidebarMenuPanel}
        role="menu"
        tabindex="-1"
        class="context-menu-panel z-200"
        style="top: {sidebarMenuPos.top}px; left: {sidebarMenuPos.left}px; {sidebarMenuPos.maxHeight != null
            ? `max-height: ${sidebarMenuPos.maxHeight}px; overflow-y: auto;`
            : ''}"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
    >
        {#if !sidebarMenu.hub}
            <button type="button" class="context-item" role="menuitem" onclick={() => onopenaddhubmenu?.()}>
                {t("relay_chat.ctx_add_hub")}
            </button>
        {/if}
        {#if sidebarMenu.hub}
            {#if !sidebarMenu.room}
                <button type="button" class="context-item" role="menuitem" onclick={() => onaddroommenu?.()}>
                    {t("relay_chat.ctx_add_room")}
                </button>
                {#if !isHubConnected(sidebarMenu.hub)}
                    <button type="button" class="context-item" role="menuitem" onclick={() => onconnecthubmenu?.()}>
                        {t("relay_chat.ctx_connect_hub")}
                    </button>
                {/if}
                {#if isHubConnected(sidebarMenu.hub)}
                    <button type="button" class="context-item" role="menuitem" onclick={() => ondisconnecthubmenu?.()}>
                        {t("relay_chat.ctx_disconnect_hub")}
                    </button>
                {/if}
            {/if}
            <button type="button" class="context-item" role="menuitem" onclick={() => oncopyhubaddressmenu?.()}>
                {t("relay_chat.ctx_copy_hub_address")}
            </button>
            <button type="button" class="context-item" role="menuitem" onclick={() => onsharehubmenu?.()}>
                {sidebarMenu.room ? t("relay_chat.ctx_share_room") : t("relay_chat.ctx_share_hub")}
            </button>
            <button type="button" class="context-item" role="menuitem" onclick={() => onopensettingsmenu?.()}>
                {t("relay_chat.ctx_hub_settings")}
            </button>
            {#if sidebarMenu.room}
                <button type="button" class="context-item" role="menuitem" onclick={() => onleaveroommenu?.()}>
                    {t("relay_chat.ctx_leave_room")}
                </button>
            {/if}
            <div class="context-menu-divider" role="separator"></div>
            <button
                type="button"
                class="context-item text-sem-danger"
                role="menuitem"
                onclick={() => onremovehubmenu?.()}
            >
                {t("relay_chat.ctx_remove_hub")}
            </button>
        {/if}
    </div>
    {#if sidebarMenuCaret}
        <div
            class="dropdown-caret fixed z-200 border-sem-border {sidebarMenuCaret.borderClass}"
            style="left: {sidebarMenuCaret.style.left}; top: {sidebarMenuCaret.style.top};"
            aria-hidden="true"
        ></div>
    {/if}
{/if}

{#if messageMenu.show && messageMenu.msg}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        bind:this={messageMenuPanel}
        role="menu"
        tabindex="-1"
        class="context-menu-panel z-200"
        style="top: {messageMenuPos.top}px; left: {messageMenuPos.left}px; {messageMenuPos.maxHeight != null
            ? `max-height: ${messageMenuPos.maxHeight}px; overflow-y: auto;`
            : ''}"
        onclick={(e) => e.stopPropagation()}
        onkeydown={(e) => e.stopPropagation()}
    >
        {#if canQuoteMessage(messageMenu.msg)}
            <button type="button" class="context-item" role="menuitem" onclick={() => onreplyquote?.()}>
                {t("relay_chat.ctx_reply_quote")}
            </button>
        {/if}
        {#if canMentionMessageAuthor(messageMenu.msg)}
            <button type="button" class="context-item" role="menuitem" onclick={() => onmentionuser?.()}>
                {t("relay_chat.ctx_mention_user")}
            </button>
        {/if}
        {#if messageMenu.msg.text}
            <button type="button" class="context-item" role="menuitem" onclick={() => oncopymessage?.()}>
                {t("relay_chat.ctx_copy_message")}
            </button>
        {/if}
        {#if canIgnoreMessageAuthor(messageMenu.msg)}
            <button type="button" class="context-item" role="menuitem" onclick={() => ontoggleignore?.()}>
                {isIgnoredAuthor(messageMenu.msg) ? t("relay_chat.ctx_unignore_user") : t("relay_chat.ctx_ignore_user")}
            </button>
        {/if}
        {#if canTranslateRelayMessage(messageMenu.msg)}
            <button type="button" class="context-item" role="menuitem" onclick={() => ontranslatemessage?.()}>
                {t("relay_chat.ctx_translate_message")}
            </button>
        {/if}
        {#if canModerateSelectedHub}
            <div class="context-menu-divider" role="separator"></div>
            <button type="button" class="context-item text-sem-danger" role="menuitem" onclick={() => onkickuser?.()}>
                {t("relay_chat.ctx_kick_user")}
            </button>
            <button type="button" class="context-item text-sem-danger" role="menuitem" onclick={() => onbanuser?.()}>
                {t("relay_chat.ctx_ban_user")}
            </button>
        {/if}
    </div>
    {#if messageMenuCaret}
        <div
            class="dropdown-caret fixed z-200 border-sem-border {messageMenuCaret.borderClass}"
            style="left: {messageMenuCaret.style.left}; top: {messageMenuCaret.style.top};"
            aria-hidden="true"
        ></div>
    {/if}
{/if}
