// SPDX-License-Identifier: 0BSD

export function frameBufferToCanvas(
    fb: Uint8Array | number[],
    w: number,
    h: number,
    bg: string,
    fg: string
): HTMLCanvasElement {
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    const ctx = c.getContext("2d");
    if (!ctx) return c;
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = fg;
    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const idx = Math.floor((y * w + x) / 8);
            const bit = (fb[idx] >> (7 - (x % 8))) & 1;
            if (bit) ctx.fillRect(x, y, 1, 1);
        }
    }
    return c;
}

export function displayBufferToPng(displayBuffer: Uint8Array | number[]): string {
    const displayArea = displayBuffer.slice(0, 512);
    const statArea = displayBuffer.slice(512, 1024);
    const displayCanvas = frameBufferToCanvas(displayArea, 64, 64, "#000000", "#FFFFFF");
    const statCanvas = frameBufferToCanvas(statArea, 64, 64, "#000000", "#FFFFFF");

    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 64;
    const ctx = canvas.getContext("2d");
    if (!ctx) return "";
    ctx.drawImage(displayCanvas, 0, 0);
    ctx.drawImage(statCanvas, 64, 0);

    const scaledCanvas = document.createElement("canvas");
    scaledCanvas.width = 512;
    scaledCanvas.height = 256;
    const sCtx = scaledCanvas.getContext("2d");
    if (!sCtx) return "";
    sCtx.imageSmoothingEnabled = false;
    sCtx.drawImage(canvas, 0, 0, 512, 256);

    return scaledCanvas.toDataURL("image/png");
}
