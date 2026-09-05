// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";

export function registerLicensesFeature() {
    registerFeature({
        id: "licenses",
        routes: [
            {
                name: "licenses",
                path: "/licenses",
                mount: "svelte",
                load: () => import("./LicensesPage.svelte"),
            },
        ],
    });
}
