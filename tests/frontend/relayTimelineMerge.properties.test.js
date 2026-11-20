// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import {
    filterUniqueOlderRelayMessages,
    mergeRelayMessages,
    relayMessageAlreadyPresent,
    relayMessageKey,
    buildRelayMessageTimeline,
} from "../../meshchatx/src/frontend/js/relayMessageTimeline.js";

// Deterministic PRNG so failures are reproducible.
function mulberry32(seed) {
    let a = seed >>> 0;
    return () => {
        a |= 0;
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function makeMsg(rnd, overrides = {}) {
    return {
        kind: "msg",
        seq: Math.floor(rnd() * 100),
        ts: 1000 + Math.floor(rnd() * 10000),
        src: `peer${Math.floor(rnd() * 5)}`,
        text: `t${Math.floor(rnd() * 500)}`,
        ...overrides,
    };
}

function randomBatch(rnd, n) {
    return Array.from({ length: n }, () => makeMsg(rnd));
}

describe("mergeRelayMessages properties", () => {
    it("is idempotent: merging the same batch twice changes nothing", () => {
        const rnd = mulberry32(42);
        for (let trial = 0; trial < 60; trial++) {
            const base = randomBatch(rnd, 10 + Math.floor(rnd() * 30));
            const extras = randomBatch(rnd, 5 + Math.floor(rnd() * 20));
            const once = mergeRelayMessages(base, extras);
            const twice = mergeRelayMessages(once, extras);
            expect(twice.map(relayMessageKey)).toEqual(once.map(relayMessageKey));
            expect(twice.length).toBe(once.length);
        }
    });

    it("never mutates its inputs", () => {
        const rnd = mulberry32(7);
        for (let trial = 0; trial < 40; trial++) {
            const base = randomBatch(rnd, 15);
            const extras = randomBatch(rnd, 10);
            const baseCopy = JSON.stringify(base);
            const extrasCopy = JSON.stringify(extras);
            mergeRelayMessages(base, extras);
            expect(JSON.stringify(base)).toBe(baseCopy);
            expect(JSON.stringify(extras)).toBe(extrasCopy);
        }
    });

    it("result is sorted by seq regardless of extras order", () => {
        const rnd = mulberry32(11);
        for (let trial = 0; trial < 40; trial++) {
            const extras = randomBatch(rnd, 20);
            const shuffled = [...extras].sort(() => rnd() - 0.5);
            const a = mergeRelayMessages([], extras);
            const b = mergeRelayMessages([], shuffled);
            expect(a.map(relayMessageKey)).toEqual(b.map(relayMessageKey));
            const seqs = a.map((m) => m.seq).filter((s) => typeof s === "number");
            for (let i = 1; i < seqs.length; i++) {
                expect(seqs[i]).toBeGreaterThanOrEqual(seqs[i - 1]);
            }
        }
    });

    it("merging batch-at-once equals merging one-by-one", () => {
        const rnd = mulberry32(13);
        for (let trial = 0; trial < 40; trial++) {
            const base = randomBatch(rnd, 10);
            const extras = randomBatch(rnd, 15);
            const atOnce = mergeRelayMessages(base, extras);
            let oneByOne = base;
            for (const m of extras) {
                oneByOne = mergeRelayMessages(oneByOne, [m]);
            }
            expect(atOnce.map(relayMessageKey)).toEqual(oneByOne.map(relayMessageKey));
        }
    });

    it("deduplicates mixed numeric/string seq representations", () => {
        const m1 = makeMsg(mulberry32(1), { seq: 5 });
        const m2 = { ...m1, seq: "5" };
        expect(relayMessageKey(m1)).toBe(relayMessageKey(m2));
        expect(relayMessageAlreadyPresent([m1], m2)).toBe(true);
        const merged = mergeRelayMessages([m1], [m2]);
        expect(merged).toHaveLength(1);
    });

    it("seq sort treats numeric strings like numbers", () => {
        const rnd = mulberry32(3);
        const base = [{ kind: "msg", seq: 10, ts: 1, src: "a", text: "x" }];
        const incoming = { kind: "msg", seq: "5", ts: 999999, src: "a", text: "y" };
        const merged = mergeRelayMessages(base, [incoming]);
        // seq "5" must sort before seq 10 even though its ts is larger.
        expect(merged[0].seq).toBe("5");
        expect(merged[1].seq).toBe(10);
        void rnd;
    });

    it("filterUniqueOlderRelayMessages dedupes mixed seq types", () => {
        const existing = [{ kind: "msg", seq: 7, ts: 1, src: "a", text: "x" }];
        const older = [
            { kind: "msg", seq: "7", ts: 2, src: "a", text: "y" },
            { kind: "msg", seq: 6, ts: 0, src: "a", text: "z" },
        ];
        const out = filterUniqueOlderRelayMessages(older, existing);
        expect(out).toHaveLength(1);
        expect(out[0].seq).toBe(6);
    });

    it("no-seq messages still dedupe by content key", () => {
        const m1 = { kind: "msg", ts: 5, src: "a", text: "hello" };
        const m2 = { ...m1 };
        const merged = mergeRelayMessages([m1], [m2]);
        expect(merged).toHaveLength(1);
    });
});

describe("relayMessageKey properties", () => {
    it("is deterministic and attribute-safe", () => {
        const rnd = mulberry32(9);
        for (let i = 0; i < 200; i++) {
            const m = makeMsg(rnd, {
                text: `x"><script>${Math.floor(rnd() * 1000)}`,
            });
            const k = relayMessageKey(m);
            expect(k).toBe(relayMessageKey(m));
            expect(k).not.toContain("<script>");
            expect(k).not.toContain('"');
        }
    });
});
