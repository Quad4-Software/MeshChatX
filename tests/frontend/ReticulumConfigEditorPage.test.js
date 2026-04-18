import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ReticulumConfigEditorPage from "@/components/tools/ReticulumConfigEditorPage.vue";
import DialogUtils from "@/js/DialogUtils";
import GlobalState from "@/js/GlobalState";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(),
        alert: vi.fn(),
        prompt: vi.fn(),
    },
}));

const SAMPLE_CONFIG =
    "[reticulum]\n  enable_transport = False\n\n[interfaces]\n  [[Default Interface]]\n    type = AutoInterface\n";
const DEFAULT_CONFIG =
    "[reticulum]\n  enable_transport = False\n\n[interfaces]\n  [[Default Interface]]\n    type = AutoInterface\n    enabled = true\n";
const CONFIG_PATH = "/tmp/.reticulum/config";

describe("ReticulumConfigEditorPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            put: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockResolvedValue({
            data: { content: SAMPLE_CONFIG, path: CONFIG_PATH },
        });
        axiosMock.put.mockResolvedValue({
            data: { message: "Reticulum config saved", path: CONFIG_PATH },
        });
        axiosMock.post.mockImplementation((url) => {
            if (url === "/api/v1/reticulum/config/reset") {
                return Promise.resolve({
                    data: {
                        message: "Reticulum config restored to defaults",
                        content: DEFAULT_CONFIG,
                        path: CONFIG_PATH,
                    },
                });
            }
            if (url === "/api/v1/reticulum/reload") {
                return Promise.resolve({
                    data: { message: "Reticulum reloaded successfully" },
                });
            }
            return Promise.resolve({ data: {} });
        });

        GlobalState.hasPendingInterfaceChanges = false;
        if (!GlobalState.modifiedInterfaceNames) {
            GlobalState.modifiedInterfaceNames = new Set();
        }
        GlobalState.modifiedInterfaceNames.clear();
    });

    afterEach(() => {
        delete window.api;
        vi.clearAllMocks();
    });

    const mountPage = () => {
        return mount(ReticulumConfigEditorPage, {
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

    it("loads the current config on mount and shows the path", async () => {
        const wrapper = mountPage();
        await flushPromises();

        expect(axiosMock.get).toHaveBeenCalledWith("/api/v1/reticulum/config/raw");
        expect(wrapper.vm.content).toBe(SAMPLE_CONFIG);
        expect(wrapper.vm.originalContent).toBe(SAMPLE_CONFIG);
        expect(wrapper.text()).toContain(CONFIG_PATH);
        expect(wrapper.text()).toContain("tools.reticulum_config_editor.title");
    });

    it("marks the editor as dirty when the textarea changes", async () => {
        const wrapper = mountPage();
        await flushPromises();
        expect(wrapper.vm.isDirty).toBe(false);

        const textarea = wrapper.find("textarea");
        await textarea.setValue(SAMPLE_CONFIG + "\n# my edit\n");

        expect(wrapper.vm.isDirty).toBe(true);
        expect(wrapper.text()).toContain("tools.reticulum_config_editor.unsaved");
    });

    it("saves config and shows the restart banner after success", async () => {
        const wrapper = mountPage();
        await flushPromises();

        const newContent = SAMPLE_CONFIG + "\n# edit\n";
        await wrapper.find("textarea").setValue(newContent);
        await wrapper.vm.saveConfig();
        await flushPromises();

        expect(axiosMock.put).toHaveBeenCalledWith("/api/v1/reticulum/config/raw", { content: newContent });
        expect(wrapper.vm.hasSavedChanges).toBe(true);
        expect(wrapper.vm.showRestartReminder).toBe(true);
        expect(GlobalState.hasPendingInterfaceChanges).toBe(true);
        expect(wrapper.text()).toContain("tools.reticulum_config_editor.restart_required");
    });

    it("does not save when the editor is not dirty", async () => {
        const wrapper = mountPage();
        await flushPromises();
        await wrapper.vm.saveConfig();
        expect(axiosMock.put).not.toHaveBeenCalled();
    });

    it("restores defaults after confirmation", async () => {
        DialogUtils.confirm.mockResolvedValue(true);
        const wrapper = mountPage();
        await flushPromises();

        await wrapper.vm.restoreDefaults();
        await flushPromises();

        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/config/reset");
        expect(wrapper.vm.content).toBe(DEFAULT_CONFIG);
        expect(wrapper.vm.originalContent).toBe(DEFAULT_CONFIG);
        expect(wrapper.vm.hasSavedChanges).toBe(true);
        expect(GlobalState.hasPendingInterfaceChanges).toBe(true);
    });

    it("does not restore defaults if the user cancels", async () => {
        DialogUtils.confirm.mockResolvedValue(false);
        const wrapper = mountPage();
        await flushPromises();

        await wrapper.vm.restoreDefaults();
        await flushPromises();

        expect(axiosMock.post).not.toHaveBeenCalledWith("/api/v1/reticulum/config/reset");
        expect(wrapper.vm.content).toBe(SAMPLE_CONFIG);
    });

    it("reloads RNS and clears the restart banner", async () => {
        const wrapper = mountPage();
        await flushPromises();
        wrapper.vm.hasSavedChanges = true;
        await wrapper.vm.$nextTick();

        await wrapper.vm.reloadRns();
        await flushPromises();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/reticulum/reload");
        expect(wrapper.vm.hasSavedChanges).toBe(false);
        expect(GlobalState.hasPendingInterfaceChanges).toBe(false);
    });

    it("discards unsaved changes back to the original content", async () => {
        const wrapper = mountPage();
        await flushPromises();

        await wrapper.find("textarea").setValue("[reticulum]\n[interfaces]\n# changed");
        expect(wrapper.vm.isDirty).toBe(true);

        wrapper.vm.discardChanges();
        expect(wrapper.vm.content).toBe(SAMPLE_CONFIG);
        expect(wrapper.vm.isDirty).toBe(false);
    });

    it("shows an error toast when load fails", async () => {
        axiosMock.get.mockRejectedValueOnce({
            response: { data: { error: "boom" } },
        });
        const wrapper = mountPage();
        await flushPromises();
        expect(wrapper.vm.content).toBe("");
    });
});
