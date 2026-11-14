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

describe("bughunt: mergeRelayMessages complexity", () => {
    it("room-open merge (2000 existing + 150 loaded) stays fast", () => {
        const base = Array.from({ length: 2000 }, (_, i) => msg(i + 1));
        const loaded = Array.from({ length: 150 }, (_, i) => msg(2001 + i));
        const t = timeMs(() => mergeRelayMessages(base, loaded));
        console.log(`merge 2000+150: ${t.toFixed(1)}ms`);
        expect(t).toBeLessThan(250);
    });

    it("worst-case merge (2000 + 2000 fresh) does not take seconds", () => {
        const base = Array.from({ length: 2000 }, (_, i) => msg(i + 1));
        const loaded = Array.from({ length: 2000 }, (_, i) => msg(2001 + i));
        const t = timeMs(() => mergeRelayMessages(base, loaded));
        console.log(`merge 2000+2000: ${t.toFixed(1)}ms`);
        expect(t, `mergeRelayMessages took ${t.toFixed(0)}ms`).toBeLessThan(1000);
    });

    it("merge without seq (fallback key path) is not pathological", () => {
        const base = Array.from({ length: 1000 }, (_, i) =>
            msg(null, `text-${i}`, { ts: i * 1000, kind: "msg" })
        );
        const loaded = Array.from({ length: 200 }, (_, i) =>
            msg(null, `old-${i}`, { ts: (i + 5000) * 1000, kind: "msg" })
        );
        const t = timeMs(() => mergeRelayMessages(base, loaded));
        console.log(`merge noseq 1000+200: ${t.toFixed(1)}ms`);
        expect(t).toBeLessThan(1000);
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
        const t0 = performance.now();
        for (let i = 2; i <= 2000; i++) {
            tl.pushLiveMessage(msg(i, `m${i}`));
        }
        await nextTick();
        const total = performance.now() - t0;
        console.log(`2000 live pushes: ${total.toFixed(0)}ms`);
        expect(tl.messages.value.length).toBe(2000);
        // Each push triggers a deep watch traversal + O(n) signature + O(n)
        // keySet rebuild + O(n) timeline rebuild => O(n^2) overall.
        expect(total, `2000 pushes took ${total.toFixed(0)}ms`).toBeLessThan(3000);
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
        const tEarly = timeMs(() => {
            for (let i = 1901; i <= 2000; i++) tl.pushLiveMessage(msg(i));
        });
        const tLate = timeMs(() => {
            for (let i = 2001; i <= 2100; i++) tl.pushLiveMessage(msg(i));
        });
        console.log(`push batch @~1950: ${tEarly.toFixed(0)}ms, @~2050: ${tLate.toFixed(0)}ms`);
        // At cap (2000) the head-trim path also runs; still each push is O(n).
        expect(tLate).toBeLessThan(3000);
    });
});
