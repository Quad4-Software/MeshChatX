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
        expect(settings).toContain("onallowlistchange={onWebUiAllowlistChange}");
        expect(settings).not.toContain('updateConfigField("web_ui_ip_allowlist"');
        const helpers = src("meshchatx/src/frontend/features/settings/lib/settingsPageHelpers.ts");
        expect(helpers).toContain('patch("/api/v1/server/security"');
        expect(helpers).toContain("web_ui_ip_allowlist");
        const actions = src("meshchatx/src/frontend/features/settings/lib/maintenanceActions.ts");
        expect(actions).toContain("/api/v1/stickers/export");
        expect(actions).toContain("/api/v1/gifs/export");
        expect(actions).toContain("/api/v1/stickers/import");
        expect(actions).toContain("/api/v1/gifs/import");
    });

    it("interfaces I2P add gates require transport and single instance", () => {
        const page = src("meshchatx/src/frontend/features/interfaces/AddInterfacePage.svelte");
        expect(page).toContain("canAddI2PInterface");
        expect(page).toContain("hasExistingI2PInterface");
        expect(page).toContain("interfaces.i2p_transport_required");
        expect(page).toContain("interfaces.i2p_already_exists");
        const i2p = src("meshchatx/src/frontend/features/interfaces/components/AddInterfaceI2pDetails.svelte");
        expect(i2p).toContain("interfaces.i2p_transport_required");
        expect(i2p).toContain("interfaces.i2p_already_exists");
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
