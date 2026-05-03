import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MicronParser from "@/js/MicronParser.js";

// Mock vuetify components before importing the component under test
vi.mock("vuetify/components/VTooltip", () => ({
    VTooltip: {
        name: "VTooltip",
        template: '<div class="v-tooltip-stub"><slot /></div>',
    },
}));

import NomadNetworkPage from "@/components/nomadnetwork/NomadNetworkPage.vue";

vi.mock("@/js/WebSocketConnection", () => ({
    default: {
        send: vi.fn(),
        on: vi.fn(),
        off: vi.fn(),
    },
}));

describe("NomadNetworkPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
        };
        window.api = axiosMock;

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
            wrapper.vm.isShowingNodePageSource = false;

            const downloadSpy = vi
                .spyOn(wrapper.vm, "downloadNomadNetPage")
                .mockImplementation((_d, _p, _f, onSuccess) => {
                    onSuccess("# ok");
                });

            await wrapper.vm.$nextTick();
            await wrapper.vm.$nextTick();

            wrapper.vm.processPartials();
            await wrapper.vm.$nextTick();

            const afterFirst = downloadSpy.mock.calls.length;
            expect(afterFirst).toBeGreaterThanOrEqual(1);

            wrapper.vm.processPartials();
            await wrapper.vm.$nextTick();

            expect(downloadSpy.mock.calls.length).toBe(afterFirst);

            downloadSpy.mockRestore();
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
});
