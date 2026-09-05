// SPDX-License-Identifier: 0BSD
import { render, cleanup, fireEvent, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NomadNetworkPage from "@/features/nomadnetwork/components/NomadNetworkPage.svelte";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalEmitter from "@/js/GlobalEmitter";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(async () => true),
        prompt: vi.fn(async () => null),
        alert: vi.fn(),
    },
}));

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(() => true),
        isOpen: vi.fn(() => true),
        on: vi.fn(),
        off: vi.fn(),
    },
}));

const TEST_DESTINATION_HASH = "aabbccddeeff00112233445566778899";

describe("NomadNetworkPage.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn((url) => {
                if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
                if (url.includes("/archives")) return Promise.resolve({ data: { archives: [] } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn(() => Promise.resolve({ data: {} })),
            delete: vi.fn(() => Promise.resolve({ data: {} })),
        };
        window.api = axiosMock;
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    it("sends page download request over WebSocket when destinationHash is provided", async () => {
        render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalledWith(
                expect.objectContaining({
                    type: "nomadnet.page.download",
                    nomadnet_page_download: expect.objectContaining({
                        destination_hash: TEST_DESTINATION_HASH,
                        path: "/page/index.mu",
                    }),
                })
            );
        });
    });

    it("shows loading indicator while page is loading", async () => {
        const { getByRole } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        expect(getByRole("status")).toBeTruthy();
    });

    it("displays page content when page download completes", async () => {
        const { container } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        const req = WebSocketConnection.send.mock.calls[0][0];
        const requestId = req.request_id;

        GlobalEmitter.emit("ws-message", {
            detail: {
                type: "nomadnet.page_download_completed",
                request_id: requestId,
                content: ">#!\n# Hello World",
            },
        });

        await waitFor(() => {
            expect(container.querySelector("iframe")).toBeTruthy();
        });
    });

    it("displays error message when page download fails", async () => {
        const { getByRole } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        const req = WebSocketConnection.send.mock.calls[0][0];
        const requestId = req.request_id;

        GlobalEmitter.emit("ws-message", {
            detail: {
                type: "nomadnet.page_download_failed",
                request_id: requestId,
                error: "Failed to load page",
            },
        });

        await waitFor(() => {
            expect(getByRole("alert")).toBeTruthy();
        });
    });
});
