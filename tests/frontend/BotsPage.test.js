// SPDX-License-Identifier: 0BSD

import { render, cleanup, screen, waitFor, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import BotsPage from "@/features/bots/BotsPage.svelte";
import DownloadUtils from "@/js/DownloadUtils";
import ToastUtils from "@/js/ToastUtils";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import {
    buildLxmfConfigPatch,
    draftFromBotLxmfConfig,
    defaultLxmfConfigDraft,
} from "@/features/bots/lib/botLxmfConfigForm.ts";
import { lxmfAddressFor, formatRelativeSince } from "@/features/bots/lib/botUtils.ts";

vi.mock("@/js/DownloadUtils", () => ({
    default: {
        downloadFromApiResponse: vi.fn(() => Promise.resolve()),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
    },
}));

describe("botLxmfConfigForm", () => {
    it("creates default draft with expected fallbacks", () => {
        const draft = defaultLxmfConfigDraft();
        expect(draft.propagation_mode).toBe("inherit");
        expect(draft.propagation_node).toBe("");
        expect(draft.propagation_fallback_enabled).toBe("inherit");
    });

    it("converts bot config to draft accurately", () => {
        const draft = draftFromBotLxmfConfig({
            propagation_mode: "autopeer",
            propagation_fallback_enabled: true,
            opportunistic_sending: false,
            direct_delivery_retries: 3,
            stamp_cost: 10,
        });
        expect(draft.propagation_mode).toBe("autopeer");
        expect(draft.propagation_fallback_enabled).toBe("true");
        expect(draft.opportunistic_sending).toBe("false");
        expect(draft.direct_delivery_retries).toBe("3");
        expect(draft.stamp_cost).toBe("10");
    });

    it("builds clean patch object from draft", () => {
        const patch = buildLxmfConfigPatch(
            {
                propagation_mode: "manual",
                propagation_node: "1234567890abcdef1234567890abcdef",
                propagation_fallback_enabled: "inherit",
                direct_delivery_retries: "",
                opportunistic_sending: "inherit",
                announce_interval_seconds: "120",
                stamp_cost: "",
            },
            { clearEmpty: true }
        );
        expect(patch.propagation_mode).toBe("manual");
        expect(patch.propagation_node).toBe("1234567890abcdef1234567890abcdef");
        expect(patch.propagation_fallback_enabled).toBeNull();
        expect(patch.direct_delivery_retries).toBeNull();
        expect(patch.announce_interval_seconds).toBe(120);
    });
});

describe("botUtils", () => {
    it("formats LXMF address properly", () => {
        expect(lxmfAddressFor({ lxmf_address: "1234567890abcdef1234567890abcdef" })).toBe(
            "1234567890abcdef1234567890abcdef"
        );
        expect(lxmfAddressFor(null)).toBe("");
    });

    it("formats relative time", () => {
        expect(formatRelativeSince(null)).toBe("");
        const now = new Date(Date.now() - 5000).toISOString();
        expect(formatRelativeSince(now)).toBe("5s");
    });
});

describe("BotsPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        registerTranslator(null);
        registerFallbackMessages({
            app: {
                tools: "Tools",
            },
            tools: {
                back_to_tools: "Back to Tools",
                bots: {
                    title: "Bots Manager",
                    description: "Manage automated bots",
                },
            },
            bots: {
                create_new_bot: "Available Templates",
                saved_bots: "Active Bots",
                start_bot: "Start Bot",
                stop_bot: "Stop Bot",
                chat_with_bot: "Chat",
                lxmf_config_saved: "LXMF config updated",
            },
            common: {
                start: "Start",
                stop: "Stop",
                save: "Save",
                cancel: "Cancel",
            },
        });

        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            patch: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/bots/status") {
                return Promise.resolve({
                    data: {
                        status: {
                            bots: [
                                {
                                    id: "bot1",
                                    name: "Test Bot",
                                    address: "<addr1>",
                                    lxmf_address: "a".repeat(32),
                                    running: true,
                                    template_id: "echo",
                                },
                            ],
                        },
                        templates: [{ id: "echo", name: "Echo Bot", description: "Echos messages" }],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
        vi.clearAllMocks();
    });

    it("renders and loads bots and templates", async () => {
        render(BotsPage);
        await waitFor(() => {
            expect(screen.getByText("Bots Manager")).toBeTruthy();
            expect(screen.getByText("Echo Bot")).toBeTruthy();
            expect(screen.getByText("Test Bot")).toBeTruthy();
        });
    });

    it("calls stop bot API when stop button is clicked", async () => {
        render(BotsPage);
        await waitFor(() => {
            expect(screen.getByText("Test Bot")).toBeTruthy();
        });

        const stopButton = screen.getByTitle("Stop Bot");
        await fireEvent.click(stopButton);

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/bots/stop", {
            bot_id: "bot1",
        });
    });

    it("navigates to messages when chat is clicked", async () => {
        render(BotsPage);
        await waitFor(() => expect(screen.getByText("Test Bot")).toBeTruthy());

        const chatButton = screen.getByTitle("Chat");
        await fireEvent.click(chatButton);

        expect(window.location.hash).toBe(`#/messages/${"a".repeat(32)}`);
    });

    it("exports bot identity through window.api and DownloadUtils", async () => {
        axiosMock.post.mockResolvedValue({
            data: new ArrayBuffer(4),
            headers: { "content-disposition": 'attachment; filename="bot_bot1_identity"' },
        });
        render(BotsPage);
        await waitFor(() => expect(screen.getByText("Test Bot")).toBeTruthy());

        const exportButton = screen.getByTitle("bots.export_identity");
        await fireEvent.click(exportButton);

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith(
                "/api/v1/bots/export",
                { bot_id: "bot1" },
                { responseType: "arraybuffer" }
            );
            expect(DownloadUtils.downloadFromApiResponse).toHaveBeenCalled();
        });
    });

    it("toasts when bot identity export fails", async () => {
        axiosMock.post.mockRejectedValue({ response: { data: { message: "nope" } } });
        render(BotsPage);
        await waitFor(() => expect(screen.getByText("Test Bot")).toBeTruthy());

        const exportButton = screen.getByTitle("bots.export_identity");
        await fireEvent.click(exportButton);

        await waitFor(() => {
            expect(ToastUtils.error).toHaveBeenCalledWith("nope");
        });
    });

    it("opens lxmf config modal and saves patch", async () => {
        axiosMock.patch.mockResolvedValue({ data: { success: true, lxmf_config: {} } });
        render(BotsPage);
        await waitFor(() => expect(screen.getByText("Test Bot")).toBeTruthy());

        const configButton = screen.getByTitle("bots.edit_lxmf_config");
        await fireEvent.click(configButton);

        const modal = screen.getByText("bots.lxmf_config_title").closest(".fixed");
        const saveButton = Array.from(modal.querySelectorAll("button")).find((b) =>
            b.className.includes("hover:text-emerald-600")
        );
        await fireEvent.click(saveButton);

        await waitFor(() => {
            expect(axiosMock.patch).toHaveBeenCalledWith(
                "/api/v1/bots/lxmf-config",
                expect.objectContaining({
                    bot_id: "bot1",
                    lxmf_config: expect.any(Object),
                })
            );
            expect(ToastUtils.success).toHaveBeenCalledWith("LXMF config updated");
        });
    });
});
