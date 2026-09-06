// SPDX-License-Identifier: 0BSD

/**
 * GlobalEmitter bridges and keyboard shortcut dispatch for the shell.
 */

import GlobalEmitter from "../../../js/GlobalEmitter.js";
import { navigate, router } from "../../../shell/hashRouter.js";
import { handleProtocolLink } from "./appShellLinks.js";
import { getBlockedDestinations, maybeShowChannelPrompt } from "./appShellConfig.js";
import { toggleSidebarCollapsed } from "./appShellNav.js";
import { syncPropagationNode } from "./appShellPropagation.js";
import type { AppShellState } from "./appShellState.svelte.js";

// Emitter bridges
// ------------------------------------------------------------------
export function onSyncPropagationNodeShell(state: AppShellState): void {
    void syncPropagationNode(state);
}

export function onKeyboardShortcutShell(state: AppShellState, action: string): void {
    handleKeyboardShortcut(state, action);
}

export function onBlockStatusChangedShell(state: AppShellState): void {
    void getBlockedDestinations(state);
}

export function onShowChangelogShell(state: AppShellState): void {
    void state.hosts.changelog?.show();
}

export function onShowTutorialShell(state: AppShellState): void {
    state.skipChangelogAfterTutorial = false;
    state.hosts.tutorial?.show();
}

export function onTutorialFinishedShell(state: AppShellState): void {
    state.skipChangelogAfterTutorial = true;
}

export function onChangelogClosedShell(state: AppShellState): void {
    maybeShowChannelPrompt(state);
}

export async function composeNewMessage(_state: AppShellState): Promise<void> {
    await navigate({ name: "messages" });
    GlobalEmitter.emit("compose-new-message");
}

export function onAppNameClick(state: AppShellState, middle?: HTMLElement | null): void {
    // user may be on mobile and unable to scroll back to the sidebar
    middle?.scrollTo({ top: 0, left: 0, behavior: "smooth" });
    void navigate("/messages");
}

export function onAndroidIntentUri(state: AppShellState, event: CustomEvent): void {
    const uri = event?.detail;
    if (typeof uri !== "string" || uri.trim() === "") {
        return;
    }
    handleProtocolLink(router, uri.trim());
}

export function handleKeyboardShortcut(state: AppShellState, action: string): void {
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
            void composeNewMessage(state);
            break;
        case "sync_messages":
            void syncPropagationNode(state);
            break;
        case "command_palette":
            // Command palette owns its shortcut. Emitted here for parity.
            break;
        case "toggle_sidebar":
            toggleSidebarCollapsed(state);
            break;
    }
}
