// SPDX-License-Identifier: 0BSD

/**
 * Config and app info fetch and persist, appearance, theme, locale, and the
 * one-shot startup prompts driven by app info.
 */

import LiveTransport from "../../../js/liveTransport.js";
import GlobalState, { mergeGlobalConfig } from "../../../js/GlobalState.js";
import NotificationUtils from "../../../js/NotificationUtils.js";
import { listOpenDestinationHashes, subscribeOpenDestinationHashes } from "../../../js/activeConversationStore.js";
import ToastUtils from "../../../js/ToastUtils.js";
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
import { normalizeUiLocaleCode, setLocale } from "../../../js/localeLoader.js";
import { patchServerConfig } from "../../../js/settings/settingsConfigService.js";
import {
    applyAppearanceTheme,
    resolveEffectiveTheme,
    shellCanvasBackgroundStyle,
    subscribeSystemTheme,
    systemPrefersDark,
} from "../../../theme/themeEngine.js";
import { apiClient } from "./appShellShared.js";
import type { ShellConfig } from "./appShellShared.js";
import { updateRingtonePlayer } from "./appShellTelephony.js";
import type { AppShellState } from "./appShellState.svelte.js";

export function onConfigUpdatedExternally(state: AppShellState, newConfig: ShellConfig): void {
    if (!newConfig || typeof newConfig !== "object") {
        return;
    }
    mergeGlobalConfig(newConfig);
    setConfig(state, newConfig);
}

// Config and app info
// ------------------------------------------------------------------
/**
 * Apply a config object and run the side effects the shell config watcher owns.
 */
export function setConfig(state: AppShellState, next: ShellConfig | null): void {
    state.config = next;
    if (next && typeof next.display_name === "string") {
        state.displayName = next.display_name;
    }
    if (next?.language) {
        void applyLocale(state, String(next.language));
    }
    if (next && next.custom_ringtone_enabled !== undefined) {
        void updateRingtonePlayer(state);
    }
    if (next) {
        applyAppearanceThemeFromConfig(state, next);
    }
    applyShellAppearance(state);
    NotificationUtils.syncAndroidNotificationContext(
        listOpenDestinationHashes(),
        Boolean(next?.do_not_disturb_enabled)
    );
}

export function applyAppearanceThemeFromConfig(state: AppShellState, config: ShellConfig): void {
    applyAppearanceTheme(config, { prefersDark: state.systemPrefersDark });
}

export function applyShellAppearance(state: AppShellState): void {
    if (typeof document === "undefined") {
        return;
    }
    const glassOn = state.config?.ui_glass_enabled !== false;
    document.documentElement.dataset.uiGlass = glassOn ? "1" : "0";
}

export async function getAppInfo(state: AppShellState): Promise<void> {
    try {
        const response = await apiClient().get("/api/v1/app/info");
        state.appInfo = response.data.app_info;

        showDatabaseHealthIssuesToastIfNeeded(state.appInfo?.database_health_issues, ToastUtils);

        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has("show-guide")) {
            state.hosts.tutorial?.show();
            urlParams.delete("show-guide");
            const newUrl = window.location.pathname + (urlParams.toString() ? `?${urlParams.toString()}` : "");
            window.history.replaceState({}, "", newUrl);
        } else if (urlParams.has("changelog")) {
            void state.hosts.changelog?.show();
            urlParams.delete("changelog");
            const newUrl = window.location.pathname + (urlParams.toString() ? `?${urlParams.toString()}` : "");
            window.history.replaceState({}, "", newUrl);
        } else if (!state.hasCheckedForModals) {
            state.hasCheckedForModals = true;
            if (state.appInfo && !state.appInfo.tutorial_seen) {
                state.hosts.tutorial?.show();
            } else if (maybeShowAndroidStorageUpgrade(state)) {
                // upgrade prompt for existing internal-storage installs
            } else if (await maybeShowPostInstallPrompt(state)) {
                // registry prompts for existing users (bump revision to re-show)
            } else if (
                state.appInfo &&
                !state.skipChangelogAfterTutorial &&
                state.appInfo.changelog_seen_version !== "999.999.999" &&
                state.appInfo.changelog_seen_version !== state.appInfo.version
            ) {
                void state.hosts.changelog?.show();
            } else if (maybeShowChannelPrompt(state)) {
                // Testing/Beta one-time prompt after changelog
            }
        }
    } catch (e) {
        console.log(e);
    }
}

export function maybeShowChannelPrompt(state: AppShellState): boolean {
    if (!shouldShowChannelPrompt(state.appInfo)) {
        return false;
    }
    const modal = state.hosts.channelPrompt;
    if (!modal || typeof modal.show !== "function" || !state.appInfo) {
        return false;
    }
    return modal.show(state.appInfo) === true;
}

export function maybeShowAndroidStorageUpgrade(state: AppShellState): boolean {
    const prompt = state.hosts.androidStorage;
    if (!prompt || typeof prompt.showUpgrade !== "function") {
        return false;
    }
    return prompt.showUpgrade();
}

export async function maybeShowPostInstallPrompt(state: AppShellState): Promise<boolean> {
    const host = state.hosts.postInstall;
    if (!host || typeof host.showNext !== "function") {
        return false;
    }
    return host.showNext();
}

export async function getConfig(state: AppShellState): Promise<void> {
    try {
        const response = await apiClient().get("/api/v1/config");
        const next = response.data?.config;
        if (next && typeof next === "object") {
            mergeGlobalConfig(next);
            setConfig(state, next);
        }
    } catch (e) {
        console.log(e);
    }
}

export function applyAnnouncedEvent(state: AppShellState, json: any): void {
    const identityHash = typeof json?.identity_hash === "string" ? json.identity_hash : "";
    if (identityHash && state.config?.identity_hash && identityHash !== state.config.identity_hash) {
        return;
    }
    const raw = json?.last_announced_at;
    if (raw != null && raw !== "") {
        const timestamp = Number(raw);
        if (state.config && Number.isFinite(timestamp)) {
            mergeGlobalConfig({ last_announced_at: timestamp });
            state.config = { ...state.config, last_announced_at: timestamp };
            return;
        }
    }
    void getConfig(state);
}

export async function getBlockedDestinations(state: AppShellState): Promise<void> {
    try {
        const response = await apiClient().get("/api/v1/blocked-destinations");
        GlobalState.blockedDestinations = response.data.blocked_destinations || [];
    } catch (e) {
        console.log("Failed to load blocked destinations:", e);
    }
}

export async function getKeyboardShortcuts(state: AppShellState): Promise<void> {
    LiveTransport.send(JSON.stringify({ type: "keyboard_shortcuts.get" }));
}

export async function updateConfig(
    state: AppShellState,
    config: Record<string, unknown>,
    label: string | null = null
): Promise<void> {
    try {
        const api = apiClient();
        if (api?.patch) {
            const next = await patchServerConfig(config, api);
            mergeGlobalConfig(next);
            setConfig(state, { ...(state.config || {}), ...next });
        } else {
            const requestId = `cfg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
            const ok = await new Promise<boolean>((resolve) => {
                const timer = setTimeout(() => {
                    if (state.pendingConfigSet?.requestId === requestId) {
                        state.pendingConfigSet = null;
                    }
                    resolve(false);
                }, 8000);
                state.pendingConfigSet = {
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
            setConfig(state, { ...(state.config || {}), ...config });
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
export function resolvePendingConfigSet(state: AppShellState, requestId: string): void {
    const pending = state.pendingConfigSet;
    if (pending && pending.requestId === requestId) {
        pending.resolve(true);
        state.pendingConfigSet = null;
    }
}

// Theme, locale, navigation helpers
// ------------------------------------------------------------------
export async function toggleTheme(state: AppShellState): Promise<void> {
    if (!state.config) {
        return;
    }
    const nextTheme = state.isDarkTheme ? "light" : "dark";
    state.config = { ...state.config, theme: nextTheme };
    await updateConfig(state, { theme: nextTheme }, "theme");
}

export async function applyLocale(state: AppShellState, langCode: string): Promise<void> {
    if (!langCode) {
        return;
    }
    const ok = await setLocale(null, langCode);
    if (!ok) {
        await setLocale(null, "en");
    }
    state.localeVersion += 1;
}

export async function onLanguageChange(state: AppShellState, langCode: string): Promise<void> {
    const code = normalizeUiLocaleCode(langCode);
    // Switch UI first so a slow or failed PATCH cannot leave the shell on English.
    await applyLocale(state, code);
    await updateConfig(state, { language: code }, "language");
}
