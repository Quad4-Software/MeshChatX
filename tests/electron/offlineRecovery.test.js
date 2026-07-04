import { describe, expect, it } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {
    buildDataCleanupGuide,
    getCrashRecoveryInfo,
    listRecoveryBackups,
    pickPreferredRestoreBackup,
} from "../../electron/offlineRecovery.js";

describe("electron/offlineRecovery", () => {
    it("lists automatic and snapshot backups newest first", () => {
        const storageDir = fs.mkdtempSync(path.join(os.tmpdir(), "meshchatx-recovery-"));
        try {
            const autoDir = path.join(storageDir, "database-backups");
            const snapshotDir = path.join(storageDir, "snapshots");
            fs.mkdirSync(autoDir, { recursive: true });
            fs.mkdirSync(snapshotDir, { recursive: true });
            fs.writeFileSync(path.join(autoDir, "backup-old.zip"), "a");
            fs.writeFileSync(path.join(autoDir, "backup-new.zip"), "ab");
            fs.writeFileSync(path.join(snapshotDir, "manual.zip"), "abc");

            const now = Date.now();
            fs.utimesSync(path.join(autoDir, "backup-old.zip"), now / 1000 - 120, now / 1000 - 120);
            fs.utimesSync(path.join(autoDir, "backup-new.zip"), now / 1000, now / 1000);
            fs.utimesSync(path.join(snapshotDir, "manual.zip"), now / 1000 - 30, now / 1000 - 30);

            const backups = listRecoveryBackups(storageDir);
            expect(backups.map((entry) => entry.name)).toEqual(["backup-new.zip", "manual.zip", "backup-old.zip"]);
        } finally {
            fs.rmSync(storageDir, { recursive: true, force: true });
        }
    });

    it("prefers non-suspicious backups for restore", () => {
        const backups = [
            { name: "backup-SUSPICIOUS-1.zip", suspicious: true, createdAt: "2026-01-02T00:00:00.000Z" },
            { name: "backup-2.zip", suspicious: false, createdAt: "2026-01-01T00:00:00.000Z" },
        ];
        expect(pickPreferredRestoreBackup(backups)?.name).toBe("backup-2.zip");
    });

    it("builds cleanup guide with storage and reticulum paths", () => {
        const guide = buildDataCleanupGuide({
            storageDir: "/home/user/.reticulum-meshchatx",
            reticulumConfigDir: "/home/user/.reticulum",
            platform: "linux",
            portableExecutableDir: null,
        });
        expect(guide).toContain("/home/user/.reticulum-meshchatx");
        expect(guide).toContain("/home/user/.reticulum");
        expect(guide).toContain("Quit MeshChatX");
    });

    it("detects database corruption in crash recovery info", () => {
        const info = getCrashRecoveryInfo({
            storageDir: "/tmp/meshchatx",
            reticulumConfigDir: "/tmp/reticulum",
            platform: "linux",
            portableExecutableDir: null,
            stderr: "sqlite3.DatabaseError: database disk image is malformed",
            stdout: "",
            exitCode: 1,
        });
        expect(info.diagnosis.category).toBe("database");
        expect(info.cleanupGuide).toContain("Complete MeshChatX / Reticulum data reset");
    });
});
