// SPDX-License-Identifier: 0BSD AND MIT

import { beforeEach, describe, expect, it } from "vitest";
import {
    DEFAULT_LAYOUT_REF,
    loadSidebarFilterLayout,
    moveSidebarFilter,
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
