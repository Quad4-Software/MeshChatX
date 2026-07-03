import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("jsqr", () => ({
    default: vi.fn(),
}));

import jsQR from "jsqr";
import {
    decodeQrFromVideo,
    describeCameraError,
    getScannerVideoConstraints,
    isCameraSupported,
    resetDecodeCanvasForTests,
} from "@/js/qrScannerUtils";

describe("qrScannerUtils", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        resetDecodeCanvasForTests();
        Object.defineProperty(global.navigator, "mediaDevices", {
            configurable: true,
            value: {
                getUserMedia: vi.fn(),
            },
        });
    });

    afterEach(() => {
        delete global.window.BarcodeDetector;
    });

    it("reports camera support when getUserMedia exists", () => {
        expect(isCameraSupported()).toBe(true);
    });

    it("prefers environment camera with higher resolution", () => {
        const constraints = getScannerVideoConstraints();
        expect(constraints.video.facingMode).toEqual({ ideal: "environment" });
        expect(constraints.video.width).toEqual({ ideal: 1280 });
        expect(constraints.video.height).toEqual({ ideal: 720 });
    });

    it("maps permission errors to the permission message", () => {
        expect(
            describeCameraError(
                { name: "NotAllowedError" },
                {
                    permissionDenied: "denied",
                    notFound: "missing",
                    failed: "failed",
                }
            )
        ).toBe("denied");
    });

    it("uses BarcodeDetector when available", async () => {
        class MockBarcodeDetector {
            detect() {
                return Promise.resolve([{ rawValue: " lxma://abc " }]);
            }
        }
        global.window.BarcodeDetector = MockBarcodeDetector;
        const video = { readyState: 2, videoWidth: 640, videoHeight: 480 };
        await expect(decodeQrFromVideo(video)).resolves.toBe("lxma://abc");
        expect(jsQR).not.toHaveBeenCalled();
    });

    it("falls back to jsQR when BarcodeDetector is unavailable", async () => {
        jsQR.mockReturnValue({ data: "lxmf://deadbeef" });
        const getContext = vi.fn(() => ({
            drawImage: vi.fn(),
            getImageData: vi.fn(() => ({ data: new Uint8ClampedArray(4) })),
        }));
        const canvas = {
            width: 0,
            height: 0,
            getContext,
        };
        vi.spyOn(document, "createElement").mockReturnValue(canvas);
        const video = {
            readyState: 2,
            videoWidth: 2,
            videoHeight: 2,
        };

        await expect(decodeQrFromVideo(video)).resolves.toBe("lxmf://deadbeef");
        expect(jsQR).toHaveBeenCalled();
    });
});
