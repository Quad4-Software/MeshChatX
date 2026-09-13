// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerContactsFeature(): void {
    registerFeature({
        id: "contacts",
        routes: [
            {
                name: "contacts",
                path: "/contacts",
                mount: "svelte",
                load: () => import("./ContactsPage.svelte"),
            },
        ],
    });
}
