// SPDX-License-Identifier: 0BSD
// Bug-hunt: relayMessageTimeline merge cost + useRelayMessageTimeline per-push cost.
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { nextTick } from "vue";
import {
    mergeRelayMessages,
    relayMessageTimelineSignature,
    buildRelayMessageTimeline,
} from "../../meshchatx/src/frontend/js/relayMessageTimeline.js";
import { useRelayMessageTimeline } from "../../meshchatx/src/frontend/js/relay/useRelayMessageTimeline.js";

const HUB_HASH = "00112233445566778899aabbccddeeff";

function msg(seq, text = "hi", overrides = {}) {
    return { kind: "msg", seq, text, ts: seq * 1000, src: "aa".repeat(16), nick: "n", ...overrides };
}

function makeTimeline(overrides = {}) {
    return useRelayMessageTimeline({
        getSelectedHubHash: () => HUB_HASH,
        getSelectedRoom: () => "lobby",
        getMessagesScrollElement: () => null,
        encodeRoom: (room) => encodeURIComponent(room),
        t: (key, params) => `${key}:${params?.count ?? ""}`,
        ...overrides,
    });
}

function timeMs(fn) {
    const t0 = performance.now();
    fn();
    return performance.now() - t0;
}

// Fixed wall-clock bounds flake on shared CI runners: the same 2000-push
// run measured 4.7s on one run and 8.6s on another with identical code, and
// a synthetic CPU calibration loop does not track the allocation/GC cost
// that dominates these paths. Instead these tests calibrate with the
// operation itself at a small size and bound the growth ratio at the large
// size. Linear work grows ~4x from quarter-size to full-size inputs; the
// bounds below allow 2x of headroom over that, so they only fire on
// super-linear blowup, not on slow hardware. Each bound also has a floor
// so sub-millisecond calibration noise cannot make the test tautological,
// and a loose absolute ceiling so a hang still fails.

// Merge is linear in total rows. 4x the rows -> expect ~4x the time.
const MERGE_RATIO = 8;
// Pushes are O(n) each on a growing list, so the total is O(n^2): 4x the
// pushes at 4x the list size -> up to 16x the time.
const PUSH_RATIO = 32;
// "Something is deeply wrong" ceilings, not perf assertions.
const MERGE_CEILING_MS = 15_000;
const PUSH_CEILING_MS = 90_000;

function merged(baseN, loadedN, startSeq = 1, nullSeq = false) {
    const base = Array.from({ length: baseN }, (_, i) =>
        msg(nullSeq ? null : startSeq + i, `b${i}`, { ts: (startSeq + i) * 1000 })
    );
    const loaded = Array.from({ length: loadedN }, (_, i) =>
        msg(nullSeq ? null : startSeq + baseN + i, `l${i}`, {
            ts: (startSeq + baseN + i) * 1000,
        })
    );
    return timeMs(() => mergeRelayMessages(base, loaded));
}

describe("bughunt: mergeRelayMessages complexity", () => {
    it("room-open merge (2000 existing + 150 loaded) scales linearly", () => {
        const warm = Math.min(merged(500, 40, 1), merged(500, 40, 1));
        const t = merged(2000, 150, 1);
        console.log(`merge 2000+150: ${t.toFixed(1)}ms (calibration ${warm.toFixed(1)}ms)`);
        const bound = Math.max(warm * MERGE_RATIO, 250);
        expect(t, `merge took ${t.toFixed(0)}ms vs bound ${bound.toFixed(0)}ms`).toBeLessThan(bound);
        expect(t).toBeLessThan(MERGE_CEILING_MS);
    });

    it("worst-case merge (2000 + 2000 fresh) scales linearly", () => {
        const warm = Math.min(merged(500, 500, 1), merged(500, 500, 1));
        const t = merged(2000, 2000, 1);
        console.log(`merge 2000+2000: ${t.toFixed(1)}ms (calibration ${warm.toFixed(1)}ms)`);
        const bound = Math.max(warm * MERGE_RATIO, 500);
        expect(t, `merge took ${t.toFixed(0)}ms vs bound ${bound.toFixed(0)}ms`).toBeLessThan(bound);
        expect(t).toBeLessThan(MERGE_CEILING_MS);
    });

    it("merge without seq (fallback key path) is not pathological", () => {
        const warm = Math.min(merged(250, 50, 1, true), merged(250, 50, 1, true));
        const t = merged(1000, 200, 1, true);
        console.log(`merge noseq 1000+200: ${t.toFixed(1)}ms (calibration ${warm.toFixed(1)}ms)`);
        const bound = Math.max(warm * MERGE_RATIO, 500);
        expect(t, `noseq merge took ${t.toFixed(0)}ms vs bound ${bound.toFixed(0)}ms`).toBeLessThan(bound);
        expect(t).toBeLessThan(MERGE_CEILING_MS);
    });
});

describe("bughunt: useRelayMessageTimeline live-push cost", () => {
    beforeEach(() => {
        window.api = { get: vi.fn().mockResolvedValue({ data: {} }) };
    });
    afterEach(() => {
        delete window.api;
        vi.restoreAllMocks();
    });

    it("pushing 2000 live messages does not blow up super-quadratically", async () => {
        const tl = makeTimeline();
        tl.messages.value = [msg(1)];
        await nextTick();
        // First 500 pushes calibrate the O(n)-per-push cost on this machine.
        const tEarly = timeMs(() => {
            for (let i = 2; i <= 500; i++) {
                tl.pushLiveMessage(msg(i, `m${i}`));
            }
        });
        const tRest = timeMs(() => {
            for (let i = 501; i <= 2000; i++) {
                tl.pushLiveMessage(msg(i, `m${i}`));
            }
        });
        await nextTick();
        console.log(`live pushes 2..500: ${tEarly.toFixed(0)}ms, 501..2000: ${tRest.toFixed(0)}ms`);
        expect(tl.messages.value.length).toBe(2000);
        // O(n^2) total: the 501..2000 segment does ~15x the work of 2..500.
        // Bound at 32x so only worse-than-quadratic behaviour fails.
        const bound = Math.max(tEarly * PUSH_RATIO, 8000);
        expect(tRest, `2000 pushes took ${tRest.toFixed(0)}ms vs bound ${bound.toFixed(0)}ms`).toBeLessThan(bound);
        expect(tEarly + tRest).toBeLessThan(PUSH_CEILING_MS);
    });

    it("per-push cost stays linear at the 2000-message cap", async () => {
        const tl = makeTimeline();
        tl.messages.value = [msg(1)];
        await nextTick();
        for (let i = 2; i <= 1900; i++) {
            tl.pushLiveMessage(msg(i));
        }
        await nextTick();
        const tEarly = timeMs(() => {
            for (let i = 1901; i <= 2000; i++) tl.pushLiveMessage(msg(i));
        });
        const tLate = timeMs(() => {
            for (let i = 2001; i <= 2100; i++) tl.pushLiveMessage(msg(i));
        });
        console.log(`push batch @~1950: ${tEarly.toFixed(0)}ms, @~2050: ${tLate.toFixed(0)}ms`);
        // Same-size batches at nearly the same list size should cost the
        // same order. 10x headroom covers the head-trim path kicking in at
        // the cap; a super-linear blowup would far exceed it. The floor
        // keeps the bound meaningful when early pushes are near-instant.
        const bound = Math.max(tEarly * 10, tEarly + 1000, 2000);
        expect(tLate, `late batch took ${tLate.toFixed(0)}ms vs bound ${bound.toFixed(0)}ms`).toBeLessThan(bound);
        expect(tLate).toBeLessThan(MERGE_CEILING_MS);
    });
});
