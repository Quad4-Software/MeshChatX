// SPDX-License-Identifier: 0BSD
import { render, cleanup, waitFor, fireEvent } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import NomadNetworkPage from "@/features/nomadnetwork/components/NomadNetworkPage.svelte";
import NomadPageRendererHost from "@/features/nomadnetwork/components/NomadPageRendererHost.svelte";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalEmitter from "@/js/GlobalEmitter";
import { dispatchWsEvent } from "@/js/registries/wsEventRegistry";
import { resetWsEventBridgeForTests } from "@/js/registries/wsEventBridge";
import GlobalState from "@/js/GlobalState";
import { NOMAD_CRASH_TAB_CHANNEL } from "@/js/nomadCrashTabShell.js";
import {
    resolveNomadImageDestination,
    resolveNomadImagePolicy,
    getNomadImageDataUrl,
    setNomadImageCacheEntry,
} from "@/features/nomadnetwork/lib/nomadPageImages.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        dismiss: vi.fn(),
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
        const { baseElement } = render(NomadNetworkPage, {
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
            expect(baseElement.querySelector("iframe")).toBeTruthy();
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

    it("browse tab keeps the tab and list when closing a node", async () => {
        const onclose = vi.fn();
        let view;
        // The browser shell applies the navigate back onto the tab props.
        const onnavigate = vi.fn((dHash, pPath) => {
            void view.rerender({
                destinationHash: dHash || "",
                pagePath: pPath || "/page/index.mu",
                onnavigate,
                onclose,
            });
        });
        view = render(NomadNetworkPage, {
            destinationHash: "",
            pagePath: "",
            onnavigate,
            onclose,
        });

        // A sidebar node click re-points this tab at a node.
        await view.rerender({
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
            onnavigate,
            onclose,
        });

        const closeBtn = await waitFor(() => view.getByTitle("Cancel"));
        await closeBtn.click();

        expect(onclose).not.toHaveBeenCalled();
        expect(onnavigate).toHaveBeenCalledWith("", "/page/index.mu", false);
        await waitFor(() => {
            expect(view.queryByTitle("Cancel")).toBeNull();
        });
    });

    it("tab opened on a node closes the whole tab", async () => {
        const onnavigate = vi.fn();
        const onclose = vi.fn();
        const { getByTitle } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
            onnavigate,
            onclose,
        });

        const closeBtn = await waitFor(() => getByTitle("Cancel"));
        await closeBtn.click();

        expect(onclose).toHaveBeenCalled();
        expect(onnavigate).not.toHaveBeenCalled();
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
        const { baseElement } = render(NomadNetworkPage, {
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
            expect(baseElement.querySelector("iframe")).toBeTruthy();
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

    it("hides the path finder menu below xl so the URL bar keeps width", async () => {
        const { getByTitle } = render(NomadNetworkPage, {
            destinationHash: TEST_DESTINATION_HASH,
            pagePath: "/page/index.mu",
        });

        await waitFor(() => {
            expect(WebSocketConnection.send).toHaveBeenCalled();
        });

        const pfButton = getByTitle("Path Finder");
        let el = pfButton;
        while (el && !(el.classList.contains("hidden") && /xl:(block|inline-block|inline-flex)/.test(el.className))) {
            el = el.parentElement;
        }
        expect(el, "path finder dropdown must stay hidden below xl").toBeTruthy();
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

    describe("image support", () => {
        const IMG_HASH = "a".repeat(32);
        const OTHER_HASH = "b".repeat(32);

        afterEach(() => {
            delete GlobalState.config.nomad_image_loading_policy;
        });

        function dispatchFrameMessage(source, data) {
            const event = new MessageEvent("message", { data });
            Object.defineProperty(event, "source", { value: source, configurable: true });
            Object.defineProperty(event, "origin", { value: "null", configurable: true });
            window.dispatchEvent(event);
        }

        function fileDownloadSends() {
            return WebSocketConnection.send.mock.calls
                .map((call) => String(call[0] || ""))
                .filter((raw) => raw.includes('"nomadnet.file.download"'))
                .map((raw) => JSON.parse(raw));
        }

        async function renderLoadedPage(props = {}) {
            const view = render(NomadNetworkPage, {
                destinationHash: IMG_HASH,
                pagePath: "/page/index.mu",
                ...props,
            });
            await waitFor(() => {
                expect(WebSocketConnection.send).toHaveBeenCalled();
            });
            await dispatchWsEvent("nomadnet.page.download", {
                type: "nomadnet.page.download",
                download_id: 31,
                nomadnet_page_download: {
                    status: "started",
                    destination_hash: IMG_HASH,
                    page_path: "/page/index.mu",
                },
            });
            await dispatchWsEvent("nomadnet.page.download", {
                type: "nomadnet.page.download",
                download_id: 31,
                nomadnet_page_download: {
                    status: "success",
                    destination_hash: IMG_HASH,
                    page_path: "/page/index.mu",
                    page_content: ">#!\n# Hi",
                },
            });
            let frame = null;
            await waitFor(() => {
                frame = document.body.querySelector("iframe");
                expect(frame).toBeTruthy();
            });
            const fakeWindow = { postMessage: vi.fn() };
            Object.defineProperty(frame, "contentWindow", {
                configurable: true,
                get: () => fakeWindow,
            });
            return { ...view, frame, fakeWindow };
        }

        function pushImages(fakeWindow, images) {
            dispatchFrameMessage(fakeWindow, {
                channel: NOMAD_CRASH_TAB_CHANNEL,
                type: "render-done",
                partials: [],
                images,
            });
        }

        it("resolves a relative image URL to the selected node", () => {
            const resolved = resolveNomadImageDestination(":/file/img.webp", IMG_HASH);
            expect(resolved.destinationHash).toBe(IMG_HASH);
            expect(resolved.filePath).toBe("/file/img.webp");
        });

        it("resolves an absolute image URL with destination hash", () => {
            const resolved = resolveNomadImageDestination(`${OTHER_HASH}:/file/img.webp`, IMG_HASH);
            expect(resolved.destinationHash).toBe(OTHER_HASH);
            expect(resolved.filePath).toBe("/file/img.webp");
        });

        it("resolves /media image URLs with any supported extension", () => {
            for (const ext of ["webp", "png", "jpg", "jpeg", "bmp", "gif", "tiff"]) {
                const resolved = resolveNomadImageDestination(`${IMG_HASH}:/media/img.${ext}`, "");
                expect(resolved.destinationHash).toBe(IMG_HASH);
                expect(resolved.filePath).toBe(`/media/img.${ext}`);
            }
        });

        it("rejects non-webp, non-image, and traversal image URLs", () => {
            expect(resolveNomadImageDestination(":/file/img.png", IMG_HASH).destinationHash).toBe("");
            expect(resolveNomadImageDestination(":/page/index.mu", IMG_HASH).destinationHash).toBe("");
            expect(resolveNomadImageDestination(":/file/../etc/shadow.webp", IMG_HASH).destinationHash).toBe("");
            expect(resolveNomadImageDestination(":/file/img.webp?x=1", IMG_HASH).destinationHash).toBe(IMG_HASH);
        });

        it("maps unknown policy values to manual", () => {
            expect(resolveNomadImagePolicy(undefined, "bogus")).toBe("manual");
            expect(resolveNomadImagePolicy(undefined, undefined)).toBe("manual");
            expect(resolveNomadImagePolicy("always", "bogus")).toBe("always");
        });

        it("uses per-node image policy override when present", () => {
            expect(resolveNomadImagePolicy("always", "manual")).toBe("always");
            expect(resolveNomadImagePolicy("never", "always")).toBe("never");
            expect(resolveNomadImagePolicy(undefined, "auto")).toBe("auto");
        });

        it("detects the MIME type from downloaded image bytes", () => {
            const pngB64 = btoa("\x89PNG\r\n\x1a\n");
            const gifB64 = btoa("GIF89a");
            const webpB64 = btoa("RIFF\x00\x00\x00\x00WEBPVP8 ");
            expect(getNomadImageDataUrl(pngB64)).toBe(`data:image/png;base64,${pngB64}`);
            expect(getNomadImageDataUrl(gifB64)).toBe(`data:image/gif;base64,${gifB64}`);
            expect(getNomadImageDataUrl(webpB64)).toBe(`data:image/webp;base64,${webpB64}`);
        });

        it("does not cache images in private browsing", () => {
            const cache = new Map();
            const key = `${IMG_HASH}:/file/img.webp`;
            setNomadImageCacheEntry(cache, key, { dataUrl: "data:,", size: "0 B" }, true);
            expect(cache.size).toBe(0);
            setNomadImageCacheEntry(cache, key, { dataUrl: "data:,", size: "0 B" }, false);
            expect(cache.size).toBe(1);
        });

        it("marks the image policy icon active only when resolved policy auto-loads", async () => {
            GlobalState.config.nomad_image_loading_policy = "manual";
            const { container } = await renderLoadedPage();
            const btn = container.querySelector('[aria-label="Image loading for this node"]');
            expect(btn).toBeTruthy();
            expect(btn.className).not.toContain("text-sem-accent");

            // per-node always override wins over a manual global policy
            const menuItem = (label) =>
                [...container.querySelectorAll('[role="menuitem"]')].find((el) =>
                    el.textContent.trim().endsWith(label)
                );

            // per-node always override wins over a manual global policy
            await fireEvent.click(btn);
            await fireEvent.click(menuItem("Always"));
            expect(btn.className).toContain("text-sem-accent");

            // a per-node never override wins over a permissive global
            GlobalState.config.nomad_image_loading_policy = "always";
            await fireEvent.click(btn);
            await fireEvent.click(menuItem("Never"));
            expect(btn.className).not.toContain("text-sem-accent");
        });

        it("sends a file download with image metadata on manual load", async () => {
            GlobalState.config.nomad_image_loading_policy = "manual";
            const { fakeWindow } = await renderLoadedPage();
            pushImages(fakeWindow, [{ url: ":/file/img.webp", path: ":/file/img.webp", alt: "test", profile: "fast" }]);
            dispatchFrameMessage(fakeWindow, {
                channel: NOMAD_CRASH_TAB_CHANNEL,
                type: "image-action",
                action: "load",
                index: 0,
            });

            await waitFor(() => {
                expect(fileDownloadSends().length).toBe(1);
            });
            const payload = fileDownloadSends()[0];
            expect(payload.nomadnet_file_download.destination_hash).toBe(IMG_HASH);
            expect(payload.nomadnet_file_download.file_path).toBe("/file/img.webp");
            expect(payload.nomadnet_file_download.data.image_id).toBe(0);
            expect(payload.nomadnet_file_download.data.image_profile).toBe("fast");
            expect(payload.nomadnet_file_download.data.request_id).toBeTruthy();
            expect(payload.request_id).toBe(payload.nomadnet_file_download.data.request_id);
        });

        it("ignores stale image websocket events with mismatched request_id", async () => {
            GlobalState.config.nomad_image_loading_policy = "manual";
            const { fakeWindow } = await renderLoadedPage();
            pushImages(fakeWindow, [{ url: ":/file/img.webp", alt: "test" }]);
            dispatchFrameMessage(fakeWindow, {
                channel: NOMAD_CRASH_TAB_CHANNEL,
                type: "image-action",
                action: "load",
                index: 0,
            });
            await waitFor(() => {
                expect(fileDownloadSends().length).toBe(1);
            });
            const requestId = fileDownloadSends()[0].nomadnet_file_download.data.request_id;

            await dispatchWsEvent("nomadnet.file.download", {
                type: "nomadnet.file.download",
                download_id: 77,
                request_id: requestId,
                nomadnet_file_download: {
                    status: "started",
                    destination_hash: IMG_HASH,
                    file_path: "/file/img.webp",
                    data: { image_id: 0, request_id: requestId },
                },
            });

            // stale event: same image_id but a different request_id
            await dispatchWsEvent("nomadnet.file.download", {
                type: "nomadnet.file.download",
                download_id: 77,
                nomadnet_file_download: {
                    status: "success",
                    destination_hash: IMG_HASH,
                    file_path: "/file/img.webp",
                    file_name: "img.webp",
                    file_bytes: btoa("RIFF\x00\x00\x00\x00WEBPVP8 "),
                    data: { image_id: 0, request_id: "stale-123" },
                },
            });

            expect(
                fakeWindow.postMessage.mock.calls.filter((c) => c[0]?.type === "set-image" && c[0]?.state === "loaded")
            ).toHaveLength(0);

            await dispatchWsEvent("nomadnet.file.download", {
                type: "nomadnet.file.download",
                download_id: 77,
                request_id: requestId,
                nomadnet_file_download: {
                    status: "success",
                    destination_hash: IMG_HASH,
                    file_path: "/file/img.webp",
                    file_name: "img.webp",
                    file_bytes: btoa("RIFF\x00\x00\x00\x00WEBPVP8 "),
                    data: { image_id: 0, request_id: requestId },
                },
            });

            await waitFor(() => {
                const loaded = fakeWindow.postMessage.mock.calls.filter(
                    (c) => c[0]?.type === "set-image" && c[0]?.state === "loaded"
                );
                expect(loaded.length).toBe(1);
                expect(loaded[0][0].dataUrl).toContain("data:image/webp;base64,");
            });
        });

        it("does not cache images in private browsing across re-renders", async () => {
            GlobalState.config.nomad_image_loading_policy = "auto";
            const { fakeWindow } = await renderLoadedPage({ isPrivate: true });
            const image = { url: ":/file/img.webp", alt: "test" };
            pushImages(fakeWindow, [image]);
            await waitFor(() => {
                expect(fileDownloadSends().length).toBe(1);
            });
            const requestId = fileDownloadSends()[0].nomadnet_file_download.data.request_id;
            await dispatchWsEvent("nomadnet.file.download", {
                type: "nomadnet.file.download",
                download_id: 78,
                request_id: requestId,
                nomadnet_file_download: {
                    status: "success",
                    destination_hash: IMG_HASH,
                    file_path: "/file/img.webp",
                    file_name: "img.webp",
                    file_bytes: btoa("RIFF\x00\x00\x00\x00WEBPVP8 "),
                    data: { image_id: 0, request_id: requestId },
                },
            });
            pushImages(fakeWindow, [image]);
            await waitFor(() => {
                expect(fileDownloadSends().length).toBe(2);
            });
        });
    });

    describe("crash tab context menu forwarding", () => {
        const IMG_HASH = "a".repeat(32);

        function dispatchFrameMessage(source, data) {
            const event = new MessageEvent("message", { data });
            Object.defineProperty(event, "source", { value: source, configurable: true });
            Object.defineProperty(event, "origin", { value: "null", configurable: true });
            window.dispatchEvent(event);
        }

        async function renderLoadedPage(props = {}) {
            const view = render(NomadNetworkPage, {
                destinationHash: IMG_HASH,
                pagePath: "/page/index.mu",
                ...props,
            });
            await waitFor(() => {
                expect(WebSocketConnection.send).toHaveBeenCalled();
            });
            await dispatchWsEvent("nomadnet.page.download", {
                type: "nomadnet.page.download",
                download_id: 41,
                nomadnet_page_download: {
                    status: "started",
                    destination_hash: IMG_HASH,
                    page_path: "/page/index.mu",
                },
            });
            await dispatchWsEvent("nomadnet.page.download", {
                type: "nomadnet.page.download",
                download_id: 41,
                nomadnet_page_download: {
                    status: "success",
                    destination_hash: IMG_HASH,
                    page_path: "/page/index.mu",
                    page_content: ">#!\n# Hi",
                },
            });
            let frame = null;
            await waitFor(() => {
                frame = document.body.querySelector("iframe");
                expect(frame).toBeTruthy();
            });
            const fakeWindow = { postMessage: vi.fn() };
            Object.defineProperty(frame, "contentWindow", {
                configurable: true,
                get: () => fakeWindow,
            });
            return { ...view, frame, fakeWindow };
        }

        it("opens the standalone context menu at the forwarded coordinates", async () => {
            const { fakeWindow } = await renderLoadedPage();
            dispatchFrameMessage(fakeWindow, {
                channel: NOMAD_CRASH_TAB_CHANNEL,
                type: "page-contextmenu",
                x: 30,
                y: 40,
            });
            await waitFor(() => {
                const panel = document.body.querySelector(".context-menu-panel");
                expect(panel).toBeTruthy();
                expect(panel.style.left).toBe("30px");
                expect(panel.style.top).toBe("40px");
            });
        });

        it("routes to the host context menu when embedded", async () => {
            const onpagecontextmenu = vi.fn();
            const { fakeWindow } = await renderLoadedPage({ onpagecontextmenu });
            dispatchFrameMessage(fakeWindow, {
                channel: NOMAD_CRASH_TAB_CHANNEL,
                type: "page-contextmenu",
                x: 11,
                y: 22,
            });
            await waitFor(() => {
                expect(onpagecontextmenu).toHaveBeenCalledWith(
                    expect.objectContaining({ clientX: 11, clientY: 22, hasActivePage: true })
                );
            });
            expect(document.body.querySelector(".context-menu-panel")).toBeFalsy();
        });
    });

    describe("websocket reconnect resend", () => {
        const IMG_HASH = "a".repeat(32);

        function sentPayloads() {
            return WebSocketConnection.send.mock.calls
                .map((call) => String(call[0] || ""))
                .filter((raw) => raw.startsWith("{"))
                .map((raw) => JSON.parse(raw));
        }

        function emitReconnect() {
            GlobalEmitter.emit("websocket-reconnected", { degraded: false, failed: [] });
        }

        function pageEvent(downloadId, status, extra = {}) {
            return {
                type: "nomadnet.page.download",
                download_id: downloadId,
                nomadnet_page_download: {
                    status,
                    destination_hash: TEST_DESTINATION_HASH,
                    page_path: "/page/index.mu",
                    ...extra,
                },
            };
        }

        // Mounts the page and lets the initial page download reach the
        // "started" stage so the download id is tracked as in-flight.
        async function renderPageDownload(downloadId) {
            const view = render(NomadNetworkPage, {
                destinationHash: TEST_DESTINATION_HASH,
                pagePath: "/page/index.mu",
            });
            await waitFor(() => {
                expect(WebSocketConnection.send).toHaveBeenCalled();
            });
            if (downloadId != null) {
                await dispatchWsEvent("nomadnet.page.download", pageEvent(downloadId, "started"));
            }
            return view;
        }

        it("cancels the orphaned page download and resends it on reconnect", async () => {
            await renderPageDownload(61);
            WebSocketConnection.send.mockClear();

            emitReconnect();

            const sent = sentPayloads();
            expect(sent).toContainEqual({ type: "nomadnet.download.cancel", download_id: 61 });
            expect(sent).toContainEqual(
                expect.objectContaining({
                    type: "nomadnet.page.download",
                    nomadnet_page_download: expect.objectContaining({
                        destination_hash: TEST_DESTINATION_HASH,
                        page_path: "/page/index.mu",
                    }),
                })
            );
        });

        it("resends without a cancel when no download id was assigned yet", async () => {
            await renderPageDownload(null);
            WebSocketConnection.send.mockClear();

            emitReconnect();

            const sent = sentPayloads();
            expect(sent.some((msg) => msg.type === "nomadnet.download.cancel")).toBe(false);
            expect(sent).toContainEqual(expect.objectContaining({ type: "nomadnet.page.download" }));
        });

        it("cancels the orphaned file download and resends it on reconnect", async () => {
            let pageMenu = null;
            const view = render(NomadNetworkPage, {
                destinationHash: TEST_DESTINATION_HASH,
                pagePath: "/page/index.mu",
                onpagecontextmenu: (menu) => {
                    pageMenu = menu;
                },
            });
            await waitFor(() => {
                expect(WebSocketConnection.send).toHaveBeenCalled();
            });
            await dispatchWsEvent("nomadnet.page.download", pageEvent(71, "started"));
            await dispatchWsEvent("nomadnet.page.download", pageEvent(71, "success", { page_content: ">#!\n# Hi" }));

            const region = view.container.querySelector('[aria-label="Nomad page content"]');
            await fireEvent.contextMenu(region);
            expect(pageMenu?.canDownloadPage).toBe(true);
            pageMenu.downloadPage();

            const filePayload = sentPayloads().find((msg) => msg.type === "nomadnet.file.download");
            expect(filePayload).toBeTruthy();

            await dispatchWsEvent("nomadnet.file.download", {
                type: "nomadnet.file.download",
                download_id: 72,
                nomadnet_file_download: {
                    status: "started",
                    destination_hash: TEST_DESTINATION_HASH,
                    file_path: "/page/index.mu",
                },
            });
            WebSocketConnection.send.mockClear();

            emitReconnect();

            const sent = sentPayloads();
            expect(sent).toContainEqual({ type: "nomadnet.download.cancel", download_id: 72 });
            expect(sent.find((msg) => msg.type === "nomadnet.file.download")).toEqual(filePayload);
        });

        it("cancels and resends in-flight image downloads on reconnect", async () => {
            GlobalState.config.nomad_image_loading_policy = "auto";
            const view = render(NomadNetworkPage, {
                destinationHash: IMG_HASH,
                pagePath: "/page/index.mu",
            });
            await waitFor(() => {
                expect(WebSocketConnection.send).toHaveBeenCalled();
            });
            await dispatchWsEvent("nomadnet.page.download", {
                type: "nomadnet.page.download",
                download_id: 41,
                nomadnet_page_download: {
                    status: "started",
                    destination_hash: IMG_HASH,
                    page_path: "/page/index.mu",
                },
            });
            await dispatchWsEvent("nomadnet.page.download", {
                type: "nomadnet.page.download",
                download_id: 41,
                nomadnet_page_download: {
                    status: "success",
                    destination_hash: IMG_HASH,
                    page_path: "/page/index.mu",
                    page_content: ">#!\n# Hi",
                },
            });
            let frame = null;
            await waitFor(() => {
                frame = document.body.querySelector("iframe");
                expect(frame).toBeTruthy();
            });
            const fakeWindow = { postMessage: vi.fn() };
            Object.defineProperty(frame, "contentWindow", {
                configurable: true,
                get: () => fakeWindow,
            });
            const frameEvent = new MessageEvent("message", {
                data: {
                    channel: NOMAD_CRASH_TAB_CHANNEL,
                    type: "render-done",
                    partials: [],
                    images: [{ url: ":/file/img.webp", alt: "test" }],
                },
            });
            Object.defineProperty(frameEvent, "source", { value: fakeWindow, configurable: true });
            Object.defineProperty(frameEvent, "origin", { value: "null", configurable: true });
            window.dispatchEvent(frameEvent);

            await waitFor(() => {
                expect(sentPayloads().filter((msg) => msg.type === "nomadnet.file.download").length).toBe(1);
            });
            const imagePayload = sentPayloads().find((msg) => msg.type === "nomadnet.file.download");
            const requestId = imagePayload.nomadnet_file_download.data.request_id;

            await dispatchWsEvent("nomadnet.file.download", {
                type: "nomadnet.file.download",
                download_id: 81,
                request_id: requestId,
                nomadnet_file_download: {
                    status: "started",
                    destination_hash: IMG_HASH,
                    file_path: "/file/img.webp",
                    data: { image_id: 0, request_id: requestId },
                },
            });
            WebSocketConnection.send.mockClear();

            emitReconnect();

            const sent = sentPayloads();
            expect(sent).toContainEqual({
                type: "nomadnet.download.cancel",
                download_id: 81,
                request_id: requestId,
            });
            const resent = sent.find((msg) => msg.type === "nomadnet.file.download");
            expect(resent).toEqual(imagePayload);
            delete GlobalState.config.nomad_image_loading_policy;
        });

        it("keeps the resent download when the stale cancelled event arrives", async () => {
            const view = await renderPageDownload(61);

            emitReconnect();
            await dispatchWsEvent("nomadnet.download.cancelled", {
                type: "nomadnet.download.cancelled",
                download_id: 61,
            });

            // the cancelled event for the old id must not flash cancelled UI
            // or purge the resent transfer: the page is still loading
            expect(view.queryByText(/cancelled|stopped/i)).toBeNull();

            await dispatchWsEvent("nomadnet.page.download", pageEvent(62, "started"));
            await dispatchWsEvent(
                "nomadnet.page.download",
                pageEvent(62, "success", { page_content: ">#!\n# Resent" })
            );
            await waitFor(() => {
                expect(document.body.querySelector("iframe")).toBeTruthy();
            });
        });

        it("settles the page load when the resend hits a dead socket", async () => {
            const ToastUtils = (await import("@/js/ToastUtils")).default;
            const view = await renderPageDownload(61);
            WebSocketConnection.send.mockReturnValue(false);

            emitReconnect();

            await waitFor(() => {
                expect(view.getByRole("alert")).toBeTruthy();
            });
            expect(ToastUtils.error).toHaveBeenCalled();
            WebSocketConnection.send.mockReturnValue(true);
        });

        it("settles the file download when the resend hits a dead socket", async () => {
            const ToastUtils = (await import("@/js/ToastUtils")).default;
            let pageMenu = null;
            const view = render(NomadNetworkPage, {
                destinationHash: TEST_DESTINATION_HASH,
                pagePath: "/page/index.mu",
                onpagecontextmenu: (menu) => {
                    pageMenu = menu;
                },
            });
            await waitFor(() => {
                expect(WebSocketConnection.send).toHaveBeenCalled();
            });
            await dispatchWsEvent("nomadnet.page.download", pageEvent(71, "started"));
            await dispatchWsEvent("nomadnet.page.download", pageEvent(71, "success", { page_content: ">#!\n# Hi" }));

            const region = view.container.querySelector('[aria-label="Nomad page content"]');
            await fireEvent.contextMenu(region);
            pageMenu.downloadPage();
            await dispatchWsEvent("nomadnet.file.download", {
                type: "nomadnet.file.download",
                download_id: 72,
                nomadnet_file_download: {
                    status: "started",
                    destination_hash: TEST_DESTINATION_HASH,
                    file_path: "/page/index.mu",
                },
            });
            await waitFor(() => {
                expect(view.getByText(/Downloading:/)).toBeTruthy();
            });

            WebSocketConnection.send.mockReturnValue(false);
            emitReconnect();

            await waitFor(() => {
                expect(view.queryByText(/Downloading:/)).toBeNull();
            });
            expect(ToastUtils.error).toHaveBeenCalled();
            WebSocketConnection.send.mockReturnValue(true);
        });

        it("sends nothing on reconnect when no download is in flight", async () => {
            const view = await renderPageDownload(71);
            await dispatchWsEvent("nomadnet.page.download", pageEvent(71, "success", { page_content: ">#!\n# Hi" }));
            await waitFor(() => {
                expect(view.container.querySelector("iframe") || document.body.querySelector("iframe")).toBeTruthy();
            });
            WebSocketConnection.send.mockClear();

            emitReconnect();

            expect(WebSocketConnection.send).not.toHaveBeenCalled();
        });
    });

    describe("touch gestures", () => {
        function fireTouch(el, type, x, y) {
            const event = new Event(type, { bubbles: true, cancelable: true });
            Object.defineProperty(event, "touches", {
                value: [{ clientX: x, clientY: y }],
                configurable: true,
            });
            el.dispatchEvent(event);
        }

        function renderHost(props = {}) {
            const view = render(NomadPageRendererHost, { hasHistory: true, ...props });
            const region = view.container.querySelector('[aria-label="Nomad page content"]');
            expect(region).toBeTruthy();
            return { view, region };
        }

        it("completed edge swipe navigates back", () => {
            const onback = vi.fn();
            const { region } = renderHost({ onback });

            fireTouch(region, "touchstart", 10, 100);
            fireTouch(region, "touchmove", 110, 100);
            fireTouch(region, "touchend", 110, 100);

            expect(onback).toHaveBeenCalledTimes(1);
        });

        it("reversing direction mid-gesture cancels an armed swipe", () => {
            const onback = vi.fn();
            const onreload = vi.fn();
            const { region } = renderHost({ onback, onreload });

            fireTouch(region, "touchstart", 10, 100);
            fireTouch(region, "touchmove", 110, 100);
            // finger drifts back and up before release: the armed swipe must not survive
            fireTouch(region, "touchmove", 30, 60);
            fireTouch(region, "touchend", 30, 60);

            expect(onback).not.toHaveBeenCalled();
            expect(onreload).not.toHaveBeenCalled();
        });

        it("reversing direction mid-gesture cancels an armed pull", () => {
            const onreload = vi.fn();
            const { region } = renderHost({ onreload });

            // start away from the left edge so the pull branch is evaluated
            fireTouch(region, "touchstart", 200, 100);
            fireTouch(region, "touchmove", 200, 220);
            // finger drags back above the start point before release
            fireTouch(region, "touchmove", 200, 80);
            fireTouch(region, "touchend", 200, 80);

            expect(onreload).not.toHaveBeenCalled();
        });

        it("touchcancel does not fire an armed swipe-back", () => {
            const onback = vi.fn();
            const { region } = renderHost({ onback });

            fireTouch(region, "touchstart", 10, 100);
            fireTouch(region, "touchmove", 110, 100);
            fireTouch(region, "touchcancel", 110, 100);

            expect(onback).not.toHaveBeenCalled();
        });

        it("touchcancel does not fire an armed pull-to-refresh", () => {
            const onreload = vi.fn();
            const { region } = renderHost({ onreload });

            fireTouch(region, "touchstart", 200, 100);
            fireTouch(region, "touchmove", 200, 220);
            fireTouch(region, "touchcancel", 200, 220);

            expect(onreload).not.toHaveBeenCalled();
        });
    });
});
