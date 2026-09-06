// SPDX-License-Identifier: 0BSD

/**
 * Bodies of the longer AppShellState derived values. Each takes the state so the
 * class keeps one line per computed value.
 */

import Utils from "../../../js/Utils.js";
import { channelLabelKey } from "../../../js/releaseChannel.js";
import { t } from "../../../js/i18n.js";
import ElectronUtils from "../../../js/ElectronUtils.js";
import { orderItemsByLayout } from "../../../js/appSidebarNavLayout.js";
import { shellCanvasBackgroundStyle } from "../../../theme/themeEngine.js";
import type { NavItem } from "./navTypes.js";
import { ACTIVE_SYNC_STATES } from "./appShellShared.js";
import { getHashPopoutValue } from "./appShellState.svelte.js";
import type { AppShellState } from "./appShellState.svelte.js";

export function showMainShell(state: AppShellState) {
    if (!state.global.authSessionResolved) {
        return false;
    }
    if (state.isAuthRoute) {
        return false;
    }
    if (!state.global.authEnabled) {
        return true;
    }
    return state.global.authenticated;
}

export function currentPopoutType(state: AppShellState) {
    const meta = state.route?.meta as { popoutType?: unknown } | undefined;
    if (meta?.popoutType) {
        return meta.popoutType;
    }
    return state.route?.query?.popout ?? getHashPopoutValue();
}

export function sidebarDisplayVersion(state: AppShellState) {
    const info = state.appInfo || {};
    if (info.display_version) {
        return info.display_version;
    }
    const base = info.version || "";
    if (info.is_dev_build && base && !String(base).endsWith("-dev")) {
        return `${base}-dev`;
    }
    return base;
}

export function sidebarVersionLabel(state: AppShellState) {
    void state.localeVersion;
    const version = state.sidebarDisplayVersion;
    if (!version) {
        return "";
    }
    const label = t("about.version", { version });
    const short =
        state.appInfo?.git_commit_short ||
        (state.appInfo?.git_commit ? String(state.appInfo.git_commit).slice(0, 7) : "");
    if (state.appInfo?.is_dev_build && short) {
        return `${label} ${short}`;
    }
    return label;
}

export function sidebarChannelLabel(state: AppShellState) {
    void state.localeVersion;
    if (!state.appInfo?.version) {
        return "";
    }
    return t(channelLabelKey(state.sidebarChannel));
}

export function sidebarVersionTitle(state: AppShellState) {
    const base = state.sidebarVersionLabel;
    const channel = state.sidebarChannelLabel;
    if (base && channel) {
        return `${base} (${channel})`;
    }
    return base;
}

export function activeNavLayout(state: AppShellState) {
    if (state.isSidebarNavEditing && state.sidebarNavLayoutDraft) {
        return state.sidebarNavLayoutDraft;
    }
    return state.sidebarNavLayoutSaved;
}

export function visibleNavItems(state: AppShellState) {
    if (!state.useGroupedAppSidebar) {
        return orderItemsByLayout(state.rawVisibleNavItems, state.activeNavLayout) as NavItem[];
    }
    const view = state.navLayoutView;
    return [...view.primaryGroups.flatMap((group) => group.items), ...view.moreItems];
}

export function lastAnnouncedSidebarLabel(state: AppShellState) {
    if (!state.config?.last_announced_at) {
        return "";
    }
    void state.lastAnnouncedTick;
    return Utils.formatSecondsAgo(state.config.last_announced_at);
}

export function identitySidebarLabel(state: AppShellState) {
    void state.localeVersion;
    const raw = state.displayName;
    const name = raw != null && String(raw).trim() !== "" ? String(raw).trim() : "";
    return name || t("app.my_identity");
}

export function isSyncingPropagationNode(state: AppShellState) {
    // Only treat sync as "running" in the chrome when the user started it.
    // Background auto-sync must not keep the header spinner forever.
    if (!state.userInitiatedPropagationSync) {
        return false;
    }
    return ACTIVE_SYNC_STATES.includes(state.propagationNodeStatus?.state);
}

export function shellCanvasStyle(state: AppShellState) {
    // Always paint a canvas color so dark mode never flashes through to the
    // light #app fallback while config is still loading.
    const background = shellCanvasBackgroundStyle(state.config || {}, state.effectiveThemeMode);
    return background ? `background-color: ${background};` : "";
}

export function themeToggleIcon(state: AppShellState) {
    if (state.config?.theme === "system") {
        return "theme-light-dark";
    }
    return state.isDarkTheme ? "brightness-6" : "brightness-4";
}

export function themeToggleTitle(state: AppShellState) {
    void state.localeVersion;
    if (state.config?.theme === "system") {
        return t("app.system_theme");
    }
    return state.isDarkTheme ? t("app.light_theme") : t("app.dark_theme");
}

export function backendOfflineBannerLabel(state: AppShellState) {
    void state.localeVersion;
    const duration = state.wsDisconnectedDurationText;
    const durationSuffix = duration ? ` \u00b7 ${duration}` : "";
    if (state.backendProcessExited) {
        const code = state.backendExitCode != null && state.backendExitCode !== "" ? ` (${state.backendExitCode})` : "";
        return `${t("app.backend_process_stopped")}${code}${durationSuffix}`;
    }
    return `${t("app.backend_disconnected")}${durationSuffix}`;
}

export function networkDegradedBannerLabel(state: AppShellState) {
    void state.localeVersion;
    const detail = state.global.networkDegradedError;
    if (detail && String(detail).trim()) {
        return String(detail).trim();
    }
    return t("app.network_degraded");
}

export function shouldShowCallOverlay(state: AppShellState) {
    const meta = (state.route?.meta || {}) as { isPopout?: boolean };
    return Boolean(
        (state.activeCall || state.isCallEnded || state.wasDeclined || state.initiationStatus) &&
        !meta.isPopout &&
        (!["call", "call-popout"].includes(state.routeName) || state.global.activeCallTab !== "phone") &&
        (!state.config?.desktop_open_calls_in_separate_window || !ElectronUtils.isElectron())
    );
}
