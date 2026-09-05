// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export { default as MapBrowser } from "./components/MapBrowser.svelte";
export { default as MapPage } from "./MapPage.svelte";
export { default as MiniChat } from "./components/MiniChat.svelte";
export { default as MapLoadingOverlay } from "./components/MapLoadingOverlay.svelte";
export { default as MapMobileNoteModal } from "./components/MapMobileNoteModal.svelte";

export function registerMapFeature(): void {
    registerFeature({
        id: "map",
        routes: [
            {
                name: "map",
                path: "/map",
                mount: "svelte",
                meta: { keepAlive: true },
                load: () => import("./components/MapBrowser.svelte"),
            },
            {
                name: "map-popout",
                path: "/popout/map",
                mount: "svelte",
                meta: { popoutType: "map", isPopout: true },
                load: () => import("./MapPage.svelte"),
            },
        ],
    });
}
