// SPDX-License-Identifier: 0BSD

/**
 * Values and types shared by the app shell state class and its helper modules.
 */

export const IDENTITY_SAVE_DEBOUNCE_MS = 500;
export const PROPAGATION_SYNC_TOAST_KEY = "propagation-sync-status";
export const PROPAGATION_SYNC_POLL_TIMEOUT_MS = 120000;
export const ACTIVE_SYNC_STATES = [
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
    channelPrompt?: { show: (info: ShellAppInfo) => boolean } | null;
    androidStorage?: { showUpgrade: () => boolean } | null;
    postInstall?: { showNext: () => Promise<boolean> } | null;
    commandPalette?: { open: () => void | Promise<void> } | null;
}

export type Timer = ReturnType<typeof setTimeout> | null;
export type Interval = ReturnType<typeof setInterval> | null;

/** Backend HTTP client installed on window by main.ts. */
export function apiClient() {
    return (window as unknown as { api: any }).api;
}

/** Electron preload bridge, absent in the browser and on Android. */
export function electronBridge() {
    return (window as unknown as { electron?: Record<string, any> }).electron;
}
