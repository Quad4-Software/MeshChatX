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

    it("resolves relative registry and worker URLs against the application origin", () => {
        vi.stubGlobal("location", { origin: "http://localhost" });
        const backing = new BergamotBacking({
            registryUrl: "/translation-packs/registry.json",
            workerUrl: "/vendor/bergamot/translator-worker.js",
        });

        expect(backing.registryUrl).toBe("http://localhost/translation-packs/registry.json");
        expect(backing.workerUrl).toBe("http://localhost/vendor/bergamot/translator-worker.js");
        vi.unstubAllGlobals();
    });

    it("derives language pair from registry key when no metadata is supplied", async () => {
        const backing = new BergamotBacking({ registryUrl: "/translation-packs/registry.json" });
        const registry = {
            enes: {
                model: { name: "/translation-packs/enes/model.npz" },
                lex: { name: "/translation-packs/enes/lex.bin" },
                vocab: { name: "/translation-packs/enes/vocab.spm" },
            },
        };
        fetchSpy.mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue(registry),
        });

        const result = await backing.loadModelRegistery();

        expect(result).toHaveLength(1);
        // Independent oracle: the 4-letter pair key encodes from = first two chars, to = last two.
        expect(result[0]).toMatchObject({
            from: "en",
            to: "es",
            files: registry.enes,
        });
    });

    it("keeps output as a permutation of input registry keys", async () => {
        const backing = new BergamotBacking({ registryUrl: "/translation-packs/registry.json" });
        const registry = {
            enes: { files: {} },
            deen: { files: {} },
            fren: { files: {} },
        };
        fetchSpy.mockResolvedValue({
            ok: true,
            json: vi.fn().mockResolvedValue(registry),
        });

        const result = await backing.loadModelRegistery();

        expect(result).toHaveLength(3);
        expect(new Set(result.map((p) => p.from + p.to))).toEqual(new Set(["enes", "deen", "fren"]));
    });

    it("only fetches translation files from the application origin", async () => {
        vi.stubGlobal("location", { origin: "http://localhost" });

        const backing = new BergamotBacking({});
        fetchSpy.mockResolvedValue({
            ok: true,
            arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8)),
        });

        await backing.fetch("/translation-packs/enes/model.npz");
        expect(fetchSpy).toHaveBeenLastCalledWith(
            "http://localhost/translation-packs/enes/model.npz",
            expect.objectContaining({ credentials: "same-origin" }),
        );

        // Same host on a different port is cross-origin.
        await expect(backing.fetch("http://localhost:3000/model.npz")).rejects.toThrow(
            "Refusing to fetch translation file from http://localhost:3000",
        );

        // Subdomain and HTTPS upgrades are also rejected.
        await expect(backing.fetch("https://localhost/model.npz")).rejects.toThrow(
            "Refusing to fetch translation file from https://localhost",
        );
        await expect(backing.fetch("https://evil.example/model.npz")).rejects.toThrow(
            "Refusing to fetch translation file from https://evil.example",
        );

        // Non-HTTP schemes should bypass the origin check and pass through to fetch.
        // The guard only applies once a resolved http(s) URL is produced.
        await backing.fetch("data:application/octet-stream;base64,AAAA");
        expect(fetchSpy).toHaveBeenLastCalledWith(
            "data:application/octet-stream;base64,AAAA",
            expect.objectContaining({ credentials: "same-origin" }),
        );

        vi.unstubAllGlobals();
    });
});
