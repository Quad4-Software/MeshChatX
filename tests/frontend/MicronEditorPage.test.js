import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import MicronEditorPage from "@/components/micron-editor/MicronEditorPage.vue";
import { micronStorage } from "@/js/MicronStorage";

// Mock micronStorage
vi.mock("@/js/MicronStorage", () => ({
    micronStorage: {
        saveTabs: vi.fn().mockResolvedValue(),
        loadTabs: vi.fn().mockResolvedValue([]),
        clearAll: vi.fn().mockResolvedValue(),
        initPromise: Promise.resolve(),
    },
}));

// Mock MicronParser
vi.mock("micron-parser", () => {
    return {
        default: vi.fn().mockImplementation(() => ({
            convertMicronToHtml: vi.fn().mockReturnValue("<div>Rendered Content</div>"),
        })),
    };
});

describe("MicronEditorPage.vue", () => {
    const mountComponent = () => {
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

    beforeEach(() => {
        vi.clearAllMocks();
        // Mock localStorage
        const localStorageMock = {
            getItem: vi.fn().mockReturnValue(null),
            setItem: vi.fn(),
            removeItem: vi.fn(),
            clear: vi.fn(),
        };
        Object.defineProperty(window, "localStorage", { value: localStorageMock, writable: true });

        // Mock window.innerWidth
        Object.defineProperty(window, "innerWidth", { value: 1200, writable: true });

        // Mock window.confirm
        window.confirm = vi.fn().mockReturnValue(true);
    });

    it("renders with default tab if no saved tabs", async () => {
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // Wait for loadContent

        expect(wrapper.vm.tabs.length).toBe(2);
        expect(wrapper.vm.tabs[0].name).toBe("tools.micron_editor.main_tab");
        expect(wrapper.vm.tabs[1].name).toBe("tools.micron_editor.guide_tab");
        expect(wrapper.text()).toContain("tools.micron_editor.title");
    });

    it("adds a new tab when clicking the add button", async () => {
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const initialTabCount = wrapper.vm.tabs.length;

        // Find add tab button
        const addButton = wrapper.find('.mdi-stub[data-icon-name="plus"]').element.parentElement;
        await addButton.click();

        expect(wrapper.vm.tabs.length).toBe(initialTabCount + 1);
        expect(wrapper.vm.activeTabIndex).toBe(initialTabCount);
        expect(micronStorage.saveTabs).toHaveBeenCalled();
    });

    it("removes a tab when clicking the close button", async () => {
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        // Already have 2 tabs (Main + Guide)
        expect(wrapper.vm.tabs.length).toBe(2);

        // Find close button on the second tab
        const closeButton = wrapper.findAll('.mdi-stub[data-icon-name="close"]')[1].element.parentElement;
        await closeButton.click();

        expect(wrapper.vm.tabs.length).toBe(1);
        expect(micronStorage.saveTabs).toHaveBeenCalled();
    });

    it("switches active tab when clicking a tab", async () => {
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        // Initially on first tab
        expect(wrapper.vm.activeTabIndex).toBe(0);

        // Click second tab (Guide)
        const tabs = wrapper.findAll(".group.flex.items-center");
        await tabs[1].trigger("click");

        expect(wrapper.vm.activeTabIndex).toBe(1);
    });

    it("resets all tabs when clicking reset button", async () => {
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const initialTabCount = wrapper.vm.tabs.length;
        await wrapper.vm.addTab();
        expect(wrapper.vm.tabs.length).toBe(initialTabCount + 1);

        // Find reset button
        const resetButton = wrapper.find('.mdi-stub[data-icon-name="refresh"]').element.parentElement;
        await resetButton.click();

        expect(window.confirm).toHaveBeenCalled();
        expect(micronStorage.clearAll).toHaveBeenCalled();
        expect(wrapper.vm.tabs.length).toBe(2); // Resets to Main + Guide
        expect(wrapper.vm.activeTabIndex).toBe(0);
    });

    it("updates rendered content when input changes", async () => {
        const wrapper = mountComponent();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const textarea = wrapper.find("textarea");
        await textarea.setValue("New Micron Content");

        expect(wrapper.vm.tabs[0].content).toBe("New Micron Content");
        expect(micronStorage.saveTabs).toHaveBeenCalled();
    });
});
