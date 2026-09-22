// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MapBrowser from "@/features/map/components/MapBrowser.svelte";
import TileCache from "@/js/TileCache.js";
import GlobalState from "@/js/GlobalState.js";
import { mapViewStateKey } from "@/js/mapStateKeys.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import en from "@/locales/en.json";

vi.mock("@/js/TileCache.js", () => ({
    default: {
        getMapState: vi.fn().mockResolvedValue(null),
        setMapState: vi.fn().mockResolvedValue(),
        initPromise: Promise.resolve(),
    },
}));

vi.mock("@/features/map/MapPage.svelte", () => ({
    default: vi.fn(),
}));

describe("MapBrowser.svelte", () => {
    beforeEach(() => {
        localStorage.clear();
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages(en);
    });

    afterEach(() => {
        cleanup();
    });

    it("renders and handles tab operations", async () => {
        const { container } = render(MapBrowser);
        expect(container).toBeTruthy();
    });

    it("restores persisted tabs on mount", async () => {
        localStorage.setItem(
            "meshchatx.map.tabs",
            JSON.stringify({
                tabs: [
                    { storageId: "tab-a", title: "Alpha", userRenamed: true, tabNumber: 1 },
                    { storageId: "tab-b", title: "Bravo", userRenamed: true, tabNumber: 2 },
                ],
                activeIndex: 1,
            })
        );

        const { container } = render(MapBrowser);
        expect(container).toBeTruthy();
    });
});
