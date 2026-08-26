// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    MIN_VIRTUAL_SIDEBAR_ITEMS,
    SIDEBAR_ROW_ESTIMATE_PX,
    estimateSidebarRowHeight,
} from "@/js/sidebarListVirtual.js";

describe("sidebarListVirtual.js", () => {
    it("MIN_VIRTUAL_SIDEBAR_ITEMS is a positive virtualization threshold", () => {
        expect(MIN_VIRTUAL_SIDEBAR_ITEMS).toBe(32);
        expect(MIN_VIRTUAL_SIDEBAR_ITEMS).toBeGreaterThan(10);
    });

    it("estimateSidebarRowHeight returns the default row estimate", () => {
        expect(estimateSidebarRowHeight(null)).toBe(SIDEBAR_ROW_ESTIMATE_PX);
        expect(estimateSidebarRowHeight({ destination_hash: "abc" })).toBe(72);
    });
});
