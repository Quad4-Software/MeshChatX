// SPDX-License-Identifier: 0BSD
// Bug-hunt: LinkUtils.splitTrailingPunctuation quadratic bracket recount.
import { describe, expect, it } from "vitest";
import LinkUtils from "../../meshchatx/src/frontend/js/LinkUtils.js";

function timeMs(fn) {
    const t0 = performance.now();
    fn();
    return performance.now() - t0;
}

describe("bughunt: LinkUtils.splitTrailingPunctuation complexity", () => {
    it("correctness: trims unbalanced trailing brackets and punctuation", () => {
        expect(LinkUtils.splitTrailingPunctuation("http://a.com/x)).")).toEqual({
            core: "http://a.com/x",
            suffix: ")).",
        });
        expect(LinkUtils.splitTrailingPunctuation("http://a.com/(ok)")).toEqual({
            core: "http://a.com/(ok)",
            suffix: "",
        });
        expect(LinkUtils.splitTrailingPunctuation("http://a.com/x...")).toEqual({
            core: "http://a.com/x",
            suffix: "...",
        });
    });

    it("does not take seconds on an 8k unbalanced-bracket URL", () => {
        // Each trailing ')' makes the code spread the whole remaining core
        // into an array and filter it twice: O(n^2). Measured ~2.3s at n=8000
        // and ~5.2s at n=16000 on this machine — a single chat message can
        // freeze the renderer for seconds.
        const s = `http://a.com/${")".repeat(8000)}`;
        const t = timeMs(() => LinkUtils.splitTrailingPunctuation(s));
        expect(t, `splitTrailingPunctuation took ${t.toFixed(0)}ms on 8k ')'`).toBeLessThan(500);
    });

    it("same cliff via renderAllLinks on a bracket-storm chat message", () => {
        const msg = `see http://evil.example/${")".repeat(8000)} !`;
        const t = timeMs(() => LinkUtils.renderAllLinks(msg));
        expect(t, `renderAllLinks took ${t.toFixed(0)}ms on 8k-paren URL`).toBeLessThan(1000);
    });

    it("scales superlinearly: 4k->8k->16k growth ratio", () => {
        // Min-of-several samples: a single sub-millisecond measurement is
        // dominated by scheduler noise on shared CI runners.
        const t = (n) => {
            let best = Infinity;
            for (let i = 0; i < 7; i += 1) {
                best = Math.min(
                    best,
                    timeMs(() => LinkUtils.splitTrailingPunctuation(`http://a.com/${")".repeat(n)}`))
                );
            }
            return best;
        };
        const a = t(4000);
        const b = t(8000);
        // Pure O(n) => ~2x; O(n^2) => ~4x. Require clearly sub-quadratic.
        expect(b / Math.max(a, 0.5), `4000=${a.toFixed(2)}ms 8000=${b.toFixed(2)}ms`).toBeLessThan(3.2);
    });
});
