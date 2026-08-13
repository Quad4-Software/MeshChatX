import { afterEach, describe, expect, it } from "vitest";
import {
    APP_SIDEBAR_NAV_LAYOUT_KEY,
    applyNavLayout,
    captureNavLayout,
    loadAppSidebarNavLayout,
    moveNavGroupByOffset,
    moveNavItem,
    moveNavItemByOffset,
    normalizeNavLayout,
    orderItemsByLayout,
    saveAppSidebarNavLayout,
} from "../../meshchatx/src/frontend/js/appSidebarNavLayout.js";

const ITEMS = [
    { id: "messages", group: "communicate", navTier: "primary" },
    { id: "call", group: "communicate", navTier: "primary" },
    { id: "contacts", group: "communicate", navTier: "primary" },
    { id: "nomadnetwork", group: "explore", navTier: "primary" },
    { id: "map", group: "explore", navTier: "primary" },
    { id: "interfaces", group: "app", navTier: "primary" },
    { id: "settings", group: "app", navTier: "primary" },
    { id: "archives", group: "explore", navTier: "more" },
    { id: "about", group: "app", navTier: "more" },
];

function groupIds(view) {
    return view.primaryGroups.map((group) => group.id);
}

function itemIds(view, groupId) {
    return view.primaryGroups.find((group) => group.id === groupId)?.items.map((item) => item.id) || [];
}

function moreIds(view) {
    return view.moreItems.map((item) => item.id);
}

describe("appSidebarNavLayout", () => {
    afterEach(() => {
        localStorage.clear();
    });

    it("applies registry group order when no layout is stored", () => {
        const view = applyNavLayout(ITEMS, null);
        expect(groupIds(view)).toEqual(["communicate", "explore", "app"]);
        expect(itemIds(view, "communicate")).toEqual(["messages", "call", "contacts"]);
        expect(itemIds(view, "explore")).toEqual(["nomadnetwork", "map"]);
        expect(moreIds(view)).toEqual(["archives", "about"]);
    });

    it("keeps unknown items and drops missing ids from a saved layout", () => {
        const layout = normalizeNavLayout({
            groupOrder: ["explore", "communicate", "app"],
            itemOrder: ["map", "ghost", "messages", "call"],
            placements: {
                map: { group: "explore", tier: "primary" },
                messages: { group: "communicate", tier: "primary" },
            },
        });
        const view = applyNavLayout(ITEMS, layout);
        expect(groupIds(view)[0]).toBe("explore");
        expect(itemIds(view, "explore")[0]).toBe("map");
        expect(itemIds(view, "communicate")).toContain("messages");
        expect(view.primaryGroups.flatMap((group) => group.items).map((item) => item.id)).not.toContain("ghost");
        expect(itemIds(view, "app")).toContain("interfaces");
    });

    it("rejects prototype-polluting ids", () => {
        const layout = normalizeNavLayout({
            groupOrder: ["__proto__", "communicate"],
            itemOrder: ["constructor", "messages"],
            placements: {
                __proto__: { group: "hack", tier: "primary" },
                messages: { group: "communicate", tier: "primary" },
            },
        });
        expect(layout.groupOrder).not.toContain("__proto__");
        expect(layout.itemOrder).not.toContain("constructor");
        expect(Object.prototype.hack).toBeUndefined();
    });

    it("moves an item before another item in the same group", () => {
        const base = captureNavLayout(applyNavLayout(ITEMS, null).primaryGroups, applyNavLayout(ITEMS, null).moreItems);
        const next = moveNavItem(base, "contacts", { type: "item", id: "messages", position: "before" }, ITEMS);
        const view = applyNavLayout(ITEMS, next);
        expect(itemIds(view, "communicate")).toEqual(["contacts", "messages", "call"]);
    });

    it("moves an item into another group and into More", () => {
        const base = captureNavLayout(applyNavLayout(ITEMS, null).primaryGroups, applyNavLayout(ITEMS, null).moreItems);
        const toExplore = moveNavItem(base, "contacts", { type: "group-start", id: "explore" }, ITEMS);
        expect(itemIds(applyNavLayout(ITEMS, toExplore), "explore")[0]).toBe("contacts");
        expect(itemIds(applyNavLayout(ITEMS, toExplore), "communicate")).not.toContain("contacts");
        const toMore = moveNavItem(toExplore, "contacts", { type: "more-start" }, ITEMS);
        expect(moreIds(applyNavLayout(ITEMS, toMore))[0]).toBe("contacts");
        expect(itemIds(applyNavLayout(ITEMS, toMore), "explore")).not.toContain("contacts");
    });

    it("moves an item across groups with offset", () => {
        const base = captureNavLayout(applyNavLayout(ITEMS, null).primaryGroups, applyNavLayout(ITEMS, null).moreItems);
        const next = moveNavItemByOffset(base, "contacts", 1, ITEMS);
        const view = applyNavLayout(ITEMS, next);
        expect(itemIds(view, "communicate")).toEqual(["messages", "call"]);
        expect(itemIds(view, "explore")).toEqual(["nomadnetwork", "contacts", "map"]);
    });

    it("reorders groups by offset", () => {
        const base = captureNavLayout(applyNavLayout(ITEMS, null).primaryGroups, applyNavLayout(ITEMS, null).moreItems);
        const next = moveNavGroupByOffset(base, "communicate", 1);
        expect(applyNavLayout(ITEMS, next).primaryGroups.map((group) => group.id)[0]).toBe("explore");
        expect(applyNavLayout(ITEMS, next).primaryGroups.map((group) => group.id)[1]).toBe("communicate");
    });

    it("classic offset preserves group placement", () => {
        const base = captureNavLayout(applyNavLayout(ITEMS, null).primaryGroups, applyNavLayout(ITEMS, null).moreItems);
        const next = moveNavItemByOffset(base, "contacts", 1, ITEMS, { preservePlacement: true });
        const view = applyNavLayout(ITEMS, next);
        expect(itemIds(view, "communicate")).toEqual(["messages", "call", "contacts"]);
        expect(
            orderItemsByLayout(ITEMS, next)
                .map((item) => item.id)
                .slice(0, 4)
        ).toEqual(["messages", "call", "nomadnetwork", "contacts"]);
    });

    it("round-trips through localStorage", () => {
        const base = captureNavLayout(applyNavLayout(ITEMS, null).primaryGroups, applyNavLayout(ITEMS, null).moreItems);
        const moved = moveNavItem(base, "map", { type: "item", id: "nomadnetwork", position: "before" }, ITEMS);
        saveAppSidebarNavLayout(moved);
        expect(localStorage.getItem(APP_SIDEBAR_NAV_LAYOUT_KEY)).toBeTruthy();
        const loaded = loadAppSidebarNavLayout();
        expect(itemIds(applyNavLayout(ITEMS, loaded), "explore")).toEqual(["map", "nomadnetwork"]);
    });

    it("shows empty groups only when requested", () => {
        const hidden = applyNavLayout(ITEMS, null);
        expect(groupIds(hidden)).not.toContain("network");
        const shown = applyNavLayout(ITEMS, null, { includeEmptyGroups: true });
        expect(groupIds(shown)).toContain("network");
        expect(itemIds(shown, "network")).toEqual([]);
    });
});
