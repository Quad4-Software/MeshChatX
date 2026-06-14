import { describe, expect, it } from "vitest";
import {
    clearCrashReport,
    diagnoseBackendCrash,
    getCrashReportPath,
    loadCrashReport,
    persistCrashReport,
} from "../../electron/backendCrashReport.js";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

describe("electron/backendCrashReport", () => {
    it("persists and reloads crash reports under storage logs", () => {
        const storageDir = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-crash-"));
        try {
            const saved = persistCrashReport(storageDir, {
                code: 17,
                stdout: "ok",
                stderr: "MemoryError: out of memory",
                at: Date.now(),
            });
            expect(saved).toBeTruthy();
            expect(fs.existsSync(getCrashReportPath(storageDir))).toBe(true);
            const loaded = loadCrashReport(storageDir);
            expect(loaded.code).toBe(17);
            expect(loaded.stderr).toContain("MemoryError");
            clearCrashReport(storageDir);
            expect(loadCrashReport(storageDir)).toBeNull();
        } finally {
            fs.rmSync(storageDir, { recursive: true, force: true });
        }
    });

    it("diagnoseBackendCrash detects memory failures", () => {
        const diagnosis = diagnoseBackendCrash("MemoryError: allocation failed", "", 1);
        expect(diagnosis.category).toBe("memory");
        expect(diagnosis.summary).toContain("memory");
    });

    it("diagnoseBackendCrash parses MESHCHAT_MEMORY startup lines", () => {
        const stdout =
            "MESHCHAT_MEMORY: total_mb=4096.0 available_mb=120.0 percent_used=97.0 action=abort emergency=false";
        const diagnosis = diagnoseBackendCrash("", stdout, 1);
        expect(diagnosis.category).toBe("memory");
        expect(diagnosis.summary).toContain("120");
    });

    it("diagnoseBackendCrash detects port conflicts", () => {
        const diagnosis = diagnoseBackendCrash("", "OSError: [Errno 98] Address already in use", 1);
        expect(diagnosis.category).toBe("port-conflict");
    });
});
