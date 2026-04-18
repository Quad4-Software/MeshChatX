import { describe, it, expect, vi, afterEach } from "vitest";
import { attachInView, isAnimatedRasterType } from "@/js/inViewObserver.js";

describe("inViewObserver", () => {
    describe("isAnimatedRasterType", () => {
        it("returns true for gif and webp", () => {
            expect(isAnimatedRasterType("gif")).toBe(true);
            expect(isAnimatedRasterType("WEBP")).toBe(true);
        });
        it("returns false for png, jpeg, empty, null", () => {
            expect(isAnimatedRasterType("png")).toBe(false);
            expect(isAnimatedRasterType("jpeg")).toBe(false);
            expect(isAnimatedRasterType("")).toBe(false);
            expect(isAnimatedRasterType(null)).toBe(false);
        });
    });

    describe("attachInView", () => {
        const origIo = globalThis.IntersectionObserver;

        afterEach(() => {
            globalThis.IntersectionObserver = origIo;
        });

        it("invokes callback with intersecting true when IntersectionObserver is undefined", () => {
            globalThis.IntersectionObserver = undefined;
            const fn = vi.fn();
            const el = document.createElement("div");
            const disconnect = attachInView(el, fn);
            expect(fn).toHaveBeenCalledTimes(1);
            expect(fn.mock.calls[0][0].isIntersecting).toBe(true);
            expect(fn.mock.calls[0][0].target).toBe(el);
            disconnect();
        });

        it("returns noop disconnect when el is null", () => {
            const fn = vi.fn();
            const disconnect = attachInView(null, fn);
            expect(fn).not.toHaveBeenCalled();
            disconnect();
        });

        it("observes element and forwards entries to callback", () => {
            const observe = vi.fn();
            const disconnectIo = vi.fn();
            let callback;
            class MockIntersectionObserver {
                constructor(cb, opts) {
                    callback = cb;
                    expect(opts.threshold).toBe(0.5);
                    expect(opts.rootMargin).toBe("10px");
                }
                observe(el) {
                    observe(el);
                }
                disconnect() {
                    disconnectIo();
                }
            }
            globalThis.IntersectionObserver = MockIntersectionObserver;

            const el = document.createElement("div");
            const fn = vi.fn();
            const disconnect = attachInView(el, fn, { threshold: 0.5, rootMargin: "10px" });

            expect(observe).toHaveBeenCalledWith(el);
            callback([{ isIntersecting: false, target: el }]);
            expect(fn).toHaveBeenCalledWith(expect.objectContaining({ isIntersecting: false, target: el }));

            disconnect();
            expect(disconnectIo).toHaveBeenCalled();
        });
    });
});
