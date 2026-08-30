import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MicronParser from "@/js/MicronParser.js";

import NomadNetworkPage from "@/components/nomadnetwork/NomadNetworkPage.vue";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

const wsMessageHandlers = [];
const wsEventHandlers = {};

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(() => true),
        isOpen: vi.fn(() => true),
        on: vi.fn((event, handler) => {
            if (event === "message") {
                wsMessageHandlers.push(handler);
                return;
            }
            if (!wsEventHandlers[event]) {
                wsEventHandlers[event] = [];
            }
            wsEventHandlers[event].push(handler);
        }),
        off: vi.fn((event, handler) => {
            if (event === "message") {
                const index = wsMessageHandlers.indexOf(handler);
                if (index >= 0) {
                    wsMessageHandlers.splice(index, 1);
                }
                return;
            }
            const list = wsEventHandlers[event] || [];
            const index = list.indexOf(handler);
            if (index >= 0) {
                list.splice(index, 1);
            }
        }),
    },
}));

describe("NomadNetworkPage.vue", () => {
    let axiosMock;

    beforeEach(async () => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
        };
        window.api = axiosMock;
        wsMessageHandlers.length = 0;
        for (const key of Object.keys(wsEventHandlers)) {
            delete wsEventHandlers[key];
        }
        vi.clearAllMocks();
        const WebSocketConnection = (await import("@/js/WebSocketConnection")).default;
        WebSocketConnection.send.mockReturnValue(true);
        WebSocketConnection.isOpen.mockReturnValue(true);

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            if (url.includes("/path")) return Promise.resolve({ data: { path: { hops: 1 } } });
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
    });

    const mountNomadNetworkPage = (props = { destinationHash: "" }) => {
        return mount(NomadNetworkPage, {
            props,
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { replace: vi.fn() },
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
    };

    it("displays 'No active node' by default", () => {
        const wrapper = mountNomadNetworkPage();
        expect(wrapper.text()).toContain("nomadnet.no_active_node");
    });

    it("debounces node search and passes search param to announces API", async () => {
        vi.useFakeTimers();
        axiosMock.isCancel = vi.fn(() => false);
        const wrapper = mountNomadNetworkPage();
        await wrapper.vm.$nextTick();
        axiosMock.get.mockClear();

        wrapper.vm.onNodesSearchChanged("nodequery");
        await vi.advanceTimersByTimeAsync(500);
        const calls = axiosMock.get.mock.calls.filter((c) => c[0] === "/api/v1/announces");
        expect(calls.length).toBeGreaterThanOrEqual(1);
        const last = calls[calls.length - 1];
        expect(last[1].params.aspect).toBe("nomadnetwork.node");
        expect(last[1].params.search).toBe("nodequery");
        vi.useRealTimers();
    });

    it("tracks isSearchingNodes while the debounce and request are pending, clearing it once resolved", async () => {
        vi.useFakeTimers();
        axiosMock.isCancel = vi.fn(() => false);

        let resolveAnnounces;
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
            if (url === "/api/v1/announces") {
                return new Promise((resolve) => {
                    resolveAnnounces = resolve;
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountNomadNetworkPage();

        // the initial mount fetch is in flight
        expect(wrapper.vm.isSearchingNodes).toBe(true);
        resolveAnnounces({ data: { announces: [], total_count: 0 } });
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isSearchingNodes).toBe(false);

        wrapper.vm.onNodesSearchChanged("nodequery");
        // indicator shows immediately, even before the debounce fires
        expect(wrapper.vm.isSearchingNodes).toBe(true);

        await vi.advanceTimersByTimeAsync(500);
        // debounce elapsed, request is now in flight and still pending
        expect(wrapper.vm.isSearchingNodes).toBe(true);

        resolveAnnounces({ data: { announces: [], total_count: 0 } });
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isSearchingNodes).toBe(false);

        vi.useRealTimers();
    });

    it("does not clear isSearchingNodes for a stale request superseded by a newer search", async () => {
        vi.useFakeTimers();
        axiosMock.isCancel = vi.fn((e) => e?.isCancelled === true);

        const pending = [];
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
            if (url === "/api/v1/announces") {
                return new Promise((resolve, reject) => {
                    pending.push({ resolve, reject });
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountNomadNetworkPage();
        await wrapper.vm.$nextTick();
        expect(pending.length).toBe(1);

        // reject the initial mount fetch as if it was aborted by a new search
        wrapper.vm.onNodesSearchChanged("first");
        await vi.advanceTimersByTimeAsync(500);
        expect(pending.length).toBe(2);
        pending[0].reject({ isCancelled: true });
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        // the newer request is still in flight, so the indicator must stay on
        expect(wrapper.vm.isSearchingNodes).toBe(true);

        pending[1].resolve({ data: { announces: [], total_count: 0 } });
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.isSearchingNodes).toBe(false);

        vi.useRealTimers();
    });

    it("loads node when destinationHash prop is provided", async () => {
        const destHash = "0123456789abcdef0123456789abcdef";
        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/announces")
                return Promise.resolve({
                    data: { announces: [{ destination_hash: destHash, display_name: "Test Node" }] },
                });
            if (url === "/api/v1/favourites") return Promise.resolve({ data: { favourites: [] } });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountNomadNetworkPage({ destinationHash: destHash });
        // Manually set favourites to avoid undefined error if mock fails
        wrapper.vm.favourites = [];
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // Wait for fetch

        expect(wrapper.vm.selectedNode.destination_hash).toBe(destHash);
    });

    it("toggles source view", async () => {
        const destHash = "0123456789abcdef0123456789abcdef";
        const wrapper = mountNomadNetworkPage({ destinationHash: destHash });
        wrapper.vm.favourites = [];
        wrapper.setData({
            selectedNode: { destination_hash: destHash, display_name: "Test Node" },
            nodePageContent: "Page Content",
            nodePagePath: "test:path",
        });
        await wrapper.vm.$nextTick();

        // Find toggle source button by icon name
        const buttons = wrapper.findAll("button");
        const toggleSourceButton = buttons.find((b) => b.html().includes('data-icon-name="code-tags"'));
        if (toggleSourceButton) {
            await toggleSourceButton.trigger("click");
            expect(wrapper.vm.isShowingNodePageSource).toBe(true);
        }
    });

    describe("showMicronRendererInMobileMenu", () => {
        it("is true on .mu page when wasm bundled and not in source view", async () => {
            const dest = "a".repeat(32);
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                wasmBundled: true,
                selectedNode: { destination_hash: dest, display_name: "N" },
                nodePagePath: `${dest}:/page/index.mu`,
                isShowingNodePageSource: false,
            });
            expect(wrapper.vm.showMicronRendererInMobileMenu).toBe(true);
        });

        it("is false without selectedNode", async () => {
            const dest = "c".repeat(32);
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                wasmBundled: true,
                selectedNode: null,
                nodePagePath: `${dest}:/page/index.mu`,
                isShowingNodePageSource: false,
            });
            expect(wrapper.vm.showMicronRendererInMobileMenu).toBe(false);
        });

        it("is false in source view", async () => {
            const dest = "b".repeat(32);
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                wasmBundled: true,
                selectedNode: { destination_hash: dest, display_name: "N" },
                nodePagePath: `${dest}:/page/index.mu`,
                isShowingNodePageSource: true,
            });
            expect(wrapper.vm.showMicronRendererInMobileMenu).toBe(false);
        });

        it("is false when wasm is not bundled", async () => {
            const dest = "d".repeat(32);
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                wasmBundled: false,
                selectedNode: { destination_hash: dest, display_name: "N" },
                nodePagePath: `${dest}:/page/index.mu`,
                isShowingNodePageSource: false,
            });
            expect(wrapper.vm.showMicronRendererInMobileMenu).toBe(false);
        });

        it("is true on .mu page when URL has Nomad data suffix after backtick", async () => {
            const dest = "e".repeat(32);
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                wasmBundled: true,
                selectedNode: { destination_hash: dest, display_name: "N" },
                nodePagePath: `${dest}:/page/repo.mu\`g=reticulum|r=nomadnet`,
                isShowingNodePageSource: false,
            });
            expect(wrapper.vm.nodePagePathIsMicronMu).toBe(true);
            expect(wrapper.vm.showMicronRendererInMobileMenu).toBe(true);
        });
    });

    describe("partials", () => {
        it("clearPartials resets partial state and timers", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.pagePartials = { "partial-0": "<span>x</span>" };
            wrapper.vm.loadedPartialIds = { "partial-0": true };
            wrapper.vm.partialIdsByKey = { "abc:path": [] };
            wrapper.vm.partialRefreshByKey = { "abc:path": 10 };
            wrapper.vm.partialRefreshTimers = { "abc:path": 12345 };

            wrapper.vm.clearPartials();

            expect(wrapper.vm.pagePartials).toEqual({});
            expect(wrapper.vm.loadedPartialIds).toEqual({});
            expect(wrapper.vm.partialIdsByKey).toEqual({});
            expect(wrapper.vm.partialRefreshByKey).toEqual({});
            expect(wrapper.vm.partialRefreshTimers).toEqual({});
        });

        it("processPartials does not call downloadNomadNetPage again after partials are marked loaded", async () => {
            const dest = "a".repeat(32);
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.selectedNode = { destination_hash: dest, display_name: "Test" };
            wrapper.vm.nodePagePath = `${dest}:/page/index.mu`;
            wrapper.vm.nodePageContent = "`{" + dest + ":/page/nested.mu}";
            const downloadSpy = vi
                .spyOn(wrapper.vm, "downloadNomadNetPage")
                .mockImplementation((_d, _p, _f, onSuccess) => {
                    onSuccess("# ok");
                });

            await wrapper.vm.$nextTick();
            await wrapper.vm.$nextTick();

            wrapper.vm.crashTabPartials = [
                {
                    id: "partial-0",
                    dest,
                    path: "/page/nested.mu",
                    refresh: null,
                    fields: null,
                },
            ];
            wrapper.vm.processPartials();
            await wrapper.vm.$nextTick();

            const afterFirst = downloadSpy.mock.calls.length;
            expect(afterFirst).toBeGreaterThanOrEqual(1);

            wrapper.vm.crashTabPartials = [
                {
                    id: "partial-0",
                    dest,
                    path: "/page/nested.mu",
                    refresh: null,
                    fields: null,
                },
            ];
            wrapper.vm.processPartials();
            await wrapper.vm.$nextTick();

            expect(downloadSpy.mock.calls.length).toBe(afterFirst);

            downloadSpy.mockRestore();
        });

        it("processPartials floors hostile 1s refresh to at least 5s", async () => {
            vi.useFakeTimers();
            const dest = "c".repeat(32);
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.selectedNode = { destination_hash: dest, display_name: "Test" };
            wrapper.vm.nodePagePath = `${dest}:/page/index.mu`;
            wrapper.vm.nodePageContent = "`{" + dest + ":/page/nested.mu`1}";
            wrapper.vm.isShowingNodePageSource = false;

            const downloadSpy = vi
                .spyOn(wrapper.vm, "downloadNomadNetPage")
                .mockImplementation((_d, _p, _f, onSuccess) => {
                    onSuccess("# ok");
                });

            await wrapper.vm.$nextTick();
            await wrapper.vm.$nextTick();
            wrapper.vm.crashTabPartials = [
                {
                    id: "partial-0",
                    dest,
                    path: "/page/nested.mu",
                    refresh: "1",
                    fields: null,
                },
            ];
            wrapper.vm.processPartials();
            await wrapper.vm.$nextTick();

            const afterFirst = downloadSpy.mock.calls.length;
            expect(afterFirst).toBeGreaterThanOrEqual(1);
            expect(wrapper.vm.partialRefreshByKey[`${dest}:/page/nested.mu`]).toBe(5);

            vi.advanceTimersByTime(1000);
            expect(downloadSpy.mock.calls.length).toBe(afterFirst);

            vi.advanceTimersByTime(4000);
            await wrapper.vm.$nextTick();
            expect(downloadSpy.mock.calls.length).toBeGreaterThan(afterFirst);

            downloadSpy.mockRestore();
            vi.useRealTimers();
        });

        it("relative page URL without selected node toasts instead of crashing", async () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.selectedNode = null;
            await expect(wrapper.vm.onNodePageUrlClick(":/page/index.mu")).resolves.toBeUndefined();
            expect(ToastUtils.warning).toHaveBeenCalled();
        });

        it("does not re-run Micron conversion when only favourites list updates", async () => {
            const dest = "b".repeat(32);
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.selectedNode = { destination_hash: dest, display_name: "Test" };
            wrapper.vm.nodePagePath = `${dest}:/page/index.mu`;
            wrapper.vm.nodePageContent = "# line one\n# line two";
            wrapper.vm.isShowingNodePageSource = false;

            await wrapper.vm.$nextTick();

            const parseSpy = vi.spyOn(MicronParser.prototype, "convertMicronToHtml");

            wrapper.vm.favourites = [{ destination_hash: "x", display_name: "Fav" }];
            await wrapper.vm.$nextTick();

            expect(parseSpy).not.toHaveBeenCalled();
            parseSpy.mockRestore();
        });

        it("renderPageContent with .mu and pagePartials injects partial content", () => {
            const dest = "a".repeat(32);
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.pagePartials = { "partial-0": "<span>Loaded partial</span>" };
            const content = "Hello\n`{" + dest + ":/page/partial.mu}\nWorld";
            const path = dest + ":/page/index.mu";

            const html = wrapper.vm.renderPageContent(path, content);

            expect(html).toContain("Loaded partial");
            expect(html).not.toContain("Loading...");
            expect(html).toContain("H");
            expect(html).toContain("W");
        });

        it("renderPageContent without pagePartials shows placeholder for partial", () => {
            const dest = "b".repeat(32);
            const wrapper = mountNomadNetworkPage();
            const content = "`{" + dest + ":/page/partial.mu}";
            const path = dest + ":/page/index.mu";

            const html = wrapper.vm.renderPageContent(path, content);

            expect(html).toContain("mu-partial");
            expect(html).toContain("Loading...");
            expect(html).toContain('data-dest="' + dest + '"');
        });
    });

    describe("page load stats", () => {
        it("formatShortDuration formats ms and seconds", () => {
            const wrapper = mountNomadNetworkPage();
            expect(wrapper.vm.formatShortDuration(0)).toBe("0 ms");
            expect(wrapper.vm.formatShortDuration(500)).toBe("500 ms");
            expect(wrapper.vm.formatShortDuration(1500)).toMatch(/1\.5 s/);
            expect(wrapper.vm.formatShortDuration(120000)).toMatch(/2m/);
        });
    });

    describe("isFailedPageContent", () => {
        const failedCases = [
            ["request_failed"],
            ["Failed loading page:"],
            ["Failed loading page: Could not establish link to destination."],
            ["Failed loading page: empty_response"],
            ["Failed loading page: request_failed"],
        ];

        it.each(failedCases)("treats %s as failed load sentinel", (content) => {
            const wrapper = mountNomadNetworkPage();
            expect(wrapper.vm.isFailedPageContent(content)).toBe(true);
        });

        const notFailedCases = [
            [null],
            [undefined],
            ["# README\nTalk about failure modes here."],
            ["FAILURE is not how we detect errors"],
            ["partial_failure in prose"],
            [""],
            ["Download cancelled"],
            ["Download cancelled."],
            ["page_download_cancelled"],
            ["<p>success</p>"],
        ];

        it.each(notFailedCases)("does not treat %s as failed load", (content) => {
            const wrapper = mountNomadNetworkPage();
            expect(wrapper.vm.isFailedPageContent(content)).toBe(false);
        });

        const boundaryCases = [
            ["phrase only mid-document", "Something happened. Failed loading page: not a real prefix.", false],
            ["leading newline before meshchat prefix", "\nFailed loading page: timeout", false],
            ["leading spaces before meshchat prefix", " Failed loading page: timeout", false],
            ["wrong casing on meshchat prefix", "failed loading page: timeout", false],
            ["wrong casing on sentinel", "REQUEST_FAILED", false],
            ["sentinel with trailing space", "request_failed ", false],
            ["sentinel with leading space", " request_failed", false],
            ["meshchat prefix substring only", "PrefixedFailed loading page: no", false],
        ];

        it.each(boundaryCases)("boundary: %s", (_label, content, expectedFailed) => {
            const wrapper = mountNomadNetworkPage();
            expect(wrapper.vm.isFailedPageContent(content)).toBe(expectedFailed);
        });

        it("non-string and boxed values are not matched as failed", () => {
            const wrapper = mountNomadNetworkPage();
            expect(wrapper.vm.isFailedPageContent(123)).toBe(false);
            expect(wrapper.vm.isFailedPageContent(NaN)).toBe(false);
            expect(wrapper.vm.isFailedPageContent(true)).toBe(false);
            expect(wrapper.vm.isFailedPageContent(false)).toBe(false);
            expect(wrapper.vm.isFailedPageContent([])).toBe(false);
            expect(wrapper.vm.isFailedPageContent({ status: "failure" })).toBe(false);
            expect(wrapper.vm.isFailedPageContent(new String("request_failed"))).toBe(false);
            expect(wrapper.vm.isFailedPageContent(new String("Failed loading page: boxed"))).toBe(false);
        });
    });

    describe("isCancelledPageContent and cancel UI", () => {
        const destHash = "d".repeat(32);

        it("treats the cancel sentinel as cancelled content", () => {
            const wrapper = mountNomadNetworkPage();
            expect(wrapper.vm.isCancelledPageContent("page_download_cancelled")).toBe(true);
            expect(wrapper.vm.isCancelledPageContent("nomadnet.page_download_cancelled")).toBe(true);
            expect(wrapper.vm.isCancelledPageContent("Failed loading page: x")).toBe(false);
            expect(wrapper.vm.isCancelledPageContent("# page")).toBe(false);
        });

        it("shows cancelled status instead of crash-tab content after cancelPageDownload", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/index.mu`,
                isLoadingNodePage: true,
                currentPageDownloadId: 42,
                nodePageContent: null,
            });
            wrapper.vm.cancelPageDownload();
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.isLoadingNodePage).toBe(false);
            expect(wrapper.vm.currentPageDownloadId).toBe(null);
            expect(wrapper.vm.nodePageContent).toBe("page_download_cancelled");
            expect(wrapper.vm.showCancelledPageState).toBe(true);
            expect(wrapper.text()).toContain("nomadnet.page_download_cancelled");
            expect(wrapper.findComponent({ name: "NomadCrashTab" }).exists()).toBe(false);

            const WebSocketConnection = (await import("@/js/WebSocketConnection")).default;
            expect(WebSocketConnection.send).toHaveBeenCalledWith(
                JSON.stringify({
                    type: "nomadnet.download.cancel",
                    download_id: 42,
                })
            );
        });

        it("optimistic cancel without download id still shows cancelled status", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/index.mu`,
                isLoadingNodePage: true,
                currentPageDownloadId: null,
                nodePageContent: null,
            });
            wrapper.vm.cancelPageDownload();
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.pendingNomadPageCancelWithoutId).toBe(true);
            expect(wrapper.vm.showCancelledPageState).toBe(true);
            expect(wrapper.findComponent({ name: "NomadCrashTab" }).exists()).toBe(false);
        });

        it("render abort shows cancelled status without wiping page bytes", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/index.mu`,
                isLoadingNodePage: false,
                nodePageContent: ">#!\n# Hello",
                pageRenderAborted: false,
                isCrashTabRendering: true,
            });
            wrapper.vm.onCrashTabAborted();
            await wrapper.vm.$nextTick();

            expect(wrapper.vm.pageRenderAborted).toBe(true);
            expect(wrapper.vm.nodePageContent).toBe(">#!\n# Hello");
            expect(wrapper.vm.showCancelledPageState).toBe(true);
            expect(wrapper.vm.canRetryCrashTabRender).toBe(true);
            expect(wrapper.findComponent({ name: "NomadCrashTab" }).exists()).toBe(false);
            expect(ToastUtils.info).toHaveBeenCalledWith("nomadnet.crash_tab_render_cancelled");

            wrapper.vm.retryCrashTabRender();
            await wrapper.vm.$nextTick();
            expect(wrapper.vm.pageRenderAborted).toBe(false);
            expect(wrapper.vm.showCancelledPageState).toBe(false);
            expect(wrapper.findComponent({ name: "NomadCrashTab" }).exists()).toBe(true);
        });

        it("shows loading banner with cancel while crash-tab is rendering", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/index.mu`,
                isLoadingNodePage: false,
                nodePageContent: ">#!\n# Hello",
                pageRenderAborted: false,
                isCrashTabRendering: true,
            });
            expect(wrapper.vm.showPageBusyBanner).toBe(true);
            expect(wrapper.vm.pageBusyBannerLine).toBe("nomadnet.load_phase_default");
            expect(wrapper.text()).toContain("nomadnet.load_phase_default");
            expect(wrapper.text()).toContain("common.cancel");
            expect(wrapper.text()).not.toContain("nomadnet.crash_tab_rendering");
            expect(wrapper.findComponent({ name: "NomadCrashTab" }).exists()).toBe(true);
        });

        it("shows empty-page status when content is blank", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/index.mu`,
                isLoadingNodePage: false,
                nodePageContent: "",
                pageRenderAborted: false,
            });
            expect(wrapper.vm.showEmptyPageState).toBe(true);
            expect(wrapper.vm.showCancelledPageState).toBe(false);
            expect(wrapper.text()).toContain("nomadnet.page_empty_title");
            expect(wrapper.findComponent({ name: "NomadCrashTab" }).exists()).toBe(false);
        });
    });

    describe("crash-tab Micron chrome props", () => {
        const destHash = "b".repeat(32);

        it("passes semantic micron classes and Nomad dark colors for .mu pages", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/index.mu`,
                isLoadingNodePage: false,
                nodePageContent: ">#!\n# Hello",
                isShowingNodePageSource: false,
            });
            expect(wrapper.vm.nomadCrashTabContentClass).toContain("nomad-page-rich");
            expect(wrapper.vm.nomadCrashTabContentClass).toContain("bg-black");
            expect(wrapper.vm.nomadCrashTabContentClass).not.toContain("text-gray-100");
            expect(wrapper.vm.nomadCrashTabContentClass).not.toContain("wrap-break-word");
            expect(wrapper.vm.nomadCrashTabColor).toBe("#dddddd");
            expect(wrapper.vm.nomadCrashTabBackground).toBe("#000000");
        });

        it("uses #!bg= header for crash-tab background", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/index.mu`,
                isLoadingNodePage: false,
                nodePageContent: "#!bg=444\nHello",
                isShowingNodePageSource: false,
            });
            expect(wrapper.vm.micronHeaderBackgroundCss).toBe("#444");
            expect(wrapper.vm.nomadCrashTabBackground).toBe("#444");
        });

        it("passes source chrome for view-source mode", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/index.mu`,
                isLoadingNodePage: false,
                nodePageContent: ">#!\n# Hello",
                isShowingNodePageSource: true,
            });
            expect(wrapper.vm.nomadCrashTabContentClass).toContain("source");
            expect(wrapper.vm.nomadCrashTabBackground).toBe("#000000");
        });

        it("pads markdown full-bleed hosts without micron black chrome", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                nodePagePath: `${destHash}:/page/readme.md`,
                isLoadingNodePage: false,
                nodePageContent: "# Title",
                isShowingNodePageSource: false,
                pageShellBackground: "#112233",
            });
            expect(wrapper.vm.nomadCrashTabContentClass).toContain("nomad-markdown-host");
            expect(wrapper.vm.nomadCrashTabContentClass).toContain("pad");
            expect(wrapper.vm.nomadCrashTabContentClass).not.toContain("bg-black");
        });
    });

    describe("hasPageLoadFailed", () => {
        const destHash = "c".repeat(32);

        it("is false while loading even if content looks like an error string", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                isLoadingNodePage: true,
                nodePageContent: "Failed loading page: race",
            });
            expect(wrapper.vm.hasPageLoadFailed).toBe(false);
        });

        it("is false without selected node even if nodePageContent is an error string", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: null,
                isLoadingNodePage: false,
                nodePageContent: "Failed loading page: orphan",
            });
            expect(wrapper.vm.hasPageLoadFailed).toBe(false);
        });

        it("is true when idle, node selected, and content matches failure detection", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                isLoadingNodePage: false,
                nodePageContent: "Failed loading page: done",
            });
            expect(wrapper.vm.hasPageLoadFailed).toBe(true);
        });

        it("is false when idle with valid page prose mentioning failure", async () => {
            const wrapper = mountNomadNetworkPage();
            await wrapper.setData({
                selectedNode: { destination_hash: destHash, display_name: "N" },
                isLoadingNodePage: false,
                nodePageContent: "# Doc\nAvoid failure during deploy.",
            });
            expect(wrapper.vm.hasPageLoadFailed).toBe(false);
        });
    });

    describe("parseNomadnetworkUrl", () => {
        it("parses absolute URL with query string", () => {
            const wrapper = mountNomadNetworkPage();
            const dest = "a".repeat(32);
            const result = wrapper.vm.parseNomadnetworkUrl(`${dest}:/file/report.pdf?version=2&format=raw`);
            expect(result).toEqual({
                destination_hash: dest,
                path: "/file/report.pdf",
                query: "version=2&format=raw",
            });
        });

        it("parses relative URL with query string", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.defaultNodePagePath = "/page/index.mu";
            const result = wrapper.vm.parseNomadnetworkUrl(":/file/data.bin?key=val");
            expect(result).toEqual({
                destination_hash: null,
                path: "/file/data.bin",
                query: "key=val",
            });
        });

        it("parses node-only URL without query", () => {
            const wrapper = mountNomadNetworkPage();
            const dest = "b".repeat(32);
            const result = wrapper.vm.parseNomadnetworkUrl(dest);
            expect(result).toEqual({
                destination_hash: dest,
                path: wrapper.vm.defaultNodePagePath,
                query: null,
            });
        });

        it("parses absolute URL without query", () => {
            const wrapper = mountNomadNetworkPage();
            const dest = "c".repeat(32);
            const result = wrapper.vm.parseNomadnetworkUrl(`${dest}:/page/index.mu`);
            expect(result).toEqual({
                destination_hash: dest,
                path: "/page/index.mu",
                query: null,
            });
        });

        it("returns null for unsupported URL", () => {
            const wrapper = mountNomadNetworkPage();
            expect(wrapper.vm.parseNomadnetworkUrl("not-a-url")).toBeNull();
        });

        it("handles empty query string after ?", () => {
            const wrapper = mountNomadNetworkPage();
            const dest = "d".repeat(32);
            const result = wrapper.vm.parseNomadnetworkUrl(`${dest}:/file/x.txt?`);
            expect(result.path).toBe("/file/x.txt");
            expect(result.query).toBe("");
        });
    });

    describe("downloadNomadNetFile", () => {
        let WebSocketConnection;

        beforeEach(async () => {
            // Re-import to get the mocked module
            WebSocketConnection = (await import("@/js/WebSocketConnection")).default;
            WebSocketConnection.send.mockClear();
        });

        it("includes data in websocket payload when provided", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.downloadNomadNetFile(
                "a".repeat(32),
                "/file/data.bin",
                "version=2&format=raw",
                vi.fn(),
                vi.fn(),
                vi.fn()
            );
            expect(WebSocketConnection.send).toHaveBeenCalledOnce();
            const payload = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
            expect(payload.type).toBe("nomadnet.file.download");
            expect(payload.nomadnet_file_download.data).toBe("version=2&format=raw");
        });

        it("omits data field when data is null", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.downloadNomadNetFile("b".repeat(32), "/file/data.bin", null, vi.fn(), vi.fn(), vi.fn());
            const payload = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
            expect(payload.nomadnet_file_download).not.toHaveProperty("data");
        });

        it("omits data field when data is undefined", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.downloadNomadNetFile("c".repeat(32), "/file/data.bin", undefined, vi.fn(), vi.fn(), vi.fn());
            const payload = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
            expect(payload.nomadnet_file_download).not.toHaveProperty("data");
        });
    });

    describe("browser context menu actions", () => {
        it("showPageSource enables source view when a page is loaded", () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.selectedNode = { destination_hash: "a".repeat(32), display_name: "Node" };
            wrapper.vm.nodePagePath = `${"a".repeat(32)}:/page/index.mu`;
            wrapper.vm.isShowingNodePageSource = false;
            expect(wrapper.vm.showPageSource()).toBe(true);
            expect(wrapper.vm.isShowingNodePageSource).toBe(true);
        });

        it("showPageSource warns when no page path is loaded", () => {
            const wrapper = mountNomadNetworkPage();
            expect(wrapper.vm.showPageSource()).toBe(false);
            expect(ToastUtils.warning).toHaveBeenCalledWith("nomadnet.view_source_unavailable");
        });

        it("downloadPageToDisk saves current page content", async () => {
            const DownloadUtils = (await import("@/js/DownloadUtils")).default;
            const downloadFile = vi.spyOn(DownloadUtils, "downloadFile").mockResolvedValue(undefined);
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.selectedNode = { destination_hash: "a".repeat(32), display_name: "Node" };
            wrapper.vm.nodePagePath = `${"a".repeat(32)}:/page/index.mu`;
            wrapper.vm.nodePageContent = "Hello Nomad";
            expect(await wrapper.vm.downloadPageToDisk()).toBe(true);
            expect(downloadFile).toHaveBeenCalledWith("index.mu", expect.any(Blob));
            expect(ToastUtils.success).toHaveBeenCalledWith("nomadnet.download_page_started");
            downloadFile.mockRestore();
        });

        it("downloadPageToDisk warns when page content is unavailable", async () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.nodePagePath = `${"a".repeat(32)}:/page/index.mu`;
            wrapper.vm.nodePageContent = null;
            expect(await wrapper.vm.downloadPageToDisk()).toBe(false);
            expect(ToastUtils.warning).toHaveBeenCalledWith("nomadnet.download_page_unavailable");
        });

        it("downloadPageToDisk reports download failures", async () => {
            const DownloadUtils = (await import("@/js/DownloadUtils")).default;
            const downloadFile = vi.spyOn(DownloadUtils, "downloadFile").mockRejectedValue(new Error("disk full"));
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.nodePagePath = `${"a".repeat(32)}:/page/index.mu`;
            wrapper.vm.nodePageContent = "Hello Nomad";
            expect(await wrapper.vm.downloadPageToDisk()).toBe(false);
            expect(ToastUtils.error).toHaveBeenCalledWith("nomadnet.download_page_failed");
            downloadFile.mockRestore();
        });

        it("toggleFavouriteFromContext adds favourite and toasts success", async () => {
            axiosMock.post.mockResolvedValueOnce({ data: {} });
            axiosMock.get.mockResolvedValueOnce({ data: { favourites: [] } });
            const wrapper = mountNomadNetworkPage();
            const node = { destination_hash: "a".repeat(32), display_name: "Node" };
            wrapper.vm.selectedNode = node;
            wrapper.vm.favourites = [];
            expect(await wrapper.vm.toggleFavouriteFromContext()).toBe(true);
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/favourites/add", {
                destination_hash: node.destination_hash,
                display_name: node.display_name,
                aspect: "nomadnetwork.node",
            });
            expect(ToastUtils.success).toHaveBeenCalledWith("nomadnet.favourite_added");
        });

        it("resolveNodeForHash prefers favourite name over Unknown Node stub", () => {
            const wrapper = mountNomadNetworkPage();
            const hash = "a".repeat(32);
            wrapper.vm.nodes = {};
            wrapper.vm.favourites = [{ destination_hash: hash, display_name: "Saved Favourite" }];
            const resolved = wrapper.vm.resolveNodeForHash(hash);
            expect(resolved.display_name).toBe("Saved Favourite");
            expect(resolved.destination_hash).toBe(hash);
        });

        it("addFavourite does not overwrite existing favourite with Unknown Node", async () => {
            axiosMock.post.mockResolvedValueOnce({ data: {} });
            axiosMock.get.mockResolvedValueOnce({ data: { favourites: [] } });
            const wrapper = mountNomadNetworkPage();
            const hash = "a".repeat(32);
            wrapper.vm.favourites = [{ destination_hash: hash, display_name: "Kept Name" }];
            await wrapper.vm.addFavourite({
                destination_hash: hash,
                display_name: "Unknown Node",
            });
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/favourites/add", {
                destination_hash: hash,
                display_name: "Kept Name",
                aspect: "nomadnetwork.node",
            });
        });

        it("addFavourite canonicalizes localized unknown names for new favourites", async () => {
            axiosMock.post.mockResolvedValueOnce({ data: {} });
            axiosMock.get.mockResolvedValueOnce({ data: { favourites: [] } });
            const wrapper = mountNomadNetworkPage();
            const hash = "b".repeat(32);
            wrapper.vm.favourites = [];
            await wrapper.vm.addFavourite({
                destination_hash: hash,
                display_name: "Unbekannter Knoten",
            });
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/favourites/add", {
                destination_hash: hash,
                display_name: "Unknown Node",
                aspect: "nomadnetwork.node",
            });
        });

        it("onNodeClick resolves favourite names through announce cache", async () => {
            const wrapper = mountNomadNetworkPage();
            const hash = "c".repeat(32);
            wrapper.vm.nodes = {
                [hash]: {
                    destination_hash: hash,
                    display_name: "From Announce",
                    aspect: "nomadnetwork.node",
                },
            };
            wrapper.vm.favourites = [{ destination_hash: hash, display_name: "Unknown Node" }];
            const loadSpy = vi.spyOn(wrapper.vm, "loadNodePage").mockResolvedValue();
            wrapper.vm.onNodeClick({ destination_hash: hash, display_name: "Unknown Node" });
            expect(wrapper.vm.selectedNode.display_name).toBe("From Announce");
            expect(loadSpy).toHaveBeenCalledWith(hash, wrapper.vm.defaultNodePagePath);
            loadSpy.mockRestore();
        });

        it("onBulkAddFavouritesFromAnnounces uses canonical unknown sentinel", async () => {
            axiosMock.post.mockResolvedValue({ data: {} });
            axiosMock.get.mockResolvedValue({ data: { favourites: [] } });
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.favourites = [];
            const hash = "d".repeat(32);
            await wrapper.vm.onBulkAddFavouritesFromAnnounces([{ destination_hash: hash, display_name: "未知节点" }]);
            expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/favourites/add", {
                destination_hash: hash,
                display_name: "Unknown Node",
                aspect: "nomadnetwork.node",
            });
        });

        it("toggleFavouriteFromContext reports API failures", async () => {
            axiosMock.post.mockRejectedValueOnce(new Error("network"));
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.selectedNode = { destination_hash: "a".repeat(32), display_name: "Node" };
            wrapper.vm.favourites = [];
            expect(await wrapper.vm.toggleFavouriteFromContext()).toBe(false);
            expect(ToastUtils.error).toHaveBeenCalledWith("nomadnet.context_menu_favourite_failed");
        });

        it("onPageContextMenu delegates to browser tab actions when embedded", () => {
            const openContextMenu = vi.fn();
            const wrapper = mountNomadNetworkPage({ destinationHash: "", embedded: true });
            wrapper.vm.nomadBrowserTabActions = { openContextMenu };
            const event = { clientX: 4, clientY: 8 };
            wrapper.vm.onPageContextMenu(event);
            expect(openContextMenu).toHaveBeenCalledWith(event);
        });

        it("runStandaloneContextAction closes menu after failures", async () => {
            const wrapper = mountNomadNetworkPage();
            wrapper.vm.standaloneContextMenu.show = true;
            await wrapper.vm.runStandaloneContextAction(() => {
                throw new Error("boom");
            });
            expect(ToastUtils.error).toHaveBeenCalledWith("nomadnet.context_menu_action_failed");
            expect(wrapper.vm.standaloneContextMenu.show).toBe(false);
        });
    });

    describe("embedded tab websocket isolation", () => {
        const hashA = "a".repeat(32);
        const hashB = "b".repeat(32);
        const pagePath = "/page/index.mu";

        const emitPageDownload = (destinationHash, status, extra = {}) => ({
            data: JSON.stringify({
                type: "nomadnet.page.download",
                download_id: 42,
                nomadnet_page_download: {
                    destination_hash: destinationHash,
                    page_path: pagePath,
                    status,
                    page_content: "<p>other tab</p>",
                    ...extra,
                },
            }),
        });

        it("inactive embedded instance ignores another tab's archived page download", async () => {
            const active = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: true,
            });
            const inactive = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: false,
            });
            await active.vm.$nextTick();
            await inactive.vm.$nextTick();

            active.vm.selectedNode = { destination_hash: hashA, display_name: "A" };
            active.vm.nodePagePath = `${hashA}:${pagePath}`;
            active.vm.nodePageContent = "<p>tab a</p>";

            inactive.vm.selectedNode = { destination_hash: hashA, display_name: "A" };
            inactive.vm.nodePagePath = `${hashA}:${pagePath}`;
            inactive.vm.nodePageContent = "<p>tab a copy</p>";

            await inactive.vm.onWebsocketMessage(emitPageDownload(hashB, "success", { is_archived_version: true }));

            expect(active.vm.nodePageContent).toBe("<p>tab a</p>");
            expect(inactive.vm.nodePageContent).toBe("<p>tab a copy</p>");
            active.unmount();
            inactive.unmount();
        });

        it("inactive embedded instance ignores started events without a callback", async () => {
            const inactive = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: false,
            });
            await inactive.vm.$nextTick();
            inactive.vm.selectedNode = { destination_hash: hashA, display_name: "A" };
            inactive.vm.nodePagePath = `${hashA}:${pagePath}`;
            inactive.vm.nodePageContent = "<p>stable</p>";

            await inactive.vm.onWebsocketMessage(emitPageDownload(hashB, "started"));

            expect(inactive.vm.currentPageDownloadId).toBeNull();
            expect(inactive.vm.nodePageLoadPhase).toBeNull();
            expect(inactive.vm.nodePageContent).toBe("<p>stable</p>");
            inactive.unmount();
        });

        it("active instance with callback still receives page download success", async () => {
            const wrapper = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: true,
            });
            await wrapper.vm.$nextTick();

            const onSuccess = vi.fn();
            wrapper.vm.nomadnetPageDownloadCallbacks[`${hashB}:${pagePath}`] = {
                onSuccessCallback: onSuccess,
            };

            await wrapper.vm.onWebsocketMessage(emitPageDownload(hashB, "success"));

            expect(onSuccess).toHaveBeenCalledWith("<p>other tab</p>");
            wrapper.unmount();
        });
    });

    describe("archive load ownership", () => {
        it("loadArchivedPage sets currentPageDownloadId so path-mismatched replies still apply", async () => {
            const WebSocketConnection = (await import("@/js/WebSocketConnection")).default;
            WebSocketConnection.send.mockReturnValue(true);

            const wrapper = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: true,
            });
            await wrapper.vm.$nextTick();

            const oldHash = "a".repeat(32);
            const archiveHash = "b".repeat(32);
            wrapper.vm.selectedNode = { destination_hash: oldHash, display_name: "A" };
            wrapper.vm.nodePagePath = `${oldHash}:/page/index.mu`;
            wrapper.vm.pageArchives = [];

            wrapper.vm.loadArchivedPage(99);

            expect(wrapper.vm.isLoadingNodePage).toBe(true);
            expect(wrapper.vm.currentPageDownloadId).toEqual(expect.any(Number));
            const downloadId = wrapper.vm.currentPageDownloadId;

            expect(
                wrapper.vm.ownsNomadPageDownloadEvent(
                    {
                        destination_hash: archiveHash,
                        page_path: "/page/old.mu",
                    },
                    downloadId
                )
            ).toBe(true);

            await wrapper.vm.onWebsocketMessage({
                data: JSON.stringify({
                    type: "nomadnet.page.download",
                    download_id: downloadId,
                    nomadnet_page_download: {
                        status: "success",
                        destination_hash: archiveHash,
                        page_path: "/page/old.mu",
                        page_content: "<p>from archive</p>",
                        is_archived_version: true,
                        archived_at: "2026-01-01T00:00:00",
                    },
                }),
            });

            expect(wrapper.vm.isLoadingNodePage).toBe(false);
            expect(wrapper.vm.nodePageContent).toBe("<p>from archive</p>");
            expect(wrapper.vm.currentPageDownloadId).toBeNull();
            wrapper.unmount();
        });

        it("archive load failure clears the stuck spinner without a download callback", async () => {
            const wrapper = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: true,
            });
            await wrapper.vm.$nextTick();
            wrapper.vm.isLoadingNodePage = true;
            wrapper.vm.currentPageDownloadId = 4242;
            wrapper.vm.nodePagePath = `${"c".repeat(32)}:/page/index.mu`;

            await wrapper.vm.onWebsocketMessage({
                data: JSON.stringify({
                    type: "nomadnet.page.download",
                    download_id: 4242,
                    nomadnet_page_download: {
                        status: "failure",
                        destination_hash: "",
                        page_path: "",
                        failure_reason: "archive not found",
                    },
                }),
            });

            expect(wrapper.vm.isLoadingNodePage).toBe(false);
            expect(wrapper.vm.currentPageDownloadId).toBeNull();
            expect(wrapper.vm.nodePageContent).toContain("archive not found");
            expect(ToastUtils.error).toHaveBeenCalled();
            wrapper.unmount();
        });

        it("page download failure toasts failed_to_load_page instead of hanging", async () => {
            const wrapper = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: true,
            });
            await wrapper.vm.$nextTick();
            wrapper.vm.isLoadingNodePage = true;
            wrapper.vm.currentPageDownloadId = 4243;
            wrapper.vm.nodePagePath = `${"c".repeat(32)}:/page/index.mu`;

            await wrapper.vm.onWebsocketMessage({
                data: JSON.stringify({
                    type: "nomadnet.page.download",
                    download_id: 4243,
                    nomadnet_page_download: {
                        status: "failure",
                        destination_hash: "",
                        page_path: "",
                        failure_reason: "request_failed",
                    },
                }),
            });

            expect(wrapper.vm.isLoadingNodePage).toBe(false);
            expect(ToastUtils.error).toHaveBeenCalledWith("nomadnet.failed_to_load_page");
            wrapper.unmount();
        });
    });

    describe("websocket send race", () => {
        it("queues primary download until websocket connects instead of hanging on Loading page", async () => {
            const WebSocketConnection = (await import("@/js/WebSocketConnection")).default;
            WebSocketConnection.send.mockReset();
            WebSocketConnection.send.mockImplementationOnce(() => false).mockImplementation(() => true);
            WebSocketConnection.isOpen.mockReturnValue(false);

            const wrapper = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: true,
            });
            await wrapper.vm.$nextTick();

            const hash = "d".repeat(32);
            const path = "/page/index.mu";
            wrapper.vm.isLoadingNodePage = true;
            wrapper.vm.nodePagePath = `${hash}:${path}`;

            const onSuccess = vi.fn();
            const onFailure = vi.fn();
            wrapper.vm.downloadNomadNetPage(hash, path, null, onSuccess, onFailure, null, { primary: true });

            expect(WebSocketConnection.send).toHaveBeenCalledTimes(1);
            expect(wrapper.vm.isLoadingNodePage).toBe(true);
            expect(onFailure).not.toHaveBeenCalled();
            expect(wsEventHandlers.connected?.length || 0).toBeGreaterThan(0);

            WebSocketConnection.isOpen.mockReturnValue(true);
            for (const handler of [...(wsEventHandlers.connected || [])]) {
                handler();
            }

            expect(WebSocketConnection.send).toHaveBeenCalledTimes(2);
            expect(onFailure).not.toHaveBeenCalled();
            expect(wrapper.vm.nomadnetPageDownloadCallbacks[`${hash}:${path}`]).toBeTruthy();
            wrapper.unmount();
        });

        it("partial started events do not overwrite primary currentPageDownloadId", async () => {
            const wrapper = mountNomadNetworkPage({
                destinationHash: "",
                embedded: true,
                isActive: true,
            });
            await wrapper.vm.$nextTick();

            const hash = "e".repeat(32);
            const mainPath = "/page/index.mu";
            const partialPath = "/page/partial.mu";
            wrapper.vm.nodePagePath = `${hash}:${mainPath}`;
            wrapper.vm.nomadnetPageDownloadCallbacks[`${hash}:${mainPath}`] = {
                primary: true,
                onSuccessCallback: vi.fn(),
                onFailureCallback: vi.fn(),
            };
            wrapper.vm.nomadnetPageDownloadCallbacks[`${hash}:${partialPath}`] = {
                primary: false,
                onSuccessCallback: vi.fn(),
                onFailureCallback: vi.fn(),
            };
            wrapper.vm.currentPageDownloadId = 100;

            await wrapper.vm.onWebsocketMessage({
                data: JSON.stringify({
                    type: "nomadnet.page.download",
                    download_id: 200,
                    nomadnet_page_download: {
                        status: "started",
                        destination_hash: hash,
                        page_path: partialPath,
                    },
                }),
            });

            expect(wrapper.vm.currentPageDownloadId).toBe(100);
            wrapper.unmount();
        });
    });

    describe("private browsing guards", () => {
        let WebSocketConnection;

        beforeEach(async () => {
            WebSocketConnection = (await import("@/js/WebSocketConnection")).default;
            WebSocketConnection.send.mockClear();
        });

        it("page and file downloads mark private true", () => {
            const wrapper = mountNomadNetworkPage({ destinationHash: "", isPrivate: true });
            wrapper.vm.downloadNomadNetPage("a".repeat(32), "/page/index.mu", null, vi.fn(), vi.fn(), vi.fn());
            const pagePayload = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
            expect(pagePayload.nomadnet_page_download.private).toBe(true);

            WebSocketConnection.send.mockClear();
            wrapper.vm.downloadNomadNetFile("a".repeat(32), "/file/x.bin", null, vi.fn(), vi.fn(), vi.fn());
            const filePayload = JSON.parse(WebSocketConnection.send.mock.calls[0][0]);
            expect(filePayload.nomadnet_file_download.private).toBe(true);
            wrapper.unmount();
        });

        it("blocks identify, archive, and favourites without sending requests", async () => {
            const wrapper = mountNomadNetworkPage({ destinationHash: "", isPrivate: true });
            wrapper.vm.selectedNode = { destination_hash: "a".repeat(32), display_name: "Node" };
            wrapper.vm.nodePagePath = `${"a".repeat(32)}:/page/index.mu`;
            wrapper.vm.nodePageContent = "# hi";

            await wrapper.vm.identify("a".repeat(32));
            expect(axiosMock.post).not.toHaveBeenCalledWith(expect.stringContaining("/identify"), expect.anything());
            expect(ToastUtils.info).toHaveBeenCalledWith("nomadnet.private_browsing_hint");

            WebSocketConnection.send.mockClear();
            wrapper.vm.manualArchive();
            expect(WebSocketConnection.send).not.toHaveBeenCalled();

            WebSocketConnection.send.mockClear();
            wrapper.vm.fetchArchives();
            expect(WebSocketConnection.send).not.toHaveBeenCalled();

            const favOk = await wrapper.vm.addFavourite(wrapper.vm.selectedNode);
            expect(favOk).toBe(false);
            expect(axiosMock.post).not.toHaveBeenCalledWith("/api/v1/favourites/add", expect.anything());
            wrapper.unmount();
        });

        it("hides identify and archive controls in the header", () => {
            const wrapper = mountNomadNetworkPage({ destinationHash: "a".repeat(32), isPrivate: true });
            wrapper.vm.selectedNode = { destination_hash: "a".repeat(32), display_name: "Node" };
            wrapper.vm.nodePageContent = "# hi";
            wrapper.vm.nodePagePath = `${"a".repeat(32)}:/page/index.mu`;
            expect(wrapper.find('[title="nomadnet.identify"]').exists()).toBe(false);
            expect(wrapper.find('[title="app.archives"]').exists()).toBe(false);
            wrapper.unmount();
        });
    });
});
