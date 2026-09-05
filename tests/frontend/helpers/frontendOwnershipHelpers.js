// SPDX-License-Identifier: 0BSD

import { existsSync, readdirSync, readFileSync, writeFileSync, statSync } from "fs";
import { join, relative } from "path";

export function repoRootFromCwd(cwd = process.cwd()) {
    return cwd;
}

export function readUtf8(absolutePath) {
    return readFileSync(absolutePath, "utf8");
}

export function listFilesRecursive(dir, exts) {
    const out = [];
    if (!existsSync(dir)) {
        return out;
    }
    for (const name of readdirSync(dir)) {
        const full = join(dir, name);
        const st = statSync(full);
        if (st.isDirectory()) {
            out.push(...listFilesRecursive(full, exts));
            continue;
        }
        if (exts.some((ext) => name.endsWith(ext))) {
            out.push(full);
        }
    }
    return out;
}

export function joinFeatureSources(repoRoot, relativeDirs) {
    const chunks = [];
    for (const rel of relativeDirs) {
        const abs = join(repoRoot, rel);
        if (statSync(abs, { throwIfNoEntry: false })?.isFile()) {
            chunks.push(readUtf8(abs));
            continue;
        }
        for (const file of listFilesRecursive(abs, [".vue", ".js", ".ts", ".svelte"])) {
            chunks.push(readUtf8(file));
        }
    }
    return chunks.join("\n");
}

export function discoverMegaPageOwnership(repoRoot) {
    const pages = [
        {
            id: "settings",
            shell: "meshchatx/src/frontend/components/settings/SettingsPage.vue",
            allowed_child_dirs: [
                "meshchatx/src/frontend/components/settings/sections",
                "meshchatx/src/frontend/js/settings",
            ],
            required_children: [
                "meshchatx/src/frontend/components/settings/SettingToggleRow.vue",
                "meshchatx/src/frontend/components/settings/SettingsSectionBlock.vue",
                "meshchatx/src/frontend/components/settings/sections/LanguageSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/DesktopSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/StrangerProtectionSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/BanishmentSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/StickersSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/GifsSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/TelephonySettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/AppearanceSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/BatterySettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/VisualiserSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/BlockedSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/AndroidSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/sections/ArchiverSettingsSection.vue",
                "meshchatx/src/frontend/components/settings/PluginsSettingsSection.vue",
            ],
            required_shell_imports: [
                "LanguageSettingsSection",
                "DesktopSettingsSection",
                "StrangerProtectionSettingsSection",
                "BanishmentSettingsSection",
                "StickersSettingsSection",
                "GifsSettingsSection",
                "TelephonySettingsSection",
                "AppearanceSettingsSection",
                "BatterySettingsSection",
                "VisualiserSettingsSection",
                "BlockedSettingsSection",
                "AndroidSettingsSection",
                "ArchiverSettingsSection",
                "PluginsSettingsSection",
                "SettingsSectionBlock",
            ],
        },
        {
            id: "map",
            shell: "meshchatx/src/frontend/components/map/MapPage.vue",
            allowed_child_dirs: ["meshchatx/src/frontend/components/map/internal", "meshchatx/src/frontend/js"],
            required_children: [
                "meshchatx/src/frontend/components/map/internal/MapClusterPanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapMarkerPanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapDrawingToolbar.vue",
                "meshchatx/src/frontend/components/map/internal/MapBearingInstructions.vue",
                "meshchatx/src/frontend/components/map/internal/MapSearchBar.vue",
                "meshchatx/src/frontend/components/map/internal/MapExportInstructions.vue",
                "meshchatx/src/frontend/components/map/internal/MapExportConfigPanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapExportProgressPanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapLoadingOverlay.vue",
                "meshchatx/src/frontend/components/map/internal/MapSidePanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapDiscoverPanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapPublishPanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapLayersPanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapOfflinePanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapVectorExchangePanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapRemoteOverlayPanel.vue",
                "meshchatx/src/frontend/components/map/internal/MapSaveDrawingModal.vue",
                "meshchatx/src/frontend/components/map/internal/MapLoadDrawingModal.vue",
                "meshchatx/src/frontend/components/map/internal/MapMobileNoteModal.vue",
                "meshchatx/src/frontend/components/map/internal/clusterUtils.ts",
                "meshchatx/src/frontend/components/map/internal/discoveredIcons.ts",
                "meshchatx/src/frontend/components/map/internal/mapDedupe.ts",
                "meshchatx/src/frontend/components/map/internal/markerStyles.ts",
            ],
            required_shell_imports: [
                "MapClusterPanel",
                "MapMarkerPanel",
                "MapDrawingToolbar",
                "MapBearingInstructions",
                "MapSearchBar",
                "MapExportInstructions",
                "MapExportConfigPanel",
                "MapExportProgressPanel",
                "MapLoadingOverlay",
                "MapSidePanel",
                "MapSaveDrawingModal",
                "MapLoadDrawingModal",
                "MapMobileNoteModal",
                "clusterUtils",
                "discoveredIcons",
                "mapDedupe",
                "markerStyles",
            ],
        },
        {
            id: "messages",
            shell: "meshchatx/src/frontend/features/messages/components/ConversationViewer.svelte",
            allowed_child_dirs: [
                "meshchatx/src/frontend/features/messages/components",
                "meshchatx/src/frontend/features/messages/components/composer",
                "meshchatx/src/frontend/features/messages/components/modals",
                "meshchatx/src/frontend/features/messages/components/outbound",
                "meshchatx/src/frontend/features/messages/components/telemetry",
                "meshchatx/src/frontend/features/messages/lib",
            ],
            required_children: [
                "meshchatx/src/frontend/features/messages/components/ConversationPeerHeader.svelte",
                "meshchatx/src/frontend/features/messages/components/ConversationMessageEntry.svelte",
                "meshchatx/src/frontend/features/messages/lib/conversationMessageHelpers.ts",
                "meshchatx/src/frontend/features/messages/components/outbound/OutboundTransferProgressFooter.svelte",
                "meshchatx/src/frontend/features/messages/components/modals/ShareContactModal.svelte",
                "meshchatx/src/frontend/features/messages/components/modals/ConversationImageModal.svelte",
                "meshchatx/src/frontend/features/messages/components/composer/AddImageButton.svelte",
                "meshchatx/src/frontend/features/messages/lib/lxmf/contactDisplay.ts",
                "meshchatx/src/frontend/features/messages/lib/lxmf/normalize.ts",
            ],
            required_shell_imports: [
                "ConversationPeerHeader",
                "ConversationMessageEntry",
                "ConversationMessageListVirtual",
                "ConversationMessageContextMenu",
                "ConversationComposer",
                "PaperMessageModal",
                "buildDisplayGroupsNewestFirst",
                "createConversationViewerActions",
            ],
        },
        {
            id: "call",
            shell: "meshchatx/src/frontend/components/call/CallPage.vue",
            allowed_child_dirs: [
                "meshchatx/src/frontend/components/call",
                "meshchatx/src/frontend/components/call/tabs",
                "meshchatx/src/frontend/components/call/audio",
            ],
            required_children: [
                "meshchatx/src/frontend/components/call/CallOverlay.vue",
                "meshchatx/src/frontend/components/call/audio/RingtoneEditor.vue",
                "meshchatx/src/frontend/components/call/tabs/CallPhonebookTab.vue",
                "meshchatx/src/frontend/components/call/tabs/CallContactsTab.vue",
                "meshchatx/src/frontend/components/call/tabs/CallVoicemailTab.vue",
                "meshchatx/src/frontend/components/call/tabs/CallTabBar.vue",
            ],
            required_shell_imports: [
                "RingtoneEditor",
                "CallPhonebookTab",
                "CallContactsTab",
                "CallVoicemailTab",
                "CallTabBar",
            ],
        },
        {
            id: "app",
            shell: "meshchatx/src/frontend/components/App.vue",
            allowed_child_dirs: ["meshchatx/src/frontend/components/layout", "meshchatx/src/frontend/components/call"],
            required_children: [
                "meshchatx/src/frontend/components/layout/AppShellBanners.vue",
                "meshchatx/src/frontend/components/layout/AppIdentitySwitchOverlay.vue",
                "meshchatx/src/frontend/components/call/CallOverlay.vue",
            ],
            required_shell_imports: ["AppShellBanners", "AppIdentitySwitchOverlay", "CallOverlay", "listNavItems"],
        },
    ];

    return {
        version: 1,
        pages: pages.map((page) => ({
            ...page,
            required_children: page.required_children.filter((rel) => existsSync(join(repoRoot, rel))),
            required_shell_imports: page.required_shell_imports,
        })),
    };
}

export function writeOwnershipFixture(repoRoot, fixturePath) {
    const payload = discoverMegaPageOwnership(repoRoot);
    writeFileSync(fixturePath, `${JSON.stringify(payload, null, 4)}\n`, "utf8");
    return payload;
}

export function loadJsonFixture(repoRoot, relativePath) {
    return JSON.parse(readUtf8(join(repoRoot, relativePath)));
}

export function assertStringsInSources(sourceText, requiredStrings, label) {
    const missing = requiredStrings.filter((s) => !sourceText.includes(s));
    if (missing.length) {
        throw new Error(`${label} missing required strings: ${missing.join(", ")}`);
    }
}

export function relativeRepoPath(repoRoot, absolutePath) {
    return relative(repoRoot, absolutePath).split("\\").join("/");
}
