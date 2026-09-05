// SPDX-License-Identifier: 0BSD

import { registerBlockedFeature } from "./blocked/index.js";
import { registerContactsFeature } from "./contacts/index.js";
import { registerDebugLogsFeature } from "./debug-logs/index.js";
import { registerForwarderFeature } from "./forwarder/index.js";
import { registerLicensesFeature } from "./licenses/index.js";
import { registerMessageBlocklistFeature } from "./message-blocklist/index.js";
import { registerMessagesFeature } from "./messages/index.js";
import { registerPaperMessageFeature } from "./paper-message/index.js";
import { registerPingFeature } from "./ping/index.js";
import { registerReticulumConfigEditorFeature } from "./reticulum-config-editor/index.js";
import { registerRnpathFeature } from "./rnpath/index.js";
import { registerRnpathTraceFeature } from "./rnpath-trace/index.js";
import { registerRnprobeFeature } from "./rnprobe/index.js";
import { registerRNStatusFeature } from "./rnstatus/index.js";
import { registerSieveFiltersFeature } from "./sieve-filters/index.js";
import { registerToolsFeature } from "./tools/index.js";
import { registerTranslatorFeature } from "./translator/index.js";

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
    registerMessageBlocklistFeature();
    registerMessagesFeature();
    registerPaperMessageFeature();
    registerPingFeature();
    registerReticulumConfigEditorFeature();
    registerRnpathFeature();
    registerRnpathTraceFeature();
    registerRnprobeFeature();
    registerRNStatusFeature();
    registerSieveFiltersFeature();
    registerToolsFeature();
    registerTranslatorFeature();
}
