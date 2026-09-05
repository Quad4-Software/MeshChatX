// SPDX-License-Identifier: 0BSD

import { registerBlockedFeature } from "./blocked/index.js";
import { registerContactsFeature } from "./contacts/index.js";
import { registerDebugLogsFeature } from "./debug-logs/index.js";
import { registerForwarderFeature } from "./forwarder/index.js";
import { registerLicensesFeature } from "./licenses/index.js";
import { registerMessagesFeature } from "./messages/index.js";
import { registerPingFeature } from "./ping/index.js";
import { registerToolsFeature } from "./tools/index.js";

let featuresRegistered = false;

/**
 * Reset for tests.
 */
export function resetAllFeaturesForTests(): void {
    featuresRegistered = false;
}

/**
 * Register feature modules that opt into routeRegistry.
 * Call once at boot after registerCoreContributions.
 * Lives under features/ so kernel js/ stays free of feature imports.
 */
export function registerAllFeatures(): void {
    if (featuresRegistered) {
        return;
    }
    featuresRegistered = true;
    registerBlockedFeature();
    registerContactsFeature();
    registerDebugLogsFeature();
    registerForwarderFeature();
    registerLicensesFeature();
    registerMessagesFeature();
    registerPingFeature();
    registerToolsFeature();
}
