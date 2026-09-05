// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { existsSync } from "fs";
import { join } from "path";
import { clearRoutes, listRoutes } from "../../meshchatx/src/frontend/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "../../meshchatx/src/frontend/js/registries/featureRegistry.js";
import { registerBlockedFeature } from "../../meshchatx/src/frontend/features/blocked/index.js";
import { registerContactsFeature } from "../../meshchatx/src/frontend/features/contacts/index.js";
import { registerDebugLogsFeature } from "../../meshchatx/src/frontend/features/debug-logs/index.js";
import { registerForwarderFeature } from "../../meshchatx/src/frontend/features/forwarder/index.js";
import { registerLicensesFeature } from "../../meshchatx/src/frontend/features/licenses/index.js";
import { registerPingFeature } from "../../meshchatx/src/frontend/features/ping/index.js";
import { registerToolsFeature } from "../../meshchatx/src/frontend/features/tools/index.js";
import { filterBlockedIdentities } from "../../meshchatx/src/frontend/features/blocked/lib/blockedList.js";

const repoRoot = process.cwd();

/**
 * Conveyor ownership for feature modules that opt into registerFeature.
 * Expand this list as pages migrate off the hardcoded main.js table.
 */
const FEATURE_MODULE_OWNERS = [
    {
        id: "blocked",
        register: registerBlockedFeature,
        required_paths: [
            "meshchatx/src/frontend/features/blocked/index.js",
            "meshchatx/src/frontend/features/blocked/BlockedPage.svelte",
            "meshchatx/src/frontend/features/blocked/lib/blockedList.js",
        ],
        route_name: "blocked",
        mount: "svelte",
    },
    {
        id: "contacts",
        register: registerContactsFeature,
        required_paths: [
            "meshchatx/src/frontend/features/contacts/index.js",
            "meshchatx/src/frontend/features/contacts/ContactsPage.svelte",
            "meshchatx/src/frontend/features/contacts/lib/contactUri.js",
            "meshchatx/src/frontend/features/contacts/lib/contactsActions.js",
            "meshchatx/src/frontend/features/contacts/components/ContactListRow.svelte",
        ],
        route_name: "contacts",
        mount: "svelte",
    },
    {
        id: "debug-logs",
        register: registerDebugLogsFeature,
        required_paths: [
            "meshchatx/src/frontend/features/debug-logs/index.js",
            "meshchatx/src/frontend/features/debug-logs/DebugLogsPage.svelte",
            "meshchatx/src/frontend/features/debug-logs/lib/debugFormat.js",
        ],
        route_name: "debug-logs",
        mount: "svelte",
    },
    {
        id: "forwarder",
        register: registerForwarderFeature,
        required_paths: [
            "meshchatx/src/frontend/features/forwarder/index.js",
            "meshchatx/src/frontend/features/forwarder/ForwarderPage.svelte",
            "meshchatx/src/frontend/features/forwarder/lib/forwarderHash.js",
        ],
        route_name: "forwarder",
        mount: "svelte",
    },
    {
        id: "licenses",
        register: registerLicensesFeature,
        required_paths: [
            "meshchatx/src/frontend/features/licenses/index.js",
            "meshchatx/src/frontend/features/licenses/LicensesPage.svelte",
            "meshchatx/src/frontend/features/licenses/lib/licenseFilter.js",
        ],
        route_name: "licenses",
        mount: "svelte",
    },
    {
        id: "ping",
        register: registerPingFeature,
        required_paths: [
            "meshchatx/src/frontend/features/ping/index.js",
            "meshchatx/src/frontend/features/ping/PingPage.svelte",
            "meshchatx/src/frontend/features/ping/lib/pingFormat.js",
        ],
        route_name: "ping",
        mount: "svelte",
    },
    {
        id: "tools",
        register: registerToolsFeature,
        required_paths: [
            "meshchatx/src/frontend/features/tools/index.js",
            "meshchatx/src/frontend/features/tools/ToolsPage.svelte",
            "meshchatx/src/frontend/features/tools/ToolsSection.svelte",
            "meshchatx/src/frontend/features/tools/lib/toolsList.js",
        ],
        route_name: "tools",
        mount: "svelte",
    },
];

describe("feature module conveyor ownership", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("each owned feature has required files and registers once", () => {
        for (const feature of FEATURE_MODULE_OWNERS) {
            for (const rel of feature.required_paths) {
                expect(existsSync(join(repoRoot, rel)), `missing ${rel}`).toBe(true);
            }
            feature.register();
            expect(listFeatureIds()).toContain(feature.id);
            const route = listRoutes().find((r) => r.name === feature.route_name);
            expect(route).toBeTruthy();
            expect(route.mount).toBe(feature.mount);
            expect(typeof route.load).toBe("function");
        }
    });

    it("blockedList filter helpers stay pure", () => {
        const list = filterBlockedIdentities(
            [
                {
                    identity_hash: "a",
                    display_name: "Ada",
                    is_node: false,
                    is_rns_blackholed: false,
                    blocked_destinations: [{ destination_hash: "a", created_at: "2026-01-02" }],
                },
                {
                    identity_hash: "b",
                    display_name: "Bob",
                    is_node: true,
                    is_rns_blackholed: false,
                    blocked_destinations: [{ destination_hash: "b", created_at: "2026-01-01" }],
                },
            ],
            { typeFilter: "node", dateSort: "newest" }
        );
        expect(list).toHaveLength(1);
        expect(list[0].identity_hash).toBe("b");
    });
});
