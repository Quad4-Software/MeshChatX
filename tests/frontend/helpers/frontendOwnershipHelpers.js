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
        for (const file of listFilesRecursive(abs, [".js", ".ts", ".svelte"])) {
            chunks.push(readUtf8(file));
        }
    }
    return chunks.join("\n");
}

export function discoverMegaPageOwnership(repoRoot) {
    const pages = [
        {
            id: "settings",
            shell: "meshchatx/src/frontend/features/settings/components/SettingsPage.svelte",
            allowed_child_dirs: [
                "meshchatx/src/frontend/features/settings/components/sections",
                "meshchatx/src/frontend/features/settings/components",
                "meshchatx/src/frontend/js/settings",
            ],
            required_children: [
                "meshchatx/src/frontend/features/settings/components/SettingToggleRow.svelte",
                "meshchatx/src/frontend/features/settings/components/SettingsSectionBlock.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/LanguageSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/DesktopSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/StrangerProtectionSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/BanishmentSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/StickersSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/GifsSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/TelephonySettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/AppearanceSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/BatterySettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/VisualiserSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/BlockedSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/AndroidSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/ArchiverSettingsSection.svelte",
                "meshchatx/src/frontend/features/settings/components/sections/PluginsSettingsSection.svelte",
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
            ],
        },
        {
            id: "map",
            shell: "meshchatx/src/frontend/features/map/MapPage.svelte",
            allowed_child_dirs: [
                "meshchatx/src/frontend/features/map/components",
                "meshchatx/src/frontend/features/map/lib",
                "meshchatx/src/frontend/js",
            ],
            required_children: [
                "meshchatx/src/frontend/features/map/components/MapHeaderBar.svelte",
                "meshchatx/src/frontend/features/map/components/MapDrawingToolbar.svelte",
                "meshchatx/src/frontend/features/map/components/MapBearingInstructions.svelte",
                "meshchatx/src/frontend/features/map/components/MapSearchBar.svelte",
                "meshchatx/src/frontend/features/map/components/MapMarkerPanel.svelte",
                "meshchatx/src/frontend/features/map/components/MapClusterPanel.svelte",
                "meshchatx/src/frontend/features/map/components/MapSettingsPanel.svelte",
                "meshchatx/src/frontend/features/map/components/MapToolsDrawer.svelte",
                "meshchatx/src/frontend/features/map/components/MapSaveDrawingModal.svelte",
                "meshchatx/src/frontend/features/map/components/MapLoadDrawingModal.svelte",
                "meshchatx/src/frontend/features/map/components/MapContextMenu.svelte",
                "meshchatx/src/frontend/features/map/components/MapMobileNoteModal.svelte",
                "meshchatx/src/frontend/features/map/components/MapLoadingOverlay.svelte",
                "meshchatx/src/frontend/features/map/lib/clusterUtils.ts",
                "meshchatx/src/frontend/features/map/lib/discoveredIcons.ts",
                "meshchatx/src/frontend/features/map/lib/mapDedupe.ts",
                "meshchatx/src/frontend/features/map/lib/markerStyles.ts",
            ],
            required_shell_imports: [
                "MapHeaderBar",
                "MapDrawingToolbar",
                "MapBearingInstructions",
                "MapSearchBar",
                "MapMarkerPanel",
                "MapClusterPanel",
                "MapSettingsPanel",
                "MapToolsDrawer",
                "MapSaveDrawingModal",
                "MapLoadDrawingModal",
                "MapContextMenu",
                "MapMobileNoteModal",
                "MapLoadingOverlay",
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
                "ConversationViewerEmptyHost",
                "ConversationViewerHeaderHost",
                "MessageDisplayEntry",
                "ConversationViewerListPane",
                "ConversationViewerComposerHost",
                "ConversationViewerModalsBridge",
                "buildDisplayGroupsNewestFirst",
                "createConversationViewerActions",
            ],
        },
        {
            id: "app",
            shell: "meshchatx/src/frontend/features/app-shell/App.svelte",
            allowed_child_dirs: [
                "meshchatx/src/frontend/features/app-shell/components",
                "meshchatx/src/frontend/features/app-shell/lib",
                "meshchatx/src/frontend/features/call",
            ],
            required_children: [
                "meshchatx/src/frontend/features/app-shell/components/AppShellBanners.svelte",
                "meshchatx/src/frontend/features/app-shell/components/AppIdentitySwitchOverlay.svelte",
                "meshchatx/src/frontend/features/call/components/CallOverlay.svelte",
            ],
            required_shell_imports: ["AppShellBanners", "AppShellOverlays", "PageOutlet", "AppShellState"],
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
