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

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(),
        alert: vi.fn(),
        prompt: vi.fn(),
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
        const wrapper = mountMicronEditorPage();
        await vi.waitFor(() => expect(wrapper.vm.tabs.length).toBeGreaterThan(0));
        await wrapper.setData({
            tabs: [{ id: 1, name: "New Tab 1", content: "hello" }],
            activeTabIndex: 0,
        });
        await wrapper.vm.publishToNode({ node_id: "n1", name: "My Server" });
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/page-nodes/n1/pages", {
            name: "index",
            content: "hello",
        });
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
});
