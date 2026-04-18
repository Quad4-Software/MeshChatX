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

    it("TGS does not fetch until intersection reports in view", async () => {
        let ioCallback;
        class MockIntersectionObserver {
            constructor(cb) {
                ioCallback = cb;
            }
            observe = vi.fn();
            disconnect = vi.fn();
        }
        globalThis.IntersectionObserver = MockIntersectionObserver;

        const baseFetch = globalThis.fetch;
        const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
            const reqUrl = typeof input === "string" ? input : (input?.url ?? "");
            if (reqUrl.includes("example.invalid/a.tgs")) {
                return {
                    arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
                };
            }
            return baseFetch(input, init);
        });

        const tgsCallCount = () =>
            fetchSpy.mock.calls.filter((c) => {
                const u = typeof c[0] === "string" ? c[0] : (c[0]?.url ?? "");
                return String(u).includes("example.invalid/a.tgs");
            }).length;

        const w = mount(StickerView, {
            props: {
                src: "https://example.invalid/a.tgs",
                imageType: "tgs",
            },
            attachTo: document.body,
        });

        await flushPromises();
        expect(tgsCallCount()).toBe(0);

        const root = w.vm.$refs.stickerRoot;
        expect(root).toBeTruthy();
        ioCallback([{ isIntersecting: true, target: root }]);
        await w.vm.$nextTick();
        await w.vm.$nextTick();
        expect(w.vm.inView).toBe(true);
        expect(w.vm.$refs.lottieMount).toBeTruthy();
        await vi.waitFor(() => {
            expect(tgsCallCount()).toBeGreaterThan(0);
        });

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

    it("mountLottie fetches and decodes gzip TGS payload", async () => {
        const { gzipSync } = await import("node:zlib");
        const payload = JSON.stringify({
            v: "5.5.7",
            fr: 30,
            ip: 0,
            op: 30,
            w: 512,
            h: 512,
            nm: "t",
            ddd: 0,
            assets: [],
            layers: [],
        });
        const gz = gzipSync(Buffer.from(payload, "utf8"));
        const ab = gz.buffer.slice(gz.byteOffset, gz.byteOffset + gz.byteLength);

        const fetchMock = vi.fn(() =>
            Promise.resolve({
                arrayBuffer: () => Promise.resolve(ab),
            })
        );
        vi.stubGlobal("fetch", fetchMock);

        const w = mount(StickerView, {
            props: {
                src: "https://example.invalid/a.tgs",
                imageType: "tgs",
            },
            attachTo: document.body,
        });

        await w.vm.$nextTick();
        expect(w.vm.$refs.lottieMount).toBeTruthy();
        w.vm.inView = true;
        await w.vm.mountLottie();
        await flushPromises();

        expect(fetchMock).toHaveBeenCalled();
        expect(w.vm.lottieAnim).toBeTruthy();
        w.unmount();
        vi.unstubAllGlobals();
    });

    afterEach(() => {
        globalThis.IntersectionObserver = origIntersectionObserver;
        vi.restoreAllMocks();
    });
});
