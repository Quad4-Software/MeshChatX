// SPDX-License-Identifier: 0BSD

/**
 * Oracles for UI navigation and keep-alive performance bugs.
 */

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { navRouteIsActive } from "../../meshchatx/src/frontend/js/navRouteActive.js";
import { shouldPollKeepAliveEmbedded } from "../../meshchatx/src/frontend/js/keepAlivePoll.js";

const ROOT = resolve(import.meta.dirname, "../..");

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

describe("shell keepAlive / stableKey route contracts", () => {
    it("messages uses stableKey and nomad/map use keepAlive", () => {
        const messages = readFileSync(resolve(ROOT, "meshchatx/src/frontend/features/messages/index.ts"), "utf8");
        const nomad = readFileSync(resolve(ROOT, "meshchatx/src/frontend/features/nomadnetwork/index.ts"), "utf8");
        const map = readFileSync(resolve(ROOT, "meshchatx/src/frontend/features/map/index.ts"), "utf8");
        const nomadBrowser = readFileSync(
            resolve(ROOT, "meshchatx/src/frontend/features/nomadnetwork/components/NomadNetworkBrowser.svelte"),
            "utf8"
        );
        expect(messages).toContain("stableKey: true");
        expect(nomad).toContain("keepAlive: true");
        expect(map).toContain("keepAlive: true");
        expect(nomadBrowser).toContain("routeHashWatchReady");
        expect(nomadBrowser).toContain("$effect");
    });
});
