// SPDX-License-Identifier: 0BSD AND MIT

import { beforeEach, describe, expect, it } from "vitest";
import {
    DEFAULT_LAYOUT_REF,
    isCustomFilterId,
    loadSidebarFilterLayout,
    makeCustomFilter,
    matchesCustomQuery,
    moveSidebarFilter,
    resolveSidebarFilterDefs,
    saveSidebarFilterLayout,
    sidebarFilterDefs,
} from "../../meshchatx/src/frontend/js/messages/sidebarFilters.js";

const KEY = "meshchatx_sidebar_filters";

describe("sidebarFilters", () => {
    beforeEach(() => {
        localStorage.removeItem(KEY);
    });

    it("returns defaults when nothing is stored", () => {
        const layout = loadSidebarFilterLayout();
        expect(layout.conversations).toEqual(["unread", "failed", "attachments"]);
        expect(layout.announces).toEqual(["direct", "pinned"]);
    });

    it("persists and reloads a custom layout", () => {
        const layout = { conversations: ["favourites", "unread"], announces: ["blocked"] };
        saveSidebarFilterLayout(layout);
        const loaded = loadSidebarFilterLayout();
        expect(loaded.conversations).toEqual(["favourites", "unread"]);
        expect(loaded.announces).toEqual(["blocked"]);
    });

    it("drops unknown ids and duplicates from stored layout", () => {
        localStorage.setItem(KEY, JSON.stringify({ conversations: ["unread", "bogus", "unread", "failed"] }));
        const loaded = loadSidebarFilterLayout();
        expect(loaded.conversations).toEqual(["unread", "failed"]);
    });

    it("falls back to defaults for a missing context key", () => {
        localStorage.setItem(KEY, JSON.stringify({ conversations: ["attachments"] }));
        const loaded = loadSidebarFilterLayout();
        expect(loaded.conversations).toEqual(["attachments"]);
        expect(loaded.announces).toEqual(["direct", "pinned"]);
    });

    it("falls back to defaults on corrupt json", () => {
        localStorage.setItem(KEY, "{nope");
        expect(loadSidebarFilterLayout().conversations).toEqual(["unread", "failed", "attachments"]);
    });

    it("moves a filter before the target and persists", () => {
        const layout = loadSidebarFilterLayout();
        const next = moveSidebarFilter(layout, "conversations", "attachments", "unread");
        expect(next.conversations).toEqual(["attachments", "unread", "failed"]);
        expect(JSON.parse(localStorage.getItem(KEY)).conversations).toEqual(["attachments", "unread", "failed"]);
    });

    it("moves a filter to the end on null target", () => {
        const layout = loadSidebarFilterLayout();
        const next = moveSidebarFilter(layout, "conversations", "unread", null);
        expect(next.conversations).toEqual(["failed", "attachments", "unread"]);
    });

    it("catalog defs are unique per context", () => {
        for (const context of ["conversations", "announces"]) {
            const ids = sidebarFilterDefs(context).map((d) => d.id);
            expect(new Set(ids).size).toBe(ids.length);
        }
    });
});

describe("custom filters", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("round-trips custom defs and ids through load/save", () => {
        const def = makeCustomFilter("Family", "mom, dad");
        expect(isCustomFilterId(def.id)).toBe(true);
        saveSidebarFilterLayout({
            conversations: ["unread", def.id],
            announces: ["direct"],
            custom: { conversations: [def] },
        });
        const loaded = loadSidebarFilterLayout();
        expect(loaded.conversations).toEqual(["unread", def.id]);
        expect(loaded.custom.conversations[0]).toMatchObject({ label: "Family", query: "mom, dad" });
        const resolved = resolveSidebarFilterDefs("conversations", loaded);
        expect(resolved[resolved.length - 1].label).toBe("Family");
    });

    it("drops unknown custom ids from layout but keeps the def", () => {
        const def = makeCustomFilter("Work", "boss");
        saveSidebarFilterLayout({
            conversations: ["unread", "custom_gone"],
            announces: ["direct"],
            custom: { conversations: [def] },
        });
        const loaded = loadSidebarFilterLayout();
        expect(loaded.conversations).toEqual(["unread"]);
        expect(loaded.custom.conversations).toHaveLength(1);
    });

    it("matches comma-separated terms against name and hash", () => {
        const item = { display_name: "Ada Lovelace", custom_display_name: null, destination_hash: "a1b2c3" };
        expect(matchesCustomQuery(item, "ada")).toBe(true);
        expect(matchesCustomQuery(item, "bob, lovelace")).toBe(true);
        expect(matchesCustomQuery(item, "A1B2")).toBe(true);
        expect(matchesCustomQuery(item, "nobody")).toBe(false);
        expect(matchesCustomQuery(item, "")).toBe(true);
        expect(matchesCustomQuery(item, "   ")).toBe(true);
    });
});
