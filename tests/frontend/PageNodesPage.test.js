// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, cleanup, waitFor, screen } from "@testing-library/svelte";
import PageNodesPage from "@/features/page-nodes/PageNodesPage.svelte";
import { PAGE_NODES_API_BASE } from "@/features/page-nodes/lib/constants.ts";
import { fetchPageNodes } from "@/features/page-nodes/lib/pageNodesApi.ts";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";

vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

describe("pageNodesApi", () => {
    beforeEach(() => {
        window.api = {
            get: vi.fn(async () => ({ data: [{ id: "n1", name: "Node" }] })),
            post: vi.fn(async () => ({ data: {} })),
            put: vi.fn(async () => ({ data: {} })),
            patch: vi.fn(async () => ({ data: {} })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    it("fetches page nodes from API base", async () => {
        const nodes = await fetchPageNodes();
        expect(window.api.get).toHaveBeenCalledWith(PAGE_NODES_API_BASE);
        expect(nodes).toHaveLength(1);
    });
});

describe("PageNodesPage.svelte", () => {
    beforeEach(() => {
        cleanup();
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            common: { loading: "Loading" },
            page_nodes: { title: "Page nodes" },
        });
        window.api = {
            get: vi.fn(async () => ({ data: [] })),
            post: vi.fn(async () => ({ data: {} })),
            put: vi.fn(async () => ({ data: {} })),
            patch: vi.fn(async () => ({ data: {} })),
            delete: vi.fn(async () => ({ data: {} })),
        };
    });

    it("loads page nodes on mount", async () => {
        render(PageNodesPage);
        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith(PAGE_NODES_API_BASE);
        });
    });

    it("shows empty state when no nodes are returned", async () => {
        registerFallbackMessages({
            common: { loading: "Loading" },
            page_nodes: { title: "Page nodes" },
            tools: {
                mesh_server: {
                    empty_title: "No mesh server nodes",
                    empty_description: "Create one to host pages",
                },
                back_to_tools: "Back",
            },
            app: { tools: "Tools" },
        });
        render(PageNodesPage);
        await waitFor(() => {
            expect(screen.getByText("No mesh server nodes")).toBeTruthy();
            expect(screen.getByText("Create one to host pages")).toBeTruthy();
        });
    });
});
