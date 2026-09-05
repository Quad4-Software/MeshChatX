// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerPingFeature() {
    registerFeature({
        id: "ping",
        routes: [
            {
                name: "ping",
                path: "/ping",
                mount: "svelte",
                load: () => import("./PingPage.svelte"),
            },
        ],
    });
}
