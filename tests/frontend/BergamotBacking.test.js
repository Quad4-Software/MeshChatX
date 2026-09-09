import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BergamotBacking } from "@/js/translation/BergamotBacking.js";

describe("BergamotBacking", () => {
    let fetchSpy;

    beforeEach(() => {
        fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue({}),
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("converts pack objects in registry to Bergamot files shape", async () => {
        const backing = new BergamotBacking({ registryUrl: "/translation-packs/registry.json" });
        const registry = {
            enes: {
                from: "en",
                to: "es",
                version: "1.0",
                files: {
                    model: { name: "/translation-packs/enes/model.npz", size: 100 },
                    lex: { name: "/translation-packs/enes/lex.bin", size: 50 },
                    vocab: { name: "/translation-packs/enes/vocab.spm", size: 25 },
                },
            },
        };
        fetchSpy.mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue(registry),
        });

        const result = await backing.loadModelRegistery();

        expect(result).toHaveLength(1);
        expect(result[0]).toEqual({
            from: "en",
            to: "es",
            files: registry.enes.files,
        });
    });

    it("rejects cross-origin fetch attempts", async () => {
        vi.stubGlobal("location", { origin: "http://localhost" });
        const backing = new BergamotBacking({});
        await expect(backing.fetch("https://evil.example/model.npz")).rejects.toThrow(
            "Refusing to fetch translation file from https://evil.example",
        );
        vi.unstubAllGlobals();
    });
});
