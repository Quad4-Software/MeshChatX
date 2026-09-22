// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export { default as NomadNetworkBrowser } from "./components/NomadNetworkBrowser.svelte";
export { default as NomadNetworkPage } from "./components/NomadNetworkPage.svelte";
export { default as NomadNetworkSidebar } from "./components/NomadNetworkSidebar.svelte";
export { default as NomadCrashTab } from "./components/NomadCrashTab.svelte";
export { default as NomadBrowserContextMenu } from "./components/NomadBrowserContextMenu.svelte";

/**
 * Nomad Network feature: Svelte NomadNetworkBrowser and NomadNetworkPage.
 * Route meta is supported by routeRegistry (popoutType / isPopout / keepAlive).
 */
export function registerNomadNetworkFeature() {
    registerFeature({
        id: "nomadnetwork",
        routes: [
            {
                name: "nomadnetwork",
                path: "/nomadnetwork/:destinationHash?",
                mount: "svelte",
                load: () => import("./components/NomadNetworkBrowser.svelte"),
                meta: { keepAlive: true },
            },
            {
                name: "nomadnetwork-popout",
                path: "/popout/nomadnetwork/:destinationHash?",
                mount: "svelte",
                load: () => import("./components/NomadNetworkPage.svelte"),
                meta: { popoutType: "nomad", isPopout: true },
            },
        ],
    });
}
