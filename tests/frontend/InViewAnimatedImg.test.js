import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import InViewAnimatedImg from "@/components/messages/InViewAnimatedImg.vue";

describe("InViewAnimatedImg.vue", () => {
    const origIo = globalThis.IntersectionObserver;

    afterEach(() => {
        globalThis.IntersectionObserver = origIo;
        vi.restoreAllMocks();
    });

    it("shows img immediately when IntersectionObserver is unavailable (fallback)", async () => {
        globalThis.IntersectionObserver = undefined;
        const w = mount(InViewAnimatedImg, {
            props: {
                src: "https://example.invalid/a.gif",
                imgClass: "w-full h-8",
            },
        });
        await flushPromises();
        expect(w.find("img").exists()).toBe(true);
        expect(w.find("img").attributes("src")).toBe("https://example.invalid/a.gif");
        expect(w.find("div[aria-hidden=true]").exists()).toBe(false);
        w.unmount();
    });

    it("shows placeholder until intersecting when observer fires false then true", async () => {
        let callback;
        class MockIntersectionObserver {
            constructor(cb) {
                callback = cb;
            }
            observe = vi.fn();
            disconnect = vi.fn();
        }
        globalThis.IntersectionObserver = MockIntersectionObserver;

        const w = mount(InViewAnimatedImg, {
            props: {
                src: "https://example.invalid/b.gif",
                imgClass: "test-img",
            },
            attachTo: document.body,
        });

        await flushPromises();
        expect(w.find("img").exists()).toBe(false);

        const wrap = w.vm.$refs.wrap;
        callback([{ isIntersecting: true, target: wrap }]);
        await flushPromises();

        expect(w.find("img").exists()).toBe(true);
        expect(w.find("img").classes()).toContain("test-img");
        w.unmount();
    });

    it("hides img when intersection becomes false", async () => {
        let callback;
        class MockIntersectionObserver {
            constructor(cb) {
                callback = cb;
            }
            observe = vi.fn();
            disconnect = vi.fn();
        }
        globalThis.IntersectionObserver = MockIntersectionObserver;

        const w = mount(InViewAnimatedImg, {
            props: { src: "https://example.invalid/c.gif", imgClass: "x" },
            attachTo: document.body,
        });
        await flushPromises();

        const wrap = w.vm.$refs.wrap;
        callback([{ isIntersecting: true, target: wrap }]);
        await flushPromises();
        expect(w.find("img").exists()).toBe(true);

        callback([{ isIntersecting: false, target: wrap }]);
        await flushPromises();
        expect(w.find("img").exists()).toBe(false);

        w.unmount();
    });

    it("disconnects observer on unmount", async () => {
        const disconnect = vi.fn();
        class MockIntersectionObserver {
            constructor() {
                this.observe = vi.fn();
                this.disconnect = disconnect;
            }
        }
        globalThis.IntersectionObserver = MockIntersectionObserver;

        const w = mount(InViewAnimatedImg, {
            props: { src: "https://example.invalid/d.gif" },
        });
        await flushPromises();
        w.unmount();
        expect(disconnect).toHaveBeenCalled();
    });

    it("emits click from img", async () => {
        globalThis.IntersectionObserver = undefined;
        const w = mount(InViewAnimatedImg, {
            props: { src: "https://example.invalid/e.gif" },
        });
        await flushPromises();
        await w.find("img").trigger("click");
        expect(w.emitted("click")).toBeTruthy();
        w.unmount();
    });

    it("uses fit-parent placeholder classes", async () => {
        globalThis.IntersectionObserver = undefined;
        const w = mount(InViewAnimatedImg, {
            props: {
                src: "https://example.invalid/f.gif",
                fitParent: true,
            },
        });
        await flushPromises();
        expect(w.vm.$el.className).toContain("absolute");
        w.unmount();
    });
});
