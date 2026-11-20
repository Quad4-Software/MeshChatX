// SPDX-License-Identifier: 0BSD
// Bug-hunt: relayMessageTimeline merge cost + useRelayMessageTimeline per-push cost.
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { nextTick } from "vue";
import { mergeRelayMessages } from "../../meshchatx/src/frontend/js/relayMessageTimeline.js";
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

// Wall-clock bounds flake on shared CI runners: the same 2000-push run
// measured 4.7s on one run and 8.6s on another with identical code, and GC
// or CPU-steal cliffs skew any ratio of two timings. These tests instead
// count work deterministically: every message object is a Proxy whose get
// trap ticks a shared counter, so the count tracks the number of property
// reads (comparisons, key builds, scans) the implementation performs
// regardless of machine speed. A super-linear implementation reads each
// element ~4x more often at 4x the size (~16x), while O(n log n) work
// reads ~4-5x. Each bound sits between the two.

// Linear / n-log-n code grows ~4x from quarter-size to full-size inputs.
// 8x gives margin while still catching ~16x quadratic behaviour.
const LINEAR_RATIO = 8;
// Push segments are O(n) per push on a growing list (key set rebuild per
// push, timeline rebuild per flush): the 501..2000 segment does ~15x the
// work of 2..500. 40x covers the by-design quadratic while catching worse.
const QUADRATIC_SEGMENT_RATIO = 40;
// Same-size batches at nearly the same list size should cost the same
// order of reads.
const BATCH_RATIO = 10;
// Wall clock stays only as a hang guard.
const CEILING_MS = 30_000;

const ops = { n: 0 };

function countedMsg(seq, text, overrides = {}) {
    return new Proxy(msg(seq, text, overrides), {
        get(target, key, receiver) {
            if (typeof key === "string") {
                ops.n++;
            }
            return Reflect.get(target, key, receiver);
        },
    });
}

function countMerge(baseN, loadedN, { nullSeq = false } = {}) {
    const base = Array.from({ length: baseN }, (_, i) =>
        countedMsg(nullSeq ? null : i + 1, `b${i}`, { ts: (i + 1) * 1000 })
    );
    const loaded = Array.from({ length: loadedN }, (_, i) =>
        countedMsg(nullSeq ? null : baseN + i + 1, `l${i}`, {
            ts: (baseN + i + 1) * 1000,
        })
    );
    const t0 = performance.now();
    ops.n = 0;
    mergeRelayMessages(base, loaded);
    const elapsed = performance.now() - t0;
    return { ops: ops.n, ms: elapsed };
}

describe("bughunt: mergeRelayMessages complexity (operation counts)", () => {
    it("room-open merge (2000 existing + 150 loaded) is near-linear", () => {
        const warm = countMerge(500, 40);
        const t = countMerge(2000, 150);
        console.log(
            `merge 2000+150: ${t.ops} reads vs ${warm.ops} reads ` +
                `(${(t.ops / warm.ops).toFixed(1)}x), ${t.ms.toFixed(0)}ms`
        );
        expect(t.ops / warm.ops).toBeLessThan(LINEAR_RATIO);
        expect(t.ms).toBeLessThan(CEILING_MS);
    });

    it("worst-case merge (2000 + 2000 fresh) is near-linear", () => {
        const warm = countMerge(500, 500);
        const t = countMerge(2000, 2000);
        console.log(
            `merge 2000+2000: ${t.ops} reads vs ${warm.ops} reads ` +
                `(${(t.ops / warm.ops).toFixed(1)}x), ${t.ms.toFixed(0)}ms`
        );
        expect(t.ops / warm.ops).toBeLessThan(LINEAR_RATIO);
        expect(t.ms).toBeLessThan(CEILING_MS);
    });

    it("merge without seq (fallback key path) is near-linear", () => {
        const warm = countMerge(250, 50, { nullSeq: true });
        const t = countMerge(1000, 200, { nullSeq: true });
        console.log(
            `merge noseq 1000+200: ${t.ops} reads vs ${warm.ops} reads ` +
                `(${(t.ops / warm.ops).toFixed(1)}x), ${t.ms.toFixed(0)}ms`
        );
        expect(t.ops / warm.ops).toBeLessThan(LINEAR_RATIO);
        expect(t.ms).toBeLessThan(CEILING_MS);
    });
});

describe("bughunt: useRelayMessageTimeline live-push cost (operation counts)", () => {
    beforeEach(() => {
        window.api = { get: vi.fn().mockResolvedValue({ data: {} }) };
    });
    afterEach(() => {
        delete window.api;
        vi.restoreAllMocks();
    });

    it("pushing 2000 live messages stays at the designed O(n^2), not worse", async () => {
        const tl = makeTimeline();
        tl.messages.value = [countedMsg(1)];
        await nextTick();
        ops.n = 0;
        const t0 = performance.now();
        for (let i = 2; i <= 500; i++) {
            tl.pushLiveMessage(countedMsg(i, `m${i}`));
        }
        const earlyOps = ops.n;
        for (let i = 501; i <= 2000; i++) {
            tl.pushLiveMessage(countedMsg(i, `m${i}`));
        }
        const lateOps = ops.n - earlyOps;
        const elapsed = performance.now() - t0;
        await nextTick();
        console.log(
            `live pushes 2..500: ${earlyOps} reads, 501..2000: ${lateOps} reads ` +
                `(${(lateOps / earlyOps).toFixed(1)}x), ${elapsed.toFixed(0)}ms`
        );
        expect(tl.messages.value.length).toBe(2000);
        expect(lateOps / earlyOps).toBeLessThan(QUADRATIC_SEGMENT_RATIO);
        expect(elapsed).toBeLessThan(CEILING_MS);
    });

    it("per-push cost stays linear at the 2000-message cap", async () => {
        const tl = makeTimeline();
        tl.messages.value = [countedMsg(1)];
        await nextTick();
        // All proxies: reads inside the measured batches count for the
        // whole list, not just the newly pushed tail.
        for (let i = 2; i <= 1900; i++) {
            tl.pushLiveMessage(countedMsg(i));
        }
        await nextTick();
        ops.n = 0;
        for (let i = 1901; i <= 2000; i++) {
            tl.pushLiveMessage(countedMsg(i));
        }
        const earlyOps = ops.n;
        ops.n = 0;
        for (let i = 2001; i <= 2100; i++) {
            tl.pushLiveMessage(countedMsg(i));
        }
        const lateOps = ops.n;
        console.log(
            `push batch @~1950: ${earlyOps} reads, @~2050: ${lateOps} reads ` + `(${(lateOps / earlyOps).toFixed(2)}x)`
        );
        expect(lateOps / earlyOps).toBeLessThan(BATCH_RATIO);
    });
});
