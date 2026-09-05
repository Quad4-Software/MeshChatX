// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export { default as RelayChatPage } from "./components/RelayChatPage.svelte";
export { default as RelayHostModerationPage } from "./components/RelayHostModerationPage.svelte";
export { default as RelayMessageEntry } from "./components/RelayMessageEntry.svelte";
export { default as RelayMessageListVirtual } from "./components/RelayMessageListVirtual.svelte";

/**
 * Reticulum Relay Chat (RRC) feature: Svelte RelayChatPage.
 * Route meta is supported by routeRegistry (popoutType / isPopout).
 */
export function registerRelayChatFeature() {
    registerFeature({
        id: "relay-chat",
        routes: [
            {
                name: "relay-chat",
                path: "/relay-chat",
                mount: "svelte",
                load: () => import("./components/RelayChatPage.svelte"),
            },
            {
                name: "relay-chat-popout",
                path: "/popout/relay-chat/:hubHash/:room?",
                mount: "svelte",
                load: () => import("./components/RelayChatPage.svelte"),
                meta: { popoutType: "relay", isPopout: true },
            },
        ],
    });
}
