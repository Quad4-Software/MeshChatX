// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, waitFor, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import RNCPPage from "@/features/rncp/RNCPPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import { loadRncpListenPrefs, saveRncpListenPrefs } from "@/features/rncp/lib/rncpPrefs.ts";
import { DEFAULT_RNCP_LISTEN_PREFS, RNCP_LISTEN_PREFS_KEY } from "@/features/rncp/lib/constants.ts";

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
        isElectron: () => false,
        showNotification: vi.fn(),
        revealPathInFolderOrCopy: vi.fn(),
        openDirectoryOrCopy: vi.fn(),
        pickFile: vi.fn(),
        pickDirectory: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        alert: vi.fn(),
        confirm: vi.fn(),
        prompt: vi.fn(),
    },
}));

const RNCP_MESSAGES = {
    title: "RNCP File Transfer",
    description: "Reticulum Network Copy Protocol",
    file_transfer: "Tool",
    usage_steps: "Usage Steps",
    step_1: "Step 1",
    step_2: "Step 2",
    step_3: "Step 3",
    send_file: "Send",
    fetch_file: "Fetch",
    listen: "Listen",
    destination_hash: "Destination",
    file_path: "File path",
    browse_file: "Browse",
    timeout_seconds: "Timeout",
    disable_compression: "No compress",
};

describe("rncpPrefs", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    afterEach(() => {
        localStorage.clear();
    });

    it("returns default prefs when nothing is saved", () => {
        const prefs = loadRncpListenPrefs();
        expect(prefs).toEqual(DEFAULT_RNCP_LISTEN_PREFS);
    });

    it("saves and loads prefs accurately", () => {
        saveRncpListenPrefs({
            listenAllowedHashes: "1234567890abcdef1234567890abcdef",
            listenFetchAllowed: true,
            listenAllowOverwrite: true,
            listenFetchJail: "/tmp/jail",
        });
        const prefs = loadRncpListenPrefs();
        expect(prefs.listenAllowedHashes).toBe("1234567890abcdef1234567890abcdef");
        expect(prefs.listenFetchAllowed).toBe(true);
        expect(prefs.listenAllowOverwrite).toBe(true);
        expect(prefs.listenFetchJail).toBe("/tmp/jail");
    });
});

describe("RNCPPage.svelte", () => {
    let apiMock;

    beforeEach(() => {
        localStorage.clear();
        registerTranslator(null);
        registerFallbackMessages({
            rncp: RNCP_MESSAGES,
        });

        apiMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/rncp/status") {
                    return Promise.resolve({
                        data: {
                            listening: false,
                            destination_hash: null,
                            receive_directory: null,
                            allowed_hashes: [],
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = apiMock;
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        localStorage.clear();
        vi.clearAllMocks();
    });

    it("renders RNCP page and header", async () => {
        render(RNCPPage);
        await waitFor(() => {
            expect(screen.getByText("RNCP File Transfer")).toBeTruthy();
            expect(screen.getByText("Usage Steps")).toBeTruthy();
        });
        expect(apiMock.get).toHaveBeenCalledWith("/api/v1/rncp/status");
    });

    it("does not wipe saved listen prefs on first mount", async () => {
        saveRncpListenPrefs({
            listenAllowedHashes: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            listenFetchJail: "/tmp/jail",
            listenFetchAllowed: true,
            listenAllowOverwrite: true,
        });
        render(RNCPPage);
        await waitFor(() => {
            const after = loadRncpListenPrefs();
            expect(after.listenAllowedHashes).toBe("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
            expect(after.listenFetchJail).toBe("/tmp/jail");
            expect(after.listenFetchAllowed).toBe(true);
            expect(after.listenAllowOverwrite).toBe(true);
            expect(localStorage.getItem(RNCP_LISTEN_PREFS_KEY)).toContain("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
        });
    });

    it("switches to listen tab without clearing persisted hashes", async () => {
        saveRncpListenPrefs({
            listenAllowedHashes: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            listenFetchJail: null,
            listenFetchAllowed: false,
            listenAllowOverwrite: false,
        });
        render(RNCPPage);
        await waitFor(() => expect(screen.getByText("Listen")).toBeTruthy());
        await fireEvent.click(screen.getByText("Listen"));
        await waitFor(() => {
            const textarea = document.querySelector("#rncp-listen-hashes");
            expect(textarea).toBeTruthy();
            expect(textarea.value).toBe("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
        });
    });
});
