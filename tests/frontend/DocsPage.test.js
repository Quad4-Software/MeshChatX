import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import DocsPage from "@/components/docs/DocsPage.vue";
import { nextTick, reactive } from "vue";

describe("DocsPage.vue", () => {
    let axiosMock;
    let i18nMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/api/v1/docs/status")) {
                    return Promise.resolve({
                        data: {
                            status: "idle",
                            progress: 0,
                            last_error: null,
                            has_docs: false,
                        },
                    });
                }
                if (url.includes("/api/v1/meshchatx-docs/list")) {
                    return Promise.resolve({ data: [] });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
        i18nMock = reactive({ locale: "en" });
    });

    afterEach(() => {
        if (wrapper) {
            wrapper.unmount();
        }
        // Do not delete window.api, as it might be used by async operations
        // and it is globally defined in setup.js anyway.
    });

    let wrapper;
    const mountDocsPage = () => {
        wrapper = mount(DocsPage, {
            global: {
                directives: {
                    "click-outside": vi.fn(),
                },
                mocks: {
                    $t: (key) => key,
                    $i18n: i18nMock,
                },
                stubs: {
                    MaterialDesignIcon: true,
                },
            },
        });
        return wrapper;
    };

    it("renders download button when no docs are present", async () => {
        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        expect(wrapper.text()).toContain("Reticulum Manual");
        const downloadBtn = wrapper.find("button.bg-blue-600");
        expect(downloadBtn.exists()).toBe(true);
        expect(downloadBtn.text()).toContain("docs.btn_download");
    });

    it("renders iframe when docs are present", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "idle",
                        progress: 100,
                        last_error: null,
                        has_docs: true,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        expect(wrapper.find("iframe").exists()).toBe(true);
        expect(wrapper.find("iframe").attributes("src")).toBe("/reticulum-docs/index.html");
    });

    it("shows progress bar during download", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "downloading",
                        progress: 45,
                        last_error: null,
                        has_docs: false,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        const progressBar = wrapper.find(".bg-blue-500");
        expect(progressBar.exists()).toBe(true);
        expect(progressBar.attributes("style")).toContain("width: 45%");
    });

    it("shows error message when status has an error", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "error",
                        progress: 0,
                        last_error: "Connection timeout",
                        has_docs: false,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        expect(wrapper.text()).toContain("docs.error");
        expect(wrapper.text()).toContain("Connection timeout");
    });

    it("calls update API when download button is clicked", async () => {
        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        const downloadBtn = wrapper.find("button.bg-blue-600");
        await downloadBtn.trigger("click");

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/docs/update");
    });

    it("changes localDocsUrl based on locale", async () => {
        const wrapper = mountDocsPage();
        await nextTick();

        i18nMock.locale = "de";
        await nextTick();
        expect(wrapper.vm.localDocsUrl).toBe("/reticulum-docs/index_de.html");

        i18nMock.locale = "en";
        await nextTick();
        expect(wrapper.vm.localDocsUrl).toBe("/reticulum-docs/index.html");
    });

    it("handles extremely long error messages in the UI", async () => {
        const longError = "Error ".repeat(100);
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "error",
                        progress: 0,
                        last_error: longError,
                        has_docs: false,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        expect(wrapper.text()).toContain("docs.error");
        expect(wrapper.text()).toContain(longError.substring(0, 100));
    });
});
