import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeAll, afterEach } from "vitest";
import StickerView from "@/components/stickers/StickerView.vue";

const origIntersectionObserver = globalThis.IntersectionObserver;

beforeAll(() => {
    const ctx = {
        fillStyle: "",
        strokeStyle: "",
        fillRect: vi.fn(),
        clearRect: vi.fn(),
        save: vi.fn(),
        restore: vi.fn(),
        translate: vi.fn(),
        scale: vi.fn(),
        rotate: vi.fn(),
        beginPath: vi.fn(),
        closePath: vi.fn(),
        moveTo: vi.fn(),
        lineTo: vi.fn(),
        arc: vi.fn(),
        fill: vi.fn(),
        stroke: vi.fn(),
        setTransform: vi.fn(),
        drawImage: vi.fn(),
        measureText: vi.fn(() => ({ width: 0 })),
        createLinearGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
        createRadialGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
    };
    HTMLCanvasElement.prototype.getContext = vi.fn(() => ctx);
});

describe("StickerView.vue", () => {
    it("renders img for static sticker", () => {
        const w = mount(StickerView, {
            props: {
                src: "https://example.invalid/sticker.png",
                imageType: "png",
                alt: "x",
            },
        });
        expect(w.find("img").exists()).toBe(true);
        expect(w.find("video").exists()).toBe(false);
        w.unmount();
    });

    it("renders video for webm", () => {
        const w = mount(StickerView, {
            props: {
                src: "https://example.invalid/s.webm",
                imageType: "webm",
            },
        });
        expect(w.find("video").exists()).toBe(true);
        w.unmount();
    });

    it("TGS renders placeholder without fetching sticker URL", async () => {
        const baseFetch = globalThis.fetch;
        const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => baseFetch(input, init));

        const w = mount(StickerView, {
            props: {
                src: "https://example.invalid/a.tgs",
                imageType: "tgs",
            },
            attachTo: document.body,
        });

        await flushPromises();
        expect(w.find("img").exists()).toBe(false);
        expect(w.find(".w-full.h-full.flex").exists()).toBe(true);
        const tgsCalls = fetchSpy.mock.calls.filter((c) => {
            const u = typeof c[0] === "string" ? c[0] : (c[0]?.url ?? "");
            return String(u).includes("example.invalid/a.tgs");
        });
        expect(tgsCalls.length).toBe(0);

        fetchSpy.mockRestore();
        w.unmount();
    });

    it("WebM calls play when in view and pause when out", async () => {
        let ioCallback;
        class MockIntersectionObserver {
            constructor(cb) {
                ioCallback = cb;
            }
            observe = vi.fn();
            disconnect = vi.fn();
        }
        globalThis.IntersectionObserver = MockIntersectionObserver;
        const playSpy = vi.spyOn(HTMLVideoElement.prototype, "play").mockResolvedValue(undefined);
        const pauseSpy = vi.spyOn(HTMLVideoElement.prototype, "pause").mockImplementation(() => {});

        const w = mount(StickerView, {
            props: {
                src: "https://example.invalid/s.webm",
                imageType: "webm",
            },
            attachTo: document.body,
        });

        await flushPromises();
        const root = w.vm.$refs.stickerRoot;
        ioCallback([{ isIntersecting: true, target: root }]);
        await flushPromises();
        expect(playSpy).toHaveBeenCalled();

        ioCallback([{ isIntersecting: false, target: root }]);
        await flushPromises();
        expect(pauseSpy).toHaveBeenCalled();

        playSpy.mockRestore();
        pauseSpy.mockRestore();
        w.unmount();
    });

    afterEach(() => {
        globalThis.IntersectionObserver = origIntersectionObserver;
        vi.restoreAllMocks();
    });
});
