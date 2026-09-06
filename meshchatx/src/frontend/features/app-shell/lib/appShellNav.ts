// SPDX-License-Identifier: 0BSD

/**
 * Sidebar nav visibility, reorder editing, collapse state, command palette,
 * and the unread counters shown on nav items.
 */

import GlobalState from "../../../js/GlobalState.js";
import { countRelayMentions } from "../../../js/relayMentionCount.js";
import { isRetryableHttpError } from "../../../js/httpRetry.js";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import { shouldShowMultiSessionToast } from "../../../js/activeSessions.js";
import { saveFeatureSidebarCollapsed } from "../../../js/browserLayoutStore.js";
import {
    applyNavLayout,
    captureNavLayout,
    cloneNavLayout,
    moveNavGroup,
    moveNavGroupByOffset,
    moveNavItem,
    moveNavItemByOffset,
    saveAppSidebarNavLayout,
} from "../../../js/appSidebarNavLayout.js";
import { navigate } from "../../../shell/hashRouter.js";
import type { NavItem } from "./navTypes.js";
import { apiClient } from "./appShellShared.js";
import type { AppShellState } from "./appShellState.svelte.js";

// Sidebar nav layout
// ------------------------------------------------------------------
export function isNavItemVisible(state: AppShellState, item: NavItem | null): boolean {
    if (!item) {
        return false;
    }
    if ((item as { visibleWhen?: string }).visibleWhen === "rrcEnabled") {
        return state.rrcEnabled;
    }
    return true;
}

export function enterSidebarNavEdit(state: AppShellState): void {
    if (state.isSidebarCollapsed || state.isSidebarNavEditing) {
        return;
    }
    const view = applyNavLayout(state.rawVisibleNavItems, state.sidebarNavLayoutSaved, {
        includeEmptyGroups: state.useGroupedAppSidebar,
    });
    state.sidebarNavLayoutDraft = captureNavLayout(view.primaryGroups, view.moreItems);
    state.isSidebarNavEditing = true;
    if (state.useGroupedAppSidebar) {
        state.isShowingMoreNav = true;
    }
}

export function discardSidebarNavEdit(state: AppShellState): void {
    state.isSidebarNavEditing = false;
    state.sidebarNavLayoutDraft = null;
}

export function saveSidebarNavLayout(state: AppShellState): void {
    if (state.isSidebarCollapsed || !state.isSidebarNavEditing) {
        return;
    }
    const layout = state.sidebarNavLayoutDraft;
    if (!layout) {
        discardSidebarNavEdit(state);
        return;
    }
    saveAppSidebarNavLayout(layout);
    state.sidebarNavLayoutSaved = cloneNavLayout(layout);
    discardSidebarNavEdit(state);
    ToastUtils.success(t("app.nav_layout_saved"));
}

export function onSidebarNavReorder(state: AppShellState, op: any): void {
    if (!state.isSidebarNavEditing || state.isSidebarCollapsed || !op) {
        return;
    }
    const preservePlacement = !state.useGroupedAppSidebar;
    const items = state.rawVisibleNavItems;
    let layout = state.sidebarNavLayoutDraft;
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
    state.sidebarNavLayoutDraft = layout;
}

export function onMoreNavToggle(state: AppShellState): void {
    if (state.isSidebarCollapsed) {
        void navigate({ name: "about" });
        return;
    }
    state.isShowingMoreNav = !state.isShowingMoreNav;
}

export function setSidebarCollapsed(state: AppShellState, collapsed: boolean): void {
    state.isSidebarCollapsed = collapsed;
    saveFeatureSidebarCollapsed("app", collapsed);
    if (collapsed) {
        discardSidebarNavEdit(state);
    }
}

export function toggleSidebarCollapsed(state: AppShellState): void {
    setSidebarCollapsed(state, !state.isSidebarCollapsed);
}

export function openCommandPalette(state: AppShellState): void {
    void state.hosts.commandPalette?.open();
}

// Counters
// ------------------------------------------------------------------
export function updateUnreadConversationsCount(state: AppShellState): void {
    if (state.unreadCountTimeout) {
        clearTimeout(state.unreadCountTimeout);
    }
    state.unreadCountTimeout = setTimeout(async () => {
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
}

export function updateRelayChatUnreadCount(state: AppShellState): void {
    if (!state.rrcEnabled) {
        GlobalState.relayChatUnreadCount = 0;
        return;
    }
    if (state.relayUnreadCountTimeout) {
        clearTimeout(state.relayUnreadCountTimeout);
    }
    state.relayUnreadCountTimeout = setTimeout(async () => {
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
}

export function handleActiveSessionsUpdated(state: AppShellState, json: any): void {
    const count = Number(json?.count ?? 0);
    const warningEnabled =
        json?.warning_enabled !== undefined
            ? json.warning_enabled !== false
            : state.config?.multi_session_warning_enabled !== false;
    const decision = shouldShowMultiSessionToast(
        count,
        warningEnabled,
        state.multiSessionWarningActive,
        json?.sessions
    );
    state.multiSessionWarningActive = decision.warned;
    if (decision.show) {
        ToastUtils.warning(t("app.multi_session_warning", { count }));
    }
}
