import fs from "fs";
import os from "os";
import path from "path";
import { describe, expect, it } from "vitest";
import { createRequire } from "module";
import crypto from "crypto";

const require = createRequire(import.meta.url);
const { verifyBackendIntegrity } = require("../../electron/backendIntegrity.js");

describe("electron/backendIntegrity", () => {
    it("returns ok when manifest is absent", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-int-"));
        try {
            const r = verifyBackendIntegrity(dir);
            expect(r.ok).toBe(true);
            expect(r.issues).toContain("Manifest missing");
        } finally {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    });

    it("detects missing file from manifest", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-int-"));
        try {
            const manifest = { files: { "missing.bin": "abc" } };
            fs.writeFileSync(path.join(dir, "backend-manifest.json"), JSON.stringify(manifest), "utf8");
            const r = verifyBackendIntegrity(dir);
            expect(r.ok).toBe(false);
            expect(r.issues.some((i) => i.includes("Missing:"))).toBe(true);
        } finally {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    });

    it("detects hash mismatch", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-int-"));
        try {
            const fileRel = "blob.bin";
            const full = path.join(dir, fileRel);
            fs.writeFileSync(full, "hello", "utf8");
            const wrongHash = "0".repeat(64);
            const manifest = { files: { [fileRel]: wrongHash } };
            fs.writeFileSync(path.join(dir, "backend-manifest.json"), JSON.stringify(manifest), "utf8");
            const r = verifyBackendIntegrity(dir);
            expect(r.ok).toBe(false);
            expect(r.issues.some((i) => i.includes("Modified:"))).toBe(true);
        } finally {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    });

    it("accepts matching manifest", () => {
        const dir = fs.mkdtempSync(path.join(os.tmpdir(), "mcx-int-"));
        try {
            const fileRel = "blob.bin";
            const full = path.join(dir, fileRel);
            const data = Buffer.from("integrity-test", "utf8");
            fs.writeFileSync(full, data);
            const hash = crypto.createHash("sha256").update(data).digest("hex");
            const manifest = {
                files: { [fileRel]: hash },
                _metadata: { date: "2020-01-01", time: "12:00:00" },
            };
            fs.writeFileSync(path.join(dir, "backend-manifest.json"), JSON.stringify(manifest), "utf8");
            const r = verifyBackendIntegrity(dir);
            expect(r.ok).toBe(true);
            expect(r.issues).toHaveLength(0);
        } finally {
            fs.rmSync(dir, { recursive: true, force: true });
        }
    });
});
