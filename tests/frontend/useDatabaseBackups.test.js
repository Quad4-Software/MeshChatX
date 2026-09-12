// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { useDatabaseBackups } from "../../meshchatx/src/frontend/js/about/useDatabaseBackups.js";

vi.mock("../../meshchatx/src/frontend/js/api/database.js", () => ({
    listSnapshots: vi.fn(async () => ({ data: { snapshots: ["s1"], total: 5 } })),
    listBackups: vi.fn(async () => ({ data: { backups: ["b1"], total: 8 } })),
    downloadSnapshots: vi.fn(async () => ({ data: new ArrayBuffer(4) })),
    downloadBackups: vi.fn(async () => ({ data: new ArrayBuffer(4) })),
}));

vi.mock("../../meshchatx/src/frontend/js/DialogUtils.js", () => ({
    default: { confirm: vi.fn(async () => true) },
}));

import * as databaseApi from "../../meshchatx/src/frontend/js/api/database.js";
import DialogUtils from "../../meshchatx/src/frontend/js/DialogUtils.js";

describe("useDatabaseBackups", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.api = {
            delete: vi.fn(async () => ({})),
            post: vi.fn(async () => ({})),
        };
    });

    it("lists snapshots with pagination params", async () => {
        const b = useDatabaseBackups();
        await b.listSnapshots();
        expect(databaseApi.listSnapshots).toHaveBeenCalledWith({ params: { limit: 3, offset: 0 } });
        expect(b.snapshots.value).toEqual(["s1"]);
        expect(b.snapshotsTotal.value).toBe(5);
    });

    it("paginates snapshots forward and back", async () => {
        const b = useDatabaseBackups();
        await b.listSnapshots();
        await b.nextSnapshots();
        expect(b.snapshotsOffset.value).toBe(3);
        await b.prevSnapshots();
        expect(b.snapshotsOffset.value).toBe(0);
    });

    it("paginates backups within total", async () => {
        const b = useDatabaseBackups();
        await b.listAutoBackups();
        await b.nextBackups();
        expect(b.autoBackupsOffset.value).toBe(4);
        await b.nextBackups(); // 4 + 4 !< total 8 -> stays
        expect(b.autoBackupsOffset.value).toBe(4);
    });

    it("delete asks for confirmation then reloads", async () => {
        const b = useDatabaseBackups();
        await b.deleteSnapshot("s1.zip");
        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(window.api.delete).toHaveBeenCalledWith("/api/v1/database/snapshots/s1.zip");
        expect(databaseApi.listSnapshots).toHaveBeenCalled();
    });

    it("delete without confirmation does nothing", async () => {
        DialogUtils.confirm.mockResolvedValueOnce(false);
        const b = useDatabaseBackups();
        await b.deleteBackup("b1.zip");
        expect(window.api.delete).not.toHaveBeenCalled();
    });

    it("createSnapshot names the snapshot and resets the field", async () => {
        const b = useDatabaseBackups();
        b.snapshotName.value = "mine";
        await b.createSnapshot();
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/database/snapshot", { name: "mine" });
        expect(b.snapshotName.value).toBe("");
        expect(b.snapshotMessage.value).toBe("Snapshot created successfully");
    });
});
