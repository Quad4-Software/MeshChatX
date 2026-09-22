// SPDX-License-Identifier: 0BSD

/**
 * Oracles for PageOutlet remount keying (stableKey / keepAlive / fullPath).
 */

import { describe, expect, it } from "vitest";
import { pageOutletMountKey } from "../../meshchatx/src/frontend/shell/pageOutletMountKey.js";

describe("pageOutletMountKey", () => {
    it("keeps stableKey and keepAlive mounts on route name across param changes", () => {
        expect(
            pageOutletMountKey({
                name: "messages",
                fullPath: "/messages/aaa",
                meta: { stableKey: true },
            })
        ).toBe("messages");
        expect(
            pageOutletMountKey({
                name: "messages",
                fullPath: "/messages/bbb",
                meta: { stableKey: true },
            })
        ).toBe("messages");
        expect(
            pageOutletMountKey({
                name: "nomadnetwork",
                fullPath: "/nomadnetwork/aaa",
                meta: { keepAlive: true },
            })
        ).toBe("nomadnetwork");
        expect(
            pageOutletMountKey({
                name: "nomadnetwork",
                fullPath: "/nomadnetwork/bbb",
                meta: { keepAlive: true },
            })
        ).toBe("nomadnetwork");
        expect(
            pageOutletMountKey({
                name: "map",
                fullPath: "/map",
                meta: { keepAlive: true },
            })
        ).toBe("map");
    });

    it("remounts ordinary routes when fullPath changes", () => {
        expect(
            pageOutletMountKey({
                name: "settings",
                fullPath: "/settings",
                meta: {},
            })
        ).toBe("settings:/settings");
        expect(
            pageOutletMountKey({
                name: "settings",
                fullPath: "/settings?tab=appearance",
                meta: {},
            })
        ).toBe("settings:/settings?tab=appearance");
    });
});
