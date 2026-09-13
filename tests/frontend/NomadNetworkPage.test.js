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

    describe("image support", () => {
        it("resolves a relative image URL to the selected node", () => {
            const hash = "a".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash });
            wrapper.vm.selectedNode = { destination_hash: hash };
            const resolved = wrapper.vm.resolveNomadImageDestination(":/file/img.webp");
            expect(resolved.destinationHash).toBe(hash);
            expect(resolved.filePath).toBe("/file/img.webp");
        });

        it("resolves an absolute image URL with destination hash", () => {
            const hash = "a".repeat(32);
            const other = "b".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash });
            wrapper.vm.selectedNode = { destination_hash: hash };
            const resolved = wrapper.vm.resolveNomadImageDestination(`${other}:/file/img.webp`);
            expect(resolved.destinationHash).toBe(other);
            expect(resolved.filePath).toBe("/file/img.webp");
        });

        it("maps unknown policy values to manual", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.config = { nomad_image_loading_policy: "bogus" };
            expect(wrapper.vm.getNomadImagePolicy()).toBe("manual");
        });

        it("uses per-node image policy override when present", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.config = { nomad_image_loading_policy: "manual" };
            wrapper.vm.nomadImagePerNodePolicies = { abc: "always" };
            expect(wrapper.vm.getNomadImagePolicy("abc")).toBe("always");
            expect(wrapper.vm.getNomadImagePolicy("def")).toBe("manual");
        });

        it("marks the image policy icon active only when resolved policy auto-loads", () => {
            const hash = "a".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash });
            wrapper.vm.selectedNode = { destination_hash: hash };
            const configStore = wrapper.vm.configStore;
            const previous = configStore.config.nomad_image_loading_policy;
            try {
                configStore.config.nomad_image_loading_policy = "manual";
                expect(wrapper.vm.selectedNodeImagesAutoLoad).toBe(false);

                configStore.config.nomad_image_loading_policy = "auto";
                expect(wrapper.vm.selectedNodeImagesAutoLoad).toBe(true);

                configStore.config.nomad_image_loading_policy = "always";
                expect(wrapper.vm.selectedNodeImagesAutoLoad).toBe(true);

                // a per-node never override wins over a permissive global
                wrapper.vm.nomadImagePerNodePolicies = { [hash]: "never" };
                expect(wrapper.vm.selectedNodeImagesAutoLoad).toBe(false);

                wrapper.vm.nomadImagePerNodePolicies = { [hash]: "always" };
                expect(wrapper.vm.selectedNodeImagesAutoLoad).toBe(true);
            } finally {
                if (previous === undefined) {
                    delete configStore.config.nomad_image_loading_policy;
                } else {
                    configStore.config.nomad_image_loading_policy = previous;
                }
            }
        });

        it("sends a file download with image metadata", async () => {
            const hash = "a".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash });
            wrapper.vm.selectedNode = { destination_hash: hash };
            wrapper.vm.config = { nomad_image_loading_policy: "manual" };
            const WebSocketConnection = (await import("@/js/WebSocketConnection")).default;
            wrapper.vm.crashTabImages = [
                {
                    url: ":/file/img.webp",
                    alt: "test",
                    w: "100",
                    h: "50",
                    size: null,
                    key: "",
                    align: "left",
                    profile: "fast",
                },
            ];
            wrapper.vm.setCrashTabImage = vi.fn();
            wrapper.vm.loadNomadImage(wrapper.vm.crashTabImages[0], 0);
            const calls = WebSocketConnection.send.mock.calls.filter((c) =>
                String(c[0]).includes('"nomadnet.file.download"')
            );
            expect(calls.length).toBe(1);
            const payload = JSON.parse(calls[0][0]);
            expect(payload.nomadnet_file_download.destination_hash).toBe(hash);
            expect(payload.nomadnet_file_download.file_path).toBe("/file/img.webp");
            expect(payload.nomadnet_file_download.data.image_id).toBe(0);
            expect(payload.nomadnet_file_download.data.image_profile).toBe("fast");
        });

        it("rejects non-webp and traversal image URLs", () => {
            const hash = "a".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash });
            wrapper.vm.selectedNode = { destination_hash: hash };
            expect(wrapper.vm.resolveNomadImageDestination(":/file/img.png").destinationHash).toBe("");
            expect(wrapper.vm.resolveNomadImageDestination(":/page/index.mu").destinationHash).toBe("");
            expect(wrapper.vm.resolveNomadImageDestination(":/file/../etc/shadow.webp").destinationHash).toBe("");
            expect(wrapper.vm.resolveNomadImageDestination(":/file/img.webp?x=1").destinationHash).toBe(hash);
        });

        it("sets the per-node image policy from the toolbar dropdown", async () => {
            const hash = "a".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash });
            wrapper.vm.selectedNode = { destination_hash: hash };
            await wrapper.vm.$nextTick();

            // one instance on mobile toolbar, one inside the desktop toolbar group
            const imageButtons = wrapper.findAll('[data-icon-name="image-outline"]');
            expect(imageButtons.length).toBe(2);

            await imageButtons[0].trigger("click");
            await wrapper.vm.$nextTick();

            const panel = document.body.querySelector(".dropdown-panel");
            expect(panel).toBeTruthy();
            const items = [...panel.querySelectorAll("div")].filter((el) =>
                el.textContent.includes("nomadnet.image_loading_policy_manual_short")
            );
            expect(items.length).toBeGreaterThan(0);
            items[items.length - 1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.nomadImagePerNodePolicies[hash]).toBe("manual");

            // choosing inherit clears the override
            await imageButtons[0].trigger("click");
            await wrapper.vm.$nextTick();
            const panel2 = document.body.querySelectorAll(".dropdown-panel");
            const lastPanel = panel2[panel2.length - 1];
            const inheritItem = [...lastPanel.querySelectorAll("div")].filter((el) =>
                el.textContent.includes("nomadnet.image_loading_policy_inherit")
            );
            inheritItem[inheritItem.length - 1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.nomadImagePerNodePolicies[hash]).toBeUndefined();
            wrapper.unmount();
            document.body.innerHTML = "";
        });

        it("resolves /media image URLs with any supported extension", () => {
            const hash = "a".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash });
            wrapper.vm.selectedNode = { destination_hash: hash };
            for (const ext of ["webp", "png", "jpg", "jpeg", "bmp", "gif", "tiff"]) {
                const resolved = wrapper.vm.resolveNomadImageDestination(`${hash}:/media/img.${ext}`);
                expect(resolved.destinationHash).toBe(hash);
                expect(resolved.filePath).toBe(`/media/img.${ext}`);
            }
        });

        it("detects the MIME type from downloaded image bytes", () => {
            const wrapper = mountNomadNetworkPage();
            const pngB64 = btoa("\x89PNG\r\n\x1a\n");
            const gifB64 = btoa("GIF89a");
            const webpB64 = btoa("RIFF\x00\x00\x00\x00WEBPVP8 ");
            expect(wrapper.vm.getNomadImageDataUrl(pngB64)).toBe(`data:image/png;base64,${pngB64}`);
            expect(wrapper.vm.getNomadImageDataUrl(gifB64)).toBe(`data:image/gif;base64,${gifB64}`);
            expect(wrapper.vm.getNomadImageDataUrl(webpB64)).toBe(`data:image/webp;base64,${webpB64}`);
        });

        it("ignores stale image websocket events with mismatched request_id", async () => {
            const hash = "a".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash });
            wrapper.vm.selectedNode = { destination_hash: hash };
            wrapper.vm.config = { nomad_image_loading_policy: "manual" };
            wrapper.vm.crashTabImages = [{ url: ":/file/img.webp", alt: "test" }];
            wrapper.vm.setCrashTabImage = vi.fn();
            wrapper.vm.loadNomadImage(wrapper.vm.crashTabImages[0], 0);
            const badRequestId = "stale-123";
            const handled = wrapper.vm.ownsNomadImageDownloadEvent(
                {
                    request_id: badRequestId,
                    destination_hash: hash,
                    file_path: "/file/img.webp",
                },
                0
            );
            expect(handled).toBe(false);
        });

        it("does not cache images in private browsing", () => {
            const hash = "a".repeat(32);
            const wrapper = mountNomadNetworkPage({ destinationHash: hash, isPrivate: true });
            wrapper.vm.setNomadImageCacheEntry(hash + ":/file/img.webp", { dataUrl: "data:," });
            expect(wrapper.vm.nomadImageCache.size).toBe(0);
        });
    });

    describe("crash tab context menu forwarding", () => {
        it("opens the standalone context menu at the forwarded coordinates", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.onCrashTabContextMenu({ clientX: 30, clientY: 40 });
            expect(wrapper.vm.standaloneContextMenu.show).toBe(true);
            expect(wrapper.vm.standaloneContextMenu.x).toBe(30);
            expect(wrapper.vm.standaloneContextMenu.y).toBe(40);
        });

        it("routes to the browser tab context menu when embedded", () => {
            const openContextMenu = vi.fn();
            const wrapper = mount(NomadNetworkPage, {
                props: { destinationHash: "", embedded: true },
                global: {
                    mocks: {
                        $t: (key) => key,
                        $route: { query: {} },
                        $router: { replace: vi.fn() },
                    },
                    provide: {
                        nomadBrowserTabActions: { openContextMenu },
                    },
                    stubs: {
                        MaterialDesignIcon: {
                            template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                            props: ["iconName"],
                        },
                        LoadingSpinner: true,
                        NomadNetworkSidebar: {
                            template: '<div class="sidebar-stub"></div>',
                            props: ["nodes", "selectedDestinationHash"],
                        },
                        NomadBrowserContextMenu: true,
                        NomadCrashTab: true,
                        VTooltip: {
                            template: '<div class="v-tooltip-stub"><slot /></div>',
                        },
                    },
                },
            });
            wrapper.vm.onCrashTabContextMenu({ clientX: 11, clientY: 22 });
            expect(openContextMenu).toHaveBeenCalledWith({ clientX: 11, clientY: 22 });
            expect(wrapper.vm.standaloneContextMenu.show).toBe(false);
        });
    });
});
