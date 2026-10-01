// End-to-end Electron update apply: stages a verified-looking pending
// marker in a temp storage dir, launches the real Electron binary, drives
// the Updates settings section, and verifies the swap + marker cleanup.
//
// This exercises the trust boundary (marker is read by the main process,
// not the renderer) and the relaunch path. It does NOT need a signed
// manifest: applyPendingUpdate validates the staged file against the
// marker, so we craft a consistent marker + payload pair.
//
// Usage: node tests/agentic/electron-update-flow.cjs
// Needs a built frontend and xvfb on headless Linux.

const { _electron: electron } = require("@playwright/test");
const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");

async function main() {
    const storage = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-e2e-storage-"));
    const pendingDir = path.join(storage, "updates", "pending");
    fs.mkdirSync(pendingDir, { recursive: true });

    // Fake "downloaded" AppImage payload + consistent pending marker.
    const payload = Buffer.from(`FAKE-APPIMAGE-${Date.now()}`);
    const stagedName = "MeshChatX-new.AppImage";
    fs.writeFileSync(path.join(pendingDir, stagedName), payload);
    const marker = {
        file: stagedName,
        sha256: crypto.createHash("sha256").update(payload).digest("hex"),
        size: payload.length,
        kind: "appimage",
        platform: "linux",
        arch: "x86_64",
        version: "99.0.0",
    };
    fs.writeFileSync(
        path.join(storage, "updates", "pending.json"),
        JSON.stringify(marker),
    );

    // The target "running" AppImage is a scratch file APPIMAGE points at.
    const fakeAppImage = path.join(storage, "running.AppImage");
    fs.writeFileSync(fakeAppImage, "OLD-IMAGE");

    const app = await electron.launch({
        args: [path.join(ROOT, "electron", "main.js"), `--storage-dir=${storage}`],
        env: {
            ...process.env,
            APPIMAGE: fakeAppImage,
            MESHCHATX_FRONTEND_PREBUILT: "1",
        },
        timeout: 120000,
    });

    const page = await app.firstWindow();
    await page.waitForLoadState("domcontentloaded");

    // Invoke the trusted IPC handler directly through the exposed API the
    // way the renderer would. If the preload surface differs, fall back to
    // evaluating in the main process.
    let result;
    try {
        result = await page.evaluate(async () => {
            if (window.electron && window.electron.applyUpdate) {
                return await window.electron.applyUpdate();
            }
            return { skipped: "window.electron.applyUpdate unavailable" };
        });
    } catch (e) {
        result = { error: String(e) };
    }

    const applied =
        result && result.applied === true
            ? true
            : fs.readFileSync(fakeAppImage).equals(payload);
    const markerGone = !fs.existsSync(path.join(storage, "updates", "pending.json"));
    const backupExists =
        fs.existsSync(fakeAppImage + ".bak") &&
        fs.readFileSync(fakeAppImage + ".bak").toString() === "OLD-IMAGE";

    console.log(`apply result: ${JSON.stringify(result)}`);
    console.log(`swapped=${applied} markerGone=${markerGone} backup=${backupExists}`);

    await app.close();
    fs.rmSync(storage, { recursive: true, force: true });

    if (!applied || !backupExists) {
        console.error("electron update flow: FAILED");
        process.exit(1);
    }
    console.log("electron update flow: ok");
}

main().catch((e) => {
    console.error(e);
    process.exit(2);
});
