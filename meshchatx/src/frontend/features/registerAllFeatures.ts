// SPDX-License-Identifier: 0BSD

import { registerAboutFeature } from "./about/index.js";
import { registerAppShellFeature } from "./app-shell/index.js";
import { registerAuthFeature } from "./auth/index.js";
import { registerBotsFeature } from "./bots/index.js";
import { registerCallFeature } from "./call/index.js";
import { registerArchivesFeature } from "./archives/index.js";
import { registerBlockedFeature } from "./blocked/index.js";
import { registerContactsFeature } from "./contacts/index.js";
import { registerDebugLogsFeature } from "./debug-logs/index.js";
import { registerDocsFeature } from "./docs/index.js";
import { registerFilesyncFeature } from "./filesync/index.js";
import { registerForwarderFeature } from "./forwarder/index.js";
import { registerInterfacesFeature } from "./interfaces/index.js";
import { registerLicensesFeature } from "./licenses/index.js";
import { registerMapFeature } from "./map/index.js";
import { registerMessageBlocklistFeature } from "./message-blocklist/index.js";
import { registerMessagesFeature } from "./messages/index.js";
import { registerMicronEditorFeature } from "./micron-editor/index.js";
import { registerNetworkVisualiserFeature } from "./network-visualiser/index.js";
import { registerNomadNetworkFeature } from "./nomadnetwork/index.js";
import { registerPageNodesFeature } from "./page-nodes/index.js";
import { registerPaperMessageFeature } from "./paper-message/index.js";
import { registerPingFeature } from "./ping/index.js";
import { registerPluginsFeature } from "./plugins/index.js";
import { registerProfileFeature } from "./profile/index.js";
import { registerPropagationNodesFeature } from "./propagation-nodes/index.js";
import { registerRelayChatFeature } from "./relay-chat/index.js";
import { registerRepositoryServerFeature } from "./repository-server/index.js";
import { registerReticulumConfigEditorFeature } from "./reticulum-config-editor/index.js";
import { registerRncpFeature } from "./rncp/index.js";
import { registerRNodeFlasherFeature } from "./rnode-flasher/index.js";
import { registerRnpathFeature } from "./rnpath/index.js";
import { registerRnpathTraceFeature } from "./rnpath-trace/index.js";
import { registerRnprobeFeature } from "./rnprobe/index.js";
import { registerRnshFeature } from "./rnsh/index.js";
import { registerRnxFeature } from "./rnx/index.js";
import { registerRNStatusFeature } from "./rnstatus/index.js";
import { registerSettingsFeature } from "./settings/index.js";
import { registerSieveFiltersFeature } from "./sieve-filters/index.js";
import { registerToolsFeature } from "./tools/index.js";
import { registerTutorialFeature } from "./tutorial/index.js";
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
    registerAboutFeature();
    registerAppShellFeature();
    registerAuthFeature();
    registerBotsFeature();
    registerCallFeature();
    registerArchivesFeature();
    registerBlockedFeature();
    registerContactsFeature();
    registerDebugLogsFeature();
    registerDocsFeature();
    registerFilesyncFeature();
    registerForwarderFeature();
    registerInterfacesFeature();
    registerLicensesFeature();
    registerMapFeature();
    registerMessageBlocklistFeature();
    registerMessagesFeature();
    registerMicronEditorFeature();
    registerNetworkVisualiserFeature();
    registerNomadNetworkFeature();
    registerPageNodesFeature();
    registerPaperMessageFeature();
    registerPingFeature();
    registerPluginsFeature();
    registerProfileFeature();
    registerPropagationNodesFeature();
    registerRelayChatFeature();
    registerRepositoryServerFeature();
    registerReticulumConfigEditorFeature();
    registerRncpFeature();
    registerRNodeFlasherFeature();
    registerRnpathFeature();
    registerRnpathTraceFeature();
    registerRnprobeFeature();
    registerRnshFeature();
    registerRnxFeature();
    registerRNStatusFeature();
    registerSettingsFeature();
    registerSieveFiltersFeature();
    registerToolsFeature();
    registerTutorialFeature();
    registerTranslatorFeature();
}
