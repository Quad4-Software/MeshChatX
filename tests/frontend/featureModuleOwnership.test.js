// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { existsSync } from "fs";
import { join } from "path";
import { clearRoutes, listRoutes } from "../../meshchatx/src/frontend/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "../../meshchatx/src/frontend/js/registries/featureRegistry.js";
import { registerAboutFeature } from "../../meshchatx/src/frontend/features/about/index.ts";
import { registerAuthFeature } from "../../meshchatx/src/frontend/features/auth/index.ts";
import { registerCallFeature } from "../../meshchatx/src/frontend/features/call/index.ts";
import { registerArchivesFeature } from "../../meshchatx/src/frontend/features/archives/index.ts";
import { registerBlockedFeature } from "../../meshchatx/src/frontend/features/blocked/index.ts";
import { registerBotsFeature } from "../../meshchatx/src/frontend/features/bots/index.ts";
import { registerContactsFeature } from "../../meshchatx/src/frontend/features/contacts/index.ts";
import { registerDebugLogsFeature } from "../../meshchatx/src/frontend/features/debug-logs/index.ts";
import { registerDocsFeature } from "../../meshchatx/src/frontend/features/docs/index.ts";
import { registerFilesyncFeature } from "../../meshchatx/src/frontend/features/filesync/index.ts";
import { registerForwarderFeature } from "../../meshchatx/src/frontend/features/forwarder/index.ts";
import { registerInterfacesFeature } from "../../meshchatx/src/frontend/features/interfaces/index.ts";
import { registerLicensesFeature } from "../../meshchatx/src/frontend/features/licenses/index.ts";
import { registerMapFeature } from "../../meshchatx/src/frontend/features/map/index.ts";
import { registerMessageBlocklistFeature } from "../../meshchatx/src/frontend/features/message-blocklist/index.ts";
import { registerMessagesFeature } from "../../meshchatx/src/frontend/features/messages/index.ts";
import { registerMicronEditorFeature } from "../../meshchatx/src/frontend/features/micron-editor/index.ts";
import { registerNomadNetworkFeature } from "../../meshchatx/src/frontend/features/nomadnetwork/index.ts";
import { registerPageNodesFeature } from "../../meshchatx/src/frontend/features/page-nodes/index.ts";
import { registerPaperMessageFeature } from "../../meshchatx/src/frontend/features/paper-message/index.ts";
import { registerPingFeature } from "../../meshchatx/src/frontend/features/ping/index.ts";
import { registerProfileFeature } from "../../meshchatx/src/frontend/features/profile/index.ts";
import { registerPropagationNodesFeature } from "../../meshchatx/src/frontend/features/propagation-nodes/index.ts";
import { registerRelayChatFeature } from "../../meshchatx/src/frontend/features/relay-chat/index.ts";
import { registerRepositoryServerFeature } from "../../meshchatx/src/frontend/features/repository-server/index.ts";
import { registerReticulumConfigEditorFeature } from "../../meshchatx/src/frontend/features/reticulum-config-editor/index.ts";
import { registerRncpFeature } from "../../meshchatx/src/frontend/features/rncp/index.ts";
import { registerRnpathFeature } from "../../meshchatx/src/frontend/features/rnpath/index.ts";
import { registerRnpathTraceFeature } from "../../meshchatx/src/frontend/features/rnpath-trace/index.ts";
import { registerRnprobeFeature } from "../../meshchatx/src/frontend/features/rnprobe/index.ts";
import { registerRnshFeature } from "../../meshchatx/src/frontend/features/rnsh/index.ts";
import { registerRnxFeature } from "../../meshchatx/src/frontend/features/rnx/index.ts";
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
        id: "auth",
        register: registerAuthFeature,
        required_paths: [
            "meshchatx/src/frontend/features/auth/index.ts",
            "meshchatx/src/frontend/features/auth/AuthPage.svelte",
            "meshchatx/src/frontend/features/auth/lib/authActions.ts",
            "meshchatx/src/frontend/features/auth/lib/constants.ts",
        ],
        route_name: "auth",
        mount: "svelte",
    },
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
        id: "interfaces",
        register: registerInterfacesFeature,
        required_paths: [
            "meshchatx/src/frontend/features/interfaces/index.ts",
            "meshchatx/src/frontend/features/interfaces/InterfacesPage.svelte",
            "meshchatx/src/frontend/features/interfaces/AddInterfacePage.svelte",
            "meshchatx/src/frontend/features/interfaces/lib/constants.ts",
            "meshchatx/src/frontend/features/interfaces/lib/types.ts",
            "meshchatx/src/frontend/features/interfaces/lib/interfacesApi.ts",
            "meshchatx/src/frontend/features/interfaces/lib/interfacesFormat.ts",
            "meshchatx/src/frontend/features/interfaces/lib/addInterfaceState.ts",
            "meshchatx/src/frontend/features/interfaces/components/Toggle.svelte",
            "meshchatx/src/frontend/features/interfaces/components/ExpandingSection.svelte",
            "meshchatx/src/frontend/features/interfaces/components/BundledDocsHint.svelte",
            "meshchatx/src/frontend/features/interfaces/components/ImportInterfacesModal.svelte",
            "meshchatx/src/frontend/features/interfaces/components/InterfaceCard.svelte",
            "meshchatx/src/frontend/features/interfaces/components/DiscoveredInterfaceCard.svelte",
            "meshchatx/src/frontend/features/interfaces/components/DiscoverySettingsPanel.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceDiscoveryPanel.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceTypeSelector.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceTcpDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceBackboneDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceUdpDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceI2pDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceRNodeDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceSerialDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceAutoDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceHttpDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceExternalDetails.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceAdvancedPanel.svelte",
            "meshchatx/src/frontend/features/interfaces/components/AddInterfaceSidebar.svelte",
        ],
        route_name: "interfaces",
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
        id: "call",
        register: registerCallFeature,
        required_paths: [
            "meshchatx/src/frontend/features/call/index.ts",
            "meshchatx/src/frontend/features/call/CallPage.svelte",
            "meshchatx/src/frontend/features/call/lib/constants.ts",
            "meshchatx/src/frontend/features/call/components/CallOverlay.svelte",
        ],
        route_name: "call",
        mount: "svelte",
    },
    {
        id: "archives",
        register: registerArchivesFeature,
        required_paths: [
            "meshchatx/src/frontend/features/archives/index.ts",
            "meshchatx/src/frontend/features/archives/ArchivesPage.svelte",
            "meshchatx/src/frontend/features/archives/lib/constants.ts",
        ],
        route_name: "archives",
        mount: "svelte",
    },
    {
        id: "repository-server",
        register: registerRepositoryServerFeature,
        required_paths: [
            "meshchatx/src/frontend/features/repository-server/index.ts",
            "meshchatx/src/frontend/features/repository-server/RepositoryServerPage.svelte",
            "meshchatx/src/frontend/features/repository-server/lib/constants.ts",
        ],
        route_name: "repository-server",
        mount: "svelte",
    },
    {
        id: "page-nodes",
        register: registerPageNodesFeature,
        required_paths: [
            "meshchatx/src/frontend/features/page-nodes/index.ts",
            "meshchatx/src/frontend/features/page-nodes/PageNodesPage.svelte",
            "meshchatx/src/frontend/features/page-nodes/lib/constants.ts",
        ],
        route_name: "mesh-server",
        mount: "svelte",
    },
    {
        id: "rnsh",
        register: registerRnshFeature,
        required_paths: [
            "meshchatx/src/frontend/features/rnsh/index.ts",
            "meshchatx/src/frontend/features/rnsh/RNSHPage.svelte",
            "meshchatx/src/frontend/features/rnsh/lib/constants.ts",
            "meshchatx/src/frontend/features/remote-shell/components/RemoteShellTerminal.svelte",
        ],
        route_name: "rnsh",
        mount: "svelte",
    },
    {
        id: "rnx",
        register: registerRnxFeature,
        required_paths: [
            "meshchatx/src/frontend/features/rnx/index.ts",
            "meshchatx/src/frontend/features/rnx/RNXPage.svelte",
            "meshchatx/src/frontend/features/rnx/lib/constants.ts",
            "meshchatx/src/frontend/features/remote-shell/components/RemoteShellTerminal.svelte",
        ],
        route_name: "rnx",
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
    {
        id: "rncp",
        register: registerRncpFeature,
        required_paths: [
            "meshchatx/src/frontend/features/rncp/index.ts",
            "meshchatx/src/frontend/features/rncp/RNCPPage.svelte",
            "meshchatx/src/frontend/features/rncp/lib/types.ts",
            "meshchatx/src/frontend/features/rncp/lib/constants.ts",
            "meshchatx/src/frontend/features/rncp/lib/rncpPrefs.ts",
            "meshchatx/src/frontend/features/rncp/lib/rncpApi.ts",
            "meshchatx/src/frontend/features/rncp/components/RNCPSendTab.svelte",
            "meshchatx/src/frontend/features/rncp/components/RNCPFetchTab.svelte",
            "meshchatx/src/frontend/features/rncp/components/RNCPListenTab.svelte",
        ],
        route_name: "rncp",
        mount: "svelte",
    },
    {
        id: "bots",
        register: registerBotsFeature,
        required_paths: [
            "meshchatx/src/frontend/features/bots/index.ts",
            "meshchatx/src/frontend/features/bots/BotsPage.svelte",
            "meshchatx/src/frontend/features/bots/lib/types.ts",
            "meshchatx/src/frontend/features/bots/lib/botLxmfConfigForm.ts",
            "meshchatx/src/frontend/features/bots/lib/botUtils.ts",
            "meshchatx/src/frontend/features/bots/lib/botsApi.ts",
            "meshchatx/src/frontend/features/bots/components/BotCard.svelte",
            "meshchatx/src/frontend/features/bots/components/BotStartModal.svelte",
            "meshchatx/src/frontend/features/bots/components/BotLxmfConfigModal.svelte",
            "meshchatx/src/frontend/features/bots/components/BotProcessLogModal.svelte",
            "meshchatx/src/frontend/features/bots/components/BotLxmfConfigFields.svelte",
        ],
        route_name: "bots",
        mount: "svelte",
    },
    {
        id: "filesync",
        register: registerFilesyncFeature,
        required_paths: [
            "meshchatx/src/frontend/features/filesync/index.ts",
            "meshchatx/src/frontend/features/filesync/RnsFilesyncPage.svelte",
            "meshchatx/src/frontend/features/filesync/lib/types.ts",
            "meshchatx/src/frontend/features/filesync/lib/constants.ts",
            "meshchatx/src/frontend/features/filesync/lib/filesyncFormat.ts",
            "meshchatx/src/frontend/features/filesync/lib/filesyncApi.ts",
            "meshchatx/src/frontend/features/filesync/components/FilesyncFolderTab.svelte",
            "meshchatx/src/frontend/features/filesync/components/FilesyncDevicesTab.svelte",
            "meshchatx/src/frontend/features/filesync/components/FilesyncFileManager.svelte",
            "meshchatx/src/frontend/features/filesync/components/FilesyncRemoteTab.svelte",
            "meshchatx/src/frontend/features/filesync/components/FilesyncSharingTab.svelte",
            "meshchatx/src/frontend/features/filesync/components/FilesyncDirectoryBrowserModal.svelte",
        ],
        route_name: "rns-filesync",
        mount: "svelte",
    },
    {
        id: "docs",
        register: registerDocsFeature,
        required_paths: [
            "meshchatx/src/frontend/features/docs/index.ts",
            "meshchatx/src/frontend/features/docs/DocsPage.svelte",
            "meshchatx/src/frontend/features/docs/lib/types.ts",
            "meshchatx/src/frontend/features/docs/lib/constants.ts",
            "meshchatx/src/frontend/features/docs/lib/docsToc.ts",
            "meshchatx/src/frontend/features/docs/lib/docsApi.ts",
            "meshchatx/src/frontend/features/docs/components/DocsStatusOverlay.svelte",
            "meshchatx/src/frontend/features/docs/components/DocsSearchResults.svelte",
            "meshchatx/src/frontend/features/docs/components/DocsSidebar.svelte",
            "meshchatx/src/frontend/features/docs/components/DocsMobileControls.svelte",
            "meshchatx/src/frontend/features/docs/components/DocsProseView.svelte",
            "meshchatx/src/frontend/features/docs/components/DocsReticulumView.svelte",
        ],
        route_name: "documentation",
        mount: "svelte",
    },
    {
        id: "propagation-nodes",
        register: registerPropagationNodesFeature,
        required_paths: [
            "meshchatx/src/frontend/features/propagation-nodes/index.ts",
            "meshchatx/src/frontend/features/propagation-nodes/PropagationNodesPage.svelte",
            "meshchatx/src/frontend/features/propagation-nodes/lib/types.ts",
            "meshchatx/src/frontend/features/propagation-nodes/lib/constants.ts",
            "meshchatx/src/frontend/features/propagation-nodes/lib/propagationFormat.ts",
            "meshchatx/src/frontend/features/propagation-nodes/lib/propagationSort.ts",
            "meshchatx/src/frontend/features/propagation-nodes/lib/propagationApi.ts",
            "meshchatx/src/frontend/features/propagation-nodes/components/PropagationHostedSection.svelte",
            "meshchatx/src/frontend/features/propagation-nodes/components/PropagationPreferredSection.svelte",
            "meshchatx/src/frontend/features/propagation-nodes/components/PropagationNodeList.svelte",
        ],
        route_name: "propagation-nodes",
        mount: "svelte",
    },
    {
        id: "micron-editor",
        register: registerMicronEditorFeature,
        required_paths: [
            "meshchatx/src/frontend/features/micron-editor/index.ts",
            "meshchatx/src/frontend/features/micron-editor/MicronEditorPage.svelte",
            "meshchatx/src/frontend/features/micron-editor/lib/types.ts",
            "meshchatx/src/frontend/features/micron-editor/lib/constants.ts",
            "meshchatx/src/frontend/features/micron-editor/lib/defaultContent.ts",
            "meshchatx/src/frontend/features/micron-editor/lib/guideContent.ts",
            "meshchatx/src/frontend/features/micron-editor/lib/micronPublish.ts",
            "meshchatx/src/frontend/features/micron-editor/lib/micronDownload.ts",
            "meshchatx/src/frontend/features/micron-editor/components/MicronEditorTabBar.svelte",
            "meshchatx/src/frontend/features/micron-editor/components/MicronPublishDropdown.svelte",
            "meshchatx/src/frontend/features/micron-editor/components/MicronPreviewPane.svelte",
        ],
        route_name: "micron-editor",
        mount: "svelte",
    },
    {
        id: "profile",
        register: registerProfileFeature,
        required_paths: [
            "meshchatx/src/frontend/features/profile/index.ts",
            "meshchatx/src/frontend/features/profile/ProfileIconPage.svelte",
            "meshchatx/src/frontend/features/profile/components/ColourPickerDropdown.svelte",
            "meshchatx/src/frontend/features/profile/lib/profileIcon.ts",
        ],
        route_name: "profile.icon",
        mount: "svelte",
    },
    {
        id: "about",
        register: registerAboutFeature,
        required_paths: [
            "meshchatx/src/frontend/features/about/index.ts",
            "meshchatx/src/frontend/features/about/AboutPage.svelte",
            "meshchatx/src/frontend/features/about/components/AboutHeroSection.svelte",
            "meshchatx/src/frontend/features/about/components/AboutSecuritySection.svelte",
            "meshchatx/src/frontend/features/about/components/AboutSessionsSection.svelte",
            "meshchatx/src/frontend/features/about/components/AboutEnvironmentSection.svelte",
            "meshchatx/src/frontend/features/about/components/AboutUsageSection.svelte",
            "meshchatx/src/frontend/features/about/components/AboutDependencySection.svelte",
            "meshchatx/src/frontend/features/about/components/AboutDatabaseSection.svelte",
            "meshchatx/src/frontend/features/about/components/AboutSnapshotsSection.svelte",
            "meshchatx/src/frontend/features/about/components/AboutAutoBackupsSection.svelte",
            "meshchatx/src/frontend/features/about/lib/types.ts",
            "meshchatx/src/frontend/features/about/lib/constants.ts",
            "meshchatx/src/frontend/features/about/lib/aboutFormat.ts",
            "meshchatx/src/frontend/features/about/lib/aboutApi.ts",
            "meshchatx/src/frontend/features/about/lib/backupApi.ts",
        ],
        route_name: "about",
        mount: "svelte",
    },
    {
        id: "nomadnetwork",
        register: registerNomadNetworkFeature,
        required_paths: [
            "meshchatx/src/frontend/features/nomadnetwork/index.ts",
            "meshchatx/src/frontend/features/nomadnetwork/components/NomadNetworkBrowser.svelte",
            "meshchatx/src/frontend/features/nomadnetwork/components/NomadNetworkPage.svelte",
            "meshchatx/src/frontend/features/nomadnetwork/components/NomadNetworkSidebar.svelte",
            "meshchatx/src/frontend/features/nomadnetwork/components/NomadCrashTab.svelte",
            "meshchatx/src/frontend/features/nomadnetwork/components/NomadBrowserContextMenu.svelte",
            "meshchatx/src/frontend/features/nomadnetwork/lib/types.ts",
            "meshchatx/src/frontend/features/nomadnetwork/lib/constants.ts",
            "meshchatx/src/frontend/features/nomadnetwork/lib/nomadBrowserTabs.ts",
            "meshchatx/src/frontend/features/nomadnetwork/lib/nomadSidebarFavourites.ts",
            "meshchatx/src/frontend/features/nomadnetwork/lib/nomadPageNavigation.ts",
            "meshchatx/src/frontend/features/nomadnetwork/lib/nomadPageDownloads.ts",
            "meshchatx/src/frontend/features/nomadnetwork/lib/nomadPageArchives.ts",
        ],
        route_name: "nomadnetwork",
        mount: "svelte",
    },
    {
        id: "relay-chat",
        register: registerRelayChatFeature,
        required_paths: [
            "meshchatx/src/frontend/features/relay-chat/index.ts",
            "meshchatx/src/frontend/features/relay-chat/components/RelayChatPage.svelte",
            "meshchatx/src/frontend/features/relay-chat/components/RelayHostModerationPage.svelte",
            "meshchatx/src/frontend/features/relay-chat/components/RelayMessageEntry.svelte",
            "meshchatx/src/frontend/features/relay-chat/components/RelayMessageListVirtual.svelte",
            "meshchatx/src/frontend/features/relay-chat/lib/types.ts",
            "meshchatx/src/frontend/features/relay-chat/lib/constants.ts",
            "meshchatx/src/frontend/features/relay-chat/lib/relayFormatters.ts",
        ],
        route_name: "relay-chat",
        mount: "svelte",
    },
    {
        id: "map",
        register: registerMapFeature,
        required_paths: [
            "meshchatx/src/frontend/features/map/index.ts",
            "meshchatx/src/frontend/features/map/MapPage.svelte",
            "meshchatx/src/frontend/features/map/components/MapBrowser.svelte",
            "meshchatx/src/frontend/features/map/components/MiniChat.svelte",
            "meshchatx/src/frontend/features/map/lib/types.ts",
            "meshchatx/src/frontend/features/map/lib/constants.ts",
            "meshchatx/src/frontend/features/map/lib/markerStyles.ts",
            "meshchatx/src/frontend/features/map/lib/clusterUtils.ts",
            "meshchatx/src/frontend/features/map/lib/mapDedupe.ts",
            "meshchatx/src/frontend/features/map/lib/discoveredIcons.ts",
        ],
        route_name: "map",
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
            console.log("Checking feature:", feature?.id);
            for (const rel of feature.required_paths) {
                expect(existsSync(join(repoRoot, rel)), `missing ${rel}`).toBe(true);
            }
            feature.register();
            expect(listFeatureIds()).toContain(feature.id);
            const route = listRoutes().find((r) => r.name === feature.route_name);
            expect(route, `route for feature ${feature.id} named ${feature.route_name}`).toBeTruthy();
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
