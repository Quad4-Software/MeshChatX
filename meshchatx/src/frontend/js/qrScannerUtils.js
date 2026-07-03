import jsQR from "jsqr";

let decodeCanvas = null;

export function resetDecodeCanvasForTests() {
    decodeCanvas = null;
}

export function isCameraSupported() {
    return typeof window !== "undefined" && !!navigator?.mediaDevices?.getUserMedia;
}

export function getScannerVideoConstraints() {
    return {
        video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1280 },
            height: { ideal: 720 },
        },
        audio: false,
    };
}

export function describeCameraError(error, messages) {
    const name = error?.name || "";
    if (name === "NotAllowedError" || name === "SecurityError") {
        return messages.permissionDenied;
    }
    if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        return messages.notFound;
    }
    return messages.failed;
}

function getDecodeCanvas() {
    if (!decodeCanvas) {
        decodeCanvas = document.createElement("canvas");
    }
    return decodeCanvas;
}

async function decodeWithBarcodeDetector(video) {
    if (typeof window.BarcodeDetector === "undefined") {
        return null;
    }
    const detector = new window.BarcodeDetector({ formats: ["qr_code"] });
    const barcodes = await detector.detect(video);
    return barcodes?.[0]?.rawValue?.trim() || null;
}

function decodeWithJsQr(video) {
    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) {
        return null;
    }
    const canvas = getDecodeCanvas();
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) {
        return null;
    }
    context.drawImage(video, 0, 0, width, height);
    const imageData = context.getImageData(0, 0, width, height);
    const result = jsQR(imageData.data, width, height, { inversionAttempts: "attemptBoth" });
    return result?.data?.trim() || null;
}

export async function decodeQrFromVideo(video) {
    if (!video || video.readyState < 2) {
        return null;
    }
    try {
        const nativeValue = await decodeWithBarcodeDetector(video);
        if (nativeValue) {
            return nativeValue;
        }
    } catch {
        // Fall back to canvas decoding below.
    }
    return decodeWithJsQr(video);
}

export async function startCameraStream() {
    const stream = await navigator.mediaDevices.getUserMedia(getScannerVideoConstraints());
    const track = stream.getVideoTracks()[0];
    if (track?.getCapabilities) {
        const capabilities = track.getCapabilities();
        if (capabilities.focusMode?.includes("continuous")) {
            try {
                await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] });
            } catch {
                // Optional; some WebViews reject advanced focus constraints.
            }
        }
    }
    return stream;
}

export async function attachStreamToVideo(stream, video) {
    if (!video) {
        return false;
    }
    video.srcObject = stream;
    await video.play();
    return true;
}
