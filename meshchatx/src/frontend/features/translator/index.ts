// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

/**
 * Offline text translation UI backed by locally imported Bergamot packs.
 */
export function registerTranslatorFeature(): void {
    registerFeature({
        id: "translator",
        routes: [
            {
                name: "translator",
                path: "/translator",
                mount: "svelte",
                load: () => import("./TranslatorPage.svelte"),
            },
        ],
    });
}
