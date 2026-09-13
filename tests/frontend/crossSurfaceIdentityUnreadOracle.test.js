// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";
import {
    isLocalMapServiceUrl,
    isPrivateOrLocalHostname,
} from "../../meshchatx/src/frontend/js/mapLocalUrl.js";

function src(rel) {
    return readFileSync(join(process.cwd(), rel), "utf8");
}

describe("cross-surface identity unread oracle", () => {
    it("identity switch clears unread counters and shell WS handlers refresh them", () => {
        const identity = src("meshchatx/src/frontend/features/app-shell/lib/appShellIdentity.ts");
        const handlers = src("meshchatx/src/frontend/features/app-shell/lib/appShellWsHandlers.ts");
        const nav = src("meshchatx/src/frontend/features/app-shell/lib/appShellNav.ts");
        expect(identity).toContain("GlobalState.unreadConversationsCount = 0");
        expect(identity).toContain("GlobalState.missedCallsCount = 0");
        expect(identity).toContain("GlobalState.relayChatUnreadCount = 0");
        expect(handlers).toContain("createShellWsHandlers");
        expect(nav).toContain("updateUnreadConversationsCount");
        expect(nav).toContain("updateRelayChatUnreadCount");
    });
});

describe("map local URL oracle", () => {
    it("treats only RFC1918 and loopback hosts as local, not all 172.*", () => {
        // Oracle: 172.16.0.0/12 is private. 172.15.x and 172.32.x are not.
        expect(isPrivateOrLocalHostname("127.0.0.1")).toBe(true);
        expect(isPrivateOrLocalHostname("10.1.2.3")).toBe(true);
        expect(isPrivateOrLocalHostname("192.168.1.1")).toBe(true);
        expect(isPrivateOrLocalHostname("172.16.0.1")).toBe(true);
        expect(isPrivateOrLocalHostname("172.31.255.255")).toBe(true);
        expect(isPrivateOrLocalHostname("172.15.0.1")).toBe(false);
        expect(isPrivateOrLocalHostname("172.32.0.1")).toBe(false);
        expect(isPrivateOrLocalHostname("8.8.8.8")).toBe(false);
        expect(isPrivateOrLocalHostname("tiles.openstreetmap.org")).toBe(false);
        expect(isPrivateOrLocalHostname("10.evil.com")).toBe(false);
        expect(isPrivateOrLocalHostname("192.168.example.com")).toBe(false);
        expect(isPrivateOrLocalHostname("172.16.evil.com")).toBe(false);
        expect(isLocalMapServiceUrl("http://10.1.2.3:8080/tiles")).toBe(true);
        expect(isLocalMapServiceUrl("http://10.0.0.1@example.com/tiles")).toBe(false);
        expect(isLocalMapServiceUrl("http://[")).toBe(false);
        expect(isLocalMapServiceUrl("https://[::")).toBe(false);
        expect(isLocalMapServiceUrl("javascript:alert(1)")).toBe(false);
    });
});
