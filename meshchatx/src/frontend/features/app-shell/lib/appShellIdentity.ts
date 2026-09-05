// SPDX-License-Identifier: 0BSD

/**
 * Identity switch application plus identity settings: display name, announce
 * interval, announce, LXMF URI, and QR.
 */

import QRCode from "qrcode";
import GlobalState, { mergeGlobalConfig } from "../../../js/GlobalState.js";
import GlobalEmitter from "../../../js/GlobalEmitter.js";
import ToastUtils from "../../../js/ToastUtils.js";
import {
    showDatabaseHealthIssuesToastIfNeeded,
    resetDatabaseHealthWarningState,
} from "../../../js/databaseHealthWarning.js";
import { t } from "../../../js/i18n.js";
import { fetchCsrfToken } from "../../../js/csrfToken.js";
import {
    loadFeatureSidebarCollapsed,
    saveFeatureSidebarCollapsed,
    clearMessagePanes,
} from "../../../js/browserLayoutStore.js";
import { micronStorage } from "../../../js/MicronStorage.js";
import { navigate, router, subscribe as subscribeRoute } from "../../../shell/hashRouter.js";
import { IDENTITY_SAVE_DEBOUNCE_MS, apiClient } from "./appShellShared.js";
import { getAppInfo, getBlockedDestinations, getConfig, updateConfig } from "./appShellConfig.js";
import { updateRelayChatUnreadCount, updateUnreadConversationsCount } from "./appShellNav.js";
import { updateRingtonePlayer, updateTelephoneStatus } from "./appShellTelephony.js";
import type { AppShellState } from "./appShellState.svelte.js";

// Identity switch
// ------------------------------------------------------------------
export function onIdentitySwitchingStartShell(state: AppShellState): void {
    state.isSwitchingIdentity = true;
    setTimeout(() => {
        if (state.isSwitchingIdentity) {
            state.isSwitchingIdentity = false;
        }
    }, 45000);
}

export function onIdentitySwitchingAbortShell(state: AppShellState): void {
    state.isSwitchingIdentity = false;
}

export function onIdentitySwitchedApplyShell(state: AppShellState, payload: unknown): void {
    applyIdentitySwitched(state, payload).catch(() => {});
}

export async function applyIdentitySwitched(state: AppShellState, json: any): Promise<void> {
    const hash = json?.identity_hash;
    const endSwitchUi = (aborted = false) => {
        state.isSwitchingIdentity = false;
        if (aborted) {
            GlobalEmitter.emit("identity-switching-abort");
        }
    };
    if (hash == null || hash === "") {
        endSwitchUi(true);
        return;
    }
    const now = Date.now();
    if (state.identitySwitchDedupeHash === hash && now - state.identitySwitchDedupeAt < 10000) {
        endSwitchUi(false);
        return;
    }
    state.identitySwitchDedupeHash = hash;
    state.identitySwitchDedupeAt = now;

    try {
        if (json?.requires_reauth && GlobalState.authEnabled) {
            ToastUtils.info(t("identities.sign_in_after_switch"));
            GlobalState.authenticated = false;
            try {
                await fetchCsrfToken(apiClient());
            } catch {
                // Next mutating request will refresh CSRF when auth completes.
            }
            if (!state.isAuthRoute) {
                void navigate("/auth");
            }
            endSwitchUi(true);
            return;
        }

        ToastUtils.success(t("identities.switched"));
        resetDatabaseHealthWarningState();
        if (state.wsLiveSyncHandle) {
            state.wsLiveSyncHandle.clearCursor();
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

        await getConfig(state);
        await updateRingtonePlayer(state);
        await getAppInfo(state);
        await getBlockedDestinations(state);
        void updateTelephoneStatus(state);
        updateUnreadConversationsCount(state);
        updateRelayChatUnreadCount(state);

        GlobalEmitter.emit("identity-switched", json);
    } catch (e) {
        console.error("applyIdentitySwitched failed", e);
        ToastUtils.error(t("identities.failed_switch"));
        endSwitchUi(true);
        return;
    }
    endSwitchUi(false);
}

// Identity footer
// ------------------------------------------------------------------
export function onDisplayNameUpdate(state: AppShellState, value: string): void {
    state.displayName = value;
    scheduleIdentitySave(state);
}

export function scheduleIdentitySave(state: AppShellState): void {
    if (state.identitySaveTimer != null) {
        clearTimeout(state.identitySaveTimer);
    }
    state.identitySaveTimer = setTimeout(() => {
        state.identitySaveTimer = null;
        void saveIdentitySettings(state);
    }, IDENTITY_SAVE_DEBOUNCE_MS);
}

export function flushIdentitySave(state: AppShellState): void {
    if (state.identitySaveTimer != null) {
        clearTimeout(state.identitySaveTimer);
        state.identitySaveTimer = null;
    }
    void saveIdentitySettings(state);
}

export async function saveIdentitySettings(state: AppShellState): Promise<void> {
    const nextName = state.displayName;
    const currentName = state.config?.display_name ?? "";
    if (String(nextName) === String(currentName)) {
        return;
    }
    await updateConfig(state, { display_name: nextName }, "display_name_placeholder");
}

export async function onAnnounceIntervalChange(state: AppShellState, seconds: number): Promise<void> {
    if (!state.config) {
        return;
    }
    state.config = { ...state.config, auto_announce_interval_seconds: seconds };
    await updateConfig(state, { auto_announce_interval_seconds: seconds }, "announce_interval");
}

export async function sendAnnounce(state: AppShellState): Promise<void> {
    try {
        await apiClient().get("/api/v1/announce");
        ToastUtils.success(t("app.announce_sent"));
    } catch (e) {
        ToastUtils.error(t("app.failed_announce"));
        console.log(e);
    }
    await getConfig(state);
}

export async function copyValue(state: AppShellState, value: string, label: string): Promise<void> {
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

export function getMyIdentityUri(state: AppShellState): string | null {
    if (!state.config?.lxmf_address_hash) {
        return null;
    }
    const publicKey = state.config?.identity_public_key;
    return publicKey
        ? `lxma://${state.config.lxmf_address_hash}:${publicKey}`
        : `lxmf://${state.config.lxmf_address_hash}`;
}

export async function openLxmfQr(state: AppShellState): Promise<void> {
    if (!state.config?.lxmf_address_hash) {
        return;
    }
    try {
        const uri = getMyIdentityUri(state) as string;
        state.lxmfQrDataUrl = await QRCode.toDataURL(uri, { margin: 1, scale: 6 });
        state.showLxmfQr = true;
    } catch {
        ToastUtils.error(t("common.error"));
    }
}

export async function copyIdentityUri(state: AppShellState): Promise<void> {
    const uri = getMyIdentityUri(state);
    if (!uri) {
        return;
    }
    await copyValue(state, uri, "Identity URI");
}
