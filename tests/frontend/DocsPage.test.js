// SPDX-License-Identifier: 0BSD

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { render, cleanup, waitFor } from "@testing-library/svelte";
import DocsPage from "@/features/docs/DocsPage.svelte";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";
import { extractDocToc, highlightMatch, resolveRelativeDocPath } from "@/features/docs/lib/docsToc.ts";
import {
    deleteDocsVersion,
    fetchDocContent,
    fetchDocsStatus,
    fetchMeshChatXDocsList,
    searchDocs,
    switchDocsVersion,
    uploadDocsZip,
} from "@/features/docs/lib/docsApi.ts";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
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

describe("docsToc utilities", () => {
    it("extracts TOC headings from html", () => {
        const html = '<h2 id="intro">Intro Heading</h2><p>text</p><h3 id="sub">Sub Heading</h3>';
        const toc = extractDocToc(html);
        expect(toc).toHaveLength(2);
        expect(toc[0]).toEqual({ id: "intro", text: "Intro Heading", level: 2 });
        expect(toc[1]).toEqual({ id: "sub", text: "Sub Heading", level: 3 });
    });

    it("highlights matching search query text", () => {
        const res = highlightMatch("Hello Reticulum World", "Reticulum");
        expect(res).toContain("Reticulum");
        expect(res).toContain("<span");
    });

    it("resolves relative doc path", () => {
        expect(resolveRelativeDocPath("en/guide/intro.md", "advanced.md")).toBe("en/guide/advanced.md");
    });
});

describe("docsApi", () => {
    beforeEach(() => {
        window.api = {
            get: vi.fn(async (url) => {
                if (url.includes("/api/v1/docs/status")) {
                    return {
                        data: {
                            status: "idle",
                            progress: 0,
                            last_error: null,
                            has_docs: true,
                            has_meshchatx_docs: true,
                            has_bundled_docs: false,
                            has_user_docs: false,
                            versions: [],
                            current_version: null,
                        },
                    };
                }
                if (url.includes("/api/v1/meshchatx-docs/list")) {
                    return { data: structuredList };
                }
                if (url.includes("/api/v1/meshchatx-docs/content")) {
                    return {
                        data: {
                            html: '<h2 id="intro">Intro</h2>',
                            content: "## Intro\n",
                            type: "markdown",
                        },
                    };
                }
                if (url.includes("/api/v1/docs/search")) {
                    return {
                        data: {
                            results: [
                                {
                                    title: "Intro",
                                    path: "en/intro.md",
                                    snippet: "Intro snippet",
                                    section: "Overview",
                                },
                            ],
                        },
                    };
                }
                return { data: {} };
            }),
            post: vi.fn(async () => ({ data: {} })),
            patch: vi.fn(async () => ({ data: {} })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    it("fetches docs status and list", async () => {
        const status = await fetchDocsStatus();
        expect(status.status).toBe("idle");
        const list = await fetchMeshChatXDocsList("en");
        expect(list.sections).toHaveLength(1);
    });

    it("fetches content and search", async () => {
        const doc = await fetchDocContent("en/getting-started.md");
        expect(doc.html).toContain("Intro");
        const results = await searchDocs("query", "en");
        expect(results).toHaveLength(1);
        expect(results[0].title).toBe("Intro");
    });

    it("switches version and deletes version", async () => {
        await switchDocsVersion("v1.0");
        expect(window.api.post).toHaveBeenCalledWith("/api/v1/docs/switch", { version: "v1.0" });
        await deleteDocsVersion("v1.0");
        expect(window.api.delete).toHaveBeenCalledWith("/api/v1/docs/version/v1.0");
    });

    it("uploads docs zip", async () => {
        const file = new File(["zip content"], "docs.zip", { type: "application/zip" });
        await uploadDocsZip("v1.0", file);
        expect(window.api.post).toHaveBeenCalled();
    });
});

describe("DocsPage.svelte component", () => {
    beforeEach(() => {
        cleanup();
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            docs: {
                title: "Documentation",
                meshchatx_docs: "MeshChatX Docs",
                reticulum_manual: "Reticulum Manual",
                search_placeholder: "Search documentation...",
                btn_upload: "Upload Docs",
                empty_state_hint: "No documentation found",
                offline_available: "Offline available",
                offline_unavailable: "Offline unavailable",
            },
        });
        window.api = {
            get: vi.fn(async (url) => {
                if (url.includes("/api/v1/docs/status")) {
                    return {
                        data: {
                            status: "idle",
                            progress: 0,
                            last_error: null,
                            has_docs: true,
                            has_meshchatx_docs: true,
                            has_bundled_docs: true,
                            has_user_docs: false,
                            versions: ["bundled"],
                            current_version: "bundled",
                        },
                    };
                }
                if (url.includes("/api/v1/meshchatx-docs/list")) {
                    return { data: structuredList };
                }
                if (url.includes("/api/v1/meshchatx-docs/content")) {
                    return {
                        data: {
                            html: '<h2 id="intro">Intro</h2>',
                            content: "## Intro\n",
                            type: "markdown",
                        },
                    };
                }
                return { data: {} };
            }),
            post: vi.fn(async () => ({ data: {} })),
            patch: vi.fn(async () => ({ data: {} })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    afterEach(() => {
        cleanup();
    });

    it("renders page with header and content", async () => {
        const { getByTestId } = render(DocsPage);
        await waitFor(() => {
            expect(getByTestId("docs-page")).toBeTruthy();
        });
    });

    it("fetches status and list on mount", async () => {
        render(DocsPage);
        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/docs/status");
        });
    });
});
