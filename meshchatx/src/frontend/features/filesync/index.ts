// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerFilesyncFeature(): void {
    registerFeature({
        id: "filesync",
        routes: [
            {
                name: "rns-filesync",
                path: "/rns-filesync",
                mount: "svelte",
                load: () => import("./RnsFilesyncPage.svelte"),
            },
        ],
    });
}
