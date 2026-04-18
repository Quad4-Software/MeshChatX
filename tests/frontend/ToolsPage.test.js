import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import ToolsPage from "@/components/tools/ToolsPage.vue";
import { createRouter, createWebHistory } from "vue-router";

describe("ToolsPage.vue", () => {
    const router = createRouter({
        history: createWebHistory(),
        routes: [
            { path: "/ping", name: "ping", component: { template: "div" } },
            { path: "/rnprobe", name: "rnprobe", component: { template: "div" } },
            { path: "/rncp", name: "rncp", component: { template: "div" } },
            { path: "/rnstatus", name: "rnstatus", component: { template: "div" } },
            { path: "/rnpath", name: "rnpath", component: { template: "div" } },
            { path: "/rnpath-trace", name: "rnpath-trace", component: { template: "div" } },
            { path: "/translator", name: "translator", component: { template: "div" } },
            { path: "/bots", name: "bots", component: { template: "div" } },
            { path: "/propagation-nodes", name: "propagation-nodes", component: { template: "div" } },
            { path: "/forwarder", name: "forwarder", component: { template: "div" } },
            { path: "/documentation", name: "documentation", component: { template: "div" } },
            { path: "/micron-editor", name: "micron-editor", component: { template: "div" } },
            { path: "/tools/reticulum-config-editor", name: "reticulum-config-editor", component: { template: "div" } },
            { path: "/paper-message", name: "paper-message", component: { template: "div" } },
            { path: "/rnode-flasher", name: "rnode-flasher", component: { template: "div" } },
            { path: "/debug-logs", name: "debug-logs", component: { template: "div" } },
            { path: "/mesh-server", name: "mesh-server", component: { template: "div" } },
        ],
    });

    const mountToolsPage = () => {
        return mount(ToolsPage, {
            global: {
                plugins: [router],
                mocks: {
                    $t: (key) => key,
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                },
            },
        });
    };

    it("renders the tools page header", () => {
        const wrapper = mountToolsPage();
        expect(wrapper.text()).toContain("tools.power_tools");
        expect(wrapper.text()).not.toContain("tools.utilities");
    });

    it("renders all tool rows", () => {
        const wrapper = mountToolsPage();
        const toolRows = wrapper.findAll(".tool-row");
        expect(toolRows.length).toBe(19);
    });

    it("filters tools based on search query", async () => {
        const wrapper = mountToolsPage();
        const searchInput = wrapper.find("input");

        await searchInput.setValue("ping");
        expect(wrapper.vm.filteredTools.length).toBe(1);
        expect(wrapper.vm.filteredTools[0].name).toBe("ping");

        await searchInput.setValue("nonexistenttool");
        expect(wrapper.vm.filteredTools.length).toBe(0);
        expect(wrapper.text()).toContain("common.no_results");
    });

    it("clears search query when close button is clicked", async () => {
        const wrapper = mountToolsPage();
        const searchInput = wrapper.find("input");

        await searchInput.setValue("ping");
        const clearButton = wrapper.find("button");
        await clearButton.trigger("click");

        expect(wrapper.vm.searchQuery).toBe("");
        expect(wrapper.vm.filteredTools.length).toBe(19);
    });
});
