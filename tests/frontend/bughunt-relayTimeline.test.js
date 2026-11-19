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

// Bounds in this file only guard against pathological blowup, but fixed
// wall-clock limits flake on shared CI runners (the same 2000-push run
// measured 4.7s on one run and 8.6s on another with identical code). Scale
// every bound by a machine-speed factor measured with a fixed CPU workload
// that is independent of the code under test. Capped so a genuinely
// pathological regression still fails on arbitrarily slow hardware.
const CALIBRATION_MS = 40;
const MAX_SPEED_FACTOR = 4;

function speedFactor() {
    let acc = 0;
    let best = Infinity;
    for (let round = 0; round < 3; round++) {
        const t0 = performance.now();
        for (let i = 0; i < 2_000_000; i++) {
            acc += (i * 2654435761) % 97;
        }
        best = Math.min(best, performance.now() - t0);
    }
    expect(acc).toBeGreaterThan(0);
    const factor = best / CALIBRATION_MS;
    return Math.min(MAX_SPEED_FACTOR, Math.max(1, factor));
}

describe("bughunt: mergeRelayMessages complexity", () => {
    it("room-open merge (2000 existing + 150 loaded) stays fast", () => {
        const k = speedFactor();
        const base = Array.from({ length: 2000 }, (_, i) => msg(i + 1));
        const loaded = Array.from({ length: 150 }, (_, i) => msg(2001 + i));
        const t = timeMs(() => mergeRelayMessages(base, loaded));
        console.log(`merge 2000+150: ${t.toFixed(1)}ms (speed factor ${k.toFixed(2)})`);
        expect(t).toBeLessThan(250 * k);
    });

    it("worst-case merge (2000 + 2000 fresh) does not take seconds", () => {
        const k = speedFactor();
        const base = Array.from({ length: 2000 }, (_, i) => msg(i + 1));
        const loaded = Array.from({ length: 2000 }, (_, i) => msg(2001 + i));
        const t = timeMs(() => mergeRelayMessages(base, loaded));
        console.log(`merge 2000+2000: ${t.toFixed(1)}ms (speed factor ${k.toFixed(2)})`);
        expect(t, `mergeRelayMessages took ${t.toFixed(0)}ms`).toBeLessThan(1000 * k);
    });

    it("merge without seq (fallback key path) is not pathological", () => {
        const k = speedFactor();
        const base = Array.from({ length: 1000 }, (_, i) => msg(null, `text-${i}`, { ts: i * 1000, kind: "msg" }));
        const loaded = Array.from({ length: 200 }, (_, i) =>
            msg(null, `old-${i}`, { ts: (i + 5000) * 1000, kind: "msg" })
        );
        const t = timeMs(() => mergeRelayMessages(base, loaded));
        console.log(`merge noseq 1000+200: ${t.toFixed(1)}ms (speed factor ${k.toFixed(2)})`);
        expect(t).toBeLessThan(1000 * k);
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

    it("pushing 2000 live messages does not take seconds (deep watch + signature + keyset)", async () => {
        const tl = makeTimeline();
        // Warm up.
        tl.messages.value = [msg(1)];
        await nextTick();
        const k = speedFactor();
        const t0 = performance.now();
        for (let i = 2; i <= 2000; i++) {
            tl.pushLiveMessage(msg(i, `m${i}`));
        }
        await nextTick();
        const total = performance.now() - t0;
        console.log(`2000 live pushes: ${total.toFixed(0)}ms (speed factor ${k.toFixed(2)})`);
        expect(tl.messages.value.length).toBe(2000);
        // Each push triggers a deep watch traversal + O(n) signature + O(n)
        // keySet rebuild + O(n) timeline rebuild => O(n^2) overall. The bound
        // only guards against pathological blowup and scales with the
        // measured runner speed.
        expect(total, `2000 pushes took ${total.toFixed(0)}ms`).toBeLessThan(8000 * k);
    });

    it("per-push cost grows with list size (last 100 pushes vs first 100)", async () => {
        const tl = makeTimeline();
        tl.messages.value = [msg(1)];
        await nextTick();
        // Fill to 1900 without timing.
        for (let i = 2; i <= 1900; i++) {
            tl.pushLiveMessage(msg(i));
        }
        await nextTick();
        const k = speedFactor();
        const tEarly = timeMs(() => {
            for (let i = 1901; i <= 2000; i++) tl.pushLiveMessage(msg(i));
        });
        const tLate = timeMs(() => {
            for (let i = 2001; i <= 2100; i++) tl.pushLiveMessage(msg(i));
        });
        console.log(
            `push batch @~1950: ${tEarly.toFixed(0)}ms, @~2050: ${tLate.toFixed(0)}ms (speed factor ${k.toFixed(2)})`
        );
        // At cap (2000) the head-trim path also runs; still each push is O(n).
        // Same scaled bound as the 2000-push test above.
        expect(tLate).toBeLessThan(5000 * k);
    });
});
