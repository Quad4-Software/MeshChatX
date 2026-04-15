import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MicronEditorPage from "@/components/micron-editor/MicronEditorPage.vue";
import { micronStorage } from "@/js/MicronStorage";
import DialogUtils from "@/js/DialogUtils";

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

    const mountMicronEditorPage = () => {
        return mount(MicronEditorPage, {
            global: {
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
