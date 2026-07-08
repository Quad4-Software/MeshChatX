import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/components/nomadnetwork/NomadNetworkPage.vue", () => ({
    default: {
        name: "NomadNetworkPage",
        template: '<div class="nnp-stub" :data-hash="destinationHash" :data-active="isActive ? \'1\' : \'0\'"></div>',
        props: {
            destinationHash: { type: String, default: "" },
            initialPath: { type: String, default: null },
            embedded: { type: Boolean, default: false },
            tabsEnabled: { type: Boolean, default: false },
            isActive: { type: Boolean, default: true },
        },
        emits: ["navigate", "open-node", "close-tab"],
        methods: {
            getEmbeddedTabStateHash() {
                return this._stateHash || "";
            },
            restoreEmbeddedTabState(hash) {
                this._stateHash = hash;
            },
        },
    },
}));

import NomadNetworkBrowser from "@/components/nomadnetwork/NomadNetworkBrowser.vue";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

const MaterialDesignIconStub = {
    name: "MaterialDesignIcon",
    template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
    props: ["iconName"],
};

describe("NomadNetworkBrowser.vue", () => {
    let routerReplace;
    let routerPush;

    const mountBrowser = (props = {}, route = { name: "nomadnetwork", params: {}, query: {} }) => {
        routerReplace = vi.fn(() => Promise.resolve());
        routerPush = vi.fn(() => Promise.resolve());
        return mount(NomadNetworkBrowser, {
            props,
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { name: "nomadnetwork", ...route },
                    $router: { replace: routerReplace, push: routerPush },
                },
                stubs: {
                    MaterialDesignIcon: MaterialDesignIconStub,
                },
            },
        });
    };

    beforeEach(() => {
        localStorage.clear();
        routerReplace = undefined;
        routerPush = undefined;
        vi.clearAllMocks();
    });

    it("creates a single tab on mount", () => {
        const wrapper = mountBrowser();
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.activeTabId).toBe(wrapper.vm.tabs[0].id);
    });

    it("seeds the first tab from the route destination hash and path", () => {
        const dest = "a".repeat(32);
        const wrapper = mountBrowser({}, { params: { destinationHash: dest }, query: { path: "/page/info.mu" } });
        expect(wrapper.vm.tabs[0].destinationHash).toBe(dest);
        expect(wrapper.vm.tabs[0].initialPath).toBe("/page/info.mu");
    });

    it("addTab creates and activates a new empty tab", () => {
        const wrapper = mountBrowser();
        const before = wrapper.vm.tabs.length;
        const id = wrapper.vm.addTab();
        expect(wrapper.vm.tabs).toHaveLength(before + 1);
        expect(wrapper.vm.activeTabId).toBe(id);
        expect(wrapper.vm.tabs.find((t) => t.id === id).destinationHash).toBe("");
    });

    it("onTabNavigate updates destination hash and title for the tab", () => {
        const wrapper = mountBrowser();
        const tab = wrapper.vm.tabs[0];
        wrapper.vm.onTabNavigate(tab.id, {
            destinationHash: "b".repeat(32),
            pagePath: "/page/index.mu",
            title: "My Node",
        });
        expect(tab.destinationHash).toBe("b".repeat(32));
        expect(tab.title).toBe("My Node");
    });

    it("tabTitle falls back to the new tab label and short hash", () => {
        const wrapper = mountBrowser();
        expect(wrapper.vm.tabTitle({ destinationHash: "", title: null })).toBe("nomadnet.new_tab");
        expect(wrapper.vm.tabTitle({ destinationHash: "c".repeat(32), title: null })).toBe("cccccccccccc");
        expect(wrapper.vm.tabTitle({ destinationHash: "c".repeat(32), title: "Named" })).toBe("Named");
    });

    it("closeTab activates a neighbour and never leaves zero tabs", () => {
        const wrapper = mountBrowser();
        const first = wrapper.vm.tabs[0].id;
        const second = wrapper.vm.addTab("d".repeat(32));
        expect(wrapper.vm.tabs).toHaveLength(2);

        wrapper.vm.closeTab(second);
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.activeTabId).toBe(first);

        wrapper.vm.closeTab(first);
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.activeTabId).toBe(wrapper.vm.tabs[0].id);
    });

    it("shows the tab strip only on wide viewports", async () => {
        const wrapper = mountBrowser();
        wrapper.vm.isWideViewport = false;
        await wrapper.vm.$nextTick();
        expect(wrapper.find('[role="tablist"]').exists()).toBe(false);

        wrapper.vm.isWideViewport = true;
        await wrapper.vm.$nextTick();
        expect(wrapper.find('[role="tablist"]').exists()).toBe(true);
    });

    it("selectTab syncs the route to the active tab destination hash", () => {
        const wrapper = mountBrowser();
        const second = wrapper.vm.addTab("e".repeat(32));
        routerReplace.mockClear();

        wrapper.vm.activeTabId = wrapper.vm.tabs[0].id;
        wrapper.vm.selectTab(second);

        expect(wrapper.vm.activeTabId).toBe(second);
        expect(routerReplace).toHaveBeenCalled();
        const arg = routerReplace.mock.calls[routerReplace.mock.calls.length - 1][0];
        expect(arg.name).toBe("nomadnetwork");
        expect(arg.params.destinationHash).toBe("e".repeat(32));
    });

    it("hides the tab strip when tabs are disabled in config", async () => {
        const wrapper = mountBrowser();
        wrapper.vm.isWideViewport = true;
        await wrapper.vm.$nextTick();
        expect(wrapper.find('[role="tablist"]').exists()).toBe(true);

        wrapper.vm.GlobalState.config.nomad_tabs_enabled = false;
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.tabsEnabled).toBe(false);
        expect(wrapper.find('[role="tablist"]').exists()).toBe(false);

        wrapper.vm.GlobalState.config.nomad_tabs_enabled = true;
    });

    it("persists tab layout to localStorage when tabs change", async () => {
        const wrapper = mountBrowser();
        wrapper.vm.onTabNavigate(wrapper.vm.tabs[0].id, {
            destinationHash: "a".repeat(32),
            pagePath: "/page/index.mu",
            title: "Node A",
        });
        wrapper.vm.addTab("b".repeat(32), "/page/b.mu", "Node B");
        await wrapper.vm.$nextTick();

        const saved = JSON.parse(localStorage.getItem("meshchatx.nomadnet.tabs"));
        expect(saved.tabs).toHaveLength(2);
        expect(saved.tabs[0]).toMatchObject({
            destinationHash: "a".repeat(32),
            path: "/page/index.mu",
            title: "Node A",
        });
        expect(saved.activeIndex).toBe(1);
    });

    it("restores persisted tabs on mount instead of seeding a single tab", () => {
        localStorage.setItem(
            "meshchatx.nomadnet.tabs",
            JSON.stringify({
                tabs: [
                    { destinationHash: "a".repeat(32), path: "/page/index.mu", title: "Node A" },
                    { destinationHash: "b".repeat(32), path: "/page/b.mu", title: "Node B" },
                ],
                activeIndex: 1,
            })
        );

        const wrapper = mountBrowser();
        expect(wrapper.vm.tabs).toHaveLength(2);
        expect(wrapper.vm.tabs[0].destinationHash).toBe("a".repeat(32));
        expect(wrapper.vm.tabs[0].initialPath).toBe("/page/index.mu");
        expect(wrapper.vm.activeTabId).toBe(wrapper.vm.tabs[1].id);
    });

    it("focuses the matching restored tab when the route targets a saved node", () => {
        localStorage.setItem(
            "meshchatx.nomadnet.tabs",
            JSON.stringify({
                tabs: [
                    { destinationHash: "a".repeat(32), path: "/page/index.mu", title: "Node A" },
                    { destinationHash: "b".repeat(32), path: "/page/b.mu", title: "Node B" },
                ],
                activeIndex: 0,
            })
        );

        const wrapper = mountBrowser({}, { params: { destinationHash: "b".repeat(32) }, query: {} });
        expect(wrapper.vm.tabs).toHaveLength(2);
        expect(wrapper.vm.activeTab.destinationHash).toBe("b".repeat(32));
    });

    it("only mounts the active tab page when multiple tabs are restored", async () => {
        localStorage.setItem(
            "meshchatx.nomadnet.tabs",
            JSON.stringify({
                tabs: [
                    { destinationHash: "a".repeat(32), path: null, title: "Alpha" },
                    { destinationHash: "b".repeat(32), path: null, title: "Bravo" },
                ],
                activeIndex: 1,
            })
        );

        const wrapper = mountBrowser({}, { params: { destinationHash: "b".repeat(32) }, query: {} });
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.tabs).toHaveLength(2);
        expect(wrapper.findAllComponents({ name: "NomadNetworkPage" })).toHaveLength(1);
        expect(wrapper.vm.activeTab.destinationHash).toBe("b".repeat(32));
    });

    it("renders one embedded NomadNetworkPage per activated tab", async () => {
        const wrapper = mountBrowser();
        wrapper.vm.addTab("f".repeat(32));
        await wrapper.vm.$nextTick();
        expect(wrapper.findAllComponents({ name: "NomadNetworkPage" })).toHaveLength(2);
        expect(wrapper.findComponent({ name: "NomadNetworkPage" }).props("embedded")).toBe(true);
    });

    it("onOpenNode creates and activates a new tab for the node", () => {
        const wrapper = mountBrowser();
        const first = wrapper.vm.activeTabId;
        wrapper.vm.onOpenNode({
            destinationHash: "g".repeat(32),
            pagePath: "/page/index.mu",
            title: "Remote Node",
            activate: true,
        });
        expect(wrapper.vm.tabs).toHaveLength(2);
        expect(wrapper.vm.activeTabId).not.toBe(first);
        expect(wrapper.vm.activeTab.destinationHash).toBe("g".repeat(32));
        expect(wrapper.vm.activeTab.initialPath).toBe("/page/index.mu");
        expect(wrapper.vm.activeTab.title).toBe("Remote Node");
    });

    it("onOpenNode focuses an existing tab when the node is already open", () => {
        const wrapper = mountBrowser();
        const existingHash = "g".repeat(32);
        const existingTabId = wrapper.vm.addTab(existingHash, "/page/index.mu", "Remote Node");
        wrapper.vm.addTab("h".repeat(32));
        expect(wrapper.vm.tabs).toHaveLength(3);
        expect(wrapper.vm.activeTabId).not.toBe(existingTabId);

        wrapper.vm.onOpenNode({
            destinationHash: existingHash,
            pagePath: "/page/other.mu",
            title: "Remote Node",
            activate: true,
        });

        expect(wrapper.vm.tabs).toHaveLength(3);
        expect(wrapper.vm.activeTabId).toBe(existingTabId);
        expect(wrapper.vm.activeTab.destinationHash).toBe(existingHash);
    });

    it("onOpenNode still creates a duplicate tab when forceNewTab is set", () => {
        const wrapper = mountBrowser();
        const existingHash = "g".repeat(32);
        wrapper.vm.addTab(existingHash, "/page/index.mu", "Remote Node");
        expect(wrapper.vm.tabs).toHaveLength(2);
        wrapper.vm.onOpenNode({
            destinationHash: existingHash,
            pagePath: "/page/other.mu",
            title: "Remote Node",
            activate: true,
            forceNewTab: true,
        });
        expect(wrapper.vm.tabs).toHaveLength(3);
    });

    it("onOpenNode can open a background tab without switching focus", () => {
        const wrapper = mountBrowser();
        const first = wrapper.vm.activeTabId;
        wrapper.vm.onOpenNode({
            destinationHash: "h".repeat(32),
            pagePath: "/page/index.mu",
            title: "Background",
            activate: false,
        });
        expect(wrapper.vm.tabs).toHaveLength(2);
        expect(wrapper.vm.activeTabId).toBe(first);
    });

    it("Ctrl+T opens a new tab when tabs are enabled", () => {
        const wrapper = mountBrowser();
        const before = wrapper.vm.tabs.length;
        window.dispatchEvent(
            new KeyboardEvent("keydown", { key: "t", ctrlKey: true, bubbles: true, cancelable: true })
        );
        expect(wrapper.vm.tabs).toHaveLength(before + 1);
    });

    it("Ctrl+W closes the active tab when tabs are enabled", () => {
        const wrapper = mountBrowser();
        wrapper.vm.addTab("i".repeat(32));
        expect(wrapper.vm.tabs).toHaveLength(2);
        window.dispatchEvent(
            new KeyboardEvent("keydown", { key: "w", ctrlKey: true, bubbles: true, cancelable: true })
        );
        expect(wrapper.vm.tabs).toHaveLength(1);
    });

    it("Ctrl+Tab cycles to the next tab", () => {
        const wrapper = mountBrowser();
        const first = wrapper.vm.activeTabId;
        const second = wrapper.vm.addTab("j".repeat(32));
        wrapper.vm.activeTabId = first;

        window.dispatchEvent(
            new KeyboardEvent("keydown", { key: "Tab", ctrlKey: true, bubbles: true, cancelable: true })
        );
        expect(wrapper.vm.activeTabId).toBe(second);
    });

    it("Ctrl+1 switches to the first tab", () => {
        const wrapper = mountBrowser();
        const first = wrapper.vm.tabs[0].id;
        wrapper.vm.addTab("k".repeat(32));

        window.dispatchEvent(
            new KeyboardEvent("keydown", { key: "1", ctrlKey: true, bubbles: true, cancelable: true })
        );
        expect(wrapper.vm.activeTabId).toBe(first);
    });

    it("passes tabsEnabled to embedded NomadNetworkPage instances", async () => {
        const wrapper = mountBrowser();
        await wrapper.vm.$nextTick();
        expect(wrapper.findComponent({ name: "NomadNetworkPage" }).props("tabsEnabled")).toBe(true);
    });

    it("marks only the active embedded page as isActive", async () => {
        const wrapper = mountBrowser();
        const hashA = "a".repeat(32);
        const hashB = "b".repeat(32);
        wrapper.vm.onTabNavigate(wrapper.vm.tabs[0].id, {
            destinationHash: hashA,
            pagePath: "/page/index.mu",
            title: "Tab A",
        });
        const tabB = wrapper.vm.addTab(hashB, "/page/index.mu", "Tab B");
        await wrapper.vm.$nextTick();

        const pages = wrapper.findAllComponents({ name: "NomadNetworkPage" });
        expect(pages).toHaveLength(2);
        const activePage = pages.find((page) => page.props("isActive") === true);
        const inactivePage = pages.find((page) => page.props("isActive") === false);
        expect(activePage?.props("destinationHash")).toBe(hashB);
        expect(inactivePage?.props("destinationHash")).toBe(hashA);

        wrapper.vm.selectTab(wrapper.vm.tabs[0].id);
        await wrapper.vm.$nextTick();

        const pagesAfter = wrapper.findAllComponents({ name: "NomadNetworkPage" });
        expect(pagesAfter[0].props("isActive")).toBe(true);
        expect(pagesAfter[1].props("isActive")).toBe(false);
        expect(pagesAfter[0].props("destinationHash")).toBe(hashA);
    });

    it("keeps first tab metadata when opening a visualizer node in a new tab", async () => {
        const wrapper = mountBrowser();
        const hashA = "c".repeat(32);
        const hashB = "d".repeat(32);
        const firstTabId = wrapper.vm.tabs[0].id;
        wrapper.vm.onTabNavigate(firstTabId, {
            destinationHash: hashA,
            pagePath: "/page/index.mu",
            title: "First",
        });
        wrapper.vm.onOpenNode({
            destinationHash: hashB,
            pagePath: "/page/other.mu",
            title: "Visualizer Node",
            forceNewTab: true,
        });
        wrapper.vm.selectTab(firstTabId);
        await wrapper.vm.$nextTick();

        const firstTab = wrapper.vm.tabs.find((tab) => tab.id === firstTabId);
        expect(firstTab.destinationHash).toBe(hashA);
        expect(wrapper.vm.activeTabId).toBe(firstTabId);
    });

    it("handleNomadOpenNode from another route opens a new tab after navigation", async () => {
        const dest = "e".repeat(32);
        const wrapper = mountBrowser({}, { name: "network-visualiser", params: {}, query: {} });
        wrapper.vm.handleNomadOpenNode({ destinationHash: dest, forceNewTab: true });
        expect(routerPush).toHaveBeenCalledWith({
            name: "nomadnetwork",
            params: { destinationHash: dest },
            query: { newTab: "1" },
        });
        await routerPush.mock.results[0].value;
        wrapper.vm.$route = {
            name: "nomadnetwork",
            params: { destinationHash: dest },
            query: { newTab: "1" },
        };
        wrapper.vm.consumeNewTabRouteQuery(wrapper.vm.$route);
        expect(wrapper.vm.tabs).toHaveLength(2);
        expect(wrapper.vm.activeTab.destinationHash).toBe(dest);
    });

    it("verifyActiveTabPage restores mismatched embedded page state", async () => {
        const wrapper = mountBrowser();
        const hashA = "f".repeat(32);
        const hashB = "0".repeat(32);
        const tabId = wrapper.vm.tabs[0].id;
        wrapper.vm.onTabNavigate(tabId, { destinationHash: hashA, pagePath: "/page/index.mu" });
        wrapper.vm.pageRefs[tabId] = {
            getEmbeddedTabStateHash: () => hashB,
            restoreEmbeddedTabState: vi.fn(),
        };
        wrapper.vm.verifyActiveTabPage(wrapper.vm.tabs[0]);
        expect(wrapper.vm.pageRefs[tabId].restoreEmbeddedTabState).toHaveBeenCalledWith(hashA, "/page/index.mu");
        expect(ToastUtils.warning).toHaveBeenCalledWith("nomadnet.tab_content_mismatch");
    });

    it("selectTab warns when tab id is unknown", () => {
        const wrapper = mountBrowser();
        wrapper.vm.selectTab(99999);
        expect(ToastUtils.warning).toHaveBeenCalledWith("nomadnet.tab_switch_failed");
    });

    it("reorders tabs while dragging", () => {
        const wrapper = mountBrowser();
        wrapper.vm.addTab("a".repeat(32), null, "Tab A");
        wrapper.vm.addTab("b".repeat(32), null, "Tab B");
        const orderBefore = wrapper.vm.tabs.map((tab) => tab.title);

        wrapper.vm.onTabDragStart(0, { dataTransfer: { effectAllowed: "", setData: vi.fn() } });
        wrapper.vm.onTabDragOver(2);
        wrapper.vm.onTabDrop(2);

        expect(wrapper.vm.tabs.map((tab) => tab.title)).not.toEqual(orderBefore);
        expect(wrapper.vm.tabs[2].title).toBe(orderBefore[0]);
        expect(wrapper.vm.dragTabIndex).toBeNull();
    });

    it("closeTabsToRight removes tabs after the target tab", () => {
        const wrapper = mountBrowser();
        wrapper.vm.addTab("a".repeat(32), null, "A");
        wrapper.vm.addTab("b".repeat(32), null, "B");
        const first = wrapper.vm.tabs[0].id;
        expect(wrapper.vm.tabs).toHaveLength(3);
        wrapper.vm.closeTabsToRight(first);
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.tabs[0].id).toBe(first);
    });

    it("closeOtherTabs keeps only the target tab", () => {
        const wrapper = mountBrowser();
        wrapper.vm.addTab("a".repeat(32), null, "A");
        const middle = wrapper.vm.tabs[0].id;
        wrapper.vm.addTab("b".repeat(32), null, "B");
        wrapper.vm.closeOtherTabs(middle);
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.tabs[0].id).toBe(middle);
    });

    it("closeAllTabs resets to a single new tab", () => {
        const wrapper = mountBrowser();
        wrapper.vm.addTab("a".repeat(32), null, "A");
        wrapper.vm.addTab("b".repeat(32), null, "B");
        wrapper.vm.closeAllTabs();
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.tabs[0].destinationHash).toBe("");
    });

    describe("context menu", () => {
        it("openTabContextMenu selects tab and shows menu", () => {
            const wrapper = mountBrowser();
            wrapper.vm.addTab("a".repeat(32), null, "Tab A");
            const tab = wrapper.vm.tabs[1];
            wrapper.vm.openTabContextMenu({ clientX: 12, clientY: 34 }, tab);
            expect(wrapper.vm.activeTabId).toBe(tab.id);
            expect(wrapper.vm.contextMenu.show).toBe(true);
            expect(wrapper.vm.contextMenu.tabId).toBe(tab.id);
            expect(wrapper.vm.contextMenu.x).toBe(12);
            expect(wrapper.vm.contextMenu.y).toBe(34);
        });

        it("runContextPageAction warns when page ref is missing", async () => {
            const wrapper = mountBrowser();
            wrapper.vm.contextMenu.show = true;
            await wrapper.vm.runContextPageAction(() => Promise.resolve());
            expect(ToastUtils.warning).toHaveBeenCalledWith("nomadnet.context_menu_page_unavailable");
            expect(wrapper.vm.contextMenu.show).toBe(false);
        });

        it("runContextPageAction surfaces unexpected errors", async () => {
            const wrapper = mountBrowser();
            const tabId = wrapper.vm.tabs[0].id;
            wrapper.vm.pageRefs[tabId] = {
                reloadNodePage: vi.fn().mockRejectedValue(new Error("boom")),
            };
            wrapper.vm.contextMenu.tabId = tabId;
            await wrapper.vm.runContextPageAction((page) => page.reloadNodePage());
            expect(ToastUtils.error).toHaveBeenCalledWith("nomadnet.context_menu_action_failed");
            expect(wrapper.vm.contextMenu.show).toBe(false);
        });

        it("onContextFavorite delegates to page toggleFavouriteFromContext", async () => {
            const wrapper = mountBrowser();
            const tabId = wrapper.vm.tabs[0].id;
            const toggleFavouriteFromContext = vi.fn().mockResolvedValue(true);
            wrapper.vm.pageRefs[tabId] = { toggleFavouriteFromContext };
            wrapper.vm.contextMenu.tabId = tabId;
            await wrapper.vm.onContextFavorite();
            expect(toggleFavouriteFromContext).toHaveBeenCalledOnce();
            expect(wrapper.vm.contextMenu.show).toBe(false);
        });
    });
});
