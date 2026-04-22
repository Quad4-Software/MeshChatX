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
                            has_bundled_docs: false,
                            has_user_docs: false,
                            versions: [],
                            current_version: null,
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

    it("renders upload prompt when no docs are present", async () => {
        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        expect(wrapper.text()).toContain("Reticulum Manual");
        expect(wrapper.text()).toContain("docs.empty_state_hint");
        expect(wrapper.text()).toContain("docs.btn_upload");
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
                        has_bundled_docs: true,
                        has_user_docs: false,
                        versions: [],
                        current_version: "bundled",
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
        expect(wrapper.find("iframe").attributes("src")).toBe("/reticulum-docs/manual/index.html");
    });

    it("shows progress bar while extracting an upload", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "extracting",
                        progress: 45,
                        last_error: null,
                        has_docs: false,
                        has_bundled_docs: false,
                        has_user_docs: false,
                        versions: [],
                        current_version: null,
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
        expect(wrapper.text()).toContain("docs.status_extracting");
    });

    it("shows error message when status has an error", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "error",
                        progress: 0,
                        last_error: "Bad zip",
                        has_docs: false,
                        has_bundled_docs: false,
                        has_user_docs: false,
                        versions: [],
                        current_version: null,
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
        expect(wrapper.text()).toContain("Bad zip");
    });

    it("does not auto-trigger any update API call on mount", async () => {
        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        expect(axiosMock.post).not.toHaveBeenCalledWith(
            expect.stringContaining("/api/v1/docs/update"),
            expect.anything()
        );
        expect(wrapper.exists()).toBe(true);
    });

    it("dismissError clears the last_error from local status", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "error",
                        progress: 0,
                        last_error: "Boom",
                        has_docs: false,
                        has_bundled_docs: false,
                        has_user_docs: false,
                        versions: [],
                        current_version: null,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();
        expect(wrapper.vm.status.last_error).toBe("Boom");
        wrapper.vm.dismissError();
        await nextTick();
        expect(wrapper.vm.status.last_error).toBeNull();
    });

    it("opens the Sphinx manual for English and localized site index for other locales", async () => {
        const wrapper = mountDocsPage();
        await nextTick();

        i18nMock.locale = "de";
        await nextTick();
        expect(wrapper.vm.localDocsUrl).toBe("/reticulum-docs/index_de.html");

        i18nMock.locale = "en";
        await nextTick();
        expect(wrapper.vm.localDocsUrl).toBe("/reticulum-docs/manual/index.html");
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
                        has_bundled_docs: false,
                        has_user_docs: false,
                        versions: [],
                        current_version: null,
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
