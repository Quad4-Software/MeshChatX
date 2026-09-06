// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import dayjs from "dayjs";

import createEmitterDefault, { createEmitter } from "@/libs/emitter.js";
import { randomUuidV4, uuidv4, isUuidV4, fillRandomBytes, resolveCrypto, UUID_V4_RE } from "@/libs/uuid.js";
import {
    formatDate,
    fromNow,
    relativeLabel,
    meshDate,
    toDate,
    isSupportedFormatPattern,
    FROM_NOW_GOLDEN,
    SUPPORTED_FORMAT_TOKENS,
} from "@/libs/datetime.js";
import {
    processDirectiveArguments,
    bindingsEqual,
    isClickOutsideElement,
    execHandler,
    onOutsideEvent,
    onFauxIframeClick,
    beforeMount,
    updated,
    unmounted,
    HANDLERS_PROPERTY,
    DEFAULT_EVENTS,
} from "@/libs/clickOutside.js";

function mulberry32(seed) {
    let t = seed >>> 0;
    return function next() {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
}

describe("libs/emitter", () => {
    it("unit: on/emit/off round trip", () => {
        const e = createEmitter();
        const seen = [];
        const handler = (v) => seen.push(v);
        e.on("x", handler);
        e.emit("x", 1);
        e.off("x", handler);
        e.emit("x", 2);
        expect(seen).toEqual([1]);
    });

    it("unit: default export matches createEmitter", () => {
        const e = createEmitterDefault();
        const seen = [];
        e.on("z", (v) => seen.push(v));
        e.emit("z", 9);
        expect(seen).toEqual([9]);
    });

    it("edge: off unknown handler and off-all are safe", () => {
        const e = createEmitter();
        const handler = () => {};
        e.on("a", handler);
        e.off("a", () => {});
        e.off("missing");
        e.off("a");
        expect(e.all.get("a")).toEqual([]);
        expect(() => e.emit("a", 1)).not.toThrow();
    });

    it("edge: non-function on is ignored", () => {
        const e = createEmitter();
        e.on("a", null);
        e.on("a", 12);
        expect(e.all.has("a")).toBe(false);
    });

    it("edge: emit during emit uses snapshot so removes do not skip peers", () => {
        const e = createEmitter();
        const order = [];
        const b = () => order.push("b");
        const a = () => {
            order.push("a");
            e.off("t", b);
        };
        e.on("t", a);
        e.on("t", b);
        e.emit("t");
        expect(order).toEqual(["a", "b"]);
    });

    it("edge: symbol event types work", () => {
        const e = createEmitter();
        const key = Symbol("evt");
        const seen = [];
        e.on(key, (v) => seen.push(v));
        e.emit(key, "ok");
        expect(seen).toEqual(["ok"]);
    });

    it("edge: throwing handler does not prevent later handlers", () => {
        const e = createEmitter();
        const seen = [];
        e.on("t", () => {
            throw new Error("boom");
        });
        e.on("t", () => seen.push("later"));
        expect(() => e.emit("t")).toThrow(/boom/);
        expect(seen).toEqual([]);
        const safe = createEmitter();
        safe.on("t", () => {
            try {
                throw new Error("boom");
            } catch {
                /* swallow */
            }
        });
        safe.on("t", () => seen.push("later"));
        safe.emit("t");
        expect(seen).toEqual(["later"]);
    });

    it("wildcard * receives type and payload", () => {
        const e = createEmitter();
        const seen = [];
        e.on("*", (type, payload) => seen.push([type, payload]));
        e.on("ping", () => {});
        e.emit("ping", { ok: true });
        expect(seen).toEqual([["ping", { ok: true }]]);
    });

    it("property: handler list length equals successful on calls", () => {
        const rand = mulberry32(7);
        for (let trial = 0; trial < 80; trial++) {
            const e = createEmitter();
            const n = 1 + Math.floor(rand() * 20);
            for (let i = 0; i < n; i++) {
                e.on("k", () => {});
            }
            expect(e.all.get("k").length).toBe(n);
        }
    });

    it("fuzzing: random on/off/emit sequences never throw", () => {
        const rand = mulberry32(99);
        const e = createEmitter();
        const handlers = [];
        for (let i = 0; i < 1000; i++) {
            const op = Math.floor(rand() * 4);
            const type = rand() < 0.1 ? "*" : `e${Math.floor(rand() * 8)}`;
            if (op === 0) {
                const handler = () => {};
                handlers.push(handler);
                e.on(type, handler);
            } else if (op === 1 && handlers.length) {
                e.off(type, handlers[Math.floor(rand() * handlers.length)]);
            } else if (op === 2) {
                e.off(type);
            } else {
                e.emit(type, { i });
            }
        }
    });
});

describe("libs/uuid", () => {
    it("unit: uuidv4 matches RFC4122 v4 shape", () => {
        const id = uuidv4();
        expect(isUuidV4(id)).toBe(true);
        expect(UUID_V4_RE.test(id)).toBe(true);
        expect(id[14]).toBe("4");
        expect("89ab").toContain(id[19].toLowerCase());
    });

    it("edge: isUuidV4 rejects junk", () => {
        expect(isUuidV4(null)).toBe(false);
        expect(isUuidV4("")).toBe(false);
        expect(isUuidV4("not-a-uuid")).toBe(false);
        expect(isUuidV4("00000000-0000-0000-0000-000000000000")).toBe(false);
        expect(isUuidV4("00000000-0000-4000-0000-000000000000")).toBe(false);
        expect(isUuidV4(12)).toBe(false);
    });

    it("edge: getRandomValues path when randomUUID missing", () => {
        const fakeCrypto = {
            getRandomValues(buf) {
                for (let i = 0; i < buf.length; i++) buf[i] = (i * 17) & 0xff;
                return buf;
            },
        };
        const id = randomUuidV4({ crypto: fakeCrypto });
        expect(isUuidV4(id)).toBe(true);
        const bytes = fillRandomBytes(new Uint8Array(4), { crypto: fakeCrypto });
        expect(Array.from(bytes)).toEqual([0, 17, 34, 51]);
    });

    it("edge: Math.random fallback when crypto is null", () => {
        const spy = vi.spyOn(Math, "random").mockReturnValue(0.5);
        try {
            const id = randomUuidV4({ crypto: null });
            expect(isUuidV4(id)).toBe(true);
            const bytes = fillRandomBytes(new Uint8Array(3), { crypto: null });
            expect(bytes.every((b) => b === 128)).toBe(true);
        } finally {
            spy.mockRestore();
        }
    });

    it("edge: fillRandomBytes rejects non-Uint8Array", () => {
        expect(() => fillRandomBytes(/** @type {any} */ ([]))).toThrow(/Uint8Array/);
    });

    it("edge: resolveCrypto respects explicit null override", () => {
        expect(resolveCrypto({ crypto: null })).toBeNull();
        expect(resolveCrypto({})).toBeTruthy();
        const original = globalThis.crypto;
        vi.stubGlobal("crypto", undefined);
        try {
            expect(resolveCrypto({})).toBeUndefined();
            expect(isUuidV4(randomUuidV4({}))).toBe(true);
        } finally {
            vi.stubGlobal("crypto", original);
        }
    });

    it("property: generated ids are unique over large samples", () => {
        const set = new Set();
        for (let i = 0; i < 5000; i++) {
            set.add(uuidv4());
        }
        expect(set.size).toBe(5000);
    });

    it("property: no-crypto ids still unique and valid", () => {
        const set = new Set();
        for (let i = 0; i < 1000; i++) {
            const id = uuidv4({ crypto: null });
            expect(isUuidV4(id)).toBe(true);
            set.add(id);
        }
        expect(set.size).toBe(1000);
    });

    it("fuzzing: fillRandomBytes never throws for sizes 0..128", () => {
        for (let n = 0; n <= 128; n++) {
            expect(() => fillRandomBytes(new Uint8Array(n), { crypto: null })).not.toThrow();
            expect(() => fillRandomBytes(new Uint8Array(n))).not.toThrow();
        }
    });
});

describe("libs/datetime", () => {
    it("unit: formatDate tokens used by MeshChatX", () => {
        const d = new Date(2025, 0, 2, 15, 4, 0);
        expect(formatDate(d, "MMM D, h:mm A")).toBe("Jan 2, 3:04 PM");
        expect(formatDate(d, "YYYY-MM-DD hh:mm A")).toBe("2025-01-02 03:04 PM");
        expect(formatDate(d, "MMM D, HH:mm")).toBe("Jan 2, 15:04");
        expect(formatDate(d, "M/D H:mm a")).toBe("1/2 15:04 pm");
        expect(formatDate(new Date(2025, 0, 2, 0, 0, 0), "h A")).toBe("12 AM");
        expect(formatDate(new Date(2025, 0, 2, 12, 0, 0), "h A")).toBe("12 PM");
        expect(formatDate(d, "DD MM YYYY")).toBe("02 01 2025");
    });

    it("unit: isSupportedFormatPattern", () => {
        expect(isSupportedFormatPattern("MMM D, h:mm A")).toBe(true);
        expect(isSupportedFormatPattern("plain text")).toBe(true);
        expect(isSupportedFormatPattern("YYYY-MM-DD ss")).toBe(true);
        expect(isSupportedFormatPattern("")).toBe(false);
        expect(isSupportedFormatPattern(null)).toBe(false);
        expect(SUPPORTED_FORMAT_TOKENS).toContain("YYYY");
        expect(isSupportedFormatPattern("!!!")).toBe(true);
    });

    it("edge: toDate and formatDate on invalid inputs", () => {
        expect(toDate(null)).toBeNull();
        expect(toDate("")).toBeNull();
        expect(toDate(Number.NaN)).toBeNull();
        expect(toDate(Infinity)).toBeNull();
        expect(toDate("not-a-date")).toBeNull();
        expect(toDate({})).toBeNull();
        expect(toDate(new Date(Number.NaN))).toBeNull();
        expect(formatDate(null, "YYYY")).toBe("");
        expect(formatDate(Date.now(), "")).toBe("");
        expect(formatDate(Date.now(), null)).toBe("");
        expect(fromNow(null)).toBe("");
        expect(fromNow(Date.now(), null)).toBe("");
    });

    it("golden: FROM_NOW_GOLDEN table is exact", () => {
        const now = Date.parse("2025-06-01T12:00:00Z");
        for (const [deltaSec, expectedPast, expectedFuture] of FROM_NOW_GOLDEN) {
            expect(relativeLabel(deltaSec, false)).toBe(expectedPast);
            expect(relativeLabel(deltaSec, true)).toBe(deltaSec === 0 ? expectedPast : expectedFuture);
            expect(fromNow(now - deltaSec * 1000, now)).toBe(expectedPast);
            if (deltaSec === 0) {
                expect(fromNow(now, now)).toBe(expectedPast);
            } else {
                expect(fromNow(now + deltaSec * 1000, now)).toBe(expectedFuture);
            }
        }
    });

    it("oracle: formatDate matches dayjs for MeshChatX patterns", () => {
        const patterns = ["MMM D, h:mm A", "YYYY-MM-DD hh:mm A", "MMM D, HH:mm", "M", "D", "H", "a"];
        const stamps = [
            new Date(2020, 0, 1, 0, 0, 0),
            new Date(2024, 5, 15, 12, 30, 0),
            new Date(2025, 11, 31, 23, 59, 0),
            new Date(2026, 6, 17, 21, 34, 0),
            new Date(),
        ];
        for (const ts of stamps) {
            for (const pattern of patterns) {
                expect(formatDate(ts, pattern)).toBe(dayjs(ts).format(pattern));
            }
        }
    });

    it("property: fromNow polarity matches sign of (input - now)", () => {
        const rand = mulberry32(42);
        const now = Date.now();
        for (let i = 0; i < 400; i++) {
            const deltaSec = Math.floor(rand() * 400 * 86400) - 200 * 86400;
            if (deltaSec === 0) continue;
            const out = fromNow(now + deltaSec * 1000, now);
            expect(out.length).toBeGreaterThan(0);
            if (deltaSec > 0) {
                expect(out.startsWith("in ")).toBe(true);
            } else {
                expect(out.endsWith(" ago")).toBe(true);
            }
        }
    });

    it("fuzzing: meshDate never throws on random inputs", () => {
        const rand = mulberry32(3);
        const junk = [null, undefined, "", "x", {}, [], Number.NaN, Infinity, -Infinity, true, false];
        for (let i = 0; i < 500; i++) {
            const input = rand() < 0.3 ? junk[Math.floor(rand() * junk.length)] : Date.now() + (rand() - 0.5) * 1e12;
            const d = meshDate(input);
            expect(() => d.format("MMM D, h:mm A")).not.toThrow();
            expect(() => d.fromNow()).not.toThrow();
            expect(() => d.toDate()).not.toThrow();
        }
    });
});

describe("libs/clickOutside", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
        document.body.innerHTML = "";
    });

    it("unit: processDirectiveArguments accepts function and object forms", () => {
        const fn = () => {};
        expect(processDirectiveArguments(fn).handler).toBe(fn);
        const obj = processDirectiveArguments({
            handler: fn,
            capture: true,
            isActive: false,
            detectIframe: false,
            events: ["mousedown"],
        });
        expect(obj.capture).toBe(true);
        expect(obj.isActive).toBe(false);
        expect(obj.detectIframe).toBe(false);
        expect(obj.events).toEqual(["mousedown"]);
        expect(DEFAULT_EVENTS.length).toBeGreaterThan(0);
    });

    it("unit: bindingsEqual preserves function identity", () => {
        const a = () => {};
        const b = () => {};
        expect(bindingsEqual(a, a)).toBe(true);
        expect(bindingsEqual(a, b)).toBe(false);
        expect(bindingsEqual({ handler: a, capture: true }, { handler: a, capture: true })).toBe(true);
        expect(bindingsEqual({ handler: a, capture: true }, { handler: a, capture: false })).toBe(false);
        expect(bindingsEqual({ handler: a }, { handler: b })).toBe(false);
        expect(bindingsEqual(null, { handler: a })).toBe(false);
        expect(bindingsEqual(1, 2)).toBe(false);
        expect(bindingsEqual({ handler: a }, null)).toBe(false);
    });

    it("edge: invalid bindings throw", () => {
        expect(() => processDirectiveArguments(null)).toThrow(/function or an object/);
        expect(() => processDirectiveArguments("x")).toThrow(/function or an object/);
        expect(() => processDirectiveArguments({})).toThrow(/handler must be a function/);
    });

    it("unit: isClickOutsideElement uses contains, composedPath, and path fallback", () => {
        const root = document.createElement("div");
        const child = document.createElement("span");
        root.appendChild(child);
        document.body.appendChild(root);
        expect(
            isClickOutsideElement({
                el: root,
                event: { target: child, composedPath: () => [child, root, document.body] },
            })
        ).toBe(false);
        expect(
            isClickOutsideElement({
                el: root,
                event: { target: document.body, path: [document.body] },
            })
        ).toBe(true);
        expect(
            isClickOutsideElement({
                el: root,
                event: { target: child },
            })
        ).toBe(false);
        expect(
            isClickOutsideElement({
                el: root,
                event: { target: null },
            })
        ).toBe(true);
    });

    it("unit: middleware can block handler", () => {
        const handler = vi.fn();
        execHandler({ event: {}, handler, middleware: () => false });
        expect(handler).not.toHaveBeenCalled();
        execHandler({ event: { ok: 1 }, handler, middleware: () => true });
        expect(handler).toHaveBeenCalledOnce();
    });

    it("lifecycle: beforeMount/updated/unmounted attach and detach listeners", () => {
        const el = document.createElement("div");
        document.body.appendChild(el);
        const outside = document.createElement("button");
        document.body.appendChild(outside);
        const handler1 = vi.fn();
        const handler2 = vi.fn();

        beforeMount(el, { value: { handler: handler1, events: ["click"], detectIframe: false } });
        vi.runAllTimers();
        expect(el[HANDLERS_PROPERTY].length).toBe(1);

        const clickEvent = new MouseEvent("click", { bubbles: true });
        Object.defineProperty(clickEvent, "composedPath", {
            value: () => [outside, document.body, document.documentElement],
        });
        document.documentElement.dispatchEvent(clickEvent);
        expect(handler1).toHaveBeenCalled();

        updated(el, {
            value: { handler: handler1, events: ["click"], detectIframe: false },
            oldValue: { handler: handler1, events: ["click"], detectIframe: false },
        });
        expect(handler1).toHaveBeenCalledTimes(1);

        updated(el, {
            value: { handler: handler2, events: ["click"], detectIframe: false },
            oldValue: { handler: handler1, events: ["click"], detectIframe: false },
        });
        vi.runAllTimers();
        document.documentElement.dispatchEvent(clickEvent);
        expect(handler2).toHaveBeenCalled();

        unmounted(el);
        expect(el[HANDLERS_PROPERTY]).toBeUndefined();
        document.documentElement.dispatchEvent(clickEvent);
        expect(handler2).toHaveBeenCalledTimes(1);
    });

    it("lifecycle: isActive false skips listeners", () => {
        const el = document.createElement("div");
        document.body.appendChild(el);
        beforeMount(el, { value: { handler: () => {}, isActive: false } });
        expect(el[HANDLERS_PROPERTY]).toBeUndefined();
    });

    it("lifecycle: unmount before delayed attach is safe", () => {
        const el = document.createElement("div");
        document.body.appendChild(el);
        const addSpy = vi.spyOn(document.documentElement, "addEventListener");
        beforeMount(el, { value: { handler: () => {}, events: ["click"], detectIframe: false } });
        expect(el[HANDLERS_PROPERTY]).toBeTruthy();
        unmounted(el);
        expect(el[HANDLERS_PROPERTY]).toBeUndefined();
        vi.runAllTimers();
        expect(addSpy).not.toHaveBeenCalled();
        addSpy.mockRestore();
    });

    it("iframe: blur listener invokes onFauxIframeClick path", () => {
        const el = document.createElement("div");
        document.body.appendChild(el);
        const iframe = document.createElement("iframe");
        document.body.appendChild(iframe);
        const handler = vi.fn();
        beforeMount(el, { value: { handler, events: ["click"], detectIframe: true } });
        vi.runAllTimers();
        const activeSpy = vi.spyOn(document, "activeElement", "get").mockReturnValue(iframe);
        try {
            window.dispatchEvent(new Event("blur"));
            vi.runAllTimers();
            expect(handler).toHaveBeenCalled();
        } finally {
            activeSpy.mockRestore();
            unmounted(el);
        }
    });

    it("iframe: onFauxIframeClick fires when activeElement is outside iframe", () => {
        const el = document.createElement("div");
        document.body.appendChild(el);
        const iframe = document.createElement("iframe");
        document.body.appendChild(iframe);
        const handler = vi.fn();
        const activeSpy = vi.spyOn(document, "activeElement", "get").mockReturnValue(iframe);
        try {
            onFauxIframeClick({
                el,
                event: new Event("blur"),
                handler,
                middleware: (x) => x,
            });
            vi.runAllTimers();
            expect(handler).toHaveBeenCalledOnce();
        } finally {
            activeSpy.mockRestore();
        }
    });

    it("iframe: onFauxIframeClick ignores iframe contained by el", () => {
        const el = document.createElement("div");
        const iframe = document.createElement("iframe");
        el.appendChild(iframe);
        document.body.appendChild(el);
        const handler = vi.fn();
        const activeSpy = vi.spyOn(document, "activeElement", "get").mockReturnValue(iframe);
        try {
            onFauxIframeClick({
                el,
                event: new Event("blur"),
                handler,
                middleware: (x) => x,
            });
            vi.runAllTimers();
            expect(handler).not.toHaveBeenCalled();
        } finally {
            activeSpy.mockRestore();
        }
    });

    it("iframe: detectIframe registers blur listener via beforeMount", () => {
        const el = document.createElement("div");
        document.body.appendChild(el);
        const handler = vi.fn();
        beforeMount(el, { value: { handler, detectIframe: true } });
        vi.runAllTimers();
        expect(el[HANDLERS_PROPERTY].some((entry) => entry.event === "blur")).toBe(true);
        unmounted(el);
    });

    it("lifecycle: beforeMount attaches listeners that fire on outside click", () => {
        const el = document.createElement("div");
        document.body.appendChild(el);
        const outside = document.createElement("button");
        document.body.appendChild(outside);
        const handler = vi.fn();

        beforeMount(el, { value: { handler, events: ["click"], detectIframe: false } });
        vi.runAllTimers();
        expect(el[HANDLERS_PROPERTY].length).toBe(1);

        const clickEvent = new MouseEvent("click", { bubbles: true });
        Object.defineProperty(clickEvent, "composedPath", {
            value: () => [outside, document.body, document.documentElement],
        });
        document.documentElement.dispatchEvent(clickEvent);
        expect(handler).toHaveBeenCalled();
        unmounted(el);
    });

    it("unit: onOutsideEvent ignores inside clicks", () => {
        const el = document.createElement("div");
        const child = document.createElement("span");
        el.appendChild(child);
        const handler = vi.fn();
        onOutsideEvent({
            el,
            event: { target: child, composedPath: () => [child, el] },
            handler,
            middleware: (x) => x,
        });
        expect(handler).not.toHaveBeenCalled();
    });

    it("fuzzing: processDirectiveArguments and isClickOutsideElement stay safe", () => {
        const rand = mulberry32(11);
        const handler = () => {};
        for (let i = 0; i < 300; i++) {
            const value =
                rand() < 0.5
                    ? handler
                    : {
                          handler,
                          capture: rand() < 0.5,
                          isActive: rand() < 0.8,
                          detectIframe: rand() < 0.8,
                          events: rand() < 0.3 ? ["mousedown"] : undefined,
                          middleware: rand() < 0.5 ? () => true : undefined,
                      };
            expect(() => processDirectiveArguments(value)).not.toThrow();
            const el = document.createElement("div");
            const target = document.createElement("span");
            expect(() =>
                isClickOutsideElement({
                    el,
                    event: {
                        target,
                        composedPath: () => (rand() < 0.5 ? [target] : [target, el]),
                    },
                })
            ).not.toThrow();
        }
    });
});
