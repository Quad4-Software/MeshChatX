// SPDX-License-Identifier: 0BSD

import { readFileSync } from "fs";
import { join } from "path";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { rnodeIntegrityKeyForSrc } from "../../meshchatx/src/frontend/js/rnode/rnodeIntegrityKey.js";
import MessagesPage from "../../meshchatx/src/frontend/components/messages/MessagesPage.vue";
import MapPage from "../../meshchatx/src/frontend/components/map/MapPage.vue";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

describe("map, messages, and rnode integrity contracts", () => {
    it("RNode SRI key for zip.min.js matches integrity.json (not js/zip.min.js)", () => {
        const integrity = JSON.parse(
            readFileSync(join(process.cwd(), "meshchatx/src/frontend/public/rnode-flasher/js/integrity.json"), "utf8")
        ).files;
        const key = rnodeIntegrityKeyForSrc("/rnode-flasher/js/zip.min.js", integrity);
        expect(key).toBe("zip.min.js");
        expect(integrity[key]).toMatch(/^sha384-/);

        const nested = rnodeIntegrityKeyForSrc("/rnode-flasher/js/crypto-js@3.9.1-1/core.js", integrity);
        expect(nested).toBe("crypto-js@3.9.1-1/core.js");

        const dist = rnodeIntegrityKeyForSrc("/rnode-flasher/js/web-serial-polyfill@1.0.15/dist/serial.js", integrity);
        expect(dist).toBe("web-serial-polyfill@1.0.15/dist/serial.js");
    });

    it("MessagesPage syncUnreadCount does not overwrite badge with a partial page count", () => {
        GlobalState.unreadConversationsCount = 12;
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const ctx = {
            conversations: [{ is_unread: true }, { is_unread: true }, { is_unread: false }],
            hasMoreConversations: true,
            filterUnreadOnly: false,
            selectedFolderId: null,
            conversationSearchTerm: "",
        };

        MessagesPage.methods.syncUnreadCount.call(ctx);
        expect(GlobalState.unreadConversationsCount).toBe(12);
        expect(emitSpy).toHaveBeenCalledWith("notifications-changed");
        emitSpy.mockRestore();
    });

    it("Map resolveMyLocationWgs84 prefers lxmf_address_hash telemetry over identity_hash", async () => {
        const lx = "aa".repeat(16);
        const id = "bb".repeat(16);
        const ctx = {
            config: {
                location_source: "browser",
                lxmf_address_hash: lx,
                identity_hash: id,
            },
            telemetryList: [
                {
                    destination_hash: lx,
                    telemetry: { location: { longitude: 11.1, latitude: 22.2 } },
                },
            ],
        };

        const loc = await MapPage.methods.resolveMyLocationWgs84.call(ctx);
        expect(loc).toEqual({ lon: 11.1, lat: 22.2 });
    });

    it("mapViewStateKey scopes TileCache map state by identity", async () => {
        const { mapViewStateKey, LEGACY_MAP_STATE_KEY } =
            await import("../../meshchatx/src/frontend/js/mapStateKeys.js");
        const a = "aa".repeat(16);
        const b = "bb".repeat(16);
        expect(mapViewStateKey(a)).not.toBe(mapViewStateKey(b));
        expect(mapViewStateKey(a)).not.toBe(LEGACY_MAP_STATE_KEY);
        expect(mapViewStateKey(a, "tab-1")).toContain(a.slice(0, 16));
        expect(mapViewStateKey(a, "tab-1")).not.toBe(mapViewStateKey(b, "tab-1"));
    });

    it("stale remote overlay generation removes layers added after a newer load started", async () => {
        const removed = [];
        const ctx = {
            map: {},
            remoteOverlayLoadGeneration: 0,
            remoteOverlayLayers: {},
            removeRemoteOverlayLayer(id) {
                removed.push(id);
                delete this.remoteOverlayLayers[id];
            },
            async ensureRemoteOverlayLayer(overlay) {
                const id = String(overlay.id);
                this.remoteOverlayLayers[id] = {
                    layer: { setVisible: vi.fn() },
                };
                // Simulate a newer overlay list while fetch is in flight.
                this.remoteOverlayLoadGeneration = 2;
            },
        };
        await MapPage.methods.onRemoteOverlaysChanged.call(ctx, [
            { id: "ov1", visible: true, status: "ready", format: "geojson" },
        ]);
        expect(removed).toEqual(["ov1"]);
        expect(ctx.remoteOverlayLayers.ov1).toBeUndefined();
    });
});
