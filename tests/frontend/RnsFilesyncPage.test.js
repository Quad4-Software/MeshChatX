// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RnsFilesyncPage from "@/features/filesync/RnsFilesyncPage.svelte";
import ToastUtils from "@/js/ToastUtils";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    formatAclRows,
    formatFileSize,
    formatProgressLabel,
    joinPath,
    peerStatusLabel,
} from "@/features/filesync/lib/filesyncFormat.ts";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/registries/wsEventRegistry.js", () => ({
    onWsEvent: vi.fn(),
    offWsEvent: vi.fn(),
}));

vi.mock("@/js/ElectronUtils", () => ({
    default: {
        openDirectoryOrCopy: vi.fn().mockResolvedValue(true),
        isElectron: vi.fn().mockReturnValue(false),
        pickDirectory: vi.fn().mockResolvedValue(null),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

vi.mock("@/js/DownloadUtils", () => ({
    default: {
        downloadFromApiResponse: vi.fn().mockResolvedValue(undefined),
    },
}));

describe("filesyncFormat", () => {
    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages({
            rns_filesync: {
                peer_connected: "Connected",
                peer_disconnected: "Disconnected",
                perm_read: "Read",
                perm_write: "Write",
                perm_delete: "Delete",
            },
        });
    });

    it("formats file size accurately", () => {
        expect(formatFileSize(0)).toBe("0 Bytes");
        expect(formatFileSize(1024)).toBe("1 KB");
        expect(formatFileSize(1048576)).toBe("1 MB");
    });

    it("joins paths safely without leading/trailing slashes", () => {
        expect(joinPath("", "subfolder")).toBe("subfolder");
        expect(joinPath("root", "child")).toBe("root/child");
        expect(joinPath("/root/", "child")).toBe("/root/child");
    });

    it("formats ACL rows from rules map", () => {
        const rows = formatAclRows({
            read: ["abc"],
            write: ["abc"],
            delete: [],
        });
        expect(rows.length).toBe(1);
        expect(rows[0].hash).toBe("abc");
        expect(rows[0].permsLabel).toBe("Read, Write");
    });

    it("formats peer status label", () => {
        expect(peerStatusLabel({ peer_id: "p1", status: "connected" })).toBe("Connected");
        expect(peerStatusLabel({ peer_id: "p1", status: "disconnected" })).toBe("Disconnected");
    });

    it("formats progress label", () => {
        expect(formatProgressLabel(null)).toBe("");
        expect(formatProgressLabel({ status: "idle" })).toBe("idle");
        expect(
            formatProgressLabel({
                file: "test.dat",
                status: "syncing",
                bytes: 1024,
                total: 2048,
            })
        ).toBe("test.dat · syncing · 1 KB / 2 KB");
    });
});

describe("RnsFilesyncPage.svelte", () => {
    let apiMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages({
            app: {
                tools: "Tools",
            },
            tools: {
                back_to_tools: "Back to Tools",
            },
            rns_filesync: {
                title: "FileSync",
                description: "Folder synchronization over Reticulum",
                eyebrow: "Tool",
                usage_steps: "Usage Steps",
                step_1: "Step 1",
                step_2: "Step 2",
                step_3: "Step 3",
                tab_folder: "Folder",
                tab_devices: "Devices",
                tab_files: "Files",
                tab_remote: "Remote Files",
                tab_sharing: "Sharing",
                status_syncing: "Syncing",
                status_stopped: "Stopped",
                peers_count: "Peers",
                files_count: "Files",
                sync_directory: "Directory",
                start: "Start",
                stop: "Stop",
                announce: "Announce",
                refresh: "Refresh",
            },
        });

        apiMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
            delete: vi.fn(),
        };
        window.api = apiMock;

        apiMock.get.mockImplementation((url) => {
            if (url === "/api/v1/filesync/status") {
                return Promise.resolve({
                    data: {
                        running: false,
                        sync_directory: "/tmp/sync",
                        storage_directory: "/tmp",
                        peers: 0,
                        files: 0,
                        monitor: true,
                        announce_interval: 300,
                    },
                });
            }
            if (url === "/api/v1/filesync/peers") {
                return Promise.resolve({ data: { peers: [] } });
            }
            if (url === "/api/v1/filesync/acl") {
                return Promise.resolve({ data: { enforce: false, rules: {} } });
            }
            return Promise.resolve({ data: {} });
        });
        apiMock.post.mockResolvedValue({ data: { ok: true } });
        apiMock.patch.mockResolvedValue({ data: { ok: true } });
        apiMock.delete.mockResolvedValue({ data: { ok: true } });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("renders and loads status and default tab", async () => {
        render(RnsFilesyncPage);
        await waitFor(() => {
            expect(screen.getByText("FileSync")).toBeTruthy();
            expect(screen.getByText("Stopped")).toBeTruthy();
        });
    });
});
