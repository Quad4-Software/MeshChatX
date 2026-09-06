// SPDX-License-Identifier: 0BSD

/**
 * Source contracts for APIs that regressed during the Svelte shell flip.
 * These assert live Svelte sources wire the correct backend paths.
 */

import { readFileSync } from "node:fs";
import { readdirSync, statSync } from "node:fs";
import { resolve, join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(import.meta.dirname, "../..");

function src(rel) {
    return readFileSync(resolve(ROOT, rel), "utf8");
}

describe("svelte shell migration API regressions", () => {
    it("map restore starter posts restore-starter", () => {
        const mapService = src("meshchatx/src/frontend/features/map/lib/mapService.ts");
        expect(mapService).toContain("/api/v1/map/mbtiles/restore-starter");
        expect(mapService).not.toContain("/api/v1/map/mbtiles/starter");
    });

    it("map telemetry peers ping and overlays use Vue-parity APIs", () => {
        const mapService = src("meshchatx/src/frontend/features/map/lib/mapService.ts");
        expect(mapService).toContain("/api/v1/telemetry/peers");
        expect(mapService).not.toContain("/api/v1/map/telemetry");
        expect(mapService).toContain("/api/v1/lxmf-messages/send");
        expect(mapService).toContain("lxmf_message");
        expect(mapService).toContain("buildMeshchatMapUri");
        expect(mapService).toContain("/api/v1/telemetry/tracking/");
        expect(mapService).toContain("/api/v1/telemetry/history/");
        expect(mapService).toContain("announce_store_map_data");
        expect(mapService).not.toContain("/api/v1/lxmf/messages/send");

        const mapPage = src("meshchatx/src/frontend/features/map/MapPage.svelte");
        expect(mapPage).toContain('onWsEvent("lxmf.telemetry"');
        expect(mapPage).toContain('offWsEvent("lxmf.telemetry"');
        expect(mapPage).toContain("buildNominatimSearchUrl");
        expect(mapPage).toContain("https://nominatim.openstreetmap.org");
        expect(mapPage).not.toContain("https://nominatim.openstreetmap.org/search");
        expect(mapPage).toContain("MapPingModal");
        expect(mapPage).toContain("shareMapView");
        expect(mapPage).toContain("applyMapViewFromRoute");
        expect(mapPage).toContain("onoverlayschanged={onRemoteOverlaysChanged}");
        expect(mapPage).toContain("handleToggleTracking");
        expect(mapPage).toContain("markerPanelPayloadFromFeature");
        expect(mapPage).toContain("onMapDrop");
        expect(mapPage).toContain("drawTelemetryPath");
        expect(mapPage).toContain("ontoggleannouncelisten={onToggleAnnounceListen}");
        expect(mapPage).toContain("ontoggleminichat=");
        expect(mapPage).toContain("readDroppedGeoFileToFeatures");

        const helpers = src("meshchatx/src/frontend/features/map/lib/mapPageHelpers.ts");
        expect(helpers).toContain("telemetry: item");
        expect(helpers).toContain("discovered: node");
        expect(helpers).not.toContain("discoveredNode:");

        const dropImport = src("meshchatx/src/frontend/features/map/lib/mapDropImport.ts");
        expect(dropImport).toContain("looksLikeGeoJsonText");
        expect(dropImport).toContain(".mbtiles");
        expect(dropImport).toContain(".gpx");

        const history = src("meshchatx/src/frontend/features/map/lib/mapTelemetryHistory.ts");
        expect(history).toContain("history_trail");
        expect(history).toContain("buildTelemetryHistoryTrailFeature");

        const overlays = src("meshchatx/src/frontend/features/map/lib/mapRemoteOverlays.ts");
        expect(overlays).toContain("/api/v1/map/overlays/${overlay.id}/content");
        expect(overlays).toContain("/api/v1/map/overlays/${id}/export");
    });

    it("settings loads trusted telemetry peers and wires sticker/gif export", () => {
        const settings = src("meshchatx/src/frontend/features/settings/components/SettingsPage.svelte");
        expect(settings).toContain("/api/v1/telemetry/trusted-peers");
        expect(settings).toContain("trusted_peers");
        expect(settings).toContain("onexport={onExportStickers}");
        expect(settings).toContain("onexport={onExportGifs}");
        const actions = src("meshchatx/src/frontend/features/settings/lib/maintenanceActions.ts");
        expect(actions).toContain("/api/v1/stickers/export");
        expect(actions).toContain("/api/v1/gifs/export");
        expect(actions).toContain("/api/v1/stickers/import");
        expect(actions).toContain("/api/v1/gifs/import");
    });

    it("profile icon hash is #/profile/icon not settings/profile-icon", () => {
        const feature = src("meshchatx/src/frontend/features/profile/index.ts");
        expect(feature).toContain('name: "profile.icon"');
        expect(feature).toContain('path: "/profile/icon"');
        expect(feature).not.toContain("settings/profile-icon");
        const accountFooter = src(
            "meshchatx/src/frontend/features/app-shell/components/AppSidebarAccountFooter.svelte"
        );
        const classicFooter = src(
            "meshchatx/src/frontend/features/app-shell/components/AppSidebarClassicFooter.svelte"
        );
        expect(accountFooter).toContain('href="#/profile/icon"');
        expect(accountFooter).not.toContain("#/settings/profile-icon");
        expect(classicFooter).toContain('href="#/profile/icon"');
        expect(classicFooter).not.toContain("#/settings/profile-icon");
    });

    it("interfaces add/edit hashes use slash paths and interface_name query", () => {
        const constants = src("meshchatx/src/frontend/features/interfaces/lib/constants.ts");
        expect(constants).toContain('INTERFACES_ADD_ROUTE_PATH = "/interfaces/add"');
        expect(constants).toContain('INTERFACES_EDIT_ROUTE_PATH = "/interfaces/edit"');
        expect(constants).toContain('INTERFACES_ADD_ROUTE_NAME = "interfaces.add"');
        expect(constants).toContain('INTERFACES_EDIT_ROUTE_NAME = "interfaces.edit"');
        const feature = src("meshchatx/src/frontend/features/interfaces/index.ts");
        expect(feature).toContain("path: INTERFACES_ADD_ROUTE_PATH");
        expect(feature).toContain("path: INTERFACES_EDIT_ROUTE_PATH");
        const list = src("meshchatx/src/frontend/features/interfaces/InterfacesPage.svelte");
        expect(list).toContain("INTERFACES_ADD_ROUTE_PATH");
        expect(list).toContain("INTERFACES_EDIT_ROUTE_PATH");
        expect(list).toContain("`#${INTERFACES_ADD_ROUTE_PATH}`");
        expect(list).toContain("`#${INTERFACES_EDIT_ROUTE_PATH}?interface_name=${encodeURIComponent(name)}`");
        expect(list).toContain("interface_name=");
        expect(list).not.toContain("INTERFACES_EDIT_ROUTE_NAME");
        expect(list).not.toContain("INTERFACES_ADD_ROUTE_NAME");
        expect(list).not.toContain("#/${INTERFACES_EDIT_ROUTE_NAME}");
        expect(list).not.toContain("#/interfaces.add");
        expect(list).not.toContain("#/interfaces.edit");
        const page = src("meshchatx/src/frontend/features/interfaces/AddInterfacePage.svelte");
        expect(page).toContain("routeQuery.interface_name");
        expect(page).toContain("editInterfaceName");
        expect(page).toContain("canAddI2PInterface");
        expect(page).toContain("hasExistingI2PInterface");
        expect(page).toContain("interfaces.i2p_transport_required");
        expect(page).toContain("interfaces.i2p_already_exists");
        expect(page).toContain("INTERFACES_ROUTE_PATH");
        expect(page).toContain("`#${INTERFACES_ROUTE_PATH}`");
        expect(page).not.toContain("#/${INTERFACES_ROUTE_NAME}");
        const i2p = src("meshchatx/src/frontend/features/interfaces/components/AddInterfaceI2pDetails.svelte");
        expect(i2p).toContain("interfaces.i2p_transport_required");
        expect(i2p).toContain("interfaces.i2p_already_exists");
    });

    it("favourites export/import use real API paths not invented nomadnet endpoints", () => {
        const actions = src("meshchatx/src/frontend/features/settings/lib/maintenanceActions.ts");
        expect(actions).toContain('api.get("/api/v1/favourites")');
        expect(actions).toContain('api.post("/api/v1/favourites/import"');
        expect(actions).toContain("loadNomadFavouritesLayout");
        expect(actions).toContain("saveNomadFavouritesLayout");
        expect(actions).toContain("meshchatx/nomadnet_favourites/v1");
        expect(actions).not.toContain("/api/v1/favourites/export/nomadnet");
        expect(actions).not.toContain("/api/v1/favourites/import/nomadnet");
        expect(actions).not.toContain("/api/v1/favourites/export");
    });

    it("battery settings wiring symbols stay connected through SettingsPage", () => {
        const batteryUi = src("meshchatx/src/frontend/features/settings/lib/batterySettingsUi.ts");
        expect(batteryUi).toContain("export async function fetchBatteryInterfaceRows");
        expect(batteryUi).toContain('api.get("/api/v1/reticulum/interfaces")');
        expect(batteryUi).toContain("export function readBatterySaverPrefs");
        expect(batteryUi).toContain("export function patchBatterySaverPrefs");
        expect(batteryUi).toContain("export async function applyBatteryBitrateLimitsNow");
        expect(batteryUi).toContain("export async function restoreBatteryBitrateLimitsNow");
        expect(batteryUi).toContain("export function toastBatteryBitrateApplyResult");
        expect(batteryUi).toContain("export function toastBatteryBitrateRestoreResult");
        const settings = src("meshchatx/src/frontend/features/settings/components/SettingsPage.svelte");
        expect(settings).toContain("BatterySettingsSection");
        expect(settings).toContain("fetchBatteryInterfaceRows");
        expect(settings).toContain("readBatterySaverPrefs");
        expect(settings).toContain("patchBatterySaverPrefs");
        expect(settings).toContain("applyBatteryBitrateLimitsNow");
        expect(settings).toContain("restoreBatteryBitrateLimitsNow");
        expect(settings).toContain("loadBatteryInterfaceRows");
        expect(settings).toContain("onBatterySaverEnabledChange");
        expect(settings).toContain("onBatterySaverPatch");
        expect(settings).toContain("onenabledchange={onBatterySaverEnabledChange}");
        expect(settings).toContain("onpatch={onBatterySaverPatch}");
        expect(settings).toContain("onapplybitrates={onApplyBatteryBitrates}");
        expect(settings).toContain("onrestorebitrates={onRestoreBatteryBitrates}");
    });

    it("server security allowlist persists via PATCH /api/v1/server/security", () => {
        const helpers = src("meshchatx/src/frontend/features/settings/lib/settingsPageHelpers.ts");
        expect(helpers).toContain("export async function saveWebUiIpAllowlist");
        expect(helpers).toContain('api.patch("/api/v1/server/security"');
        expect(helpers).toContain("web_ui_ip_allowlist: allowlist");
        const settings = src("meshchatx/src/frontend/features/settings/components/SettingsPage.svelte");
        expect(settings).toContain("saveWebUiIpAllowlist as saveWebUiIpAllowlistHelper");
        expect(settings).toContain("onWebUiAllowlistChange");
        expect(settings).toContain("onallowlistchange={onWebUiAllowlistChange}");
        expect(settings).toContain("saveWebUiIpAllowlistHelper");
        expect(settings).not.toContain('updateConfigField("web_ui_ip_allowlist"');
        expect(settings).toContain('window.api.get("/api/v1/server/security")');
    });

    it("live nav and command sources never emit dotted #/foo.bar hashes", () => {
        const dottedHash = /#\/[A-Za-z0-9_-]+\.[A-Za-z0-9_.-]+/;
        const liveSources = [
            "meshchatx/src/frontend/features/app-shell/components/SidebarLink.svelte",
            "meshchatx/src/frontend/features/app-shell/components/CommandPalette.svelte",
            "meshchatx/src/frontend/features/app-shell/components/AppShellOverlays.svelte",
            "meshchatx/src/frontend/features/app-shell/components/AppSidebarAccountFooter.svelte",
            "meshchatx/src/frontend/features/app-shell/components/AppSidebarClassicFooter.svelte",
            "meshchatx/src/frontend/features/app-shell/lib/appShellCommands.ts",
            "meshchatx/src/frontend/features/app-shell/lib/appShellNav.ts",
            "meshchatx/src/frontend/features/tools/lib/toolsList.ts",
            "meshchatx/src/frontend/js/registries/coreNavEntries.ts",
            "meshchatx/src/frontend/features/interfaces/InterfacesPage.svelte",
            "meshchatx/src/frontend/features/interfaces/AddInterfacePage.svelte",
            "meshchatx/src/frontend/features/interfaces/lib/constants.ts",
            "meshchatx/src/frontend/features/profile/index.ts",
        ];
        const offenders = [];
        for (const rel of liveSources) {
            const text = src(rel);
            const match = text.match(dottedHash);
            if (match) {
                offenders.push(`${rel}: ${match[0]}`);
            }
        }
        expect(offenders).toEqual([]);

        const sidebarLink = src("meshchatx/src/frontend/features/app-shell/components/SidebarLink.svelte");
        expect(sidebarLink).toContain("resolveTarget");
        expect(sidebarLink).toContain("return `#${resolveTarget(to)}`");
        expect(sidebarLink).not.toContain("return `#/${to.name}`");

        const palette = src("meshchatx/src/frontend/features/app-shell/components/CommandPalette.svelte");
        expect(palette).toContain("void navigate(result.route)");
        expect(palette).not.toContain("`#/${result.route.name");

        const overlays = src("meshchatx/src/frontend/features/app-shell/components/AppShellOverlays.svelte");
        expect(overlays).toContain("onnavigate={onCommandPaletteNavigate}");

        const toolsList = src("meshchatx/src/frontend/features/tools/lib/toolsList.ts");
        expect(toolsList).toContain("if (route.path)");
        expect(toolsList).toContain("return `#${resolveTarget({ name })}`");
        expect(toolsList).toContain("dotted names become path segments");
    });

    it("relay leave uses HTTP DELETE and persists hub and room order", () => {
        const page = src("meshchatx/src/frontend/features/relay-chat/components/RelayChatPage.svelte");
        expect(page).toContain("/api/v1/rrc/active/clear");
        expect(page).toContain("/api/v1/rrc/hubs/order");
        expect(page).toContain("onreorderhubs={onReorderHubs}");
        expect(page).toContain("onreorderrooms={onReorderRooms}");
        expect(page).toContain("onpersistroomorder");
        expect(page).toContain("/api/v1/rrc/hubs/${current.hub_hash}/rooms/order");
        expect(page).toContain("room_names:");
        expect(page).toContain("/api/v1/rrc/hubs/${hubH}/rooms/${encodeURIComponent(room)}");
        expect(page).toContain("/rooms/${encodeURIComponent(room)}/messages");
        expect(page).not.toContain('type: "rrc.leave_room"');
        expect(page).toContain("/api/v1/rrc/hubs/${hubObj.hub_hash}/disconnect");
        expect(page).toContain("/api/v1/rrc/hubs/${hubObj.hub_hash}/connect");
        const header = src("meshchatx/src/frontend/features/relay-chat/components/RelayChatHeader.svelte");
        expect(header).toContain("onclearmessages");
        expect(header).toContain("ondisconnecthub");
        const sidebar = src("meshchatx/src/frontend/features/relay-chat/components/RelayHubSidebar.svelte");
        expect(sidebar).toContain("orderedKnownRoomNames");
        expect(sidebar).toContain("onpersistroomorder");
        expect(sidebar).toContain("onreorderrooms");
        const modals = src("meshchatx/src/frontend/features/relay-chat/components/RelayChatModals.svelte");
        expect(modals).toContain("ctx_leave_room");
        expect(modals).toContain("ctx_disconnect_hub");
        expect(modals).toContain("ctx_connect_hub");
        expect(modals).toContain("onleaveroom");
        expect(modals).toContain("ondisconnecthub");
    });

    it("boot uses svelte-i18n and live App.svelte without vue-i18n createI18n", () => {
        const main = src("meshchatx/src/frontend/main.ts");
        expect(main).toContain("initSvelteI18n");
        expect(main).toContain("features/app-shell/App.svelte");
        expect(main).toContain("getCurrentUiLocale");
        expect(main).not.toContain('from "vue-i18n"');
        expect(main).not.toContain("configureVueIslands");
        expect(main).not.toContain("i18n.global.locale");
    });

    it("plugin routes register via hashRouter featureLoad only", () => {
        const host = src("meshchatx/src/frontend/js/plugins/PluginHost.ts");
        expect(host).toContain("featureLoad:");
        expect(host).not.toContain("FeaturePageHost.vue");
    });

    it("command palette and sidebar resolve routes by registry path not dotted name", () => {
        const palette = src("meshchatx/src/frontend/features/app-shell/components/CommandPalette.svelte");
        expect(palette).toContain('import { navigate } from "../../../shell/hashRouter.js"');
        expect(palette).toContain("navigate(result.route)");
        expect(palette).toContain("void navigate(peerRoute)");
        expect(palette).not.toContain("`#/${result.route.name");
        expect(palette).not.toContain("window.location.hash = `#/${");
        const link = src("meshchatx/src/frontend/features/app-shell/components/SidebarLink.svelte");
        expect(link).toContain("resolveTarget(to)");
        expect(link).not.toContain("`#/${to.name}`");
    });

    it("call overlay keeps minimized hangup and ended voicemail playback", () => {
        const overlay = src("meshchatx/src/frontend/features/call/components/CallOverlay.svelte");
        expect(overlay).toContain("AudioWaveformPlayer");
        expect(overlay).toContain("getVoicemailAudioSrc");
        expect(overlay).toContain("isMinimized && !isEnded");
        expect(overlay).toContain("phone-hangup");
        expect(overlay).toContain("tx_bytes");
        expect(overlay).toContain("rx_bytes");
        expect(overlay).not.toContain("audio_bytes_sent");
        expect(overlay).not.toContain("voicemailStatus: _voicemailStatus");
    });

    it("call page redial clears ended state and play-latest actually plays audio", () => {
        const handlers = src("meshchatx/src/frontend/features/call/lib/callPageHandlers.ts");
        expect(handlers).toContain("pageState.isCallEnded = false");
        expect(handlers).toContain("pageState.wasDeclined = false");
        expect(handlers).toContain("pageState.wasVoicemail = false");
        expect(handlers).toContain("pageState.lastCall = null");
        expect(handlers).toContain("playVoicemail(voicemail)");
        expect(handlers).not.toMatch(
            /function onPlayLatestVoicemail\(\)[^{]*\{\s*if \(pageState\.voicemails\.length > 0\) onMarkVoicemailRead/
        );
        const controller = src("meshchatx/src/frontend/features/call/lib/callPageController.ts");
        expect(controller).toContain("async playVoicemail");
        expect(controller).toContain("/api/v1/telephone/voicemails/");
    });

    it("settings auth enable navigates to auth and telephony uses LXST toasts", () => {
        const settings = src("meshchatx/src/frontend/features/settings/components/SettingsPage.svelte");
        expect(settings).toContain('import { navigate } from "../../../shell/hashRouter.js"');
        expect(settings).toContain("async function onAuthEnabledChange");
        expect(settings).toContain('navigate({ name: "auth" })');
        expect(settings).toContain("serverSecurity = { ...serverSecurity, auth_enabled: !!value }");
        expect(settings).toContain("onauthenabledchange={onAuthEnabledChange}");
        expect(settings).toContain("async function onTelephoneEnabledChange");
        expect(settings).toContain('t("call.telephony_enabled")');
        expect(settings).toContain('t("call.telephony_disabled")');
        expect(settings).toContain('t("call.failed_to_update_call_settings")');
        expect(settings).toContain("onenabledchange={onTelephoneEnabledChange}");
        expect(settings).not.toContain('onauthenabledchange={(val) => updateConfigField("auth_enabled", val)}');
        expect(settings).not.toContain('onenabledchange={(val) => updateConfigField("telephone_enabled", val)}');
    });

    it("auth login setup about propagation and rnode entry points keep Vue paths", () => {
        const auth = src("meshchatx/src/frontend/features/auth/index.ts");
        expect(auth).toContain('name: "auth"');
        expect(auth).toContain('path: "/auth"');
        const authPage = src("meshchatx/src/frontend/features/auth/AuthPage.svelte");
        expect(authPage).toContain("API_AUTH_STATUS");
        expect(authPage).toContain("API_AUTH_LOGIN");
        expect(authPage).toContain("API_AUTH_SETUP");
        expect(authPage).toContain("window.location.reload()");

        const about = src("meshchatx/src/frontend/features/about/index.ts");
        expect(about).toContain('path: "/about"');
        const aboutHero = src("meshchatx/src/frontend/features/about/components/AboutHeroSection.svelte");
        expect(aboutHero).toContain('href="#/licenses"');
        const backupApi = src("meshchatx/src/frontend/features/about/lib/backupApi.ts");
        expect(backupApi).toContain("/api/v1/database/backup/download");
        expect(backupApi).toContain("/api/v1/database/snapshots");
        expect(backupApi).toContain("/api/v1/database/restore");

        const prop = src("meshchatx/src/frontend/features/propagation-nodes/index.ts");
        expect(prop).toContain('path: "/propagation-nodes"');
        const propApi = src("meshchatx/src/frontend/features/propagation-nodes/lib/propagationApi.ts");
        const propConstants = src("meshchatx/src/frontend/features/propagation-nodes/lib/constants.ts");
        expect(propApi).toContain("PROPAGATION_NODES_API_BASE");
        expect(propApi).toContain("PROPAGATION_NODE_RESTART_ENDPOINT");
        expect(propApi).toContain("ANNOUNCE_API_ENDPOINT");
        expect(propConstants).toContain("/api/v1/lxmf/propagation-nodes");
        expect(propConstants).toContain("/api/v1/lxmf/propagation-node/restart");
        expect(propConstants).toContain("/api/v1/announce");
        const propSettings = src(
            "meshchatx/src/frontend/features/settings/components/sections/PropagationSettingsSection.svelte"
        );
        expect(propSettings).toContain('href="#/propagation-nodes"');

        const rnode = src("meshchatx/src/frontend/features/rnode-flasher/index.ts");
        expect(rnode).toContain('path: "/tools/rnode-flasher"');
        const tools = src("meshchatx/src/frontend/js/registries/coreToolsEntries.ts");
        expect(tools).toContain('name: "rnode-flasher"');
        expect(tools).toContain('href: "/rnode-flasher/index.html"');
        const commands = src("meshchatx/src/frontend/js/registries/coreCommandEntries.ts");
        expect(commands).toContain('id: "nav-rnode-flasher"');
        expect(commands).toContain('route: { name: "rnode-flasher" }');
        const flasherPage = src("meshchatx/src/frontend/features/rnode-flasher/RNodeFlasherPage.svelte");
        expect(flasherPage).toContain('href="/rnode-flasher/index.html"');
        const registerAll = src("meshchatx/src/frontend/features/registerAllFeatures.ts");
        expect(registerAll).toContain("registerAuthFeature()");
        expect(registerAll).toContain("registerAboutFeature()");
        expect(registerAll).toContain("registerPropagationNodesFeature()");
        expect(registerAll).toContain("registerRNodeFlasherFeature()");
        expect(registerAll).toContain("registerCallFeature()");
    });

    it("plugin enable hot-loads pluginHost after POST enable", () => {
        const section = src(
            "meshchatx/src/frontend/features/settings/components/sections/PluginsSettingsSection.svelte"
        );
        expect(section).toContain("pluginHost.loadEnabledPlugins");
        expect(section).toContain("getCurrentUiLocale");
        expect(section).toContain("/api/v1/plugins/${encodeURIComponent(pluginId)}/enable");
        expect(section).toContain("plugins.settings.confirm_remove");
        expect(section).not.toContain('t("plugins.settings.remove_confirm"');
    });

    it("network visualiser attaches announce meta and opens aspect-aware destinations", () => {
        const nav = src("meshchatx/src/frontend/features/network-visualiser/lib/visualiserNavigation.ts");
        expect(nav).toContain("openAnnounceDestination");
        expect(nav).toContain("attachAnnounceMetaToNodes");
        expect(nav).toContain('aspect === "lxmf.delivery"');
        expect(nav).toContain('aspect === "nomadnetwork.node"');
        const runner = src("meshchatx/src/frontend/features/network-visualiser/lib/visualiserUpdateRunner.ts");
        expect(runner).toContain("attachAnnounceMetaToNodes");
        const setup = src("meshchatx/src/frontend/features/network-visualiser/lib/visualiserRendererSetup.ts");
        expect(setup).toContain("openAnnounceDestination");
        expect(setup).toContain("onDoubleClickNode");
        expect(setup).not.toContain("window.location.hash = `#/messages/${meta.hash}`");
    });

    it("archives page falls back to hashRouter for open-live and content clicks", () => {
        const page = src("meshchatx/src/frontend/features/archives/ArchivesPage.svelte");
        expect(page).toContain("router as hashRouter");
        expect(page).toContain("activeRouter");
        expect(page).toContain("openInNomadnet(archive, activeRouter)");
        expect(page).toContain("handleArchiveContentClick(event, activeRouter)");
        expect(page).toContain("API_NOMADNET_ARCHIVES_RECRAWL");
    });

    it("frontend tree has no remaining .vue sources", () => {
        const root = resolve(ROOT, "meshchatx/src/frontend");
        const vueFiles = [];
        function walk(dir) {
            for (const name of readdirSync(dir)) {
                const p = join(dir, name);
                if (statSync(p).isDirectory()) walk(p);
                else if (name.endsWith(".vue")) vueFiles.push(p);
            }
        }
        walk(root);
        expect(vueFiles).toEqual([]);
    });

    it("sidebar identities and interface docs deep links use registered hash paths", () => {
        const footer = src("meshchatx/src/frontend/features/app-shell/components/AppSidebarAccountFooter.svelte");
        const panel = src("meshchatx/src/frontend/features/app-shell/components/AppShellSidebarPanel.svelte");
        const docsHint = src("meshchatx/src/frontend/features/interfaces/components/BundledDocsHint.svelte");
        expect(footer).toContain('href="#/identities"');
        expect(footer).toContain('window.location.hash = "#/identities"');
        expect(footer).not.toContain("#/settings/identities");
        expect(panel).toContain('onnavigatetoidentities={() => void navigate({ name: "identities" })}');
        expect(docsHint).toContain("openBundledReticulumManualPath");
        expect(docsHint).toContain("openBundledReticulumManualPath(router, docsRelPath)");
        expect(docsHint).not.toContain("#/docs?");
    });

    it("conversation start-call posts telephone API and popout uses hash URL", () => {
        const viewer = src("meshchatx/src/frontend/features/messages/components/ConversationViewer.svelte");
        expect(viewer).toContain("startCallWithSelectedPeer");
        expect(viewer).toContain("openConversationPopout");
        expect(viewer).toContain("/api/v1/telephone/call/${selectedHash}");
        expect(viewer).toContain("#/popout/messages/");
        expect(viewer).toContain("onstartcall={() => void startCallWithSelectedPeer()}");
        expect(viewer).toContain("onpopout={() => openConversationPopout()}");
        expect(viewer).not.toContain('GlobalEmitter.emit("start-call"');
    });

    it("nomad and relay popouts open hash URLs and nomad render options match renderer contract", () => {
        const nomad = src("meshchatx/src/frontend/features/nomadnetwork/components/NomadNetworkPage.svelte");
        const relay = src("meshchatx/src/frontend/features/relay-chat/components/RelayChatPage.svelte");
        expect(nomad).toContain("#/popout/nomadnetwork/");
        expect(nomad).toContain("nomad_micron_wasm_use");
        expect(nomad).toContain("nomadDestinationHash");
        expect(nomad).toContain("renderMarkdown");
        expect(nomad).toContain("preloadNomadMicronWasm");
        expect(nomad).toContain("patchServerConfig");
        expect(nomad).toContain("applyNomadMicronDefaultEngine");
        expect(nomad).not.toContain("window.open(target,");
        expect(nomad).not.toContain("wasmEnabled:");
        expect(relay).toContain("#/popout/relay-chat/");
        expect(relay).not.toContain("const target = `/popout/relay-chat/");
    });

    it("nomad crash-tab shell, host, recovery, and keepAlive stay wired after Svelte migration", () => {
        const shell = src("meshchatx/src/frontend/js/nomadCrashTabShell.ts");
        const crashTab = src("meshchatx/src/frontend/features/nomadnetwork/components/NomadCrashTab.svelte");
        const host = src("meshchatx/src/frontend/features/nomadnetwork/components/NomadPageRendererHost.svelte");
        const page = src("meshchatx/src/frontend/features/nomadnetwork/components/NomadNetworkPage.svelte");
        const browser = src("meshchatx/src/frontend/features/nomadnetwork/components/NomadNetworkBrowser.svelte");
        const feature = src("meshchatx/src/frontend/features/nomadnetwork/index.ts");
        const hostLib = src("meshchatx/src/frontend/features/nomadnetwork/lib/nomadCrashTabHost.ts");
        const bridge = src("meshchatx/src/frontend/features/nomadnetwork/lib/nomadCrashTabBridge.ts");
        const hung = src("meshchatx/src/frontend/features/nomadnetwork/components/NomadCrashTabHungAlert.svelte");
        const html = src("meshchatx/src/frontend/nomad-crash-tab.html");
        const outlet = src("meshchatx/src/frontend/shell/PageOutlet.svelte");
        const outletKey = src("meshchatx/src/frontend/shell/pageOutletMountKey.ts");

        expect(shell).toContain('NOMAD_CRASH_TAB_CHANNEL = "nomad-crash-tab"');
        expect(shell).toContain("nomadCrashTabRendererUrl");
        expect(shell).toContain("/nomad-crash-tab.html");
        expect(html).toContain("nomadCrashTabMain");
        expect(crashTab).toContain("nomadCrashTabRendererUrl");
        expect(crashTab).toContain('sandbox="allow-scripts"');
        expect(crashTab).toContain("NomadCrashTabHungAlert");
        expect(crashTab).toContain("abortRender");
        expect(bridge).toContain("NOMAD_CRASH_TAB_CHANNEL");
        expect(bridge).toContain("NomadCrashTabWatchdog");
        expect(hung).toContain("nomadnet.crash_tab_title");
        expect(host).toContain("showCrashTabHost");
        expect(host).toContain("<NomadCrashTab");
        expect(host).toContain("active={active && isActive}");
        expect(host).toContain("oncrashtababorted");
        expect(hostLib).toContain("shouldShowCrashTabHost");
        expect(hostLib).toContain("canRetryCrashTabRender");
        expect(page).toContain("shouldShowCrashTabHost");
        expect(page).toContain("NomadPageRendererHost");
        expect(page).toContain("{crashTabPageContent}");
        expect(page).toContain("{canRetryCrashTabRender}");
        expect(page).toContain("isCrashTabRendering");
        expect(page).toContain("beginCrashTabRenderWait");
        expect(page).toContain("oncrashtababorted");
        expect(page).toContain("oncrashtabrenderstarted");
        expect(page).toContain("oncrashtabrenderdone");
        expect(page).toContain("oncrashtabhung");
        expect(page).toContain("pageRenderAborted = false");
        expect(page).toContain("rendererHost?.abortRender()");
        expect(page).not.toContain("canRetryCrashTabRender={true}");
        expect(page).not.toContain("nomadCrashTabBackground = bg");
        expect(browser).toContain("active={tab.id === selectedTabId}");
        expect(feature).toContain("meta: { keepAlive: true }");
        expect(outlet).toContain("keepAliveCache");
        expect(outletKey).toContain("route.meta?.keepAlive");
    });

    it("filesync and bots unsubscribe websocket-reconnected with stable handlers", () => {
        const filesync = src("meshchatx/src/frontend/features/filesync/RnsFilesyncPage.svelte");
        const bots = src("meshchatx/src/frontend/features/bots/BotsPage.svelte");
        expect(filesync).toContain("function onWebsocketReconnected()");
        expect(filesync).toContain('GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected)');
        expect(filesync).toContain('GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected)');
        expect(bots).toContain("function onWebsocketReconnected()");
        expect(bots).toContain('GlobalEmitter.on("websocket-reconnected", onWebsocketReconnected)');
        expect(bots).toContain('GlobalEmitter.off("websocket-reconnected", onWebsocketReconnected)');
    });

    it("command palette awaits navigate before compose-new-message emit", () => {
        const palette = src("meshchatx/src/frontend/features/app-shell/components/CommandPalette.svelte");
        const overlays = src("meshchatx/src/frontend/features/app-shell/components/AppShellOverlays.svelte");
        expect(palette).toContain('await Promise.resolve(onnavigate({ name: "messages" }))');
        expect(palette).toContain('await navigate({ name: "messages" })');
        expect(palette).toContain('GlobalEmitter.emit("compose-new-message")');
        expect(overlays).toContain("return navigate(route as never)");
    });

    it("messages viewer restores stamp path dialogs, image context actions, and field-preserving retry", () => {
        const viewer = src("meshchatx/src/frontend/features/messages/components/ConversationViewer.svelte");
        const header = src("meshchatx/src/frontend/features/messages/components/ConversationViewerHeaderHost.svelte");
        const bridge = src("meshchatx/src/frontend/features/messages/components/ConversationViewerModalsBridge.svelte");
        const host = src("meshchatx/src/frontend/features/messages/components/ConversationViewerModalsHost.svelte");
        const lightboxMenu = src(
            "meshchatx/src/frontend/features/messages/components/ConversationLightboxContextMenu.svelte"
        );
        const lightboxLib = src("meshchatx/src/frontend/features/messages/lib/conversationViewerLightbox.ts");
        const mutations = src("meshchatx/src/frontend/features/messages/lib/conversationViewerMutations.ts");
        const drafts = src("meshchatx/src/frontend/features/messages/lib/conversationDrafts.ts");
        const draftConstants = src("meshchatx/src/frontend/features/messages/lib/constants.ts");
        const pathActions = src("meshchatx/src/frontend/features/messages/lib/conversationPathActions.ts");

        expect(header).toContain("onstampinfoclick");
        expect(header).toContain("onsignalmetricsclick");
        expect(viewer).toContain("formatStampInfoAlert");
        expect(viewer).toContain("formatPeerPathClickAlert");
        expect(viewer).toContain("formatSignalMetricsAlert");
        expect(viewer).not.toContain("#/interfaces?highlight=");
        expect(viewer).toContain("retryOutboundMessageItem");
        expect(viewer).toContain("retryAllFailedOrCancelledMessages");
        expect(viewer).toContain("listFailedOrCancelledOutbound");
        expect(viewer).toContain("copyMessageImageToClipboard");
        expect(viewer).toContain("saveMessageImageToStickers");
        expect(viewer).toContain("saveMessageImageToGifs");
        expect(viewer).toContain("oncontextmenulightbox");
        expect(viewer).toContain("oncopylightbox");
        expect(viewer).toContain("downloadLightboxImage");
        expect(viewer).toContain("copyLightboxImage");
        expect(bridge).toContain("oncopyimagecontextmenu={() => oncopyimage?.()}");
        expect(bridge).toContain("onsavestickercontextmenu={() => onsavesticker?.()}");
        expect(bridge).toContain("onsavegifcontextmenu={() => onsavegif?.()}");
        expect(bridge).toContain("oncontextmenulightbox");
        expect(bridge).toContain("oncopylightbox");
        expect(host).toContain("oncontextmenu={(event) => oncontextmenulightbox?.(event)}");
        expect(host).toContain("ConversationLightboxContextMenu");
        expect(lightboxMenu).toContain("messages.copy_image_to_clipboard");
        expect(lightboxMenu).toContain("messages.save_image_to_device");
        expect(lightboxMenu).not.toContain("stickers.save_to_library");
        expect(lightboxLib).toContain("lightboxActiveChatItem");
        expect(lightboxLib).toContain("openLightboxContextMenu");
        expect(mutations).toContain("/api/v1/lxmf-messages/send");
        expect(mutations).toContain("fields: msg.fields");
        expect(mutations).toContain("/api/v1/stickers");
        expect(mutations).toContain("/api/v1/gifs");
        expect(mutations).toContain("copyImageBlobToClipboard");
        expect(mutations).not.toContain("delivery_method");
        expect(drafts).toContain("LEGACY_COMPOSE_DRAFTS_STORAGE_KEY");
        expect(draftConstants).toContain('LEGACY_COMPOSE_DRAFTS_STORAGE_KEY = "meshchat.drafts"');
        expect(pathActions).toContain("formatStampInfoAlert");
        expect(pathActions).toContain("path_stale_hint");
        expect(pathActions).toContain("path_unresponsive_hint");
    });
});
