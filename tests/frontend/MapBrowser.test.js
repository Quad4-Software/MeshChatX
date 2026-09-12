import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/js/TileCache", () => ({
    default: {
        getMapState: vi.fn().mockResolvedValue(null),
        setMapState: vi.fn().mockResolvedValue(),
        initPromise: Promise.resolve(),
    },
}));

vi.mock("@/components/map/MapPage.vue", () => ({
    default: {
        name: "MapPage",
        template: '<div class="map-page-stub" :data-storage-id="tabStorageId"></div>',
        props: {
            embedded: { type: Boolean, default: false },
            tabStorageId: { type: String, default: "" },
            tabTitle: { type: String, default: "" },
            isActiveTab: { type: Boolean, default: true },
        },
        emits: ["update-title"],
    },
}));

import TileCache from "@/js/TileCache";
import MapBrowser from "@/components/map/MapBrowser.vue";
import { mapViewStateKey } from "@/js/mapStateKeys.js";
import { useConfigStore } from "@/js/stores/configStore.js";

const MaterialDesignIconStub = {
    name: "MaterialDesignIcon",
    template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
    props: ["iconName"],
};

describe("MapBrowser.vue", () => {
    const mountBrowser = async (route = { name: "map", params: {}, query: {} }) => {
        const wrapper = mount(MapBrowser, {
            global: {
                mocks: {
                    $t: (key, params) => {
                        if (key === "map.tab_default_name") {
                            return `Map ${params?.number ?? ""}`.trim();
                        }
                        return key;
                    },
                    $route: { name: "map", ...route },
                    $router: { replace: vi.fn(() => Promise.resolve()) },
                },
                stubs: {
                    MaterialDesignIcon: MaterialDesignIconStub,
                },
            },
        });
        await flushPromises();
        return wrapper;
    };

    beforeEach(() => {
        localStorage.clear();
        vi.clearAllMocks();
    });

    it("creates a single tab on mount", async () => {
        const wrapper = await mountBrowser();
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.activeTabId).toBe(wrapper.vm.tabs[0].id);
    });

    it("addTab creates and activates a new tab with a stable storage id", async () => {
        const wrapper = await mountBrowser();
        const before = wrapper.vm.tabs.length;
        const id = wrapper.vm.addTab();
        expect(wrapper.vm.tabs).toHaveLength(before + 1);
        expect(wrapper.vm.activeTabId).toBe(id);
        expect(wrapper.vm.tabs.find((t) => t.id === id).storageId).toBeTruthy();
    });

    it("tabTitle uses the saved title and falls back to the new map label", async () => {
        const wrapper = await mountBrowser();
        expect(wrapper.vm.tabTitle({ title: "Field AO" })).toBe("Field AO");
        expect(wrapper.vm.tabTitle({ title: null })).toBe("map.new_tab");
    });

    it("closeTab activates a neighbour and never leaves zero tabs", async () => {
        const wrapper = await mountBrowser();
        const first = wrapper.vm.tabs[0].id;
        const second = wrapper.vm.addTab("Second map");
        expect(wrapper.vm.tabs).toHaveLength(2);

        wrapper.vm.closeTab(second);
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.activeTabId).toBe(first);

        wrapper.vm.closeTab(first);
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.activeTabId).toBe(wrapper.vm.tabs[0].id);
    });

    it("shows the tab strip only on wide viewports", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.isWideViewport = false;
        await wrapper.vm.$nextTick();
        expect(wrapper.find('[role="tablist"]').exists()).toBe(false);

        wrapper.vm.isWideViewport = true;
        await wrapper.vm.$nextTick();
        expect(wrapper.find('[role="tablist"]').exists()).toBe(true);
    });

    it("persists tab layout to localStorage when tabs change", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.addTab("Ops map");
        await wrapper.vm.$nextTick();

        const saved = JSON.parse(localStorage.getItem("meshchatx.map.tabs"));
        expect(saved.tabs).toHaveLength(2);
        expect(saved.tabs[1]).toMatchObject({
            title: "Ops map",
            userRenamed: true,
        });
        expect(saved.activeIndex).toBe(1);
    });

    it("restores persisted tabs on mount", async () => {
        localStorage.setItem(
            "meshchatx.map.tabs",
            JSON.stringify({
                tabs: [
                    { storageId: "tab-a", title: "Alpha", userRenamed: true, tabNumber: 1 },
                    { storageId: "tab-b", title: "Bravo", userRenamed: true, tabNumber: 2 },
                ],
                activeIndex: 1,
            })
        );

        const wrapper = await mountBrowser();
        expect(wrapper.vm.tabs).toHaveLength(2);
        expect(wrapper.vm.tabs[0].storageId).toBe("tab-a");
        expect(wrapper.vm.activeTabId).toBe(wrapper.vm.tabs[1].id);
    });

    it("renames a tab on commit and marks it user-renamed", async () => {
        const wrapper = await mountBrowser();
        const tab = wrapper.vm.tabs[0];
        wrapper.vm.startRename(tab.id);
        wrapper.vm.renameDraft = "  Relay site  ";
        wrapper.vm.commitRename();

        expect(tab.title).toBe("Relay site");
        expect(tab.userRenamed).toBe(true);
    });

    it("does not overwrite a user-renamed title from map search suggestions", async () => {
        const wrapper = await mountBrowser();
        const tab = wrapper.vm.tabs[0];
        tab.userRenamed = true;
        tab.title = "My map";

        wrapper.vm.onMapUpdateTitle(tab.id, "San Francisco");
        expect(tab.title).toBe("My map");
    });

    it("updates an auto title from map search suggestions", async () => {
        const wrapper = await mountBrowser();
        const tab = wrapper.vm.tabs[0];

        wrapper.vm.onMapUpdateTitle(tab.id, "San Francisco");
        expect(tab.title).toBe("San Francisco");
    });

    it("migrates legacy last_view state into the first restored tab", async () => {
        TileCache.getMapState.mockImplementation(async (key) => {
            if (key === "last_view") {
                return { center: [1, 2], zoom: 8 };
            }
            return null;
        });

        localStorage.setItem(
            "meshchatx.map.tabs",
            JSON.stringify({
                tabs: [{ storageId: "legacy-tab", title: "Map 1", userRenamed: false, tabNumber: 1 }],
                activeIndex: 0,
            })
        );

        await mountBrowser();
        await vi.waitFor(() => {
            expect(TileCache.setMapState).toHaveBeenCalledWith(
                mapViewStateKey(useConfigStore().config?.identity_hash, "legacy-tab"),
                expect.objectContaining({ center: [1, 2], zoom: 8 })
            );
        });
    });

    it("renders one embedded MapPage per tab", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.addTab("Second");
        await wrapper.vm.$nextTick();
        const pages = wrapper.findAllComponents({ name: "MapPage" });
        expect(pages).toHaveLength(2);
        expect(pages[0].props("embedded")).toBe(true);
        expect(pages[1].props("embedded")).toBe(true);
        expect(pages[1].props("isActiveTab")).toBe(true);
        expect(pages[0].props("isActiveTab")).toBe(false);
    });

    it("Ctrl+T opens a new tab on wide viewports", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.isWideViewport = true;
        const before = wrapper.vm.tabs.length;
        window.dispatchEvent(
            new KeyboardEvent("keydown", { key: "t", ctrlKey: true, bubbles: true, cancelable: true })
        );
        expect(wrapper.vm.tabs).toHaveLength(before + 1);
    });

    it("ignores tab keyboard shortcuts on narrow viewports", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.isWideViewport = false;
        const before = wrapper.vm.tabs.length;
        window.dispatchEvent(
            new KeyboardEvent("keydown", { key: "t", ctrlKey: true, bubbles: true, cancelable: true })
        );
        expect(wrapper.vm.tabs).toHaveLength(before);
    });

    it("marks the active map tab inactive while the keep-alive route is cached", async () => {
        const wrapper = await mountBrowser();
        const active = wrapper.findAllComponents({ name: "MapPage" }).find((page) => page.props("isActiveTab"));
        expect(active).toBeTruthy();
        wrapper.vm.isRouteActive = false;
        await wrapper.vm.$nextTick();
        expect(
            wrapper.findAllComponents({ name: "MapPage" }).every((page) => page.props("isActiveTab") === false)
        ).toBe(true);
        wrapper.vm.isRouteActive = true;
        await wrapper.vm.$nextTick();
        expect(wrapper.findAllComponents({ name: "MapPage" }).some((page) => page.props("isActiveTab") === true)).toBe(
            true
        );
    });

    it("deactivated and activated toggle isRouteActive", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.$options.deactivated.call(wrapper.vm);
        expect(wrapper.vm.isRouteActive).toBe(false);
        wrapper.vm.$options.activated.call(wrapper.vm);
        expect(wrapper.vm.isRouteActive).toBe(true);
    });

    it("right-click on a tab selects it and opens the tab context menu", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.addTab("Second");
        await wrapper.vm.$nextTick();

        const firstId = wrapper.vm.tabs[0].id;
        const tabButtons = wrapper.findAll('[role="tab"]');
        expect(tabButtons).toHaveLength(2);

        await tabButtons[0].trigger("contextmenu", { clientX: 40, clientY: 12 });
        expect(wrapper.vm.tabContextMenu.show).toBe(true);
        expect(wrapper.vm.tabContextMenu.tabId).toBe(firstId);
        expect(wrapper.vm.tabContextMenu.x).toBe(40);
        expect(wrapper.vm.tabContextMenu.y).toBe(12);
        expect(wrapper.vm.activeTabId).toBe(firstId);
    });

    it("context menu renders tab actions in the teleported panel", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.addTab("Second");
        await wrapper.vm.$nextTick();

        wrapper.vm.openTabContextMenu({ clientX: 10, clientY: 10 }, wrapper.vm.tabs[0]);
        await wrapper.vm.$nextTick();

        const menu = document.body.querySelector(".context-menu-panel, [class*='context']");
        expect(menu).toBeTruthy();
        expect(document.body.textContent).toContain("common.rename");
        expect(document.body.textContent).toContain("map.close_other_tabs");
    });

    it("close tabs to the right removes only later tabs", async () => {
        const wrapper = await mountBrowser();
        const keep = wrapper.vm.tabs[0].id;
        wrapper.vm.addTab("B");
        wrapper.vm.addTab("C");
        expect(wrapper.vm.tabs).toHaveLength(3);

        wrapper.vm.tabContextMenu.tabId = keep;
        wrapper.vm.onContextCloseTabsRight();
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.tabs[0].id).toBe(keep);
        expect(wrapper.vm.tabContextMenu.show).toBe(false);
    });

    it("close other tabs keeps only the context tab and keeps it active", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.addTab("B");
        const keep = wrapper.vm.addTab("C");
        expect(wrapper.vm.tabs).toHaveLength(3);

        wrapper.vm.tabContextMenu.tabId = keep;
        wrapper.vm.onContextCloseOtherTabs();
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.tabs[0].id).toBe(keep);
        expect(wrapper.vm.activeTabId).toBe(keep);
    });

    it("close all tabs leaves one fresh tab", async () => {
        const wrapper = await mountBrowser();
        wrapper.vm.addTab("B");
        wrapper.vm.addTab("C");
        wrapper.vm.onContextCloseAllTabs();
        expect(wrapper.vm.tabs).toHaveLength(1);
        expect(wrapper.vm.activeTabId).toBe(wrapper.vm.tabs[0].id);
    });

    it("canCloseRight is false for the last tab", async () => {
        const wrapper = await mountBrowser();
        const last = wrapper.vm.addTab("Last");
        wrapper.vm.tabContextMenu.tabId = last;
        expect(wrapper.vm.tabContextMenuCanCloseRight).toBe(false);
        wrapper.vm.tabContextMenu.tabId = wrapper.vm.tabs[0].id;
        expect(wrapper.vm.tabContextMenuCanCloseRight).toBe(true);
    });

    it("rename from the context menu starts rename for that tab", async () => {
        const wrapper = await mountBrowser();
        const second = wrapper.vm.addTab("Second");
        wrapper.vm.tabContextMenu = { show: true, tabId: second, x: 0, y: 0, justOpened: false };
        wrapper.vm.onContextRenameTab();
        expect(wrapper.vm.renamingTabId).toBe(second);
        expect(wrapper.vm.tabContextMenu.show).toBe(false);
    });
});
