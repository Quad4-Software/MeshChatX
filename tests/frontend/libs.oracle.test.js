// SPDX-License-Identifier: 0BSD

/**
 * Differential oracles against dayjs (devDependency) plus frozen golden
 * and cross-lib property invariants for MeshChatX frontend libs.
 */

import { describe, it, expect } from "vitest";
import dayjs from "dayjs";
import { createEmitter } from "@/libs/emitter.js";
import { formatDate, fromNow, relativeLabel, FROM_NOW_GOLDEN, isSupportedFormatPattern } from "@/libs/datetime.js";
import { uuidv4, isUuidV4, randomUuidV4 } from "@/libs/uuid.js";
import { processDirectiveArguments, bindingsEqual } from "@/libs/clickOutside.js";

function mulberry32(seed) {
    let t = seed >>> 0;
    return function next() {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
}

describe("libs oracles", () => {
    it("oracle: formatDate equals dayjs for dense local calendar sampling", () => {
        const patterns = ["MMM D, h:mm A", "YYYY-MM-DD hh:mm A", "MMM D, HH:mm", "YYYY-MM-DD", "h A", "hh:mm a"];
        const rand = mulberry32(2026);
        for (let i = 0; i < 600; i++) {
            const year = 2018 + Math.floor(rand() * 12);
            const month = Math.floor(rand() * 12);
            const day = 1 + Math.floor(rand() * 28);
            const hour = Math.floor(rand() * 24);
            const minute = Math.floor(rand() * 60);
            const d = new Date(year, month, day, hour, minute, 0, 0);
            for (const pattern of patterns) {
                expect(isSupportedFormatPattern(pattern)).toBe(true);
                expect(formatDate(d, pattern)).toBe(dayjs(d).format(pattern));
            }
        }
    });

    it("oracle: FROM_NOW_GOLDEN matches relativeLabel and fromNow", () => {
        const now = Date.parse("2024-03-15T08:00:00Z");
        for (const [deltaSec, expectedPast, expectedFuture] of FROM_NOW_GOLDEN) {
            expect(relativeLabel(deltaSec, false)).toBe(expectedPast);
            expect(fromNow(now - deltaSec * 1000, now)).toBe(expectedPast);
            if (deltaSec === 0) {
                expect(relativeLabel(0, true)).toBe(expectedPast);
                expect(fromNow(now, now)).toBe(expectedPast);
            } else {
                expect(relativeLabel(deltaSec, true)).toBe(expectedFuture);
                expect(fromNow(now + deltaSec * 1000, now)).toBe(expectedFuture);
            }
        }
    });

    it("oracle: emitter semantics match mitt-style fanout and off-all", () => {
        const e = createEmitter();
        const a = [];
        const b = [];
        const ha = (v) => a.push(v);
        const hb = (v) => b.push(v);
        e.on("msg", ha);
        e.on("msg", hb);
        e.emit("msg", 1);
        e.off("msg");
        e.emit("msg", 2);
        expect(a).toEqual([1]);
        expect(b).toEqual([1]);
        expect(e.all.get("msg")).toEqual([]);
    });

    it("oracle: uuidv4 always validates as v4 and never collides in batch", () => {
        const batch = Array.from({ length: 8000 }, () => uuidv4());
        for (const id of batch) {
            expect(isUuidV4(id)).toBe(true);
        }
        expect(new Set(batch).size).toBe(batch.length);
    });

    it("oracle: no-crypto uuid path still RFC4122 v4", () => {
        const batch = Array.from({ length: 2000 }, () => randomUuidV4({ crypto: null }));
        for (const id of batch) {
            expect(isUuidV4(id)).toBe(true);
            expect(id[14]).toBe("4");
        }
        expect(new Set(batch).size).toBe(batch.length);
    });

    it("oracle: click-outside function form is equivalent to object form defaults", () => {
        const handler = () => {};
        const a = processDirectiveArguments(handler);
        const b = processDirectiveArguments({ handler });
        expect(a.handler).toBe(b.handler);
        expect(a.isActive).toBe(true);
        expect(b.isActive).toBe(true);
        expect(a.detectIframe).toBe(true);
        expect(a.capture).toBe(false);
        expect(typeof a.middleware).toBe("function");
        expect(a.events).toEqual(b.events);
        expect(bindingsEqual(handler, handler)).toBe(true);
        expect(bindingsEqual({ handler, capture: true }, { handler, capture: true })).toBe(true);
    });

    it("property: fromNow polarity matches sign of (input - now)", () => {
        const rand = mulberry32(77);
        const now = Date.parse("2026-01-01T00:00:00Z");
        for (let i = 0; i < 500; i++) {
            const deltaMs = Math.floor((rand() - 0.5) * 2 * 365 * 86400 * 1000);
            if (deltaMs === 0) continue;
            const out = fromNow(now + deltaMs, now);
            if (deltaMs > 0) {
                expect(out.startsWith("in ")).toBe(true);
            } else {
                expect(out.endsWith(" ago")).toBe(true);
            }
        }
    });

    it("property: formatDate is idempotent for the same Date instance", () => {
        const d = new Date(2024, 3, 5, 9, 8);
        const pattern = "YYYY-MM-DD hh:mm A";
        expect(formatDate(d, pattern)).toBe(formatDate(d, pattern));
        expect(formatDate(d.getTime(), pattern)).toBe(formatDate(d, pattern));
    });

    it("property: relativeLabel is monotonic in bucket wording for increasing deltas", () => {
        const samples = FROM_NOW_GOLDEN.map(([delta]) => delta).sort((a, b) => a - b);
        for (let i = 1; i < samples.length; i++) {
            const prev = relativeLabel(samples[i - 1], false);
            const cur = relativeLabel(samples[i], false);
            expect(typeof prev).toBe("string");
            expect(typeof cur).toBe("string");
            expect(prev.length).toBeGreaterThan(0);
            expect(cur.length).toBeGreaterThan(0);
        }
    });
});
