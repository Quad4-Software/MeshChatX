import crypto from "crypto";
import fs from "fs";
import os from "os";
import path from "path";
import { afterEach, describe, expect, it } from "vitest";

import { applyPendingUpdate, readPendingMarker } from "../../electron/updateApply.js";

let tmpDir = null;
let savedAppImage;

function makeTmp() {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-update-apply-"));
    fs.mkdirSync(path.join(tmpDir, "updates", "pending"), { recursive: true });
    return tmpDir;
}

function stage(dir, name, bytes, overrides = {}) {
    const p = path.join(dir, "updates", "pending", name);
    fs.writeFileSync(p, bytes);
    const marker = {
        file: name,
        sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
        size: bytes.length,
        kind: "appimage",
        platform: "linux",
        arch: "x86_64",
        version: "9.9.9",
        ...overrides,
    };
    fs.writeFileSync(path.join(dir, "updates", "pending.json"), JSON.stringify(marker));
    return { path: p, marker };
}

afterEach(() => {
    if (savedAppImage === undefined) {
        delete process.env.APPIMAGE;
    } else {
        process.env.APPIMAGE = savedAppImage;
    }
    if (tmpDir) {
        fs.rmSync(tmpDir, { recursive: true, force: true });
        tmpDir = null;
    }
});

describe("electron/updateApply", () => {
    it("rejects when no pending marker exists", () => {
        const dir = makeTmp();
        expect(applyPendingUpdate(dir).error).toBe("no_pending_update");
    });

    it("rejects malformed markers", () => {
        const dir = makeTmp();
        fs.writeFileSync(
            path.join(dir, "updates", "pending.json"),
            JSON.stringify({ file: "../escape", sha256: "x", kind: "appimage" }),
        );
        const res = applyPendingUpdate(dir);
        expect(res.applied).toBe(false);
        expect(res.error).toBe("bad_pending_marker");
    });

    it("rejects non-appimage kinds", () => {
        const dir = makeTmp();
        stage(dir, "pkg.deb", Buffer.from("data"), { kind: "deb" });
        const res = applyPendingUpdate(dir);
        expect(res.applied).toBe(false);
        expect(res.error).toBe("unsupported_kind");
    });

    it("rejects when not running from an AppImage", () => {
        const dir = makeTmp();
        stage(dir, "new.AppImage", Buffer.from("img"));
        savedAppImage = process.env.APPIMAGE;
        delete process.env.APPIMAGE;
        const res = applyPendingUpdate(dir);
        expect(res.applied).toBe(false);
        expect(res.error).toBe("not_appimage");
    });

    it("rejects a staged file whose hash does not match", () => {
        const dir = makeTmp();
        const s = stage(dir, "new.AppImage", Buffer.from("img"));
        const target = path.join(dir, "old.AppImage");
        fs.writeFileSync(target, "old");
        savedAppImage = process.env.APPIMAGE;
        process.env.APPIMAGE = target;
        fs.writeFileSync(s.path, "tampered-after-staging");
        const res = applyPendingUpdate(dir);
        expect(res.applied).toBe(false);
        expect(res.error).toBe("sha256_mismatch");
        expect(fs.readFileSync(target)).toEqual(Buffer.from("old"));
    });

    it("swaps a verified payload into place, backs up and clears marker", () => {
        const dir = makeTmp();
        const payload = Buffer.from("new-verified-image");
        const s = stage(dir, "new.AppImage", payload);
        const target = path.join(dir, "app.AppImage");
        fs.writeFileSync(target, "old-image");
        savedAppImage = process.env.APPIMAGE;
        process.env.APPIMAGE = target;

        const res = applyPendingUpdate(dir);
        expect(res.applied).toBe(true);
        expect(fs.readFileSync(target)).toEqual(payload);
        expect(fs.readFileSync(target + ".bak")).toEqual(Buffer.from("old-image"));
        expect(fs.existsSync(s.path)).toBe(false);
        expect(readPendingMarker(dir)).toBe(null);
        const mode = fs.statSync(target).mode & 0o777;
        expect(mode & 0o111).not.toBe(0);
    });

    it("ignores a marker path field pointing outside pending dir", () => {
        const dir = makeTmp();
        const payload = Buffer.from("img");
        const s = stage(dir, "new.AppImage", payload);
        // marker.file is basename-only; smuggle an absolute marker.path which
        // the apply logic must ignore entirely.
        fs.writeFileSync(
            path.join(dir, "updates", "pending.json"),
            JSON.stringify({
                ...s.marker,
                path: "/etc/passwd",
            }),
        );
        const target = path.join(dir, "app.AppImage");
        fs.writeFileSync(target, "old-image");
        savedAppImage = process.env.APPIMAGE;
        process.env.APPIMAGE = target;
        const res = applyPendingUpdate(dir);
        expect(res.applied).toBe(true); // staged basename payload applied
        expect(fs.readFileSync(target)).toEqual(payload);
    });
});
