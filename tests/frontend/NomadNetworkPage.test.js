// SPDX-License-Identifier: 0BSD
import { render, cleanup, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NomadNetworkPage from "@/features/nomadnetwork/components/NomadNetworkPage.svelte";
import WebSocketConnection from "@/js/WebSocketConnection";
import { dispatchWsEvent } from "@/js/registries/wsEventRegistry";
import { resetWsEventBridgeForTests } from "@/js/registries/wsEventBridge";

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
        resetWsEventBridgeForTests();
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
            expect(WebSocketConnection.send).toHaveBeenCalled();
            const raw = WebSocketConnection.send.mock.calls.find((call) => {
                const msg = call[0];
                return typeof msg === "string" && msg.includes("nomadnet.page.download");
            })?.[0];
            expect(raw).toBeTruthy();
            const payload = JSON.parse(raw);
            expect(payload).toEqual(
                expect.objectContaining({
                    type: "nomadnet.page.download",
                    nomadnet_page_download: expect.objectContaining({
                        destination_hash: TEST_DESTINATION_HASH,
                        page_path: "/page/index.mu",
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

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalled();
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 1,
            nomadnet_page_download: {
                status: "started",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
            },
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 1,
            nomadnet_page_download: {
                status: "success",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
                page_content: ">#!\n# Hello World",
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

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalled();
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 2,
            nomadnet_page_download: {
                status: "started",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
            },
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 2,
            nomadnet_page_download: {
                status: "failure",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
                failure_reason: "Failed to load page",
            },
        });

        await waitFor(() => {
            expect(getByRole("alert")).toBeTruthy();
        });
    });

    it("clears busy loading when cancel arrives for the owned download id", async () => {
        const { getByText } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalled();
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 9,
            nomadnet_page_download: {
                status: "started",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
            },
        });

        await dispatchWsEvent("nomadnet.download.cancelled", {
            type: "nomadnet.download.cancelled",
            download_id: 9,
        });

        await waitFor(() => {
            expect(getByText(/cancelled|stopped/i)).toBeTruthy();
        });
    });

    it("posts identify-on-connect and refreshes favourites", async () => {
        const onfavouriteschanged = vi.fn();
        const { getByTitle } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
            favourites: [{ destination_hash: TEST_DESTINATION_HASH, display_name: "Node", identify_on_connect: false }],
            onfavouriteschanged,
        });

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalled();
        });

        const identifyBtn = getByTitle(/Identify when connecting/i);
        await identifyBtn.click();

        await waitFor(() => {
            expect(axiosMock.post).toHaveBeenCalledWith(
                `/api/v1/favourites/${TEST_DESTINATION_HASH}/identify-on-connect`,
                expect.objectContaining({ enabled: true, aspect: "nomadnetwork.node" })
            );
            expect(onfavouriteschanged).toHaveBeenCalled();
        });
    });

    it("reassembles chunked page downloads into page content", async () => {
        const { container } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalled();
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 11,
            nomadnet_page_download: {
                status: "started",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
            },
        });

        const pageText = ">#!\n# Chunked Hello";
        const bytes = new TextEncoder().encode(pageText);
        const mid = Math.floor(bytes.length / 2);
        const toB64 = (slice) => {
            let binary = "";
            for (let i = 0; i < slice.length; i++) binary += String.fromCharCode(slice[i]);
            return btoa(binary);
        };

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 11,
            nomadnet_page_download: {
                status: "chunk",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
                offset: 0,
                total: bytes.length,
                chunk_index: 0,
                chunk_b64: toB64(bytes.slice(0, mid)),
            },
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 11,
            nomadnet_page_download: {
                status: "chunk",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
                offset: mid,
                total: bytes.length,
                chunk_index: 1,
                chunk_b64: toB64(bytes.slice(mid)),
            },
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 11,
            nomadnet_page_download: {
                status: "success",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
                chunked: true,
                total: bytes.length,
            },
        });

        await waitFor(() => {
            expect(container.querySelector("iframe")).toBeTruthy();
        });
    });

    it("serves a second load of the same path from in-tab cache without another WS send", async () => {
        const { getByTitle } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalled();
        });

        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 21,
            nomadnet_page_download: {
                status: "started",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
            },
        });
        await dispatchWsEvent("nomadnet.page.download", {
            type: "nomadnet.page.download",
            download_id: 21,
            nomadnet_page_download: {
                status: "success",
                destination_hash: TEST_DESTINATION_HASH,
                page_path: "/page/index.mu",
                page_content: ">#!\n# Cached",
            },
        });

        const sendCountAfterFirst = WebSocketConnection.send.mock.calls.filter((call) =>
            String(call[0] || "").includes("nomadnet.page.download")
        ).length;

        const homeBtn = getByTitle(/Home|home/i);
        await homeBtn.click();

        const sendCountAfterHome = WebSocketConnection.send.mock.calls.filter((call) =>
            String(call[0] || "").includes("nomadnet.page.download")
        ).length;
        expect(sendCountAfterHome).toBe(sendCountAfterFirst);
    });

    it("uses destination path finder HTTP helpers instead of path_probe WS", async () => {
        const ToastUtils = (await import("@/js/ToastUtils")).default;
        const { getByTitle, getByText } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalled();
        });

        await getByTitle("Path Finder").click();
        await getByText("Request path").click();

        await waitFor(() => {
            const usedPathProbe = WebSocketConnection.send.mock.calls.some((call) =>
                String(call[0] || "").includes("path_probe")
            );
            expect(usedPathProbe).toBe(false);
            expect(axiosMock.post).toHaveBeenCalledWith(`/api/v1/destination/${TEST_DESTINATION_HASH}/request-path`);
            expect(ToastUtils.success).toHaveBeenCalled();
        });
    });
});
