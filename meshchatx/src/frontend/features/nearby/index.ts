// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export { default as NearbyPage } from "./NearbyPage.svelte";

export function registerNearbyFeature(): void {
    registerFeature({
        id: "nearby",
        routes: [
            {
                name: "nearby",
                path: "/tools/nearby",
                mount: "svelte",
                load: () => import("./NearbyPage.svelte"),
            },
        ],
    });
}
