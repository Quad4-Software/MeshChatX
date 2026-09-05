// SPDX-License-Identifier: 0BSD

/**
 * App shell state and lifecycle, ported from components/App.vue.
 * Holds live transport wiring, banner state, identity switch, sidebar layout,
 * telephony chrome, and propagation sync so App.svelte stays a thin template.
 * GlobalState is still a Vue reactive object, so its fields are mirrored into
 * runes state through a Vue watcher.
 */

import { watch } from "vue";
import QRCode from "qrcode";
import DialogUtils from "../../../js/DialogUtils.js";
import LiveTransport from "../../../js/liveTransport.js";
import { installWsLiveSync } from "../../../js/wsLiveSync.js";
import { formatDisconnectedDuration, WS_DISCONNECT_BANNER_GRACE_MS } from "../../../js/wsConnectionSupport.js";
import { applyAuthStatusToGlobalState, fetchAuthStatus } from "../../../js/authSessionSync.js";
import GlobalState, { mergeGlobalConfig } from "../../../js/GlobalState.js";
import { countRelayMentions } from "../../../js/relayMentionCount.js";
import { isRetryableHttpError } from "../../../js/httpRetry.js";
import Utils from "../../../js/Utils.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import NotificationUtils from "../../../js/NotificationUtils.js";
import NotificationSoundUtils from "../../../js/NotificationSoundUtils.js";
import { listOpenDestinationHashes, subscribeOpenDestinationHashes } from "../../../js/activeConversationStore.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    CLIENT_HEAP_SAMPLE_INTERVAL_MS,
    MEMORY_WARNING_TOAST_KEY,
    evaluateClientHeapSample,
    markMemoryWarningDismissed,
    showMemoryWarningToastIfNeeded,
} from "../../../js/healthMemoryWarning.js";
import {
    showDatabaseHealthIssuesToastIfNeeded,
    resetDatabaseHealthWarningState,
} from "../../../js/databaseHealthWarning.js";
import {
    channelBadgeClass,
    channelLabelKey,
    normalizeReleaseChannel,
    shouldShowChannelPrompt,
} from "../../../js/releaseChannel.js";
import { t } from "../../../js/i18n.js";
import ElectronUtils from "../../../js/ElectronUtils.js";
import {
    shouldShowLanBindNoAuthBanner,
    dismissLanBindNoAuthBanner,
    isLanBindNoAuthBannerDismissed,
} from "../../../js/lanBindWarning.js";
import { isMeshChatXAndroid } from "../../../js/webAudioMicPermission.js";
import { postRequestPath } from "../../../js/reticulumPathfinding.js";
import { fetchCsrfToken } from "../../../js/csrfToken.js";
import ToneGenerator from "../../../js/ToneGenerator.js";
import { listNavItems } from "../../../js/registries/navRegistry.js";
import { onWsEvent, offWsEvent } from "../../../js/registries/wsEventRegistry.js";
import { shouldShowMultiSessionToast } from "../../../js/activeSessions.js";
import { isDatabaseRecoveryError, recoveryLocationForNetworkError } from "../../../js/networkRecovery.js";
import fatalErrorState from "../../../js/fatalErrorState.js";
import type { FatalErrorRecord } from "../../../js/fatalErrorState.js";
import { loadFeatureSidebarCollapsed, saveFeatureSidebarCollapsed, clearMessagePanes } from "../../../js/browserLayoutStore.js";
import { micronStorage } from "../../../js/MicronStorage.js";
import {
    applyNavLayout,
    captureNavLayout,
    cloneNavLayout,
    loadAppSidebarNavLayout,
    moveNavGroup,
    moveNavGroupByOffset,
    moveNavItem,
    moveNavItemByOffset,
    orderItemsByLayout,
    saveAppSidebarNavLayout,
} from "../../../js/appSidebarNavLayout.js";
import type { NavLayout } from "../../../js/appSidebarNavLayout.js";
import {
    applyBackgroundPollInterval,
    BATTERY_SAVER_CHANGED_EVENT,
    loadBatterySaverPrefs,
} from "../../../js/settings/batterySaverPrefs.js";
import { normalizeUiLocaleCode, setLocale } from "../../../js/localeLoader.js";
import { patchServerConfig } from "../../../js/settings/settingsConfigService.js";
import {
    applyAppearanceTheme,
    resolveEffectiveTheme,
    shellCanvasBackgroundStyle,
    subscribeSystemTheme,
    systemPrefersDark,
} from "../../../theme/themeEngine.js";
import { navigate, router, subscribe as subscribeRoute } from "../../../shell/hashRouter.js";
import type { ActiveRoute } from "../../../shell/hashRouter.js";
import { handleProtocolLink } from "./appShellLinks.js";
import { createShellWsHandlers } from "./appShellWsHandlers.js";
import type { NavGroup, NavItem } from "./navTypes.js";

const IDENTITY_SAVE_DEBOUNCE_MS = 500;
const PROPAGATION_SYNC_TOAST_KEY = "propagation-sync-status";
const PROPAGATION_SYNC_POLL_TIMEOUT_MS = 120000;
const ACTIVE_SYNC_STATES = [
    "path_requested",
    "link_establishing",
    "link_established",
    "request_sent",
    "receiving",
    "response_received",
];

export interface ShellConfig {
    [key: string]: unknown;
}

export interface ShellAppInfo {
    version?: string;
    display_version?: string;
    is_dev_build?: boolean;
    git_commit?: string;
    git_commit_short?: string;
    build_channel?: string;
    emergency?: boolean;
    tutorial_seen?: boolean;
    changelog_seen_version?: string;
    database_health_issues?: unknown;
}

/** Modal and palette instances bound by App.svelte. */
export interface ShellHosts {
    changelog?: { show: () => void | Promise<void> } | null;
    tutorial?: { show: () => void; hide?: () => void; isOpen?: () => boolean } | null;
    channelPrompt?: { show: (info: unknown) => boolean } | null;
    androidStorage?: { showUpgrade: () => boolean } | null;
    postInstall?: { showNext: () => Promise<boolean> } | null;
    commandPalette?: { open: () => void | Promise<void> } | null;
}

type Timer = ReturnType<typeof setTimeout> | null;
type Interval = ReturnType<typeof setInterval> | null;

function apiClient() {
    return (window as unknown as { api: any }).api;
}

function electronBridge() {
    return (window as unknown as { electron?: Record<string, any> }).electron;
}

export class AppShellState {
    hosts: ShellHosts = {};

    /** Mirror of the Vue reactive GlobalState fields the shell reads. */
    global = $state({
        authSessionResolved: false,
        authEnabled: false,
        authenticated: false,
        isLoopbackBind: true,
        demoMode: false,
        networkDegraded: false,
        networkDegradedError: null as string | null,
        networkStarting: false,
        networkReady: true,
        unreadConversationsCount: 0,
        relayChatUnreadCount: 0,
        missedCallsCount: 0,
        activeCallTab: "phone" as string,
        rrcEnabled: true,
    });

    route = $state<ActiveRoute | null>(null);
    localeVersion = $state(0);
    fatalError = $state<FatalErrorRecord | null>(null);

    config = $state<ShellConfig | null>(null);
    appInfo = $state<ShellAppInfo | null>(null);
    displayName = $state("Anonymous Peer");

    isSidebarOpen = $state(false);
    isSidebarCollapsed = $state(false);
    isShowingMoreNav = $state(false);
    isSidebarNavEditing = $state(false);
    sidebarNavLayoutSaved = $state<NavLayout | null>(null);
    sidebarNavLayoutDraft = $state<NavLayout | null>(null);

    isSwitchingIdentity = $state(false);
    shellRunning = $state(false);
    liveTransportReady = $state(false);
    lastAnnouncedTick = $state(0);

    hasCheckedForModals = false;
    skipChangelogAfterTutorial = false;
    lanBindNoAuthBannerDismissed = $state(isLanBindNoAuthBannerDismissed());

    showLxmfQr = $state(false);
    lxmfQrDataUrl = $state<string | null>(null);

    activeCall = $state<any>(null);
    lastCall = $state<any>(null);
    voicemailStatus = $state<any>(null);
    propagationNodeStatus = $state<any>(null);
    isCallEnded = $state(false);
    wasDeclined = $state(false);
    initiationStatus = $state<string | null>(null);
    initiationTargetHash = $state<string | null>(null);
    initiationTargetName = $state<string | null>(null);
    isCallWindowOpen = false;
    isFetchingRingtone = false;
    ringtonePlayer: HTMLAudioElement | null = null;
    ringtoneAutoplayBlocked = false;
    toneGenerator = new ToneGenerator();
    endedTimeout: Timer = null;

    wsDisconnected = $state(false);
    wsDisconnectedDurationText = $state("");
    wsReconnectedBanner = $state(false);
    backendProcessExited = $state(false);
    backendExitCode = $state<string | number | null>(null);
    backendRestarting = $state(false);
    networkRecovering = $state(false);
    databaseAutoRecovering = $state(false);
    userInitiatedPropagationSync = $state(false);
    systemPrefersDark = $state(systemPrefersDark());

    private wsDisconnectedAt: number | null = null;
    private wsDisconnectBannerShown = false;
    private wsDisconnectTickTimer: Interval = null;
    private wsDisconnectGraceTimer: Timer = null;
    private wsReconnectedHideTimer: Timer = null;

    private reloadInterval: Interval = null;
    private appInfoInterval: Interval = null;
    private unreadCountInterval: Interval = null;
    private clientHeapMemoryTimer: Interval = null;
    private propagationSyncPollTimer: Interval = null;
    private isPropagationSyncPolling = false;
    private unreadCountTimeout: Timer = null;
    private relayUnreadCountTimeout: Timer = null;
    private identitySaveTimer: Timer = null;

    private wsLiveSyncHandle: { dispose: () => void; clearCursor: () => void } | null = null;
    private shellWsHandlerCleanups: Array<() => void> = [];
    private identitySwitchDedupeHash: string | null = null;
    private identitySwitchDedupeAt = 0;
    private multiSessionWarningActive = false;
    private pendingConfigSet: { requestId: string; resolve: (value: boolean) => void } | null = null;
    private meshWaitStarted = false;

    private disposers: Array<() => void> = [];
    private boundIntentUri = (event: Event) => this.onAndroidIntentUri(event as CustomEvent);
    private boundRingtoneUnlock = () => this.onRingtoneUnlockGesture();

    // ------------------------------------------------------------------
    // Derived shell chrome
    // ------------------------------------------------------------------

    readonly routeName = $derived(this.route?.name ?? "");
    readonly isAuthRoute = $derived(this.routeName === "auth");

    readonly showMainShell = $derived.by(() => {
        if (!this.global.authSessionResolved) {
            return false;
        }
        if (this.isAuthRoute) {
            return false;
        }
        if (!this.global.authEnabled) {
            return true;
        }
        return this.global.authenticated;
    });

    readonly currentPopoutType = $derived.by(() => {
        const meta = this.route?.meta as { popoutType?: unknown } | undefined;
        if (meta?.popoutType) {
            return meta.popoutType;
        }
        return this.route?.query?.popout ?? getHashPopoutValue();
    });

    readonly isPopoutMode = $derived(this.currentPopoutType != null);

    readonly sidebarDisplayVersion = $derived.by(() => {
        const info = this.appInfo || {};
        if (info.display_version) {
            return info.display_version;
        }
        const base = info.version || "";
        if (info.is_dev_build && base && !String(base).endsWith("-dev")) {
            return `${base}-dev`;
        }
        return base;
    });

    readonly sidebarVersionLabel = $derived.by(() => {
        void this.localeVersion;
        const version = this.sidebarDisplayVersion;
        if (!version) {
            return "";
        }
        const label = t("about.version", { version });
        const short =
            this.appInfo?.git_commit_short ||
            (this.appInfo?.git_commit ? String(this.appInfo.git_commit).slice(0, 7) : "");
        if (this.appInfo?.is_dev_build && short) {
            return `${label} ${short}`;
        }
        return label;
    });

    readonly sidebarChannel = $derived(normalizeReleaseChannel(this.appInfo?.build_channel));

    readonly sidebarChannelLabel = $derived.by(() => {
        void this.localeVersion;
        if (!this.appInfo?.version) {
            return "";
        }
        return t(channelLabelKey(this.sidebarChannel));
    });

    readonly sidebarChannelBadgeClass = $derived(channelBadgeClass(this.sidebarChannel));

    readonly sidebarVersionTitle = $derived.by(() => {
        const base = this.sidebarVersionLabel;
        const channel = this.sidebarChannelLabel;
        if (base && channel) {
            return `${base} (${channel})`;
        }
        return base;
    });

    readonly rrcEnabled = $derived(this.global.rrcEnabled);

    readonly rawVisibleNavItems = $derived.by(() =>
        (listNavItems() as NavItem[]).filter((item) => this.isNavItemVisible(item))
    );

    readonly activeNavLayout = $derived.by(() => {
        if (this.isSidebarNavEditing && this.sidebarNavLayoutDraft) {
            return this.sidebarNavLayoutDraft;
        }
        return this.sidebarNavLayoutSaved;
    });

    readonly useGroupedAppSidebar = $derived(this.config?.app_sidebar_layout !== "classic");

    readonly navLayoutView = $derived.by(() =>
        applyNavLayout(this.rawVisibleNavItems, this.activeNavLayout, {
            includeEmptyGroups: this.isSidebarNavEditing && this.useGroupedAppSidebar,
        })
    ) as { primaryGroups: NavGroup[]; moreItems: NavItem[] };

    readonly visibleNavItems = $derived.by(() => {
        if (!this.useGroupedAppSidebar) {
            return orderItemsByLayout(this.rawVisibleNavItems, this.activeNavLayout) as NavItem[];
        }
        const view = this.navLayoutView;
        return [...view.primaryGroups.flatMap((group) => group.items), ...view.moreItems];
    });

    readonly moreNavItems = $derived(this.navLayoutView.moreItems);
    readonly primaryNavGroups = $derived(this.navLayoutView.primaryGroups);

    readonly lastAnnouncedSidebarLabel = $derived.by(() => {
        if (!this.config?.last_announced_at) {
            return "";
        }
        void this.lastAnnouncedTick;
        return Utils.formatSecondsAgo(this.config.last_announced_at);
    });

    readonly identitySidebarLabel = $derived.by(() => {
        void this.localeVersion;
        const raw = this.displayName;
        const name = raw != null && String(raw).trim() !== "" ? String(raw).trim() : "";
        return name || t("app.my_identity");
    });

    readonly isSyncingPropagationNode = $derived.by(() => {
        // Only treat sync as "running" in the chrome when the user started it.
        // Background auto-sync must not keep the header spinner forever.
        if (!this.userInitiatedPropagationSync) {
            return false;
        }
        return ACTIVE_SYNC_STATES.includes(this.propagationNodeStatus?.state);
    });

    readonly inboundDeliveryCount = $derived.by(() => {
        const count = this.propagationNodeStatus?.inbound_delivery_count;
        return Number.isFinite(Number(count)) ? Math.max(0, Number(count)) : 0;
    });

    readonly effectiveThemeMode = $derived(resolveEffectiveTheme(this.config?.theme, this.systemPrefersDark));
    readonly isDarkTheme = $derived(this.effectiveThemeMode === "dark");

    readonly shellCanvasStyle = $derived.by(() => {
        if (!this.config) {
            return "";
        }
        const background = shellCanvasBackgroundStyle(this.config, this.effectiveThemeMode);
        return background ? `background-color: ${background};` : "";
    });

    readonly themeToggleIcon = $derived.by(() => {
        if (this.config?.theme === "system") {
            return "theme-light-dark";
        }
        return this.isDarkTheme ? "brightness-6" : "brightness-4";
    });

    readonly themeToggleTitle = $derived.by(() => {
        void this.localeVersion;
        if (this.config?.theme === "system") {
            return t("app.system_theme");
        }
        return this.isDarkTheme ? t("app.light_theme") : t("app.dark_theme");
    });

    // ------------------------------------------------------------------
    // Banner derivations
    // ------------------------------------------------------------------

    readonly showWsDisconnectedBanner = $derived(this.shellRunning && this.wsDisconnected && !this.isAuthRoute);

    readonly backendOfflineBannerLabel = $derived.by(() => {
        void this.localeVersion;
        const duration = this.wsDisconnectedDurationText;
        const durationSuffix = duration ? ` \u00b7 ${duration}` : "";
        if (this.backendProcessExited) {
            const code = this.backendExitCode != null && this.backendExitCode !== "" ? ` (${this.backendExitCode})` : "";
            return `${t("app.backend_process_stopped")}${code}${durationSuffix}`;
        }
        return `${t("app.backend_disconnected")}${durationSuffix}`;
    });

    readonly showBackendRecoveryActions = $derived.by(
        () =>
            this.showWsDisconnectedBanner &&
            this.backendProcessExited &&
            ElectronUtils.isElectron() &&
            typeof electronBridge()?.restartBackend === "function"
    );

    readonly showNetworkDegradedBanner = $derived(Boolean(this.global.networkDegraded) && !this.isAuthRoute);

    readonly showNetworkStartingBanner = $derived.by(
        () =>
            Boolean(this.global.networkStarting) &&
            !this.global.networkDegraded &&
            !this.global.networkReady &&
            !this.isAuthRoute
    );

    readonly showLanBindNoAuthBanner = $derived.by(() =>
        shouldShowLanBindNoAuthBanner({
            dismissed: this.lanBindNoAuthBannerDismissed,
            isElectron: ElectronUtils.isElectron(),
            isAndroid: isMeshChatXAndroid(),
            authEnabled: this.global.authEnabled,
            isLoopbackBind: this.global.isLoopbackBind,
            routeName: this.routeName,
        })
    );

    readonly networkDegradedBannerLabel = $derived.by(() => {
        void this.localeVersion;
        const detail = this.global.networkDegradedError;
        if (detail && String(detail).trim()) {
            return String(detail).trim();
        }
        return t("app.network_degraded");
    });

    readonly showDatabaseRecoveryActions = $derived(isDatabaseRecoveryError(this.global.networkDegradedError));

    readonly shouldShowCallOverlay = $derived.by(() => {
        const meta = (this.route?.meta || {}) as { isPopout?: boolean };
        return Boolean(
            (this.activeCall || this.isCallEnded || this.wasDeclined || this.initiationStatus) &&
                !meta.isPopout &&
                (!["call", "call-popout"].includes(this.routeName) || this.global.activeCallTab !== "phone") &&
                (!this.config?.desktop_open_calls_in_separate_window || !ElectronUtils.isElectron())
        );
    });

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------

    /**
     * Wire GlobalState mirroring, route tracking, and window listeners.
     * Call once from App.svelte onMount. Returns nothing, use destroy() to undo.
     */
    init(): void {
        this.disposers.push(
            watch(
                () => [
                    GlobalState.authSessionResolved,
                    GlobalState.authEnabled,
                    GlobalState.authenticated,
                    GlobalState.isLoopbackBind,
                    GlobalState.demoMode,
                    GlobalState.networkDegraded,
                    GlobalState.networkDegradedError,
                    GlobalState.networkStarting,
                    GlobalState.networkReady,
                    GlobalState.unreadConversationsCount,
                    GlobalState.relayChatUnreadCount,
                    GlobalState.missedCallsCount,
                    GlobalState.activeCallTab,
                    GlobalState.config?.rrc_enabled,
                ],
                () => this.syncGlobalMirror(),
                { immediate: true }
            )
        );

        this.disposers.push(
            watch(
                () => fatalErrorState.active,
                (next) => {
                    this.fatalError = next;
                },
                { immediate: true }
            )
        );

        this.disposers.push(
            subscribeRoute((route) => {
                const previous = this.route;
                this.route = route;
                if (previous && previous.name) {
                    this.isSidebarOpen = false;
                    if (this.hosts.tutorial?.isOpen?.()) {
                        this.hosts.tutorial.hide?.();
                    }
                }
                this.applyShellAuthState();
                this.maybeNavigateNetworkRecovery();
            })
        );

        try {
            const savedSidebarCollapsed = loadFeatureSidebarCollapsed("app");
            if (savedSidebarCollapsed !== null) {
                this.isSidebarCollapsed = savedSidebarCollapsed;
            }
            this.sidebarNavLayoutSaved = loadAppSidebarNavLayout();
            const detailed = localStorage.getItem("meshchatx_detailed_outbound_send_status");
            if (detailed === "true" || detailed === "false") {
                GlobalState.detailedOutboundSendStatus = detailed === "true";
            }
            const grouping = localStorage.getItem("meshchatx_message_timestamp_grouping_enabled");
            if (grouping === "true" || grouping === "false") {
                GlobalState.messageTimestampGroupingEnabled = grouping === "true";
            }
            const transfer = localStorage.getItem("meshchatx_outbound_transfer_progress_enabled");
            if (transfer === "true" || transfer === "false") {
                GlobalState.outboundTransferProgressEnabled = transfer === "true";
            }
        } catch {
            // ignore
        }

        this.disposers.push(
            watch(
                () => [GlobalState.networkDegraded, GlobalState.networkDegradedError],
                () => this.maybeNavigateNetworkRecovery()
            )
        );
        this.maybeNavigateNetworkRecovery();

        const unsubscribeTheme = subscribeSystemTheme(window, (prefersDark: boolean) => {
            this.systemPrefersDark = prefersDark;
            if (this.config?.theme === "system") {
                this.applyAppearanceThemeFromConfig(this.config);
            }
        });
        if (typeof unsubscribeTheme === "function") {
            this.disposers.push(unsubscribeTheme);
        }
        this.applyShellAppearance();

        if (ElectronUtils.isElectron()) {
            const electron = electronBridge();
            if (typeof electron?.onBackendProcessExited === "function") {
                electron.onBackendProcessExited((payload: { code?: string | number }) => {
                    this.onBackendProcessExited(payload);
                });
            }
            if (typeof electron?.onProtocolLink === "function") {
                electron.onProtocolLink((url: string) => {
                    handleProtocolLink(router, url);
                });
            }
        }

        window.addEventListener("meshchatx-intent-uri", this.boundIntentUri);
        window.addEventListener("pointerdown", this.boundRingtoneUnlock, true);
        window.addEventListener("keydown", this.boundRingtoneUnlock, true);

        const unsubscribeOpenConversations = subscribeOpenDestinationHashes((hashes: string[]) => {
            NotificationUtils.syncAndroidNotificationContext(hashes, Boolean(this.config?.do_not_disturb_enabled));
        });
        if (typeof unsubscribeOpenConversations === "function") {
            this.disposers.push(unsubscribeOpenConversations);
        }
        NotificationUtils.syncAndroidNotificationContext(
            listOpenDestinationHashes(),
            Boolean(this.config?.do_not_disturb_enabled)
        );

        this.applyShellAuthState();
    }

    destroy(): void {
        if (this.identitySaveTimer != null) {
            clearTimeout(this.identitySaveTimer);
            this.identitySaveTimer = null;
        }
        if (this.propagationSyncPollTimer != null) {
            clearInterval(this.propagationSyncPollTimer);
            this.propagationSyncPollTimer = null;
        }
        this.isPropagationSyncPolling = false;
        this.stopShell();
        this.clearWsShellUiTimers();
        if (this.endedTimeout) {
            clearTimeout(this.endedTimeout);
            this.endedTimeout = null;
        }
        this.stopRingtone();
        this.toneGenerator.stop();
        window.removeEventListener("meshchatx-intent-uri", this.boundIntentUri);
        window.removeEventListener("pointerdown", this.boundRingtoneUnlock, true);
        window.removeEventListener("keydown", this.boundRingtoneUnlock, true);
        for (const dispose of this.disposers) {
            try {
                dispose();
            } catch {
                // ignore
            }
        }
        this.disposers = [];
    }

    private syncGlobalMirror(): void {
        this.global.authSessionResolved = GlobalState.authSessionResolved;
        this.global.authEnabled = GlobalState.authEnabled;
        this.global.authenticated = GlobalState.authenticated;
        this.global.isLoopbackBind = GlobalState.isLoopbackBind;
        this.global.demoMode = GlobalState.demoMode;
        this.global.networkDegraded = GlobalState.networkDegraded;
        this.global.networkDegradedError = GlobalState.networkDegradedError;
        this.global.networkStarting = GlobalState.networkStarting;
        this.global.networkReady = GlobalState.networkReady;
        this.global.unreadConversationsCount = GlobalState.unreadConversationsCount;
        this.global.relayChatUnreadCount = GlobalState.relayChatUnreadCount;
        this.global.missedCallsCount = GlobalState.missedCallsCount;
        this.global.activeCallTab = GlobalState.activeCallTab;
        this.global.rrcEnabled = GlobalState.config?.rrc_enabled !== false;
    }

    // ------------------------------------------------------------------
    // Auth gate and shell start/stop
    // ------------------------------------------------------------------

    applyShellAuthState(): void {
        if (!this.global.authSessionResolved) {
            return;
        }
        const needShell = !this.global.authEnabled || (this.global.authenticated && !this.isAuthRoute);
        if (needShell && !this.shellRunning) {
            if (this.global.networkStarting && !this.global.networkReady && !this.global.networkDegraded) {
                this.waitForMeshThenStartShell();
                return;
            }
            this.startShell();
        } else if (!needShell && this.shellRunning) {
            this.stopShell();
        }
    }

    private waitForMeshThenStartShell(): void {
        if (this.meshWaitStarted) {
            return;
        }
        this.meshWaitStarted = true;
        const stopWatch = watch(
            () => [GlobalState.networkReady, GlobalState.networkDegraded, GlobalState.networkStarting],
            () => {
                if (GlobalState.networkReady || GlobalState.networkDegraded || !GlobalState.networkStarting) {
                    stopWatch();
                    this.meshWaitStarted = false;
                    if (!this.shellRunning) {
                        this.applyShellAuthState();
                    }
                }
            },
            { immediate: true }
        );
    }

    startShell(): void {
        if (this.shellRunning) {
            return;
        }
        this.shellRunning = true;
        this.wsLiveSyncHandle = installWsLiveSync({
            connection: LiveTransport,
            onNeedsResync: async () => {
                await this.resyncShellAfterWebsocketReconnect();
            },
        });
        LiveTransport.on("disconnected", this.onWsShellDisconnected);
        LiveTransport.on("connected", this.onWsShellConnected);
        LiveTransport.on("ready", this.onLiveTransportReady);
        LiveTransport.on("queue_expired", this.onLiveQueueExpired);
        LiveTransport.on("transport_fallback", this.onTransportFallback);
        void this.bootstrapLiveTransport();
        this.registerShellWsHandlers();
        this.startClientHeapMemoryWatch();
        GlobalEmitter.on("toast-dismissed", this.onToastDismissedShell);
        GlobalEmitter.on("identity-switching-start", this.onIdentitySwitchingStartShell);
        GlobalEmitter.on("identity-switching-abort", this.onIdentitySwitchingAbortShell);
        GlobalEmitter.on("identity-switched-apply", this.onIdentitySwitchedApplyShell);
        GlobalEmitter.on("sync-propagation-node", this.onSyncPropagationNodeShell);
        GlobalEmitter.on("config-updated", this.onConfigUpdatedExternally);
        GlobalEmitter.on("keyboard-shortcut", this.onKeyboardShortcutShell);
        GlobalEmitter.on("block-status-changed", this.onBlockStatusChangedShell);
        GlobalEmitter.on("show-changelog", this.onShowChangelogShell);
        GlobalEmitter.on("show-tutorial", this.onShowTutorialShell);
        GlobalEmitter.on("tutorial-finished", this.onTutorialFinishedShell);
        GlobalEmitter.on("changelog-closed", this.onChangelogClosedShell);
        GlobalEmitter.on("notifications-changed", this.updateUnreadConversationsCount);

        void this.getAppInfo();
        void this.getConfig();
        void this.getBlockedDestinations();
        void this.getKeyboardShortcuts();
        void this.updateRingtonePlayer();
        void this.updateTelephoneStatus();
        void this.updatePropagationNodeStatus();

        GlobalEmitter.on(BATTERY_SAVER_CHANGED_EVENT, this.onBatterySaverPrefsChangedShell);
        this.startShellPollIntervals();
        this.updateUnreadConversationsCount();
        this.updateRelayChatUnreadCount();
    }

    stopShell(): void {
        if (!this.shellRunning) {
            return;
        }
        this.shellRunning = false;
        this.stopClientHeapMemoryWatch();
        GlobalEmitter.off("toast-dismissed", this.onToastDismissedShell);
        clearInterval(this.reloadInterval as ReturnType<typeof setInterval>);
        this.reloadInterval = null;
        clearInterval(this.appInfoInterval as ReturnType<typeof setInterval>);
        this.appInfoInterval = null;
        clearInterval(this.unreadCountInterval as ReturnType<typeof setInterval>);
        this.unreadCountInterval = null;
        GlobalEmitter.off(BATTERY_SAVER_CHANGED_EVENT, this.onBatterySaverPrefsChangedShell);
        LiveTransport.off("disconnected", this.onWsShellDisconnected);
        LiveTransport.off("connected", this.onWsShellConnected);
        LiveTransport.off("ready", this.onLiveTransportReady);
        LiveTransport.off("queue_expired", this.onLiveQueueExpired);
        LiveTransport.off("transport_fallback", this.onTransportFallback);
        if (this.wsLiveSyncHandle) {
            this.wsLiveSyncHandle.dispose();
            this.wsLiveSyncHandle = null;
        }
        this.unregisterShellWsHandlers();
        GlobalEmitter.off("identity-switching-start", this.onIdentitySwitchingStartShell);
        GlobalEmitter.off("identity-switching-abort", this.onIdentitySwitchingAbortShell);
        GlobalEmitter.off("identity-switched-apply", this.onIdentitySwitchedApplyShell);
        GlobalEmitter.off("sync-propagation-node", this.onSyncPropagationNodeShell);
        GlobalEmitter.off("config-updated", this.onConfigUpdatedExternally);
        GlobalEmitter.off("keyboard-shortcut", this.onKeyboardShortcutShell);
        GlobalEmitter.off("block-status-changed", this.onBlockStatusChangedShell);
        GlobalEmitter.off("show-changelog", this.onShowChangelogShell);
        GlobalEmitter.off("show-tutorial", this.onShowTutorialShell);
        GlobalEmitter.off("tutorial-finished", this.onTutorialFinishedShell);
        GlobalEmitter.off("changelog-closed", this.onChangelogClosedShell);
        GlobalEmitter.off("notifications-changed", this.updateUnreadConversationsCount);
        this.clearWsShellUiTimers();
        this.wsDisconnected = false;
        this.wsDisconnectedAt = null;
        this.wsDisconnectedDurationText = "";
        this.wsDisconnectBannerShown = false;
        this.wsReconnectedBanner = false;
        this.backendProcessExited = false;
        this.backendExitCode = null;
        this.backendRestarting = false;
        this.liveTransportReady = false;
        LiveTransport.destroy();
    }

    private async bootstrapLiveTransport(): Promise<void> {
        try {
            const status = await apiClient().get("/api/v1/status");
            const webtransport = status?.data?.webtransport || {};
            const mode = this.config?.live_transport_mode || "auto";
            LiveTransport.configure({ mode, webtransport });
        } catch {
            LiveTransport.configure({
                mode: this.config?.live_transport_mode || "auto",
                webtransport: { server_available: false },
            });
        }
        await LiveTransport.connect();
    }

    private onLiveTransportReady = (): void => {
        this.liveTransportReady = true;
        GlobalState.liveTransportReady = true;
        this.startShellPollIntervals();
        this.onWsShellReady();
    };

    private onLiveQueueExpired = (): void => {
        ToastUtils.warning(t("app.live_queue_expired"));
    };

    private onTransportFallback = (): void => {
        ToastUtils.warning(t("app.live_transport_fallback_websocket"));
    };

    private startShellPollIntervals(): void {
        clearInterval(this.reloadInterval as ReturnType<typeof setInterval>);
        clearInterval(this.appInfoInterval as ReturnType<typeof setInterval>);
        clearInterval(this.unreadCountInterval as ReturnType<typeof setInterval>);
        this.reloadInterval = null;
        this.appInfoInterval = null;
        this.unreadCountInterval = null;
        if (!this.shellRunning) {
            return;
        }
        const prefs = loadBatterySaverPrefs();
        const ready = this.liveTransportReady === true;
        const telephoneMs = ready ? 15000 : 1000;
        const unreadMs = ready ? 30000 : 5000;
        const appInfoMs = 15000;
        this.reloadInterval = setInterval(() => {
            void this.updateTelephoneStatus();
            void this.updatePropagationNodeStatus();
            this.lastAnnouncedTick += 1;
        }, applyBackgroundPollInterval(telephoneMs, prefs));
        this.appInfoInterval = setInterval(() => {
            void this.getAppInfo();
        }, applyBackgroundPollInterval(appInfoMs, prefs));
        this.unreadCountInterval = setInterval(() => {
            this.updateUnreadConversationsCount();
            this.updateRelayChatUnreadCount();
        }, applyBackgroundPollInterval(unreadMs, prefs));
    }

    private onBatterySaverPrefsChangedShell = (): void => {
        if (this.shellRunning) {
            this.startShellPollIntervals();
        }
    };

    private onToastDismissedShell = ({ key }: { key?: string }): void => {
        if (key === MEMORY_WARNING_TOAST_KEY) {
            markMemoryWarningDismissed();
        }
    };

    private startClientHeapMemoryWatch(): void {
        this.stopClientHeapMemoryWatch();
        this.clientHeapMemoryTimer = setInterval(() => {
            this.sampleClientHeapMemory();
        }, CLIENT_HEAP_SAMPLE_INTERVAL_MS);
        this.sampleClientHeapMemory();
    }

    private stopClientHeapMemoryWatch(): void {
        if (this.clientHeapMemoryTimer != null) {
            clearInterval(this.clientHeapMemoryTimer);
            this.clientHeapMemoryTimer = null;
        }
    }

    private sampleClientHeapMemory(): void {
        let memoryInfo = null;
        try {
            memoryInfo = (performance as unknown as { memory?: unknown })?.memory ?? null;
        } catch {
            memoryInfo = null;
        }
        const result = evaluateClientHeapSample(memoryInfo);
        if (result.shouldWarn) {
            showMemoryWarningToastIfNeeded(ToastUtils, { fromClientHeap: true });
        }
    }

    // ------------------------------------------------------------------
    // WebSocket connection banners
    // ------------------------------------------------------------------

    private registerShellWsHandlers(): void {
        this.unregisterShellWsHandlers();
        const handlers = createShellWsHandlers(this);
        for (const [type, handler] of Object.entries(handlers)) {
            const bound = (payload: any) => handler(payload);
            onWsEvent(type, bound);
            this.shellWsHandlerCleanups.push(() => offWsEvent(type, bound));
        }
    }

    private unregisterShellWsHandlers(): void {
        for (const cleanup of this.shellWsHandlerCleanups) {
            cleanup();
        }
        this.shellWsHandlerCleanups = [];
    }

    private clearWsShellUiTimers(): void {
        if (this.wsDisconnectTickTimer != null) {
            clearInterval(this.wsDisconnectTickTimer);
            this.wsDisconnectTickTimer = null;
        }
        if (this.wsDisconnectGraceTimer != null) {
            clearTimeout(this.wsDisconnectGraceTimer);
            this.wsDisconnectGraceTimer = null;
        }
        if (this.wsReconnectedHideTimer != null) {
            clearTimeout(this.wsReconnectedHideTimer);
            this.wsReconnectedHideTimer = null;
        }
    }

    onBackendProcessExited(payload: { code?: string | number } = {}): void {
        if (!this.shellRunning) {
            return;
        }
        this.backendProcessExited = true;
        this.backendExitCode = payload?.code ?? null;
        // Process exit is serious: show disconnect immediately.
        this.showWsDisconnectedBannerNow();
    }

    private showWsDisconnectedBannerNow(): void {
        if (!this.shellRunning) {
            return;
        }
        if (this.wsDisconnectGraceTimer != null) {
            clearTimeout(this.wsDisconnectGraceTimer);
            this.wsDisconnectGraceTimer = null;
        }
        this.wsDisconnected = true;
        this.wsDisconnectBannerShown = true;
        this.wsDisconnectedAt = this.wsDisconnectedAt || Date.now();
        this.tickWsDisconnectedLabel();
        if (this.wsDisconnectTickTimer != null) {
            clearInterval(this.wsDisconnectTickTimer);
        }
        this.wsDisconnectTickTimer = setInterval(() => this.tickWsDisconnectedLabel(), 1000);
    }

    private onWsShellDisconnected = (): void => {
        if (!this.shellRunning) {
            return;
        }
        this.liveTransportReady = false;
        GlobalState.liveTransportReady = false;
        this.startShellPollIntervals();
        // Ignore brief reconnect blips (startup, Android resume). Only scare
        // the user if the socket stays down past the grace window.
        if (this.wsDisconnected) {
            return;
        }
        if (this.wsDisconnectGraceTimer != null) {
            return;
        }
        this.wsDisconnectedAt = Date.now();
        this.wsDisconnectGraceTimer = setTimeout(() => {
            this.wsDisconnectGraceTimer = null;
            this.showWsDisconnectedBannerNow();
        }, WS_DISCONNECT_BANNER_GRACE_MS);
    };

    private tickWsDisconnectedLabel(): void {
        if (!this.wsDisconnectedAt) {
            this.wsDisconnectedDurationText = "";
            return;
        }
        this.wsDisconnectedDurationText = formatDisconnectedDuration(Date.now() - this.wsDisconnectedAt);
    }

    private clearWsDisconnectedUi(): void {
        if (this.wsDisconnectGraceTimer != null) {
            clearTimeout(this.wsDisconnectGraceTimer);
            this.wsDisconnectGraceTimer = null;
        }
        this.wsDisconnected = false;
        this.wsDisconnectedAt = null;
        this.wsDisconnectedDurationText = "";
        this.wsDisconnectBannerShown = false;
        this.backendProcessExited = false;
        this.backendExitCode = null;
        if (this.wsDisconnectTickTimer != null) {
            clearInterval(this.wsDisconnectTickTimer);
            this.wsDisconnectTickTimer = null;
        }
    }

    private celebrateWsReconnected(): void {
        this.wsReconnectedBanner = true;
        if (this.wsReconnectedHideTimer != null) {
            clearTimeout(this.wsReconnectedHideTimer);
        }
        this.wsReconnectedHideTimer = setTimeout(() => {
            this.wsReconnectedBanner = false;
            this.wsReconnectedHideTimer = null;
        }, 4500);
    }

    private onWsShellConnected = async (payload: { isReconnect?: boolean } = {}): Promise<void> => {
        if (!this.shellRunning) {
            return;
        }
        // TCP open is not recovery. Vite proxies and restart flaps can OPEN then
        // CLOSE without a backend frame. Keep the grace timer running until ready.
        if (payload.isReconnect === true) {
            await this.resyncShellAfterWebsocketReconnect();
        }
    };

    private onWsShellReady(): void {
        if (!this.shellRunning) {
            return;
        }
        const sawDisconnectBanner = this.wsDisconnectBannerShown;
        this.clearWsDisconnectedUi();
        if (sawDisconnectBanner) {
            this.celebrateWsReconnected();
        }
    }

    async resyncShellAfterWebsocketReconnect(): Promise<void> {
        try {
            const status = await fetchAuthStatus(apiClient());
            applyAuthStatusToGlobalState(status);
        } catch {
            // ignore
        }
        try {
            await fetchCsrfToken(apiClient());
        } catch {
            // ignore
        }
        for (const step of [
            () => this.getAppInfo(),
            () => this.getConfig(),
            () => this.getBlockedDestinations(),
            () => this.getKeyboardShortcuts(),
            () => this.updateRingtonePlayer(),
            () => this.updateTelephoneStatus(),
            () => this.updatePropagationNodeStatus(),
        ]) {
            try {
                await step();
            } catch {
                // ignore
            }
        }
        GlobalEmitter.emit("websocket-reconnected");
    }

    // ------------------------------------------------------------------
    // Banner actions
    // ------------------------------------------------------------------

    async onRestartBackend(): Promise<void> {
        const electron = electronBridge();
        if (!electron?.restartBackend) {
            return;
        }
        this.backendRestarting = true;
        try {
            const result = await electron.restartBackend();
            if (!result?.ok) {
                ToastUtils.error(result?.error || t("app.restart_backend_failed"));
                return;
            }
            ToastUtils.info(t("app.restart_backend_started"));
        } catch {
            ToastUtils.error(t("app.restart_backend_failed"));
        } finally {
            this.backendRestarting = false;
        }
    }

    async onViewBackendCrashReport(): Promise<void> {
        const electron = electronBridge();
        if (!electron?.openBackendCrashReport) {
            return;
        }
        try {
            const result = await electron.openBackendCrashReport();
            if (!result?.ok) {
                ToastUtils.error(result?.error || t("app.view_backend_logs_failed"));
            }
        } catch {
            ToastUtils.error(t("app.view_backend_logs_failed"));
        }
    }

    onOpenInterfacesForRecovery(): void {
        void navigate({ name: "interfaces" });
    }

    onOpenSettingsForRecovery(): void {
        void navigate({ name: "settings" });
    }

    onDismissLanBindNoAuthBanner(): void {
        dismissLanBindNoAuthBanner();
        this.lanBindNoAuthBannerDismissed = true;
    }

    onOpenBackupsForRecovery(): void {
        void navigate({ name: "about", hash: "#about-database-backups" });
    }

    async onAutoRecoverDatabase(): Promise<void> {
        if (this.databaseAutoRecovering) {
            return;
        }
        if (!(await DialogUtils.confirm(t("about.auto_recover_confirm")))) {
            return;
        }
        this.databaseAutoRecovering = true;
        try {
            const response = await apiClient().post("/api/v1/database/auto-recover", { relaunch: true });
            const strategy = response.data?.strategy;
            const message = response.data?.message;
            if (strategy === "restore_backup") {
                ToastUtils.success(message || t("about.auto_recover_backup"));
                if (response.data?.requires_relaunch) {
                    return;
                }
            } else if (strategy === "sqlite_recovery") {
                ToastUtils.success(message || t("about.recovery_complete"));
                await this.onRecoverNetwork();
            } else {
                ToastUtils.error(message || t("about.auto_recover_failed"));
            }
        } catch (e) {
            const error = e as { response?: { data?: { message?: string; error?: string } } };
            ToastUtils.error(
                error.response?.data?.message || error.response?.data?.error || t("about.auto_recover_failed")
            );
        } finally {
            this.databaseAutoRecovering = false;
        }
    }

    async onRecoverNetwork(): Promise<void> {
        if (this.networkRecovering) {
            return;
        }
        this.networkRecovering = true;
        try {
            const response = await apiClient().post("/api/v1/reticulum/recover", {});
            if (response.data?.status?.network_ready) {
                GlobalState.networkDegraded = false;
                GlobalState.networkDegradedError = null;
                ToastUtils.success(response.data.message || t("app.network_recovered"));
                return;
            }
            const error = response.data?.error || response.data?.message || t("app.network_recover_failed");
            GlobalState.networkDegradedError = error;
            ToastUtils.error(error);
        } catch (e) {
            const failure = e as { response?: { data?: { message?: string; error?: string } } };
            const error =
                failure.response?.data?.error || failure.response?.data?.message || t("app.network_recover_failed");
            GlobalState.networkDegradedError = error;
            ToastUtils.error(error);
        } finally {
            this.networkRecovering = false;
        }
    }

    maybeNavigateNetworkRecovery(): void {
        if (!GlobalState.networkDegraded || this.isAuthRoute) {
            return;
        }
        const location = recoveryLocationForNetworkError(GlobalState.networkDegradedError);
        if (!location) {
            return;
        }
        if (location.name === "about" && this.routeName === "about" && this.route?.hash === "#about-database-backups") {
            return;
        }
        void navigate(location);
    }

    // ------------------------------------------------------------------
    // Identity switch
    // ------------------------------------------------------------------

    private onIdentitySwitchingStartShell = (): void => {
        this.isSwitchingIdentity = true;
        setTimeout(() => {
            if (this.isSwitchingIdentity) {
                this.isSwitchingIdentity = false;
            }
        }, 45000);
    };

    private onIdentitySwitchingAbortShell = (): void => {
        this.isSwitchingIdentity = false;
    };

    private onIdentitySwitchedApplyShell = (payload: unknown): void => {
        this.applyIdentitySwitched(payload).catch(() => {});
    };

    async applyIdentitySwitched(json: any): Promise<void> {
        const hash = json?.identity_hash;
        const endSwitchUi = (aborted = false) => {
            this.isSwitchingIdentity = false;
            if (aborted) {
                GlobalEmitter.emit("identity-switching-abort");
            }
        };
        if (hash == null || hash === "") {
            endSwitchUi(true);
            return;
        }
        const now = Date.now();
        if (this.identitySwitchDedupeHash === hash && now - this.identitySwitchDedupeAt < 10000) {
            endSwitchUi(false);
            return;
        }
        this.identitySwitchDedupeHash = hash;
        this.identitySwitchDedupeAt = now;

        try {
            if (json?.requires_reauth && GlobalState.authEnabled) {
                ToastUtils.info(t("identities.sign_in_after_switch"));
                GlobalState.authenticated = false;
                try {
                    await fetchCsrfToken(apiClient());
                } catch {
                    // Next mutating request will refresh CSRF when auth completes.
                }
                if (!this.isAuthRoute) {
                    void navigate("/auth");
                }
                endSwitchUi(true);
                return;
            }

            ToastUtils.success(t("identities.switched"));
            resetDatabaseHealthWarningState();
            if (this.wsLiveSyncHandle) {
                this.wsLiveSyncHandle.clearCursor();
            }

            GlobalState.unreadConversationsCount = 0;
            GlobalState.missedCallsCount = 0;
            GlobalState.relayChatUnreadCount = 0;
            GlobalState.blockedDestinations = [];

            // Drop device-global UI caches that must not follow the new identity.
            clearMessagePanes();
            try {
                if (typeof window !== "undefined" && window.localStorage) {
                    window.localStorage.removeItem("micron_editor_content");
                }
            } catch {
                // ignore
            }
            try {
                await micronStorage.clearAll();
            } catch {
                // ignore
            }

            await this.getConfig();
            await this.updateRingtonePlayer();
            await this.getAppInfo();
            await this.getBlockedDestinations();
            void this.updateTelephoneStatus();
            this.updateUnreadConversationsCount();
            this.updateRelayChatUnreadCount();

            GlobalEmitter.emit("identity-switched", json);
        } catch (e) {
            console.error("applyIdentitySwitched failed", e);
            ToastUtils.error(t("identities.failed_switch"));
            endSwitchUi(true);
            return;
        }
        endSwitchUi(false);
    }

    // ------------------------------------------------------------------
    // Emitter bridges
    // ------------------------------------------------------------------

    private onSyncPropagationNodeShell = (): void => {
        void this.syncPropagationNode();
    };

    private onKeyboardShortcutShell = (action: string): void => {
        this.handleKeyboardShortcut(action);
    };

    private onBlockStatusChangedShell = (): void => {
        void this.getBlockedDestinations();
    };

    private onShowChangelogShell = (): void => {
        void this.hosts.changelog?.show();
    };

    private onShowTutorialShell = (): void => {
        this.skipChangelogAfterTutorial = false;
        this.hosts.tutorial?.show();
    };

    private onTutorialFinishedShell = (): void => {
        this.skipChangelogAfterTutorial = true;
    };

    private onChangelogClosedShell = (): void => {
        this.maybeShowChannelPrompt();
    };

    onConfigUpdatedExternally = (newConfig: ShellConfig): void => {
        if (!newConfig || typeof newConfig !== "object") {
            return;
        }
        mergeGlobalConfig(newConfig);
        this.setConfig(newConfig);
    };

    // ------------------------------------------------------------------
    // Config and app info
    // ------------------------------------------------------------------

    /**
     * Apply a config object and run the side effects App.vue kept in its watcher.
     */
    setConfig(next: ShellConfig | null): void {
        this.config = next;
        if (next && typeof next.display_name === "string") {
            this.displayName = next.display_name;
        }
        if (next?.language) {
            void this.applyLocale(String(next.language));
        }
        if (next && next.custom_ringtone_enabled !== undefined) {
            void this.updateRingtonePlayer();
        }
        if (next) {
            this.applyAppearanceThemeFromConfig(next);
        }
        this.applyShellAppearance();
        NotificationUtils.syncAndroidNotificationContext(
            listOpenDestinationHashes(),
            Boolean(next?.do_not_disturb_enabled)
        );
    }

    applyAppearanceThemeFromConfig(config: ShellConfig): void {
        applyAppearanceTheme(config, { prefersDark: this.systemPrefersDark });
    }

    applyShellAppearance(): void {
        if (typeof document === "undefined") {
            return;
        }
        const glassOn = this.config?.ui_glass_enabled !== false;
        document.documentElement.dataset.uiGlass = glassOn ? "1" : "0";
    }

    async getAppInfo(): Promise<void> {
        try {
            const response = await apiClient().get("/api/v1/app/info");
            this.appInfo = response.data.app_info;

            showDatabaseHealthIssuesToastIfNeeded(this.appInfo?.database_health_issues, ToastUtils);

            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has("show-guide")) {
                this.hosts.tutorial?.show();
                urlParams.delete("show-guide");
                const newUrl = window.location.pathname + (urlParams.toString() ? `?${urlParams.toString()}` : "");
                window.history.replaceState({}, "", newUrl);
            } else if (urlParams.has("changelog")) {
                void this.hosts.changelog?.show();
                urlParams.delete("changelog");
                const newUrl = window.location.pathname + (urlParams.toString() ? `?${urlParams.toString()}` : "");
                window.history.replaceState({}, "", newUrl);
            } else if (!this.hasCheckedForModals) {
                this.hasCheckedForModals = true;
                if (this.appInfo && !this.appInfo.tutorial_seen) {
                    this.hosts.tutorial?.show();
                } else if (this.maybeShowAndroidStorageUpgrade()) {
                    // upgrade prompt for existing internal-storage installs
                } else if (await this.maybeShowPostInstallPrompt()) {
                    // registry prompts for existing users (bump revision to re-show)
                } else if (
                    this.appInfo &&
                    !this.skipChangelogAfterTutorial &&
                    this.appInfo.changelog_seen_version !== "999.999.999" &&
                    this.appInfo.changelog_seen_version !== this.appInfo.version
                ) {
                    void this.hosts.changelog?.show();
                } else if (this.maybeShowChannelPrompt()) {
                    // Testing/Beta one-time prompt after changelog
                }
            }
        } catch (e) {
            console.log(e);
        }
    }

    maybeShowChannelPrompt(): boolean {
        if (!shouldShowChannelPrompt(this.appInfo)) {
            return false;
        }
        const modal = this.hosts.channelPrompt;
        if (!modal || typeof modal.show !== "function") {
            return false;
        }
        return modal.show(this.appInfo) === true;
    }

    maybeShowAndroidStorageUpgrade(): boolean {
        const prompt = this.hosts.androidStorage;
        if (!prompt || typeof prompt.showUpgrade !== "function") {
            return false;
        }
        return prompt.showUpgrade();
    }

    async maybeShowPostInstallPrompt(): Promise<boolean> {
        const host = this.hosts.postInstall;
        if (!host || typeof host.showNext !== "function") {
            return false;
        }
        return host.showNext();
    }

    async getConfig(): Promise<void> {
        try {
            const response = await apiClient().get("/api/v1/config");
            const next = response.data?.config;
            if (next && typeof next === "object") {
                mergeGlobalConfig(next);
                this.setConfig(next);
            }
        } catch (e) {
            console.log(e);
        }
    }

    applyAnnouncedEvent(json: any): void {
        const identityHash = typeof json?.identity_hash === "string" ? json.identity_hash : "";
        if (identityHash && this.config?.identity_hash && identityHash !== this.config.identity_hash) {
            return;
        }
        const raw = json?.last_announced_at;
        if (raw != null && raw !== "") {
            const timestamp = Number(raw);
            if (this.config && Number.isFinite(timestamp)) {
                mergeGlobalConfig({ last_announced_at: timestamp });
                this.config = { ...this.config, last_announced_at: timestamp };
                return;
            }
        }
        void this.getConfig();
    }

    async getBlockedDestinations(): Promise<void> {
        try {
            const response = await apiClient().get("/api/v1/blocked-destinations");
            GlobalState.blockedDestinations = response.data.blocked_destinations || [];
        } catch (e) {
            console.log("Failed to load blocked destinations:", e);
        }
    }

    async getKeyboardShortcuts(): Promise<void> {
        LiveTransport.send(JSON.stringify({ type: "keyboard_shortcuts.get" }));
    }

    async updateConfig(config: Record<string, unknown>, label: string | null = null): Promise<void> {
        try {
            const api = apiClient();
            if (api?.patch) {
                const next = await patchServerConfig(config, api);
                mergeGlobalConfig(next);
                this.setConfig({ ...(this.config || {}), ...next });
            } else {
                const requestId = `cfg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
                const ok = await new Promise<boolean>((resolve) => {
                    const timer = setTimeout(() => {
                        if (this.pendingConfigSet?.requestId === requestId) {
                            this.pendingConfigSet = null;
                        }
                        resolve(false);
                    }, 8000);
                    this.pendingConfigSet = {
                        requestId,
                        resolve: (value: boolean) => {
                            clearTimeout(timer);
                            resolve(value);
                        },
                    };
                    LiveTransport.sendQueued(
                        JSON.stringify({
                            type: "config.set",
                            config,
                            request_id: requestId,
                        })
                    );
                });
                if (!ok) {
                    throw new Error("config.set failed or timed out");
                }
                mergeGlobalConfig(config);
                this.setConfig({ ...(this.config || {}), ...config });
            }
            if (label) {
                ToastUtils.success(
                    t("app.setting_auto_saved", {
                        label: t(`app.${label.toLowerCase().replace(/ /g, "_")}`),
                    })
                );
            }
        } catch (e) {
            console.error(e);
            if (label) {
                ToastUtils.error(t("common.save_failed"));
            }
        }
    }

    /**
     * Resolve a pending WebSocket config.set round trip.
     */
    resolvePendingConfigSet(requestId: string): void {
        const pending = this.pendingConfigSet;
        if (pending && pending.requestId === requestId) {
            pending.resolve(true);
            this.pendingConfigSet = null;
        }
    }

    // ------------------------------------------------------------------
    // Identity footer
    // ------------------------------------------------------------------

    onDisplayNameUpdate(value: string): void {
        this.displayName = value;
        this.scheduleIdentitySave();
    }

    private scheduleIdentitySave(): void {
        if (this.identitySaveTimer != null) {
            clearTimeout(this.identitySaveTimer);
        }
        this.identitySaveTimer = setTimeout(() => {
            this.identitySaveTimer = null;
            void this.saveIdentitySettings();
        }, IDENTITY_SAVE_DEBOUNCE_MS);
    }

    flushIdentitySave(): void {
        if (this.identitySaveTimer != null) {
            clearTimeout(this.identitySaveTimer);
            this.identitySaveTimer = null;
        }
        void this.saveIdentitySettings();
    }

    private async saveIdentitySettings(): Promise<void> {
        const nextName = this.displayName;
        const currentName = this.config?.display_name ?? "";
        if (String(nextName) === String(currentName)) {
            return;
        }
        await this.updateConfig({ display_name: nextName }, "display_name_placeholder");
    }

    async onAnnounceIntervalChange(seconds: number): Promise<void> {
        if (!this.config) {
            return;
        }
        this.config = { ...this.config, auto_announce_interval_seconds: seconds };
        await this.updateConfig({ auto_announce_interval_seconds: seconds }, "announce_interval");
    }

    async sendAnnounce(): Promise<void> {
        try {
            await apiClient().get("/api/v1/announce");
            ToastUtils.success(t("app.announce_sent"));
        } catch (e) {
            ToastUtils.error(t("app.failed_announce"));
            console.log(e);
        }
        await this.getConfig();
    }

    async copyValue(value: string, label: string): Promise<void> {
        if (!value) {
            return;
        }
        try {
            await navigator.clipboard.writeText(value);
            ToastUtils.success(`${label} copied`);
        } catch {
            ToastUtils.success(value);
        }
    }

    getMyIdentityUri(): string | null {
        if (!this.config?.lxmf_address_hash) {
            return null;
        }
        const publicKey = this.config?.identity_public_key;
        return publicKey
            ? `lxma://${this.config.lxmf_address_hash}:${publicKey}`
            : `lxmf://${this.config.lxmf_address_hash}`;
    }

    async openLxmfQr(): Promise<void> {
        if (!this.config?.lxmf_address_hash) {
            return;
        }
        try {
            const uri = this.getMyIdentityUri() as string;
            this.lxmfQrDataUrl = await QRCode.toDataURL(uri, { margin: 1, scale: 6 });
            this.showLxmfQr = true;
        } catch {
            ToastUtils.error(t("common.error"));
        }
    }

    async copyIdentityUri(): Promise<void> {
        const uri = this.getMyIdentityUri();
        if (!uri) {
            return;
        }
        await this.copyValue(uri, "Identity URI");
    }

    // ------------------------------------------------------------------
    // Sidebar nav layout
    // ------------------------------------------------------------------

    isNavItemVisible(item: NavItem | null): boolean {
        if (!item) {
            return false;
        }
        if ((item as { visibleWhen?: string }).visibleWhen === "rrcEnabled") {
            return this.rrcEnabled;
        }
        return true;
    }

    enterSidebarNavEdit(): void {
        if (this.isSidebarCollapsed || this.isSidebarNavEditing) {
            return;
        }
        const view = applyNavLayout(this.rawVisibleNavItems, this.sidebarNavLayoutSaved, {
            includeEmptyGroups: this.useGroupedAppSidebar,
        });
        this.sidebarNavLayoutDraft = captureNavLayout(view.primaryGroups, view.moreItems);
        this.isSidebarNavEditing = true;
        if (this.useGroupedAppSidebar) {
            this.isShowingMoreNav = true;
        }
    }

    discardSidebarNavEdit(): void {
        this.isSidebarNavEditing = false;
        this.sidebarNavLayoutDraft = null;
    }

    saveSidebarNavLayout(): void {
        if (this.isSidebarCollapsed || !this.isSidebarNavEditing) {
            return;
        }
        const layout = this.sidebarNavLayoutDraft;
        if (!layout) {
            this.discardSidebarNavEdit();
            return;
        }
        saveAppSidebarNavLayout(layout);
        this.sidebarNavLayoutSaved = cloneNavLayout(layout);
        this.discardSidebarNavEdit();
        ToastUtils.success(t("app.nav_layout_saved"));
    }

    onSidebarNavReorder(op: any): void {
        if (!this.isSidebarNavEditing || this.isSidebarCollapsed || !op) {
            return;
        }
        const preservePlacement = !this.useGroupedAppSidebar;
        const items = this.rawVisibleNavItems;
        let layout = this.sidebarNavLayoutDraft;
        if (!layout) {
            return;
        }
        if (op.kind === "item") {
            layout = moveNavItem(layout, op.itemId, op.target, items, { preservePlacement });
        } else if (op.kind === "group") {
            layout = moveNavGroup(layout, op.groupId, op.beforeGroupId);
        } else if (op.kind === "item-offset") {
            layout = moveNavItemByOffset(layout, op.itemId, op.delta, items, { preservePlacement });
        } else if (op.kind === "group-offset") {
            layout = moveNavGroupByOffset(layout, op.groupId, op.delta);
        }
        this.sidebarNavLayoutDraft = layout;
    }

    onMoreNavToggle(): void {
        if (this.isSidebarCollapsed) {
            void navigate({ name: "about" });
            return;
        }
        this.isShowingMoreNav = !this.isShowingMoreNav;
    }

    setSidebarCollapsed(collapsed: boolean): void {
        this.isSidebarCollapsed = collapsed;
        saveFeatureSidebarCollapsed("app", collapsed);
        if (collapsed) {
            this.discardSidebarNavEdit();
        }
    }

    toggleSidebarCollapsed(): void {
        this.setSidebarCollapsed(!this.isSidebarCollapsed);
    }

    openCommandPalette(): void {
        void this.hosts.commandPalette?.open();
    }

    // ------------------------------------------------------------------
    // Counters
    // ------------------------------------------------------------------

    updateUnreadConversationsCount = (): void => {
        if (this.unreadCountTimeout) {
            clearTimeout(this.unreadCountTimeout);
        }
        this.unreadCountTimeout = setTimeout(async () => {
            try {
                const response = await apiClient().get("/api/v1/notifications", {
                    params: { unread: true, limit: 1 },
                });
                GlobalState.unreadConversationsCount = response.data?.lxmf_total_unread_count ?? 0;
            } catch (e) {
                if (!isRetryableHttpError(e)) {
                    console.error("Failed to update unread conversations count", e);
                }
            }
        }, 300);
    };

    updateRelayChatUnreadCount = (): void => {
        if (!this.rrcEnabled) {
            GlobalState.relayChatUnreadCount = 0;
            return;
        }
        if (this.relayUnreadCountTimeout) {
            clearTimeout(this.relayUnreadCountTimeout);
        }
        this.relayUnreadCountTimeout = setTimeout(async () => {
            try {
                const response = await apiClient().get("/api/v1/rrc/hubs");
                const hubs = response.data?.hubs || [];
                GlobalState.relayChatUnreadCount = countRelayMentions(hubs);
            } catch (e) {
                if (!isRetryableHttpError(e)) {
                    console.error("Failed to update relay chat mention count", e);
                }
            }
        }, 300);
    };

    handleActiveSessionsUpdated(json: any): void {
        const count = Number(json?.count ?? 0);
        const warningEnabled =
            json?.warning_enabled !== undefined
                ? json.warning_enabled !== false
                : this.config?.multi_session_warning_enabled !== false;
        const decision = shouldShowMultiSessionToast(count, warningEnabled, this.multiSessionWarningActive, json?.sessions);
        this.multiSessionWarningActive = decision.warned;
        if (decision.show) {
            ToastUtils.warning(t("app.multi_session_warning", { count }));
        }
    }

    // ------------------------------------------------------------------
    // Propagation node sync
    // ------------------------------------------------------------------

    propagationSyncStatusLabel(state: string | null | undefined): string {
        if (state == null || state === "") {
            return t("app.propagation_sync_state.unknown");
        }
        const key = `app.propagation_sync_state.${state}`;
        const translated = t(key);
        return translated !== key ? translated : t("app.propagation_sync_state.unknown");
    }

    propagationSyncLiveToastMessage(): string {
        const status = this.propagationNodeStatus?.state ?? "unknown";
        const progress = Math.round(this.propagationNodeStatus?.progress ?? 0);
        return t("app.propagation_sync_live", {
            status: this.propagationSyncStatusLabel(status),
            progress,
        });
    }

    async syncPropagationNode(): Promise<void> {
        // ask to stop syncing if already syncing
        if (this.isSyncingPropagationNode) {
            if (await DialogUtils.confirm(t("app.stop_sync_confirm"))) {
                await this.stopSyncingPropagationNode();
            }
            return;
        }

        this.userInitiatedPropagationSync = true;

        try {
            const preferredHash = this.config?.lxmf_preferred_propagation_node_destination_hash;
            if (preferredHash) {
                // Best-effort path priming. /sync also requests a path.
                try {
                    await postRequestPath(apiClient(), preferredHash);
                } catch {
                    // continue to sync
                }
            }
            await apiClient().post("/api/v1/lxmf/propagation-node/sync");
        } catch (e) {
            this.userInitiatedPropagationSync = false;
            const error = e as { response?: { data?: { message?: string; error?: string } } };
            ToastUtils.error(
                error.response?.data?.message ?? error.response?.data?.error ?? t("app.sync_error_generic")
            );
            return;
        }

        await this.updatePropagationNodeStatus();

        this.isPropagationSyncPolling = false;
        const pollStartedAt = Date.now();

        const poll = async (): Promise<void> => {
            if (this.isPropagationSyncPolling) {
                return;
            }
            this.isPropagationSyncPolling = true;
            try {
                await this.updatePropagationNodeStatus();
                if (this.isSyncingPropagationNode) {
                    if (Date.now() - pollStartedAt > PROPAGATION_SYNC_POLL_TIMEOUT_MS) {
                        if (this.propagationSyncPollTimer != null) {
                            clearInterval(this.propagationSyncPollTimer);
                            this.propagationSyncPollTimer = null;
                        }
                        await this.stopSyncingPropagationNode();
                        this.userInitiatedPropagationSync = false;
                        ToastUtils.error(
                            t("app.sync_error", {
                                status: this.propagationSyncStatusLabel("path_timeout"),
                            })
                        );
                        return;
                    }
                    ToastUtils.loading(this.propagationSyncLiveToastMessage(), 0, PROPAGATION_SYNC_TOAST_KEY);
                    return;
                }
                if (this.propagationSyncPollTimer != null) {
                    clearInterval(this.propagationSyncPollTimer);
                    this.propagationSyncPollTimer = null;
                }
                this.userInitiatedPropagationSync = false;
                ToastUtils.dismiss(PROPAGATION_SYNC_TOAST_KEY);
                const status = this.propagationNodeStatus?.state;
                const messagesReceived = this.propagationNodeStatus?.messages_received ?? 0;
                const messagesStored = this.propagationNodeStatus?.messages_stored ?? 0;
                const deliveryConfirmations = this.propagationNodeStatus?.delivery_confirmations ?? 0;
                const messagesHidden = this.propagationNodeStatus?.messages_hidden ?? 0;
                if (status === "complete" || status === "idle") {
                    const base = t("app.sync_complete", { count: messagesReceived });
                    const details = `${messagesStored} stored, ${deliveryConfirmations} confirmations, ${messagesHidden} hidden`;
                    ToastUtils.success(`${base} (${details})`);
                } else {
                    ToastUtils.error(
                        t("app.sync_error", {
                            status: this.propagationSyncStatusLabel(status),
                        })
                    );
                }
            } finally {
                this.isPropagationSyncPolling = false;
            }
        };

        if (this.isSyncingPropagationNode) {
            ToastUtils.loading(this.propagationSyncLiveToastMessage(), 0, PROPAGATION_SYNC_TOAST_KEY);
            this.propagationSyncPollTimer = setInterval(() => void poll(), 500);
        } else {
            this.userInitiatedPropagationSync = false;
        }
        await poll();
    }

    async stopSyncingPropagationNode(): Promise<void> {
        try {
            await apiClient().post("/api/v1/lxmf/propagation-node/stop-sync");
        } catch {
            // do nothing on error
        }
        if (this.propagationSyncPollTimer != null) {
            clearInterval(this.propagationSyncPollTimer);
            this.propagationSyncPollTimer = null;
        }
        this.isPropagationSyncPolling = false;
        this.userInitiatedPropagationSync = false;
        ToastUtils.dismiss(PROPAGATION_SYNC_TOAST_KEY);
        await this.updatePropagationNodeStatus();
    }

    async cancelInboundDeliveries(): Promise<void> {
        const count = this.inboundDeliveryCount;
        if (count <= 0) {
            return;
        }
        if (!(await DialogUtils.confirm(t("app.cancel_inbound_confirm", { count })))) {
            return;
        }
        try {
            const response = await apiClient().post("/api/v1/lxmf/propagation-node/cancel-inbound", {});
            const cancelled = response?.data?.cancelled ?? 0;
            ToastUtils.success(t("app.cancel_inbound_done", { count: cancelled }));
            if (response?.data?.inbound_deliveries) {
                this.propagationNodeStatus = {
                    ...(this.propagationNodeStatus || {}),
                    inbound_delivery_count: response.data.inbound_delivery_count ?? 0,
                    inbound_deliveries: response.data.inbound_deliveries,
                };
            } else {
                await this.updatePropagationNodeStatus();
            }
        } catch (e) {
            const error = e as { response?: { data?: { message?: string } } };
            ToastUtils.error(error.response?.data?.message ?? t("app.cancel_inbound_failed"));
        }
    }

    async updatePropagationNodeStatus(): Promise<void> {
        try {
            const response = await apiClient().get("/api/v1/lxmf/propagation-node/status");
            this.propagationNodeStatus = response.data.propagation_node_status;
            const state = this.propagationNodeStatus?.state;
            if (this.userInitiatedPropagationSync && state && !ACTIVE_SYNC_STATES.includes(state)) {
                this.userInitiatedPropagationSync = false;
            }
        } catch {
            // do nothing on error
        }
    }

    // ------------------------------------------------------------------
    // Telephony chrome
    // ------------------------------------------------------------------

    onRingtoneUnlockGesture(): void {
        NotificationSoundUtils.unlockAutoplay();
        if (!this.ringtoneAutoplayBlocked) {
            return;
        }
        this.ringtoneAutoplayBlocked = false;
        if (this.activeCall?.status === 4 && this.activeCall?.is_incoming) {
            this.playRingtone();
        }
    }

    async updateRingtonePlayer(): Promise<void> {
        if (this.ringtonePlayer) {
            this.ringtonePlayer.pause();
            this.ringtonePlayer = null;
        }
        if (this.config?.custom_ringtone_enabled) {
            try {
                const response = await apiClient().get("/api/v1/telephone/ringtones/status");
                const status = response.data;
                if (status.has_custom_ringtone && status.id) {
                    this.ringtonePlayer = new Audio(`/api/v1/telephone/ringtones/${status.id}/audio`);
                    this.ringtonePlayer.loop = true;
                    if (status.volume !== undefined) {
                        this.ringtonePlayer.volume = status.volume;
                    }
                }
            } catch (e) {
                console.error("Failed to update ringtone player:", e);
            }
        }
    }

    playRingtone(): void {
        if (!this.ringtonePlayer || this.ringtoneAutoplayBlocked) {
            return;
        }
        if (this.ringtonePlayer.paused) {
            this.ringtonePlayer.play().catch((e: { name?: string }) => {
                if (e?.name === "NotAllowedError") {
                    // Browser autoplay policy blocked playback until user gesture.
                    this.ringtoneAutoplayBlocked = true;
                    return;
                }
                console.warn("Failed to play custom ringtone:", e);
            });
        }
    }

    stopRingtone(): void {
        if (this.ringtonePlayer) {
            try {
                this.ringtonePlayer.pause();
                this.ringtonePlayer.currentTime = 0;
            } catch {
                // ignore errors during pause
            }
        }
    }

    async updateTelephoneStatus(options: { forceHistoryRefresh?: boolean } = {}): Promise<void> {
        try {
            const response = await apiClient().get("/api/v1/telephone/status");
            const oldCall = this.activeCall;
            const newCall = response.data.active_call;

            this.activeCall = newCall;
            if (this.activeCall) {
                this.toneGenerator.stop();
            }
            this.voicemailStatus = response.data.voicemail;
            this.initiationStatus = response.data.initiation_status;
            this.initiationTargetHash = response.data.initiation_target_hash;
            this.initiationTargetName = response.data.initiation_target_name;
            GlobalState.missedCallsCount = response.data?.missed_calls_unread_count ?? 0;

            const justEnded = oldCall != null && this.activeCall == null;
            const forceHistory = options.forceHistoryRefresh === true;
            if (justEnded || forceHistory) {
                if (justEnded) {
                    this.lastCall = oldCall;
                    if (this.config?.telephone_tone_generator_enabled) {
                        this.toneGenerator.setVolume(this.config.telephone_tone_generator_volume);
                        this.toneGenerator.playBusyTone();
                    }
                }

                GlobalEmitter.emit("telephone-history-updated");

                if (justEnded && !this.wasDeclined) {
                    this.isCallEnded = true;
                }

                if (justEnded) {
                    if (this.endedTimeout) {
                        clearTimeout(this.endedTimeout);
                    }
                    this.endedTimeout = setTimeout(() => {
                        this.isCallEnded = false;
                        this.wasDeclined = false;
                        this.lastCall = null;
                    }, 5000);
                }
            }

            if (this.initiationStatus === "Ringing...") {
                if (this.config?.telephone_tone_generator_enabled) {
                    this.toneGenerator.setVolume(this.config.telephone_tone_generator_volume);
                    this.toneGenerator.playRingback();
                }
            } else if (!this.initiationStatus && !this.activeCall && !this.isCallEnded) {
                // Only stop if we are not ringing, in a call, or just finished a call
                this.toneGenerator.stop();
            }

            if (ElectronUtils.isElectron()) {
                const electron = electronBridge();
                if (this.activeCall) {
                    electron?.setPowerSaveBlocker(true);
                } else if (!this.initiationStatus) {
                    electron?.setPowerSaveBlocker(false);
                }
            }

            const meta = (this.route?.meta || {}) as { isPopout?: boolean };
            if (
                (this.activeCall || this.initiationStatus) &&
                this.config?.desktop_open_calls_in_separate_window &&
                ElectronUtils.isElectron()
            ) {
                if (!this.isCallWindowOpen && !meta.isPopout) {
                    this.isCallWindowOpen = true;
                    window.open("/call.html", "MeshChatXCallWindow", "width=600,height=800");
                }
            } else {
                this.isCallWindowOpen = false;
            }

            if (this.activeCall?.status === 4 && this.activeCall?.is_incoming) {
                if (!this.ringtonePlayer && this.config?.custom_ringtone_enabled && !this.isFetchingRingtone) {
                    this.isFetchingRingtone = true;
                    try {
                        const callerHash = this.activeCall.remote_identity_hash;
                        const ringResponse = await apiClient().get(
                            `/api/v1/telephone/ringtones/status?caller_hash=${callerHash}`
                        );
                        const status = ringResponse.data;
                        if (status.has_custom_ringtone && status.id) {
                            // Double check the call did not end during the await.
                            if (this.activeCall?.status === 4) {
                                this.stopRingtone();
                                this.ringtonePlayer = new Audio(`/api/v1/telephone/ringtones/${status.id}/audio`);
                                this.ringtonePlayer.loop = true;
                                if (status.volume !== undefined) {
                                    this.ringtonePlayer.volume = status.volume;
                                }
                                this.playRingtone();
                            }
                        }
                    } finally {
                        this.isFetchingRingtone = false;
                    }
                } else if (this.ringtonePlayer && this.activeCall?.status === 4) {
                    this.playRingtone();
                }
            } else if (this.ringtonePlayer) {
                this.stopRingtone();
                this.ringtonePlayer = null;
            }

            if (newCall && oldCall) {
                newCall.is_mic_muted = oldCall.is_mic_muted;
                newCall.is_speaker_muted = oldCall.is_speaker_muted;
            }

            if (justEnded) {
                // handled above
            } else if (this.activeCall != null) {
                this.isCallEnded = false;
                this.wasDeclined = false;
                this.lastCall = null;
                if (this.endedTimeout) {
                    clearTimeout(this.endedTimeout);
                }
            } else if (!this.endedTimeout) {
                this.isCallEnded = false;
                this.wasDeclined = false;
                this.lastCall = null;
            }
        } catch {
            // do nothing on error
        }
    }

    onOverlayHangup(): void {
        if (this.activeCall && this.activeCall.is_incoming && this.activeCall.status === 4) {
            this.wasDeclined = true;
        }
    }

    onToggleMic(isMuted: boolean): void {
        if (this.activeCall) {
            this.activeCall.is_mic_muted = isMuted;
        }
    }

    onToggleSpeaker(isMuted: boolean): void {
        if (this.activeCall) {
            this.activeCall.is_speaker_muted = isMuted;
        }
    }

    // ------------------------------------------------------------------
    // Theme, locale, navigation helpers
    // ------------------------------------------------------------------

    async toggleTheme(): Promise<void> {
        if (!this.config) {
            return;
        }
        const nextTheme = this.isDarkTheme ? "light" : "dark";
        this.config = { ...this.config, theme: nextTheme };
        await this.updateConfig({ theme: nextTheme }, "theme");
    }

    async applyLocale(langCode: string): Promise<void> {
        if (!langCode) {
            return;
        }
        const ok = await setLocale(null, langCode);
        if (!ok) {
            await setLocale(null, "en");
        }
        this.localeVersion += 1;
    }

    async onLanguageChange(langCode: string): Promise<void> {
        const code = normalizeUiLocaleCode(langCode);
        // Switch UI first so a slow or failed PATCH cannot leave the shell on English.
        await this.applyLocale(code);
        await this.updateConfig({ language: code }, "language");
    }

    async composeNewMessage(): Promise<void> {
        await navigate({ name: "messages" });
        GlobalEmitter.emit("compose-new-message");
    }

    onAppNameClick(middle?: HTMLElement | null): void {
        // user may be on mobile and unable to scroll back to the sidebar
        middle?.scrollTo({ top: 0, left: 0, behavior: "smooth" });
        void navigate("/messages");
    }

    onAndroidIntentUri(event: CustomEvent): void {
        const uri = event?.detail;
        if (typeof uri !== "string" || uri.trim() === "") {
            return;
        }
        handleProtocolLink(router, uri.trim());
    }

    handleKeyboardShortcut(action: string): void {
        switch (action) {
            case "nav_messages":
                void navigate({ name: "messages" });
                break;
            case "nav_nomad":
                void navigate({ name: "nomadnetwork" });
                break;
            case "nav_map":
                void navigate({ name: "map" });
                break;
            case "nav_paper":
                void navigate({ name: "paper-message" });
                break;
            case "nav_archives":
                void navigate({ name: "archives" });
                break;
            case "nav_calls":
                void navigate({ name: "call" });
                break;
            case "nav_settings":
                void navigate({ name: "settings" });
                break;
            case "compose_message":
                void this.composeNewMessage();
                break;
            case "sync_messages":
                void this.syncPropagationNode();
                break;
            case "command_palette":
                // Command palette owns its shortcut. Emitted here for parity.
                break;
            case "toggle_sidebar":
                this.toggleSidebarCollapsed();
                break;
        }
    }
}

/**
 * Read a popout marker straight off the URL for early boot, before the router
 * has resolved a route.
 */
export function getHashPopoutValue(): string | null {
    if (typeof window === "undefined") {
        return null;
    }
    const hash = window.location.hash || "";
    const match = hash.match(/popout=([^&]+)/);
    return match ? decodeURIComponent(match[1]) : null;
}
