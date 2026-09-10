import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

let TranslationService;
let mockTranslate;
let mockDelete;

vi.mock("@browsermt/bergamot-translator", () => ({
    LatencyOptimisedTranslator: class {
        translate(request, options) {
            return mockTranslate(request, options);
        }
        delete() {
            return mockDelete();
        }
    },
}));

vi.mock("@/js/translation/BergamotBacking.js", () => ({
    BergamotBacking: class {
        constructor() {}
    },
}));

describe("TranslationService", () => {
    beforeEach(async () => {
        mockTranslate = vi.fn();
        mockDelete = vi.fn().mockResolvedValue();
        vi.resetModules();
        TranslationService = await import("@/js/TranslationService.js");
    });

    afterEach(() => {
        vi.clearAllMocks();
        vi.unstubAllGlobals();
    });

    it("serialises concurrent translate calls instead of superseding them", async () => {
        let resolveFirst;
        const firstPromise = new Promise((resolve) => {
            resolveFirst = resolve;
        });
        mockTranslate
            .mockReturnValueOnce(firstPromise)
            .mockReturnValueOnce(Promise.resolve({ target: { text: "second" } }));

        const p1 = TranslationService.translate({ from: "en", to: "es", text: "hello" });
        const p2 = TranslationService.translate({ from: "en", to: "es", text: "world" });

        resolveFirst({ target: { text: "first" } });

        const [r1, r2] = await Promise.all([p1, p2]);
        expect(r1.target.text).toBe("first");
        expect(r2.target.text).toBe("second");
        expect(mockTranslate).toHaveBeenCalledTimes(2);
    });

    it("rejects a call that is already aborted", async () => {
        const controller = new AbortController();
        controller.abort();
        await expect(
            TranslationService.translate({ from: "en", to: "es", text: "hello", signal: controller.signal })
        ).rejects.toThrow("Translation cancelled");
    });

    it("never invokes the underlying translator concurrently", async () => {
        let pending = 0;
        let maxPending = 0;
        mockTranslate.mockImplementation(() => {
            pending += 1;
            maxPending = Math.max(maxPending, pending);
            return new Promise((resolve) => {
                setTimeout(() => {
                    pending -= 1;
                    resolve({ target: { text: "ok" } });
                }, 5);
            });
        });

        const p1 = TranslationService.translate({ from: "en", to: "es", text: "a" });
        const p2 = TranslationService.translate({ from: "en", to: "es", text: "b" });
        const p3 = TranslationService.translate({ from: "en", to: "es", text: "c" });

        await Promise.all([p1, p2, p3]);

        // The queue must guarantee that only one in-flight call exists at a time.
        expect(maxPending).toBe(1);
        expect(mockTranslate).toHaveBeenCalledTimes(3);
    });

    it("waits for an active translation before deleting the translator", async () => {
        let resolveTranslate;
        mockTranslate.mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolveTranslate = resolve;
                })
        );

        const p = TranslationService.translate({ from: "en", to: "es", text: "hello" });
        await new Promise((r) => setTimeout(r, 0));
        expect(mockTranslate).toHaveBeenCalledTimes(1);
        expect(mockDelete).not.toHaveBeenCalled();

        const refreshP = TranslationService.refreshPacks();
        await new Promise((r) => setTimeout(r, 0));
        // refreshPacks is queued behind the in-flight translate; no delete yet.
        expect(mockDelete).not.toHaveBeenCalled();

        resolveTranslate({ target: { text: "done" } });
        await refreshP;
        expect(mockDelete).toHaveBeenCalledTimes(1);
        await p;
    });

    it("does not set an explicit Content-Type on pack upload", async () => {
        const post = vi.fn().mockResolvedValue({ data: { pairs: ["enes"] } });
        vi.stubGlobal("api", { post });

        const file = new Blob(["archive"], { type: "application/zip" });
        await TranslationService.importPack(file);

        expect(post).toHaveBeenCalledTimes(1);
        const [_url, body, config] = post.mock.calls[0];
        expect(body).toBeInstanceOf(FormData);
        expect(config?.headers?.["Content-Type"]).toBeUndefined();
    });
});
