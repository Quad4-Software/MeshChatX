import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/components/nomadnetwork/NomadNetworkPage.vue", () => ({
    default: {
        name: "NomadNetworkPage",
        template: '<div class="nnp-stub" :data-hash="destinationHash"></div>',
        props: {
            destinationHash: { type: String, default: "" },
            initialPath: { type: String, default: null },
            embedded: { type: Boolean, default: false },
        },
        emits: ["navigate", "close-tab"],
    },
}));

import NomadNetworkBrowser from "@/components/nomadnetwork/NomadNetworkBrowser.vue";

const MaterialDesignIconStub = {
    name: "MaterialDesignIcon",
    template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
    props: ["iconName"],
};

describe("NomadNetworkBrowser.vue", () => {
    let routerReplace;

    const mountBrowser = (props = {}, route = { params: {}, query: {} }) => {
        routerReplace = vi.fn(() => Promise.resolve());
        return mount(NomadNetworkBrowser, {
            props,
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: route,
                    $router: { replace: routerReplace },
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

    it("renders one embedded NomadNetworkPage per tab", async () => {
        const wrapper = mountBrowser();
        wrapper.vm.addTab("f".repeat(32));
        await wrapper.vm.$nextTick();
        expect(wrapper.findAllComponents({ name: "NomadNetworkPage" })).toHaveLength(2);
        expect(wrapper.findComponent({ name: "NomadNetworkPage" }).props("embedded")).toBe(true);
    });
});
