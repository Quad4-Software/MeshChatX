// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import PaperMessagePage from "@/features/paper-message/PaperMessagePage.svelte";
import WebSocketConnection from "@/js/WebSocketConnection.js";
import ToastUtils from "@/js/ToastUtils.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import { canGeneratePaperMessage, isValidLxmUri } from "@/features/paper-message/lib/paperQr.ts";
import { printPaperQr } from "@/features/paper-message/lib/paperPrint.ts";
import { sendPaperMessageApi } from "@/features/paper-message/lib/paperSend.ts";
import { registerPaperMessageFeature } from "@/features/paper-message/index.ts";
import { clearRoutes, listRoutes } from "@/js/registries/routeRegistry.js";
import { clearFeatureIds, listFeatureIds } from "@/js/registries/featureRegistry.js";
import { dispatchWsEvent } from "@/js/registries/wsEventRegistry.ts";

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        send: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("qrcode", () => ({
    default: {
        toCanvas: vi.fn().mockResolvedValue({}),
    },
}));

describe("paper-message lib helpers", () => {
    it("validates inputs for paper message generation", () => {
        expect(canGeneratePaperMessage("a".repeat(32), "Hello")).toBe(true);
        expect(canGeneratePaperMessage("a".repeat(32), "")).toBe(false);
        expect(canGeneratePaperMessage("short", "Hello")).toBe(false);
        expect(canGeneratePaperMessage("", "Hello")).toBe(false);
    });

    it("validates LXM URI schemes", () => {
        expect(isValidLxmUri("lxmf://abcdef123456")).toBe(true);
        expect(isValidLxmUri("http://example.com")).toBe(false);
        expect(isValidLxmUri("")).toBe(false);
    });

    it("printPaperQr returns false if canvas is missing", () => {
        expect(printPaperQr({ canvas: null, destinationHash: "abc" })).toBe(false);
    });

    it("sendPaperMessageApi posts payload and shows success toast", async () => {
        const postMock = vi.fn().mockResolvedValue({
            data: { lxmf_message: { destination_hash: "a".repeat(32) } },
        });
        window.api = { post: postMock };

        const res = await sendPaperMessageApi({
            destinationHash: "a".repeat(32),
            generatedUri: "lxmf://testuri",
        });

        expect(res.success).toBe(true);
        expect(postMock).toHaveBeenCalledWith(
            "/api/v1/lxmf-messages/send",
            expect.objectContaining({
                delivery_method: "opportunistic",
                lxmf_message: expect.objectContaining({
                    destination_hash: "a".repeat(32),
                }),
            })
        );
        delete window.api;
    });
});

describe("registerPaperMessageFeature", () => {
    beforeEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    afterEach(() => {
        clearRoutes();
        clearFeatureIds();
    });

    it("registers paper-message route correctly", () => {
        registerPaperMessageFeature();
        expect(listFeatureIds()).toContain("paper-message");
        const route = listRoutes().find((r) => r.name === "paper-message");
        expect(route).toBeTruthy();
        expect(route?.path).toBe("/tools/paper-message");
        expect(route?.mount).toBe("svelte");
    });
});

describe("PaperMessagePage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        registerTranslator(null);
        registerFallbackMessages({
            app: { tools: "Tools" },
            tools: {
                paper_message: {
                    title: "Paper Message",
                    description: "Offline paper QR messaging",
                },
            },
            messages: {
                compose: "Compose Message",
                destination_hash: "Destination Hash",
                destination_hash_placeholder: "Destination hash (32 hex)",
                title: "Title",
                title_placeholder: "Optional title",
                content: "Content",
                content_placeholder: "Message content",
                generate_paper_message: "Generate Paper Message",
                generating_paper_message: "Generating...",
                generated_qr_code: "Generated QR Code",
                scan_with_lxmf_app: "Scan with an LXMF app",
                print_qr_code: "Print QR Code",
                download_qr_code: "Download QR Code",
                copy_uri: "Copy URI",
                send_paper_message: "Send Paper Message",
                sending: "Sending...",
                ingest_paper_message: "Ingest Paper Message",
                ingest_instructions: "Paste or scan a Paper Message URI",
                paste_from_clipboard: "Paste",
                scan_with_camera: "Scan QR",
                ingest_uri_placeholder: "lxmf://...",
                read_lxm: "Read LXM",
                failed_read_clipboard: "Failed to read clipboard",
                uri_copied: "URI copied",
                failed_copy_uri: "Failed to copy URI",
                paper_message_sent: "Paper message sent",
                failed_send_paper: "Failed to send paper message",
            },
        });
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("renders the paper message page", () => {
        render(PaperMessagePage);
        expect(screen.getByText("Paper Message")).toBeTruthy();
        expect(screen.getByText("Compose Message")).toBeTruthy();
    });

    it("enables generate button only when inputs are valid", async () => {
        render(PaperMessagePage);

        const generateBtn = screen.getByText(/Generate Paper Message/);
        expect(generateBtn.closest("button")?.hasAttribute("disabled")).toBe(true);

        const hashInput = screen.getByPlaceholderText(/Destination hash/);
        const contentInput = screen.getByPlaceholderText(/Type your message/);

        await fireEvent.input(hashInput, { target: { value: "a".repeat(32) } });
        await fireEvent.input(contentInput, { target: { value: "Hello World" } });

        expect(generateBtn.closest("button")?.hasAttribute("disabled")).toBe(false);
    });

    it("sends websocket request to generate paper message", async () => {
        render(PaperMessagePage);

        const hashInput = screen.getByPlaceholderText(/Destination hash/);
        const titleInput = screen.getByPlaceholderText(/Message title/);
        const contentInput = screen.getByPlaceholderText(/Type your message/);

        await fireEvent.input(hashInput, { target: { value: "a".repeat(32) } });
        await fireEvent.input(titleInput, { target: { value: "Test Title" } });
        await fireEvent.input(contentInput, { target: { value: "Hello World" } });

        const generateBtn = screen.getByText(/Generate Paper Message/);
        await fireEvent.click(generateBtn);

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxm.generate_paper_uri",
                destination_hash: "a".repeat(32),
                content: "Hello World",
                title: "Test Title",
            })
        );
    });

    it("handles websocket result and shows QR code section", async () => {
        render(PaperMessagePage);

        await dispatchWsEvent("lxm.generate_paper_uri.result", {
            type: "lxm.generate_paper_uri.result",
            status: "success",
            uri: "lxmf://testuri",
        });

        await waitFor(() => {
            expect(screen.getByText("Generated QR Code")).toBeTruthy();
        });
    });

    it("calls ingest API when ingest button is clicked", async () => {
        render(PaperMessagePage);

        const ingestInput = screen.getByPlaceholderText(/lxmf:\/\//);
        await fireEvent.input(ingestInput, { target: { value: "lxmf://ingestme" } });

        const ingestBtn = screen.getByText("Read LXM");
        await fireEvent.click(ingestBtn);

        expect(WebSocketConnection.send).toHaveBeenCalledWith(
            JSON.stringify({
                type: "lxm.ingest_uri",
                uri: "lxmf://ingestme",
            })
        );
    });
});
