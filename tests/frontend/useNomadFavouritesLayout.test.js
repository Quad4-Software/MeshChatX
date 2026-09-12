// SPDX-License-Identifier: 0BSD

import { ref } from "vue";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { useNomadFavouritesLayout } from "../../meshchatx/src/frontend/js/nomadnet/useNomadFavouritesLayout.js";
import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils.js";
import { _resetNomadFavouritesLayoutSaveStateForTests } from "../../meshchatx/src/frontend/js/nomadFavouritesLayoutStore.js";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(),
        prompt: vi.fn((msg, def) => Promise.resolve(def || "renamed")),
    },
}));

describe("useNomadFavouritesLayout", () => {
    const favouriteA = { destination_hash: "a".repeat(32), display_name: "Node A" };
    const favouriteB = { destination_hash: "b".repeat(32), display_name: "Node B" };

    let axiosMock;

    beforeEach(() => {
        _resetNomadFavouritesLayoutSaveStateForTests();
        axiosMock = {
            get: vi.fn().mockResolvedValue({ data: { layout: null } }),
            put: vi.fn().mockImplementation((_url, body) => Promise.resolve({ data: body || {} })),
        };
        window.api = axiosMock;
        vi.stubGlobal("localStorage", {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        });
    });

    afterEach(() => {
        delete window.api;
        vi.unstubAllGlobals();
        _resetNomadFavouritesLayoutSaveStateForTests();
    });

    it("resets to a single default section", () => {
        const layout = useNomadFavouritesLayout();
        layout.resetDefaultSections();
        expect(layout.sections.value).toEqual([
            { id: "default", name: "nomadnet.favourites", collapsed: false },
        ]);
        expect(layout.sectionOrder.value).toEqual(["default"]);
        expect(layout.favouritesBySection.value).toEqual({ default: [] });
    });

    it("applyFavouriteLayout applies a persisted layout and falls back to defaults", () => {
        const layout = useNomadFavouritesLayout();
        layout.applyFavouriteLayout({
            sections: [{ id: "custom", name: "Custom", collapsed: true }],
            sectionOrder: ["custom"],
            favouritesBySection: { custom: [favouriteA.destination_hash] },
        });
        expect(layout.sections.value[0].id).toBe("custom");
        expect(layout.sections.value[0].collapsed).toBe(true);
        expect(layout.favouritesBySection.value.custom).toEqual([favouriteA.destination_hash]);
    });

    it("applyFavouriteLayout keeps existing sections when layout is null", () => {
        const layout = useNomadFavouritesLayout();
        layout.applyFavouriteLayout({
            sections: [{ id: "custom", name: "Custom", collapsed: false }],
            sectionOrder: ["custom"],
            favouritesBySection: {},
        });
        layout.applyFavouriteLayout(null);
        expect(layout.sections.value[0].id).toBe("custom");
    });

    it("toggleSectionCollapse flips the collapsed flag", () => {
        const layout = useNomadFavouritesLayout();
        layout.resetDefaultSections();
        layout.toggleSectionCollapse("default");
        expect(layout.sections.value[0].collapsed).toBe(true);
        layout.toggleSectionCollapse("default");
        expect(layout.sections.value[0].collapsed).toBe(false);
        layout.toggleSectionCollapse("missing");
        expect(layout.sections.value[0].collapsed).toBe(false);
    });

    it("moveFavouritesToSection moves hashes and clears drag state", () => {
        const layout = useNomadFavouritesLayout();
        layout.applyFavouriteLayout({
            sections: [
                { id: "default", name: "Favourites", collapsed: false },
                { id: "custom", name: "Custom", collapsed: false },
            ],
            sectionOrder: ["default", "custom"],
            favouritesBySection: {
                default: [favouriteA.destination_hash, favouriteB.destination_hash],
                custom: [],
            },
        });
        layout.draggingFavouriteHashes.value = [favouriteA.destination_hash];
        layout.draggingFavouriteHash.value = favouriteA.destination_hash;
        layout.dragOverSectionId.value = "custom";

        layout.moveFavouritesToSection([favouriteA.destination_hash], "custom");

        expect(layout.favouritesBySection.value.custom).toEqual([favouriteA.destination_hash]);
        expect(layout.favouritesBySection.value.default).toEqual([favouriteB.destination_hash]);
        expect(layout.draggingFavouriteHashes.value).toEqual([]);
        expect(layout.draggingFavouriteHash.value).toBeNull();
        expect(layout.dragOverSectionId.value).toBeNull();
    });

    it("moveFavouritesToSection inserts before the target hash", () => {
        const layout = useNomadFavouritesLayout();
        layout.applyFavouriteLayout({
            sections: [{ id: "default", name: "Favourites", collapsed: false }],
            sectionOrder: ["default"],
            favouritesBySection: { default: [favouriteA.destination_hash, favouriteB.destination_hash] },
        });
        layout.moveFavouriteToSection(favouriteB.destination_hash, "default", favouriteA.destination_hash);
        expect(layout.favouritesBySection.value.default).toEqual([
            favouriteB.destination_hash,
            favouriteA.destination_hash,
        ]);
    });

    it("ensureFavouriteLayout assigns unplaced favourites to the default section", () => {
        const favourites = ref([favouriteA, favouriteB]);
        const layout = useNomadFavouritesLayout({ getFavourites: () => favourites.value });
        layout.resetDefaultSections();
        layout.ensureFavouriteLayout();
        expect(layout.favouritesBySection.value.default).toEqual([
            favouriteA.destination_hash,
            favouriteB.destination_hash,
        ]);
    });

    it("ensureFavouriteLayout keeps custom placement and is a no-op with no favourites", () => {
        const favourites = ref([favouriteA]);
        const layout = useNomadFavouritesLayout({ getFavourites: () => favourites.value });
        layout.applyFavouriteLayout({
            sections: [
                { id: "default", name: "Favourites", collapsed: false },
                { id: "custom", name: "Custom", collapsed: false },
            ],
            sectionOrder: ["default", "custom"],
            favouritesBySection: { default: [], custom: [favouriteA.destination_hash] },
        });
        layout.ensureFavouriteLayout();
        expect(layout.favouritesBySection.value.custom).toEqual([favouriteA.destination_hash]);
        expect(layout.favouritesBySection.value.default).toEqual([]);

        favourites.value = [];
        layout.favouritesBySection.value = { default: [], custom: [favouriteA.destination_hash] };
        layout.ensureFavouriteLayout();
        expect(layout.favouritesBySection.value.custom).toEqual([favouriteA.destination_hash]);
    });

    it("sectionsWithFavourites resolves favourites and filters by search term", () => {
        const favourites = ref([favouriteA, favouriteB]);
        const layout = useNomadFavouritesLayout({ getFavourites: () => favourites.value });
        layout.resetDefaultSections();
        layout.ensureFavouriteLayout();

        expect(layout.sectionsWithFavourites.value[0].favourites).toEqual([favouriteA, favouriteB]);
        expect(layout.favouritesSearchNoResults.value).toBe(false);

        layout.favouritesSearchTerm.value = "node b";
        expect(layout.sectionsWithFavourites.value[0].favourites).toEqual([favouriteB]);
        expect(layout.favouritesSearchNoResults.value).toBe(false);

        layout.favouritesSearchTerm.value = "nothing matches";
        expect(layout.sectionsWithFavourites.value[0].favourites).toEqual([]);
        expect(layout.favouritesSearchNoResults.value).toBe(true);
        expect(layout.flatVisibleFavouriteDestinationHashes.value).toEqual([]);
    });

    it("collapsedFavouritePreview returns up to five favourites in section order", () => {
        const favourites = ref(
            Array.from({ length: 7 }, (_, i) => ({
                destination_hash: String(i).repeat(32),
                display_name: `Node ${i}`,
            }))
        );
        const layout = useNomadFavouritesLayout({ getFavourites: () => favourites.value });
        layout.resetDefaultSections();
        layout.ensureFavouriteLayout();
        expect(layout.collapsedFavouritePreview.value).toHaveLength(5);
    });

    it("saveSectionName renames a section and clears editing state", () => {
        const layout = useNomadFavouritesLayout();
        layout.resetDefaultSections();
        layout.editingSectionId.value = "default";
        layout.editingSectionName.value = "  Renamed  ";
        layout.saveSectionName();
        expect(layout.sections.value[0].name).toBe("Renamed");
        expect(layout.editingSectionId.value).toBeNull();
        expect(layout.editingSectionName.value).toBe("");
    });

    it("saveSectionName ignores blank names but still exits editing", () => {
        const layout = useNomadFavouritesLayout();
        layout.resetDefaultSections();
        layout.editingSectionId.value = "default";
        layout.editingSectionName.value = "   ";
        layout.saveSectionName();
        expect(layout.sections.value[0].name).toBe("nomadnet.favourites");
        expect(layout.editingSectionId.value).toBeNull();
    });

    it("createSection appends a prompted section", async () => {
        const layout = useNomadFavouritesLayout();
        layout.resetDefaultSections();
        await layout.createSection();
        expect(DialogUtils.prompt).toHaveBeenCalledWith("nomadnet.enter_section_name", "nomadnet.new_section");
        expect(layout.sections.value).toHaveLength(2);
        expect(layout.sections.value[1].name).toBe("nomadnet.new_section");
        expect(layout.sectionOrder.value).toEqual(["default", layout.sections.value[1].id]);
        expect(layout.favouritesBySection.value[layout.sections.value[1].id]).toEqual([]);
    });

    it("createSection does nothing when the prompt is cancelled", async () => {
        DialogUtils.prompt.mockResolvedValueOnce(null);
        const layout = useNomadFavouritesLayout();
        layout.resetDefaultSections();
        await layout.createSection();
        expect(layout.sections.value).toHaveLength(1);
    });

    it("isFavouriteRowDragging reflects draggingFavouriteHashes", () => {
        const layout = useNomadFavouritesLayout();
        expect(layout.isFavouriteRowDragging("x")).toBe(false);
        layout.draggingFavouriteHashes.value = ["x"];
        expect(layout.isFavouriteRowDragging("x")).toBe(true);
    });

    it("persistFavouriteLayout immediate saves through the favourites layout API", async () => {
        const layout = useNomadFavouritesLayout();
        layout.resetDefaultSections();
        await layout.persistFavouriteLayout({ immediate: true });
        expect(axiosMock.put).toHaveBeenCalledWith(
            "/api/v1/favourites/layout",
            expect.objectContaining({
                layout: expect.objectContaining({ sectionOrder: ["default"] }),
            })
        );
    });

    it("persistFavouriteLayout debounces non-immediate saves", async () => {
        vi.useFakeTimers();
        const layout = useNomadFavouritesLayout();
        layout.resetDefaultSections();
        layout.persistFavouriteLayout();
        layout.persistFavouriteLayout();
        await vi.advanceTimersByTimeAsync(250);
        expect(axiosMock.put).toHaveBeenCalledTimes(1);
        vi.useRealTimers();
    });

    it("a user persist invalidates an in-flight layout reload", async () => {
        let resolveGet;
        axiosMock.get.mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolveGet = resolve;
                })
        );
        const favourites = ref([favouriteA]);
        const layout = useNomadFavouritesLayout({ getFavourites: () => favourites.value });
        layout.resetDefaultSections();

        const reload = layout.reloadFavouriteLayoutFromStore();
        layout.favouritesBySection.value = { default: [favouriteA.destination_hash] };
        await layout.persistFavouriteLayout({ immediate: true });

        resolveGet({ data: { layout: { sections: [], sectionOrder: [], favouritesBySection: {} } } });
        await reload;
        expect(layout.favouritesBySection.value.default).toEqual([favouriteA.destination_hash]);
    });
});
