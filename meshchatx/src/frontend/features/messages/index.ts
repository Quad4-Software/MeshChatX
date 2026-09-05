// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Messages feature: Svelte MessagesPage and ConversationViewer.
 * Route meta is supported by routeRegistry (popoutType / isPopout / stableKey).
 */
export function registerMessagesFeature() {
    registerFeature({
        id: "messages",
        routes: [
            {
                name: "messages",
                path: "/messages/:destinationHash?",
                mount: "svelte",
                load: () => import("./MessagesPage.svelte"),
                meta: { stableKey: true },
            },
            {
                name: "messages-popout",
                path: "/popout/messages/:destinationHash?",
                mount: "svelte",
                load: () => import("./MessagesPage.svelte"),
                meta: { popoutType: "conversation", isPopout: true },
            },
        ],
    });
}
