import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MicronEditorPage from "@/components/micron-editor/MicronEditorPage.vue";
import { micronStorage } from "@/js/MicronStorage";
import DialogUtils from "@/js/DialogUtils";

const micronEditorT = (key, params = {}) => {
    const strings = {
        "tools.micron_editor.new_tab": "New Tab",
        "tools.micron_editor.publish_prompt_name":
            'index.mu already exists on "{server}". Enter a page name (without .mu):',
        "tools.micron_editor.publish_published": 'Published "{page}" to {server}',
        "tools.micron_editor.publish_failed": "Failed to publish page",
    };
    let out = strings[key] ?? key;
    for (const [k, v] of Object.entries(params)) {
        out = out.replace(`{${k}}`, String(v));
    }
    return out;
};

vi.mock("@/js/MicronStorage", () => ({
    micronStorage: {
        loadTabs: vi.fn().mockResolvedValue([]),
        saveTabs: vi.fn().mockResolvedValue(),
        clearAll: vi.fn().mockResolvedValue(),
    },
}));

vi.mock("@/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(),
        alert: vi.fn(),
        prompt: vi.fn(),
    },
}));

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

describe("MicronEditorPage.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Mock localStorage
        Object.defineProperty(window, "localStorage", {
            value: {
                getItem: vi.fn(),
                setItem: vi.fn(),
                removeItem: vi.fn(),
            },
            writable: true,
        });
    });

    const mountMicronEditorPage = (t = micronEditorT) => {
        return mount(MicronEditorPage, {
            global: {
                mocks: {
                    $t: t,
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                    "router-link": {
                        template: "<a><slot /></a>",
                    },
                },
            },
        });
    };

    it("renders the micron editor", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        expect(wrapper.text()).toContain("tools.micron_editor.title");
    });

    it("adds a new tab", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        const initialCount = wrapper.vm.tabs.length;

        const addButton = wrapper.findAll("button").find((b) => b.html().includes("plus"));
        await addButton.trigger("click");

        expect(wrapper.vm.tabs.length).toBe(initialCount + 1);
        expect(wrapper.vm.activeTabIndex).toBe(initialCount);
    });

    it("renders micron content to html", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));

        await wrapper.setData({
            tabs: [{ id: 1, name: "Test", content: "TestContent" }],
            activeTabIndex: 0,
        });

        wrapper.vm.renderActiveTab();
        await wrapper.vm.$nextTick();
        expect(wrapper.find(".nodeContainer").text()).toContain("TestContent");
    });

    it("isUnsetMicronTabName matches default new tab labels", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        expect(wrapper.vm.isUnsetMicronTabName("New Tab 2")).toBe(true);
        expect(wrapper.vm.isUnsetMicronTabName("Homepage")).toBe(false);
        expect(wrapper.vm.isUnsetMicronTabName("Main")).toBe(false);
    });

    it("resolvePublishPageBase uses index when server has no index.mu", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        const tab = { name: "New Tab 1", content: "x" };
        await expect(wrapper.vm.resolvePublishPageBase(tab, [], "srv")).resolves.toBe("index");
    });

    it("resolvePublishPageBase uses tab name when index.mu exists and tab is renamed", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        const tab = { name: "About Page", content: "x" };
        await expect(wrapper.vm.resolvePublishPageBase(tab, ["index.mu"], "srv")).resolves.toBe("About_Page");
    });

    it("resolvePublishPageBase prompts when index.mu exists and tab name is unset", async () => {
        DialogUtils.prompt.mockResolvedValue("custom_page");
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        const tab = { name: "New Tab 1", content: "x" };
        await expect(wrapper.vm.resolvePublishPageBase(tab, ["index.mu"], "srv")).resolves.toBe("custom_page");
        expect(DialogUtils.prompt).toHaveBeenCalled();
    });

    it("publishToNode posts index.mu when server has no index page", async () => {
        window.api = {
            get: vi.fn().mockResolvedValue({ data: { pages: [] } }),
            post: vi.fn().mockResolvedValue({ data: { name: "index.mu" } }),
        };
        DialogUtils.confirm.mockResolvedValue(false);
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({
            tabs: [{ id: 1, name: "New Tab 1", content: "hello" }],
            activeTabIndex: 0,
        });
        const dest = "a".repeat(32);
        await wrapper.vm.publishToNode({
            node_id: "n1",
            name: "My Server",
            running: true,
            destination_hash: dest,
        });
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/page-nodes/n1/pages", {
            name: "index",
            content: "hello",
        });
        expect(wrapper.vm.lastPublished).toEqual({
            destinationHash: dest,
            pagePath: "/page/index.mu",
            pageName: "index.mu",
            serverName: "My Server",
        });
    });

    it("createMeshServerAndPublish creates, starts, publishes, and can open NomadNet", async () => {
        const dest = "b".repeat(32);
        window.api = {
            get: vi.fn().mockResolvedValue({ data: { pages: [] } }),
            post: vi
                .fn()
                .mockResolvedValueOnce({ data: { node_id: "n2", name: "Micron Pages", running: false } })
                .mockResolvedValueOnce({ data: { destination_hash: dest, message: "Node started" } })
                .mockResolvedValueOnce({ data: { name: "index.mu" } }),
        };
        DialogUtils.prompt.mockResolvedValue("Micron Pages");
        DialogUtils.confirm.mockResolvedValue(true);
        const push = vi.fn().mockResolvedValue();
        const wrapper = mountMicronEditorPage();
        wrapper.vm.$router = { push };
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({
            tabs: [{ id: 1, name: "New Tab 1", content: "hi" }],
            activeTabIndex: 0,
        });
        await wrapper.vm.createMeshServerAndPublish();
        expect(window.api.post).toHaveBeenNthCalledWith(1, "/api/v1/page-nodes", { name: "Micron Pages" });
        expect(window.api.post).toHaveBeenNthCalledWith(2, "/api/v1/page-nodes/n2/start");
        expect(window.api.post).toHaveBeenNthCalledWith(3, "/api/v1/page-nodes/n2/pages", {
            name: "index",
            content: "hi",
        });
        expect(push).toHaveBeenCalledWith({
            name: "nomadnetwork",
            params: { destinationHash: dest },
            query: { path: "/page/index.mu", newTab: "1" },
        });
    });

    it("publishToNode starts a stopped server before uploading", async () => {
        const dest = "c".repeat(32);
        window.api = {
            get: vi.fn().mockResolvedValue({ data: { pages: [] } }),
            post: vi
                .fn()
                .mockResolvedValueOnce({ data: { destination_hash: dest } })
                .mockResolvedValueOnce({ data: { name: "index.mu" } }),
        };
        DialogUtils.confirm.mockResolvedValue(false);
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({
            tabs: [{ id: 1, name: "New Tab 1", content: "x" }],
            activeTabIndex: 0,
        });
        await wrapper.vm.publishToNode({ node_id: "n3", name: "Stopped", running: false });
        expect(window.api.post).toHaveBeenNthCalledWith(1, "/api/v1/page-nodes/n3/start");
        expect(window.api.post).toHaveBeenNthCalledWith(2, "/api/v1/page-nodes/n3/pages", {
            name: "index",
            content: "x",
        });
    });

    it("pageBaseWithExtension preserves html tab extension when publishing", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        const tab = { name: "Landing.html", content: "<p>hi</p>" };
        expect(wrapper.vm.pageBaseWithExtension("landing", tab)).toBe("landing.html");
    });

    it("onPreviewClick opens http links externally", async () => {
        const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        const preview = wrapper.find(".nodeContainer");
        preview.element.innerHTML = '<a href="https://example.com/page.html">Example</a>';
        const link = preview.find("a");
        await link.trigger("click");
        expect(openSpy).toHaveBeenCalledWith("https://example.com/page.html", "_blank", "noopener,noreferrer");
        openSpy.mockRestore();
    });

    it("resets all content", async () => {
        DialogUtils.confirm.mockResolvedValue(true);
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));

        const resetButton = wrapper.findAll("button").find((b) => b.html().includes('data-icon-name="refresh"'));
        expect(resetButton).toBeDefined();
        await resetButton.trigger("click");

        expect(micronStorage.clearAll).toHaveBeenCalled();
        expect(wrapper.vm.tabs.length).toBe(2); // main and guide
    }, 20_000);

    it("moveTab reorders tabs and keeps the active tab selected", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({
            tabs: [
                { id: 1, name: "A", content: "a" },
                { id: 2, name: "B", content: "b" },
                { id: 3, name: "C", content: "c" },
            ],
            activeTabIndex: 1,
        });
        wrapper.vm.moveTab(1, 0);
        expect(wrapper.vm.tabs.map((t) => t.name)).toEqual(["B", "A", "C"]);
        expect(wrapper.vm.activeTabIndex).toBe(0);
        expect(micronStorage.saveTabs).toHaveBeenCalled();
    });

    it("moveTab ignores out-of-range and no-op moves", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({
            tabs: [
                { id: 1, name: "A", content: "a" },
                { id: 2, name: "B", content: "b" },
            ],
            activeTabIndex: 0,
        });
        wrapper.vm.moveTab(0, 0);
        wrapper.vm.moveTab(5, 0);
        wrapper.vm.moveTab(0, 9);
        expect(wrapper.vm.tabs.map((t) => t.name)).toEqual(["A", "B"]);
    });

    it("buildSiteIndexPage emits micron links for each page", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        const dest = "d".repeat(32);
        const content = wrapper.vm.buildSiteIndexPage(dest, [
            { name: "about.mu", label: "About" },
            { name: "news.mu", label: "News [x]" },
        ]);
        expect(content).toContain(`[About\`${dest}:/page/about.mu]`);
        expect(content).toContain(`[News x\`${dest}:/page/news.mu]`);
    });

    it("publishSite uploads pages in order and writes the index page", async () => {
        const dest = "e".repeat(32);
        window.api = {
            get: vi.fn().mockResolvedValue({ data: { pages: [] } }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        DialogUtils.confirm.mockResolvedValue(false);
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({
            tabs: [{ id: 1, name: "A", content: "a" }],
            pageNodes: [{ node_id: "n9", name: "Srv", running: true, destination_hash: dest }],
        });
        await wrapper.vm.publishSite({
            nodeId: "n9",
            pages: [
                { name: "one.mu", content: "1", label: "One" },
                { name: "two.mu", content: "2", label: "Two" },
            ],
            generateIndex: true,
        });
        const posts = window.api.post.mock.calls.filter((c) => c[0] === "/api/v1/page-nodes/n9/pages");
        expect(posts.map((c) => c[1].name)).toEqual(["one.mu", "two.mu", "index.mu"]);
        expect(posts[2][1].content).toContain(`[One\`${dest}:/page/one.mu]`);
        expect(wrapper.vm.lastPublished?.pageName).toBe("index.mu");
        expect(wrapper.vm.showPublishSiteModal).toBe(false);
    });

    it("publishSite creates a new server when no nodeId is given", async () => {
        const dest = "f".repeat(32);
        window.api = {
            get: vi.fn().mockResolvedValue({ data: { pages: [] } }),
            post: vi
                .fn()
                .mockResolvedValueOnce({ data: { node_id: "n10", name: "Fresh", running: false } })
                .mockResolvedValueOnce({ data: { destination_hash: dest } })
                .mockResolvedValue({ data: {} }),
        };
        DialogUtils.confirm.mockResolvedValue(false);
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({ pageNodes: [] });
        await wrapper.vm.publishSite({
            nodeId: null,
            newServerName: "Fresh",
            pages: [{ name: "index.mu", content: "home", label: "Home" }],
            generateIndex: false,
        });
        expect(window.api.post).toHaveBeenNthCalledWith(1, "/api/v1/page-nodes", { name: "Fresh" });
        expect(window.api.post).toHaveBeenNthCalledWith(2, "/api/v1/page-nodes/n10/start");
        expect(window.api.post).toHaveBeenNthCalledWith(3, "/api/v1/page-nodes/n10/pages", {
            name: "index.mu",
            content: "home",
        });
    });

    it("onIdentitySwitched clears storage and resets tabs", async () => {
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({
            tabs: [{ id: 1, name: "Secret", content: "from-identity-a" }],
            activeTabIndex: 0,
        });
        await wrapper.vm.onIdentitySwitched();
        expect(micronStorage.clearAll).toHaveBeenCalled();
        expect(micronStorage.saveTabs).toHaveBeenCalled();
        expect(wrapper.vm.tabs.length).toBe(2);
        expect(wrapper.vm.tabs[0].content).not.toContain("from-identity-a");
        expect(wrapper.vm.activeTabIndex).toBe(0);
    });
});
