import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    MAX_HASHES_PER_SECTION,
    MAX_SECTION_NAME_LEN,
    MAX_SECTIONS,
    MAX_TOTAL_HASHES,
    _resetNomadFavouritesLayoutSaveStateForTests,
    loadNomadFavouritesLayout,
    normalizeNomadFavouritesLayout,
    saveNomadFavouritesLayout,
    serializeNomadFavouritesLayout,
} from "@/js/nomadFavouritesLayoutStore.js";

describe("nomadFavouritesLayoutStore", () => {
    beforeEach(() => {
        _resetNomadFavouritesLayoutSaveStateForTests();
        vi.stubGlobal("localStorage", {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        });
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        _resetNomadFavouritesLayoutSaveStateForTests();
    });

    it("normalizes layout shape", () => {
        const normalized = normalizeNomadFavouritesLayout({
            sections: [
                { id: "default", name: "Favourites", collapsed: false },
                { id: "custom", name: "Custom", collapsed: true },
                { id: "default", name: "dup" },
            ],
            sectionOrder: ["custom", "missing"],
            favouritesBySection: {
                custom: ["abc", 1],
                orphan: ["x"],
            },
        });
        expect(normalized.sections).toHaveLength(2);
        expect(normalized.sectionOrder).toEqual(["custom", "default"]);
        expect(normalized.favouritesBySection.custom).toEqual(["abc"]);
        expect(normalized.favouritesBySection.default).toEqual([]);
        expect(normalized.favouritesBySection.orphan).toBeUndefined();
    });

    it("rejects arrays and prototype pollution keys", () => {
        expect(normalizeNomadFavouritesLayout([])).toBeNull();
        const normalized = normalizeNomadFavouritesLayout({
            sections: [
                { id: "__proto__", name: "bad" },
                { id: "constructor", name: "bad" },
                { id: "ok", name: "Good" },
            ],
            favouritesBySection: {
                __proto__: ["a"],
                ok: ["b"],
            },
        });
        expect(normalized.sections.map((s) => s.id)).toEqual(["ok"]);
        expect(normalized.favouritesBySection.ok).toEqual(["b"]);
        expect(Object.prototype.hasOwnProperty.call(normalized.favouritesBySection, "__proto__")).toBe(false);
    });

    it("enforces size caps", () => {
        const sections = Array.from({ length: MAX_SECTIONS + 8 }, (_, i) => ({
            id: `s${i}`,
            name: "n".repeat(MAX_SECTION_NAME_LEN + 20),
        }));
        const hashes = Array.from({ length: MAX_HASHES_PER_SECTION + 20 }, (_, i) => i.toString(16).padStart(32, "0"));
        const normalized = normalizeNomadFavouritesLayout({
            sections,
            sectionOrder: sections.map((s) => s.id),
            favouritesBySection: { s0: hashes },
        });
        expect(normalized.sections).toHaveLength(MAX_SECTIONS);
        expect(normalized.sections[0].name).toHaveLength(MAX_SECTION_NAME_LEN);
        expect(normalized.favouritesBySection.s0).toHaveLength(MAX_HASHES_PER_SECTION);
    });

    it("enforces total hash cap across sections", () => {
        const sections = [
            { id: "a", name: "A" },
            { id: "b", name: "B" },
            { id: "c", name: "C" },
            { id: "d", name: "D" },
        ];
        const per = Math.floor(MAX_TOTAL_HASHES / 4) + 20;
        const normalized = normalizeNomadFavouritesLayout({
            sections,
            favouritesBySection: Object.fromEntries(
                sections.map((s) => [
                    s.id,
                    Array.from({ length: per }, (_, i) => `${s.id}${i}`.padEnd(32, "0").slice(0, 32)),
                ])
            ),
        });
        const total = Object.values(normalized.favouritesBySection).reduce((n, arr) => n + arr.length, 0);
        expect(total).toBeLessThanOrEqual(MAX_TOTAL_HASHES);
    });

    it("loads remote layout and caches locally", async () => {
        const layout = {
            sections: [{ id: "default", name: "Favourites", collapsed: false }],
            sectionOrder: ["default"],
            favouritesBySection: { default: ["a"] },
        };
        const api = {
            get: vi.fn().mockResolvedValue({ data: { layout } }),
            put: vi.fn(),
        };
        const loaded = await loadNomadFavouritesLayout(api);
        expect(loaded.favouritesBySection.default).toEqual(["a"]);
        expect(localStorage.setItem).toHaveBeenCalled();
        expect(api.put).not.toHaveBeenCalled();
    });

    it("migrates localStorage layout to the API when remote is empty", async () => {
        const layout = {
            sections: [{ id: "default", name: "Favourites", collapsed: false }],
            sectionOrder: ["default"],
            favouritesBySection: { default: ["migrated"] },
        };
        localStorage.getItem.mockImplementation((key) => {
            if (key === "meshchat.nomadnet.favourites.layout") {
                return JSON.stringify(layout);
            }
            return null;
        });
        const api = {
            get: vi.fn().mockResolvedValue({ data: { layout: null } }),
            put: vi.fn().mockResolvedValue({ data: { layout } }),
        };
        const loaded = await loadNomadFavouritesLayout(api);
        expect(loaded.favouritesBySection.default).toEqual(["migrated"]);
        expect(api.put).toHaveBeenCalledWith("/api/v1/favourites/layout", { layout });
    });

    it("skips no-op saves after an identical layout was persisted", async () => {
        const layout = {
            sections: [{ id: "default", name: "Favourites", collapsed: false }],
            sectionOrder: ["default"],
            favouritesBySection: { default: [] },
        };
        const api = {
            put: vi.fn().mockResolvedValue({ data: { layout } }),
        };
        await saveNomadFavouritesLayout(api, layout);
        await saveNomadFavouritesLayout(api, layout);
        expect(api.put).toHaveBeenCalledTimes(1);
        expect(serializeNomadFavouritesLayout(layout)).toContain("default");
    });

    it("coalesces concurrent saves into one PUT of the latest layout", async () => {
        const resolvers = [];
        const api = {
            put: vi.fn(
                () =>
                    new Promise((resolve) => {
                        resolvers.push(resolve);
                    })
            ),
        };
        const first = {
            sections: [{ id: "default", name: "Favourites", collapsed: false }],
            sectionOrder: ["default"],
            favouritesBySection: { default: ["one"] },
        };
        const second = {
            sections: [{ id: "default", name: "Favourites", collapsed: false }],
            sectionOrder: ["default"],
            favouritesBySection: { default: ["two"] },
        };
        const p1 = saveNomadFavouritesLayout(api, first);
        const p2 = saveNomadFavouritesLayout(api, second);
        await Promise.resolve();
        expect(api.put).toHaveBeenCalledTimes(1);
        expect(api.put.mock.calls[0][1].layout.favouritesBySection.default).toEqual(["one"]);
        resolvers[0]({ data: { layout: first } });
        await vi.waitFor(() => expect(api.put).toHaveBeenCalledTimes(2));
        expect(api.put.mock.calls[1][1].layout.favouritesBySection.default).toEqual(["two"]);
        resolvers[1]({ data: { layout: second } });
        await Promise.all([p1, p2]);
        expect(api.put).toHaveBeenCalledTimes(2);
    });

    it("fuzzing: normalize never throws on random payloads", () => {
        const samples = [
            null,
            undefined,
            0,
            1,
            true,
            false,
            "",
            "layout",
            [],
            {},
            { sections: null },
            { sections: "x" },
            { sections: [{ id: 1 }] },
            { sections: [{ id: "a", name: { nested: true } }], favouritesBySection: [] },
            { sections: [{ id: "a" }], favouritesBySection: { a: "not-array" } },
            { sections: [{ id: "a" }], favouritesBySection: { a: [null, {}, [], "ok"] } },
        ];
        for (let i = 0; i < 200; i++) {
            samples.push({
                sections: Array.from({ length: (i % 10) + 1 }, (_, j) => ({
                    id: i % 7 === 0 ? `__proto__` : `id-${i}-${j}`,
                    name: String.fromCharCode(0x20 + ((i + j) % 90)).repeat((i % 40) + 1),
                    collapsed: i % 2 === 0,
                })),
                sectionOrder: [`id-${i}-0`, "missing", null, 12],
                favouritesBySection: {
                    [`id-${i}-0`]: Array.from({ length: (i % 15) + 1 }, (_, k) =>
                        k % 5 === 0 ? k : `h${i}${k}`.padEnd(32, "0").slice(0, 32)
                    ),
                },
            });
        }
        for (const sample of samples) {
            expect(() => normalizeNomadFavouritesLayout(sample)).not.toThrow();
            const out = normalizeNomadFavouritesLayout(sample);
            if (out) {
                expect(out.sections.length).toBeGreaterThan(0);
                expect(out.sections.length).toBeLessThanOrEqual(MAX_SECTIONS);
                expect(out.sectionOrder.length).toBe(out.sections.length);
            }
        }
    });
});
