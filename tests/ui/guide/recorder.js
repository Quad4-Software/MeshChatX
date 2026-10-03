/**
 * Animated capture for docs guides: records the live page via CDP
 * Page.startScreencast while actions run, then assembles frames into an
 * animated WebP (preferred) or GIF with ffmpeg.
 *
 *   const rec = await startGuideRecording(page);
 *   ...drive the UI...
 *   await rec.stop();                        // writes frames
 *   await rec.save("docs/en/assets/guides/send-message.webp");
 *
 * Frames capture actual paint output (no fixed fps), so wall-clock pacing of
 * actions is preserved loosely by frame timestamps.
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execFileSync } = require("child_process");

/**
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<{stop: () => Promise<void>, save: (outFile: string, opts?) => Promise<void>, frameCount: () => number}>}
 */
async function startGuideRecording(page) {
    const cdp = await page.context().newCDPSession(page);
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-guide-"));
    const stamps = [];
    let n = 0;

    const onFrame = (e) => {
        const file = path.join(dir, `f${String(++n).padStart(5, "0")}.jpg`);
        fs.writeFileSync(file, Buffer.from(e.data, "base64"));
        stamps.push(e.metadata && e.metadata.timestamp ? e.metadata.timestamp : null);
        cdp.send("Page.screencastFrameAck", { sessionId: e.sessionId }).catch(() => {});
    };
    cdp.on("Page.screencastFrame", onFrame);

    await cdp.send("Page.startScreencast", {
        format: "jpeg",
        quality: 82,
        everyNthFrame: 1,
    });

    return {
        frameCount: () => n,
        async stop() {
            await cdp.send("Page.stopScreencast").catch(() => {});
            cdp.off("Page.screencastFrame", onFrame);
        },
        /**
         * Assemble to animated .webp or .gif via ffmpeg.
         * @param {string} outFile .webp or .gif
         * @param {{fps?: number, loop?: number}} opts
         */
        async save(outFile, opts = {}) {
            const fps = opts.fps ?? 8;
            const loop = opts.loop ?? 0;
            if (n === 0) {
                throw new Error("no screencast frames captured");
            }
            fs.mkdirSync(path.dirname(outFile), { recursive: true });
            const isGif = outFile.endsWith(".gif");
            const args = [
                "-y",
                "-framerate", String(fps),
                "-i", path.join(dir, "f%05d.jpg"),
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                ...(isGif
                    ? ["-loop", String(loop)]
                    : ["-c:v", "libwebp", "-lossless", "0", "-q:v", "70", "-loop", String(loop), "-preset", "picture"]),
                outFile,
            ];
            try {
                execFileSync("ffmpeg", args, { stdio: "pipe" });
            } finally {
                fs.rmSync(dir, { recursive: true, force: true });
            }
        },
        async cleanup() {
            await this.stop();
            fs.rmSync(dir, { recursive: true, force: true });
        },
    };
}

module.exports = { startGuideRecording };
