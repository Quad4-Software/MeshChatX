// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, waitFor } from "@testing-library/svelte";
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
        registerTranslator(null);
        registerFallbackMessages({
            rncp: {
                title: "RNCP File Transfer",
                description: "Reticulum Network Copy Protocol",
                eyebrow: "Tool",
                usage_steps: "Usage Steps",
                step_1: "Step 1",
                step_2: "Step 2",
                step_3: "Step 3",
                tab_send: "Send",
                tab_fetch: "Fetch",
                tab_listen: "Listen",
            },
        });

        apiMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/rn_tools/rncp/status") {
                    return Promise.resolve({
                        data: {
                            is_listening: false,
                            listener_destination_hash: null,
                            received_files: [],
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
        vi.clearAllMocks();
    });

    it("renders RNCP page and header", async () => {
        render(RNCPPage);
        await waitFor(() => {
            expect(screen.getByText("RNCP File Transfer")).toBeTruthy();
            expect(screen.getByText("Usage Steps")).toBeTruthy();
        });
    });
});
