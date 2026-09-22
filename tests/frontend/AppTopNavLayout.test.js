import { describe, it, expect, beforeEach } from "vitest";

import {
    APP_TOP_NAV_LAYOUT_KEY,
    DEFAULT_TOP_NAV_ITEM_IDS,
    normalizeTopNavItemIds,
    orderedTopNavItems,
    resetTopNavItemIds,
    resolveTopNavItemIds,
    saveTopNavItemIds,
    topNavLayoutState,
} from "../../meshchatx/src/frontend/js/appTopNavLayout.svelte.js";

const item = (id) => ({ id });

beforeEach(() => {
    window.localStorage.clear();
    resetTopNavItemIds();
});

describe("appTopNavLayout", () => {
    it("defaults to relay chat, calls, and nomadnet", () => {
        expect(resolveTopNavItemIds(null)).toEqual(["relay-chat", "call", "nomadnetwork"]);
        expect(DEFAULT_TOP_NAV_ITEM_IDS).toContain("nomadnetwork");
    });

    it("persists a custom set and order", () => {
        saveTopNavItemIds(["map", "messages", "map", "  contacts  "]);
        expect(topNavLayoutState.itemIds).toEqual(["map", "messages", "contacts"]);
        expect(JSON.parse(window.localStorage.getItem(APP_TOP_NAV_LAYOUT_KEY))).toEqual([
            "map",
            "messages",
            "contacts",
        ]);
    });

    it("normalizes junk out of stored ids", () => {
        expect(normalizeTopNavItemIds("not-an-array")).toBeNull();
        expect(normalizeTopNavItemIds(null)).toBeNull();
        expect(normalizeTopNavItemIds(["map", 42, "", "__proto__", "map"])).toEqual(["map"]);
    });

    it("reset restores the default set", () => {
        saveTopNavItemIds(["map"]);
        resetTopNavItemIds();
        expect(topNavLayoutState.itemIds).toBeNull();
        expect(window.localStorage.getItem(APP_TOP_NAV_LAYOUT_KEY)).toBeNull();
    });

    it("orders available items by the pinned list and skips unknown ids", () => {
        const available = [item("messages"), item("map"), item("call")];
        const ordered = orderedTopNavItems(available, ["call", "ghost", "map"]);
        expect(ordered.map((i) => i.id)).toEqual(["call", "map"]);
    });

    it("allows pinning zero items", () => {
        saveTopNavItemIds([]);
        expect(orderedTopNavItems([item("map")], topNavLayoutState.itemIds)).toEqual([]);
    });
});
