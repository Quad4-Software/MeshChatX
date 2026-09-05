// SPDX-License-Identifier: 0BSD

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { clearRoutes, registerRoute } from "../../meshchatx/src/frontend/js/registries/routeRegistry.js";
import {
    getCurrentRoute,
    navigate,
    parseHashLocation,
    resetForTests,
    resolveRoute,
    resolveTarget,
    setNavigationGuard,
    start,
    subscribe,
} from "../../meshchatx/src/frontend/shell/hashRouter.js";

const load = () => Promise.resolve({ default: {} });

function registerTestRoutes() {
    clearRoutes();
    registerRoute({ name: "messages", path: "/messages/:destinationHash?", mount: "svelte", load });
    registerRoute({ name: "about", path: "/about", mount: "svelte", load });
    registerRoute({ name: "auth", path: "/auth", mount: "svelte", load });
    registerRoute({ name: "map", path: "/map", mount: "svelte", load, meta: { keepAlive: true } });
    registerRoute({
        name: "relay-chat-popout",
        path: "/popout/relay-chat/:hubHash/:room?",
        mount: "svelte",
        load,
    });
}

describe("hashRouter", () => {
    beforeEach(() => {
        registerTestRoutes();
        window.location.hash = "";
    });

    afterEach(() => {
        resetForTests();
        clearRoutes();
    });

    it("splits path, query, and fragment", () => {
        expect(parseHashLocation("#/about?tab=x#anchor")).toEqual({
            path: "/about",
            search: "tab=x",
            hash: "#anchor",
        });
    });

    it("matches optional params", () => {
        expect(resolveRoute("/messages").name).toBe("messages");
        expect(resolveRoute("/messages").params).toEqual({});
        const withHash = resolveRoute("/messages/abc123");
        expect(withHash.name).toBe("messages");
        expect(withHash.params).toEqual({ destinationHash: "abc123" });
    });

    it("requires non-optional params", () => {
        expect(resolveRoute("/popout/relay-chat").matched).toBe(false);
        expect(resolveRoute("/popout/relay-chat/aabb").params).toEqual({ hubHash: "aabb" });
        expect(resolveRoute("/popout/relay-chat/aabb/general").params).toEqual({
            hubHash: "aabb",
            room: "general",
        });
    });

    it("rejects extra segments", () => {
        expect(resolveRoute("/about/extra").matched).toBe(false);
    });

    it("carries meta and query onto the route", () => {
        const route = resolveRoute("/map", "lat=1&lon=2", "#frag");
        expect(route.meta.keepAlive).toBe(true);
        expect(route.query).toEqual({ lat: "1", lon: "2" });
        expect(route.hash).toBe("#frag");
        expect(route.fullPath).toBe("/map?lat=1&lon=2#frag");
    });

    it("builds hrefs from named targets", () => {
        expect(resolveTarget({ name: "messages", params: { destinationHash: "ff00" } })).toBe("/messages/ff00");
        expect(resolveTarget({ name: "messages" })).toBe("/messages");
        expect(resolveTarget({ name: "about", hash: "#about-database-backups" })).toBe(
            "/about#about-database-backups"
        );
        expect(resolveTarget({ name: "map", query: { lat: 1, zoom: null } })).toBe("/map?lat=1");
    });

    it("redirects the root path to messages", async () => {
        window.location.hash = "#/";
        start();
        await Promise.resolve();
        expect(getCurrentRoute()?.name).toBe("messages");
    });

    it("notifies subscribers on navigation", async () => {
        window.location.hash = "#/about";
        start();
        await Promise.resolve();
        const seen = [];
        const unsubscribe = subscribe((route) => seen.push(route?.name ?? null));
        await navigate({ name: "map" });
        await new Promise((resolve) => setTimeout(resolve, 0));
        unsubscribe();
        expect(seen[0]).toBe("about");
        expect(seen).toContain("map");
    });

    it("honours a guard redirect", async () => {
        setNavigationGuard((to) => (to.name === "auth" ? { allow: true } : { allow: false, redirect: "/auth" }));
        window.location.hash = "#/about";
        start();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(getCurrentRoute()?.name).toBe("auth");
    });
});
