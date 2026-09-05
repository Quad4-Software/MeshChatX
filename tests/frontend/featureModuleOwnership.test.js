// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { existsSync } from "fs";
import { join } from "path";
import { clearRoutes, listRoutes } from "../../meshchatx/src/frontend/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "../../meshchatx/src/frontend/js/registries/featureRegistry.js";
import { registerBlockedFeature } from "../../meshchatx/src/frontend/features/blocked/index.ts";
import { registerContactsFeature } from "../../meshchatx/src/frontend/features/contacts/index.ts";
import { registerDebugLogsFeature } from "../../meshchatx/src/frontend/features/debug-logs/index.ts";
import { registerForwarderFeature } from "../../meshchatx/src/frontend/features/forwarder/index.ts";
import { registerLicensesFeature } from "../../meshchatx/src/frontend/features/licenses/index.ts";
import { registerMessageBlocklistFeature } from "../../meshchatx/src/frontend/features/message-blocklist/index.ts";
import { registerMessagesFeature } from "../../meshchatx/src/frontend/features/messages/index.ts";
import { registerPaperMessageFeature } from "../../meshchatx/src/frontend/features/paper-message/index.ts";
import { registerPingFeature } from "../../meshchatx/src/frontend/features/ping/index.ts";
import { registerReticulumConfigEditorFeature } from "../../meshchatx/src/frontend/features/reticulum-config-editor/index.ts";
import { registerRnpathFeature } from "../../meshchatx/src/frontend/features/rnpath/index.ts";
import { registerRnpathTraceFeature } from "../../meshchatx/src/frontend/features/rnpath-trace/index.ts";
import { registerRnprobeFeature } from "../../meshchatx/src/frontend/features/rnprobe/index.ts";
import { registerRNStatusFeature } from "../../meshchatx/src/frontend/features/rnstatus/index.ts";
import { registerSieveFiltersFeature } from "../../meshchatx/src/frontend/features/sieve-filters/index.ts";
import { registerToolsFeature } from "../../meshchatx/src/frontend/features/tools/index.ts";
import { registerTranslatorFeature } from "../../meshchatx/src/frontend/features/translator/index.ts";
import { filterBlockedIdentities } from "../../meshchatx/src/frontend/features/blocked/lib/blockedList.ts";

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
            "meshchatx/src/frontend/features/blocked/index.ts",
            "meshchatx/src/frontend/features/blocked/BlockedPage.svelte",
            "meshchatx/src/frontend/features/blocked/lib/blockedList.ts",
        ],
        route_name: "blocked",
        mount: "svelte",
    },
    {
        id: "contacts",
        register: registerContactsFeature,
        required_paths: [
            "meshchatx/src/frontend/features/contacts/index.ts",
            "meshchatx/src/frontend/features/contacts/ContactsPage.svelte",
            "meshchatx/src/frontend/features/contacts/lib/contactUri.ts",
            "meshchatx/src/frontend/features/contacts/lib/contactsActions.ts",
            "meshchatx/src/frontend/features/contacts/components/ContactListRow.svelte",
        ],
        route_name: "contacts",
        mount: "svelte",
    },
    {
        id: "debug-logs",
        register: registerDebugLogsFeature,
        required_paths: [
            "meshchatx/src/frontend/features/debug-logs/index.ts",
            "meshchatx/src/frontend/features/debug-logs/DebugLogsPage.svelte",
            "meshchatx/src/frontend/features/debug-logs/lib/debugFormat.ts",
        ],
        route_name: "debug-logs",
        mount: "svelte",
    },
    {
        id: "forwarder",
        register: registerForwarderFeature,
        required_paths: [
            "meshchatx/src/frontend/features/forwarder/index.ts",
            "meshchatx/src/frontend/features/forwarder/ForwarderPage.svelte",
            "meshchatx/src/frontend/features/forwarder/lib/forwarderHash.ts",
        ],
        route_name: "forwarder",
        mount: "svelte",
    },
    {
        id: "licenses",
        register: registerLicensesFeature,
        required_paths: [
            "meshchatx/src/frontend/features/licenses/index.ts",
            "meshchatx/src/frontend/features/licenses/LicensesPage.svelte",
            "meshchatx/src/frontend/features/licenses/lib/licenseFilter.ts",
        ],
        route_name: "licenses",
        mount: "svelte",
    },
    {
        id: "messages",
        register: registerMessagesFeature,
        required_paths: [
            "meshchatx/src/frontend/features/messages/index.ts",
            "meshchatx/src/frontend/features/messages/MessagesPage.svelte",
            "meshchatx/src/frontend/features/messages/lib/paneLayout.ts",
            "meshchatx/src/frontend/features/messages/lib/conversationListApply.ts",
            "meshchatx/src/frontend/features/messages/lib/conversationViewerMessages.ts",
            "meshchatx/src/frontend/features/messages/lib/conversationScroll.ts",
            "meshchatx/src/frontend/features/messages/lib/conversationPaperIngest.ts",
            "meshchatx/src/frontend/features/messages/lib/unreadDismiss.ts",
            "meshchatx/src/frontend/features/messages/components/MessagesSidebar.svelte",
            "meshchatx/src/frontend/features/messages/components/ConversationViewer.svelte",
            "meshchatx/src/frontend/features/messages/components/ConversationMessageEntry.svelte",
            "meshchatx/src/frontend/features/messages/components/ConversationMessageListVirtual.svelte",
            "meshchatx/src/frontend/features/messages/components/ConversationComposer.svelte",
        ],
        route_name: "messages",
        mount: "svelte",
    },
    {
        id: "ping",
        register: registerPingFeature,
        required_paths: [
            "meshchatx/src/frontend/features/ping/index.ts",
            "meshchatx/src/frontend/features/ping/PingPage.svelte",
            "meshchatx/src/frontend/features/ping/lib/pingFormat.ts",
        ],
        route_name: "ping",
        mount: "svelte",
    },
    {
        id: "message-blocklist",
        register: registerMessageBlocklistFeature,
        required_paths: [
            "meshchatx/src/frontend/features/message-blocklist/index.ts",
            "meshchatx/src/frontend/features/message-blocklist/MessageBlocklistPage.svelte",
            "meshchatx/src/frontend/features/message-blocklist/lib/blocklistRules.ts",
            "meshchatx/src/frontend/features/message-blocklist/lib/constants.ts",
        ],
        route_name: "message-blocklist",
        mount: "svelte",
    },
    {
        id: "sieve-filters",
        register: registerSieveFiltersFeature,
        required_paths: [
            "meshchatx/src/frontend/features/sieve-filters/index.ts",
            "meshchatx/src/frontend/features/sieve-filters/SieveFiltersPage.svelte",
            "meshchatx/src/frontend/features/sieve-filters/lib/sieveRules.ts",
            "meshchatx/src/frontend/features/sieve-filters/lib/constants.ts",
        ],
        route_name: "sieve-filters",
        mount: "svelte",
    },
    {
        id: "paper-message",
        register: registerPaperMessageFeature,
        required_paths: [
            "meshchatx/src/frontend/features/paper-message/index.ts",
            "meshchatx/src/frontend/features/paper-message/PaperMessagePage.svelte",
            "meshchatx/src/frontend/features/paper-message/lib/paperPrint.ts",
            "meshchatx/src/frontend/features/paper-message/lib/constants.ts",
        ],
        route_name: "paper-message",
        mount: "svelte",
    },
    {
        id: "reticulum-config-editor",
        register: registerReticulumConfigEditorFeature,
        required_paths: [
            "meshchatx/src/frontend/features/reticulum-config-editor/index.ts",
            "meshchatx/src/frontend/features/reticulum-config-editor/ReticulumConfigEditorPage.svelte",
            "meshchatx/src/frontend/features/reticulum-config-editor/lib/configFormat.ts",
            "meshchatx/src/frontend/features/reticulum-config-editor/lib/constants.ts",
        ],
        route_name: "reticulum-config-editor",
        mount: "svelte",
    },
    {
        id: "rnprobe",
        register: registerRnprobeFeature,
        required_paths: [
            "meshchatx/src/frontend/features/rnprobe/index.ts",
            "meshchatx/src/frontend/features/rnprobe/RNProbePage.svelte",
            "meshchatx/src/frontend/features/rnprobe/lib/probeFormat.ts",
            "meshchatx/src/frontend/features/rnprobe/lib/constants.ts",
        ],
        route_name: "rnprobe",
        mount: "svelte",
    },
    {
        id: "rnpath-trace",
        register: registerRnpathTraceFeature,
        required_paths: [
            "meshchatx/src/frontend/features/rnpath-trace/index.ts",
            "meshchatx/src/frontend/features/rnpath-trace/RNPathTracePage.svelte",
            "meshchatx/src/frontend/features/rnpath-trace/lib/traceFormat.ts",
            "meshchatx/src/frontend/features/rnpath-trace/lib/constants.ts",
        ],
        route_name: "rnpath-trace",
        mount: "svelte",
    },
    {
        id: "rnpath",
        register: registerRnpathFeature,
        required_paths: [
            "meshchatx/src/frontend/features/rnpath/index.ts",
            "meshchatx/src/frontend/features/rnpath/RNPathPage.svelte",
            "meshchatx/src/frontend/features/rnpath/lib/pathQuery.ts",
            "meshchatx/src/frontend/features/rnpath/lib/constants.ts",
        ],
        route_name: "rnpath",
        mount: "svelte",
    },
    {
        id: "rnstatus",
        register: registerRNStatusFeature,
        required_paths: [
            "meshchatx/src/frontend/features/rnstatus/index.ts",
            "meshchatx/src/frontend/features/rnstatus/RNStatusPage.svelte",
            "meshchatx/src/frontend/features/rnstatus/lib/statusFormat.ts",
            "meshchatx/src/frontend/features/rnstatus/lib/constants.ts",
        ],
        route_name: "rnstatus",
        mount: "svelte",
    },
    {
        id: "translator",
        register: registerTranslatorFeature,
        required_paths: [
            "meshchatx/src/frontend/features/translator/index.ts",
            "meshchatx/src/frontend/features/translator/TranslatorPage.svelte",
            "meshchatx/src/frontend/features/translator/lib/translatorEngine.ts",
            "meshchatx/src/frontend/features/translator/lib/constants.ts",
        ],
        route_name: "translator",
        mount: "svelte",
    },
    {
        id: "tools",
        register: registerToolsFeature,
        required_paths: [
            "meshchatx/src/frontend/features/tools/index.ts",
            "meshchatx/src/frontend/features/tools/ToolsPage.svelte",
            "meshchatx/src/frontend/features/tools/ToolsSection.svelte",
            "meshchatx/src/frontend/features/tools/lib/toolsList.ts",
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
