import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as TranslationService from "@/js/TranslationService.js";

const mockTranslate = vi.fn();
const mockDelete = vi.fn();

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
    beforeEach(() => {
        mockTranslate.mockReset();
        mockDelete.mockReset();
    });

    afterEach(() => {
        vi.clearAllMocks();
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
            TranslationService.translate({ from: "en", to: "es", text: "hello", signal: controller.signal }),
        ).rejects.toThrow("Translation cancelled");
    });
});
