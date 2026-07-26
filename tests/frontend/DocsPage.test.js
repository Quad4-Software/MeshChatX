import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import DocsPage from "@/components/docs/DocsPage.vue";
import { nextTick, reactive } from "vue";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const structuredList = {
    docs: [{ name: "getting-started.md", path: "en/getting-started.md", type: "markdown" }],
    sections: [
        {
            id: "overview",
            title: "Overview",
            items: [
                {
                    path: "en/getting-started.md",
                    title: "Getting started",
                    lang: "en",
                    type: "markdown",
                },
            ],
        },
    ],
    languages: [{ code: "en", name: "English" }],
    default_language: "en",
};

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
                            has_meshchatx_docs: true,
                            has_bundled_docs: false,
                            has_user_docs: false,
                            versions: [],
                            current_version: null,
                        },
                    });
                }
                if (url.includes("/api/v1/meshchatx-docs/list")) {
                    return Promise.resolve({ data: structuredList });
                }
                if (url.includes("/api/v1/meshchatx-docs/content")) {
                    return Promise.resolve({
                        data: {
                            html: '<h2 id="intro">Intro</h2><h3 id="details">Details</h3>',
                            content: "## Intro\n",
                            type: "markdown",
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            patch: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
        i18nMock = reactive({ locale: "en" });
        vi.spyOn(window, "confirm").mockReturnValue(true);
        vi.spyOn(window, "prompt").mockReturnValue("v-test");
        vi.spyOn(window, "alert").mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
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
                    $t: (key, params) => {
                        if (params && params.count !== undefined) {
                            return `${key}:${params.count}`;
                        }
                        if (params && params.percent !== undefined) {
                            return `${key}:${params.percent}`;
                        }
                        if (params && params.message !== undefined) {
                            return `${key}:${params.message}`;
                        }
                        if (params && params.version !== undefined) {
                            return `${key}:${params.version}`;
                        }
                        return key;
                    },
                    $i18n: i18nMock,
                },
                stubs: {
                    MaterialDesignIcon: true,
                    ToolsPageHeader: true,
                },
            },
        });
        return wrapper;
    };

    it("renders upload prompt when no docs are present", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "idle",
                        progress: 0,
                        last_error: null,
                        has_docs: false,
                        has_meshchatx_docs: false,
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
        wrapper.vm.activeTab = "reticulum";
        await nextTick();
        await nextTick();

        expect(wrapper.text()).toContain("docs.reticulum_manual");
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

    it("opens the Sphinx manual by default and localized site index via Reticulum language picker", async () => {
        const wrapper = mountDocsPage();
        await nextTick();

        // App UI locale must not rewrite the Reticulum docs entry URL.
        i18nMock.locale = "de";
        await nextTick();
        expect(wrapper.vm.localDocsUrl).toBe("/reticulum-docs/manual/index.html");

        await wrapper.vm.setLanguage("de");
        await nextTick();
        expect(wrapper.vm.localDocsUrl).toMatch(/^\/reticulum-docs\/index_de\.html/);

        await wrapper.vm.setLanguage("en");
        await nextTick();
        expect(wrapper.vm.localDocsUrl).toMatch(/^\/reticulum-docs\/manual\/index\.html/);
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

    it("loads structured sections and auto-selects the first guide", async () => {
        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();
        await nextTick();

        expect(wrapper.text()).toContain("Overview");
        expect(wrapper.text()).toContain("Getting started");
        expect(wrapper.vm.selectedDocPath).toBe("en/getting-started.md");
        expect(wrapper.vm.docToc).toEqual([
            { id: "intro", text: "Intro", level: 2 },
            { id: "details", text: "Details", level: 3 },
        ]);
    });

    it("shows list error when meshchatx docs list request fails", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "idle",
                        progress: 0,
                        last_error: null,
                        has_docs: false,
                        has_meshchatx_docs: true,
                        has_bundled_docs: false,
                        has_user_docs: false,
                        versions: [],
                        current_version: null,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) {
                return Promise.reject({
                    response: { data: { error: "Server exploded" } },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        expect(wrapper.vm.meshchatxListError).toBe("Server exploded");
        expect(wrapper.text()).toContain("Server exploded");
    });

    it("shows doc load error when content request fails", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "idle",
                        progress: 0,
                        last_error: null,
                        has_docs: false,
                        has_meshchatx_docs: true,
                        has_bundled_docs: false,
                        has_user_docs: false,
                        versions: [],
                        current_version: null,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) {
                return Promise.resolve({ data: structuredList });
            }
            if (url.includes("/api/v1/meshchatx-docs/content")) {
                return Promise.reject({
                    response: { data: { error: "Document not found" } },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();
        await nextTick();

        expect(wrapper.vm.docLoadError).toBe("Document not found");
        expect(wrapper.text()).toContain("docs.load_doc_failed");
    });

    it("shows manifest warning when list includes manifest_error", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "idle",
                        progress: 0,
                        last_error: null,
                        has_docs: false,
                        has_meshchatx_docs: true,
                        has_bundled_docs: false,
                        has_user_docs: false,
                        versions: [],
                        current_version: null,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) {
                return Promise.resolve({
                    data: { ...structuredList, manifest_error: "Invalid manifest JSON" },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/content")) {
                return Promise.resolve({
                    data: { html: "<p>ok</p>", content: "ok", type: "markdown" },
                });
            }
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        expect(wrapper.vm.manifestWarning).toBe("docs.manifest_warning");
        expect(wrapper.text()).toContain("docs.manifest_warning");
    });

    it("extractDocToc returns empty array for invalid html", () => {
        const wrapper = mountDocsPage();
        expect(wrapper.vm.extractDocToc("")).toEqual([]);
        expect(wrapper.vm.extractDocToc("<p>no headings</p>")).toEqual([]);
    });

    it("navigateTo selects nested meshchatx docs from search results", async () => {
        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();

        const selectSpy = vi.spyOn(wrapper.vm, "selectDoc");
        wrapper.vm.navigateTo("/meshchatx-docs/en/getting-started.md");
        await nextTick();

        expect(wrapper.vm.activeTab).toBe("meshchatx");
        expect(selectSpy).toHaveBeenCalledWith("en/getting-started.md");
        expect(wrapper.vm.searchQuery).toBe("");
    });

    it("shows search error state when search request fails", async () => {
        const wrapper = mountDocsPage();
        await nextTick();

        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/search")) {
                return Promise.reject(new Error("network down"));
            }
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "idle",
                        progress: 0,
                        last_error: null,
                        has_docs: true,
                        has_meshchatx_docs: true,
                        has_bundled_docs: true,
                        has_user_docs: false,
                        versions: [],
                        current_version: null,
                    },
                });
            }
            if (url.includes("/api/v1/meshchatx-docs/list")) {
                return Promise.resolve({ data: structuredList });
            }
            return Promise.resolve({ data: {} });
        });

        wrapper.vm.searchQuery = "reticulum";
        await wrapper.vm.performSearch();
        await nextTick();

        expect(wrapper.vm.searchError).toBe("docs.search_failed");
        expect(wrapper.text()).toContain("docs.search_failed");
    });

    it("scrollToHeading targets the rendered article element", async () => {
        const wrapper = mountDocsPage();
        await nextTick();
        await nextTick();
        await nextTick();

        const intro = wrapper.vm.$refs.docsProse.querySelector("#intro");
        intro.scrollIntoView = vi.fn();

        wrapper.vm.scrollToHeading("intro");

        expect(intro.scrollIntoView).toHaveBeenCalled();
    });

    it("onReticulumFrameLoad reveals the iframe", async () => {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/api/v1/docs/status")) {
                return Promise.resolve({
                    data: {
                        status: "idle",
                        progress: 100,
                        last_error: null,
                        has_docs: true,
                        has_meshchatx_docs: false,
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

        wrapper.vm.$refs.docsFrame = { style: { opacity: "0" } };
        wrapper.vm.onReticulumFrameLoad();
        expect(wrapper.vm.$refs.docsFrame.style.opacity).toBe("1");
    });
});
