// SPDX-License-Identifier: 0BSD

import GlobalState, { mergeGlobalConfig } from "../../../js/GlobalState.js";
import {
    channelBadgeClass,
    channelLabelKey,
    normalizeReleaseChannel,
    shouldShowChannelPrompt,
} from "../../../js/releaseChannel.js";
import ElectronUtils from "../../../js/ElectronUtils.js";
import {
    shouldShowLanBindNoAuthBanner,
    dismissLanBindNoAuthBanner,
    isLanBindNoAuthBannerDismissed,
} from "../../../js/lanBindWarning.js";
import { isMeshChatXAndroid } from "../../../js/webAudioMicPermission.js";
import ToneGenerator from "../../../js/ToneGenerator.js";
import { listNavItems } from "../../../js/registries/navRegistry.js";
import { isDatabaseRecoveryError, recoveryLocationForNetworkError } from "../../../js/networkRecovery.js";
import type { FatalErrorRecord } from "../../../js/fatalErrorState.js";
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
    applyAppearanceTheme,
    resolveEffectiveTheme,
    shellCanvasBackgroundStyle,
    systemPrefersDark,
} from "../../../theme/themeEngine.js";
import type { ActiveRoute } from "../../../shell/hashRouter.js";
import type { NavGroup, NavItem } from "./navTypes.js";
import { electronBridge } from "./appShellShared.js";
import type { ShellConfig, ShellAppInfo, ShellHosts, Timer, Interval } from "./appShellShared.js";
import * as lifecycle from "./appShellLifecycle.js";
import * as recovery from "./appShellRecovery.js";
import * as identity from "./appShellIdentity.js";
import * as config from "./appShellConfig.js";
import * as nav from "./appShellNav.js";
import * as commands from "./appShellCommands.js";
import * as derived from "./appShellDerived.js";
import { isNavItemVisible } from "./appShellNav.js";
import { onAndroidIntentUri } from "./appShellCommands.js";
import { onRingtoneUnlockGesture } from "./appShellTelephony.js";

/**
 * App shell state, ported from components/App.vue.
 * Holds the reactive fields and computed values App.svelte reads. Behaviour
 * lives in the appShell* helper modules so no single file carries the whole
 * shell. GlobalState is still a Vue reactive object, so its fields are
 * mirrored into runes state through a Vue watcher.
 */

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

    wsDisconnectedAt: number | null = null;

    wsDisconnectBannerShown = false;

    wsDisconnectTickTimer: Interval = null;

    wsDisconnectGraceTimer: Timer = null;

    wsReconnectedHideTimer: Timer = null;

    reloadInterval: Interval = null;

    appInfoInterval: Interval = null;

    unreadCountInterval: Interval = null;

    clientHeapMemoryTimer: Interval = null;

    propagationSyncPollTimer: Interval = null;

    isPropagationSyncPolling = false;

    unreadCountTimeout: Timer = null;

    relayUnreadCountTimeout: Timer = null;

    identitySaveTimer: Timer = null;

    wsLiveSyncHandle: { dispose: () => void; clearCursor: () => void } | null = null;

    shellWsHandlerCleanups: Array<() => void> = [];

    identitySwitchDedupeHash: string | null = null;

    identitySwitchDedupeAt = 0;

    multiSessionWarningActive = false;

    pendingConfigSet: { requestId: string; resolve: (value: boolean) => void } | null = null;

    meshWaitStarted = false;

    disposers: Array<() => void> = [];

    boundIntentUri = (event: Event) => onAndroidIntentUri(this, event as CustomEvent);

    boundRingtoneUnlock = () => onRingtoneUnlockGesture(this);

    // ------------------------------------------------------------------
    // Derived shell chrome
    // ------------------------------------------------------------------
    readonly routeName = $derived(this.route?.name ?? "");

    readonly isAuthRoute = $derived(this.routeName === "auth");

    readonly showMainShell = $derived.by(() => derived.showMainShell(this));

    readonly currentPopoutType = $derived.by(() => derived.currentPopoutType(this));

    readonly isPopoutMode = $derived(this.currentPopoutType != null);

    readonly sidebarDisplayVersion = $derived.by(() => derived.sidebarDisplayVersion(this));

    readonly sidebarVersionLabel = $derived.by(() => derived.sidebarVersionLabel(this));

    readonly sidebarChannel = $derived(normalizeReleaseChannel(this.appInfo?.build_channel));

    readonly sidebarChannelLabel = $derived.by(() => derived.sidebarChannelLabel(this));

    readonly sidebarChannelBadgeClass = $derived(channelBadgeClass(this.sidebarChannel));

    readonly sidebarVersionTitle = $derived.by(() => derived.sidebarVersionTitle(this));

    readonly rrcEnabled = $derived(this.global.rrcEnabled);

    readonly rawVisibleNavItems = $derived.by(() =>
        (listNavItems() as NavItem[]).filter((item) => isNavItemVisible(this, item))
    );

    readonly activeNavLayout = $derived.by(() => derived.activeNavLayout(this));

    readonly useGroupedAppSidebar = $derived(this.config?.app_sidebar_layout !== "classic");

    readonly navLayoutView = $derived.by(() =>
        applyNavLayout(this.rawVisibleNavItems, this.activeNavLayout, {
            includeEmptyGroups: this.isSidebarNavEditing && this.useGroupedAppSidebar,
        })
    ) as { primaryGroups: NavGroup[]; moreItems: NavItem[] };

    readonly visibleNavItems = $derived.by(() => derived.visibleNavItems(this));

    readonly moreNavItems = $derived(this.navLayoutView.moreItems);

    readonly primaryNavGroups = $derived(this.navLayoutView.primaryGroups);

    readonly lastAnnouncedSidebarLabel = $derived.by(() => derived.lastAnnouncedSidebarLabel(this));

    readonly identitySidebarLabel = $derived.by(() => derived.identitySidebarLabel(this));

    readonly isSyncingPropagationNode = $derived.by(() => derived.isSyncingPropagationNode(this));

    readonly inboundDeliveryCount = $derived.by(() => {
        const count = this.propagationNodeStatus?.inbound_delivery_count;
        return Number.isFinite(Number(count)) ? Math.max(0, Number(count)) : 0;
    });

    readonly effectiveThemeMode = $derived(resolveEffectiveTheme(this.config?.theme, this.systemPrefersDark));

    readonly isDarkTheme = $derived(this.effectiveThemeMode === "dark");

    readonly shellCanvasStyle = $derived.by(() => derived.shellCanvasStyle(this));

    readonly themeToggleIcon = $derived.by(() => derived.themeToggleIcon(this));

    readonly themeToggleTitle = $derived.by(() => derived.themeToggleTitle(this));

    // ------------------------------------------------------------------
    // Banner derivations
    // ------------------------------------------------------------------
    readonly showWsDisconnectedBanner = $derived(this.shellRunning && this.wsDisconnected && !this.isAuthRoute);

    readonly backendOfflineBannerLabel = $derived.by(() => derived.backendOfflineBannerLabel(this));

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

    readonly networkDegradedBannerLabel = $derived.by(() => derived.networkDegradedBannerLabel(this));

    readonly showDatabaseRecoveryActions = $derived(isDatabaseRecoveryError(this.global.networkDegradedError));

    readonly shouldShowCallOverlay = $derived.by(() => derived.shouldShowCallOverlay(this));

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------
    /**
     * Wire GlobalState mirroring, route tracking, and window listeners.
     * Call once from App.svelte onMount. Returns nothing, use destroy() to undo.
     */

    readonly onLiveTransportReady = (): void => lifecycle.onLiveTransportReady(this);

    readonly onLiveQueueExpired = (): void => lifecycle.onLiveQueueExpired(this);

    readonly onTransportFallback = (): void => lifecycle.onTransportFallback(this);

    readonly onBatterySaverPrefsChangedShell = (): void => lifecycle.onBatterySaverPrefsChangedShell(this);

    readonly onToastDismissedShell = (payload: { key?: string }): void =>
        lifecycle.onToastDismissedShell(this, payload);

    readonly onWsShellDisconnected = (): void => recovery.onWsShellDisconnected(this);

    readonly onWsShellConnected = async (payload: { isReconnect?: boolean } = {}): Promise<void> =>
        recovery.onWsShellConnected(this, payload);

    readonly onIdentitySwitchingStartShell = (): void => identity.onIdentitySwitchingStartShell(this);

    readonly onIdentitySwitchingAbortShell = (): void => identity.onIdentitySwitchingAbortShell(this);

    readonly onIdentitySwitchedApplyShell = (payload: unknown): void =>
        identity.onIdentitySwitchedApplyShell(this, payload);

    readonly onSyncPropagationNodeShell = (): void => commands.onSyncPropagationNodeShell(this);

    readonly onKeyboardShortcutShell = (action: string): void => commands.onKeyboardShortcutShell(this, action);

    readonly onBlockStatusChangedShell = (): void => commands.onBlockStatusChangedShell(this);

    readonly onShowChangelogShell = (): void => commands.onShowChangelogShell(this);

    readonly onShowTutorialShell = (): void => commands.onShowTutorialShell(this);

    readonly onTutorialFinishedShell = (): void => commands.onTutorialFinishedShell(this);

    readonly onChangelogClosedShell = (): void => commands.onChangelogClosedShell(this);

    readonly onConfigUpdatedExternally = (newConfig: ShellConfig): void =>
        config.onConfigUpdatedExternally(this, newConfig);

    readonly updateUnreadConversationsCount = (): void => nav.updateUnreadConversationsCount(this);

    readonly updateRelayChatUnreadCount = (): void => nav.updateRelayChatUnreadCount(this);

    /** Called from App.svelte onMount. Registers every listener and watcher. */
    init(): void {
        lifecycle.init(this);
    }

    /** Called from App.svelte onDestroy. Runs every disposer registered by init. */
    destroy(): void {
        lifecycle.destroy(this);
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

export type { ShellAppInfo, ShellConfig, ShellHosts } from "./appShellShared.js";
