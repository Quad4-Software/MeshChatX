// SPDX-License-Identifier: 0BSD

import { registerFeature } from "../../js/registries/featureRegistry.js";
import {
    INTERFACES_FEATURE_ID,
    INTERFACES_ROUTE_NAME,
    INTERFACES_ROUTE_PATH,
    INTERFACES_ADD_ROUTE_NAME,
    INTERFACES_ADD_ROUTE_PATH,
    INTERFACES_EDIT_ROUTE_NAME,
    INTERFACES_EDIT_ROUTE_PATH,
} from "./lib/constants.js";

/**
 * Register Interfaces feature with main, add, and edit routes
 */
export function registerInterfacesFeature(): void {
    registerFeature({
        id: INTERFACES_FEATURE_ID,
        routes: [
            {
                name: INTERFACES_ROUTE_NAME,
                path: INTERFACES_ROUTE_PATH,
                mount: "svelte",
                load: () => import("./InterfacesPage.svelte"),
            },
            {
                name: INTERFACES_ADD_ROUTE_NAME,
                path: INTERFACES_ADD_ROUTE_PATH,
                mount: "svelte",
                load: () => import("./AddInterfacePage.svelte"),
            },
            {
                name: INTERFACES_EDIT_ROUTE_NAME,
                path: INTERFACES_EDIT_ROUTE_PATH,
                mount: "svelte",
                load: () => import("./AddInterfacePage.svelte"),
            },
        ],
    });
}
