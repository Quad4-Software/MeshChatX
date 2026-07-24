// SPDX-License-Identifier: 0BSD

import { readFileSync } from "fs";
import { join } from "path";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { rnodeIntegrityKeyForSrc } from "../../meshchatx/src/frontend/js/rnode/rnodeIntegrityKey.js";
import MessagesPage from "../../meshchatx/src/frontend/components/messages/MessagesPage.vue";
import MapPage from "../../meshchatx/src/frontend/components/map/MapPage.vue";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import GlobalEmitter from "../../meshchatx/src/frontend/js/GlobalEmitter";

describe("follow-up oracles from exploratory hunt", () => {
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
});
