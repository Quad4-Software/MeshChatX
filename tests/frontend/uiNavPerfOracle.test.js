// SPDX-License-Identifier: 0BSD

/**
 * Oracles for UI navigation and keep-alive performance bugs.
 */

import { describe, expect, it } from "vitest";
import { navRouteIsActive } from "../../meshchatx/src/frontend/js/navRouteActive.js";
import { shouldPollKeepAliveEmbedded } from "../../meshchatx/src/frontend/js/keepAlivePoll.js";

describe("navRouteIsActive", () => {
    it("matches exact names and dotted children, not siblings", () => {
        expect(navRouteIsActive("interfaces", "interfaces")).toBe(true);
        expect(navRouteIsActive("interfaces", "interfaces.add")).toBe(true);
        expect(navRouteIsActive("interfaces", "interfaces.edit")).toBe(true);
        expect(navRouteIsActive("messages", "messages")).toBe(true);
        expect(navRouteIsActive("interfaces", "settings")).toBe(false);
        expect(navRouteIsActive("call", "call-popout")).toBe(false);
        expect(navRouteIsActive("messages", "nomadnetwork")).toBe(false);
        expect(navRouteIsActive("", "interfaces")).toBe(false);
        expect(navRouteIsActive("interfaces", null)).toBe(false);
        expect(navRouteIsActive(undefined, "interfaces")).toBe(false);
    });
});

describe("keep-alive poll gates", () => {
    it("skips polls for inactive embedded tabs and keeps them for the visible tab", () => {
        expect(shouldPollKeepAliveEmbedded(true, false)).toBe(false);
        expect(shouldPollKeepAliveEmbedded(true, true)).toBe(true);
        expect(shouldPollKeepAliveEmbedded(false, false)).toBe(true);
        expect(shouldPollKeepAliveEmbedded(false, true)).toBe(true);
    });
});
