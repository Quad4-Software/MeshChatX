import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import ToolsPage from "@/features/tools/ToolsPage.svelte";
import {
    filterTools,
    groupTools,
    loadCollapsedSections,
    saveCollapsedSections,
    toolRouteHref,
} from "@/features/tools/lib/toolsList.ts";
import { registerCoreContributions } from "@/js/registries/registerCoreContributions.js";
import { clearRoutes, registerRoute } from "@/js/registries/routeRegistry.js";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";

registerCoreContributions();

describe("toolsList helpers", () => {
    it("builds hash hrefs", () => {
        expect(toolRouteHref({ name: "ping" })).toBe("#/ping");
        expect(toolRouteHref({ name: "paper-message" })).toBe("#/tools/paper-message");
        expect(toolRouteHref({ name: "rnode-flasher" })).toBe("#/tools/rnode-flasher");
        expect(toolRouteHref({ path: "/rncp" })).toBe("#/rncp");
    });

    it("resolves rnode-flasher via registered path not dotted name", () => {
        clearRoutes();
        registerRoute({
            name: "rnode-flasher",
            path: "/tools/rnode-flasher",
            mount: "svelte",
            load: () => Promise.resolve({ default: {} }),
        });
        expect(toolRouteHref({ name: "rnode-flasher" })).toBe("#/tools/rnode-flasher");
        expect(toolRouteHref({ name: "rnode-flasher" })).not.toBe("#/rnode-flasher");
        clearRoutes();
    });

    it("resolves dotted route names via hashRouter path not name-as-path", () => {
        clearRoutes();
        registerRoute({
            name: "interfaces.add",
            path: "/interfaces/add",
            mount: "svelte",
            load: () => Promise.resolve({ default: {} }),
        });
        expect(toolRouteHref({ name: "interfaces.add" })).toBe("#/interfaces/add");
        expect(toolRouteHref({ name: "interfaces.add" })).not.toBe("#/interfaces.add");
        clearRoutes();
    });

    it("filters and groups tools", () => {
        const tools = [
            { name: "ping", title: "Ping", description: "reach", group: "diagnostics" },
            { name: "rncp", title: "RNCP", description: "copy", group: "transfer" },
        ];
        expect(filterTools(tools, "ping")).toHaveLength(1);
        expect(groupTools(tools)?.map((s) => s.id)).toEqual(["diagnostics", "transfer"]);
    });

    it("persists collapsed sections", () => {
        localStorage.clear();
        saveCollapsedSections({ diagnostics: true });
        expect(loadCollapsedSections()).toEqual({ diagnostics: true });
    });
});

describe("ToolsPage.svelte", () => {
    beforeEach(() => {
        localStorage.clear();
        registerTranslator(null);
        registerFallbackMessages({
            common: {
                search: "Search",
                no_results: "common.no_results",
            },
            tools: {
                power_tools: "tools.power_tools",
                search_placeholder: "Search {count} tools",
                diagnostics_description: "desc",
                alpha_badge: "tools.alpha_badge",
                beta_badge: "beta",
                coming_soon_badge: "soon",
                group: {
                    diagnostics: "Diagnostics",
                    transfer: "Transfer",
                    messaging: "Messaging",
                    network: "Network",
                    other: "Other",
                },
                ping: { title: "tools.ping.title", description: "d" },
                rnsh: { title: "tools.rnsh.title", description: "d" },
                rns_filesync: { title: "tools.rns_filesync.title", description: "d" },
            },
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("renders the tools page header", () => {
        render(ToolsPage);
        expect(screen.getByText("tools.power_tools")).toBeTruthy();
        expect(screen.queryByText("tools.utilities")).toBeNull();
    });

    it("renders tool rows", () => {
        const { container } = render(ToolsPage);
        expect(container.querySelectorAll(".tool-row").length).toBeGreaterThan(5);
    });

    it("filters tools based on search query", async () => {
        render(ToolsPage);
        const searchInput = screen.getByPlaceholderText(/Search \d+ tools/);
        await fireEvent.input(searchInput, { target: { value: "ping" } });
        await waitFor(() => {
            expect(screen.getByText("tools.ping.title")).toBeTruthy();
        });
        await fireEvent.input(searchInput, { target: { value: "nonexistenttool" } });
        expect(await screen.findByText("common.no_results")).toBeTruthy();
    });

    it("shows an alpha badge on the rnsh tool", () => {
        render(ToolsPage);
        const rnsh = screen.getByText("tools.rnsh.title").closest(".tool-row");
        expect(rnsh?.textContent).toContain("tools.alpha_badge");
    });

    it("shows an alpha badge on the rns-filesync tool", () => {
        render(ToolsPage);
        const row = screen.getByText("tools.rns_filesync.title").closest(".tool-row");
        expect(row?.textContent).toContain("tools.alpha_badge");
    });

    it("clears search query when close button is clicked", async () => {
        render(ToolsPage);
        const searchInput = screen.getByPlaceholderText(/Search \d+ tools/);
        await fireEvent.input(searchInput, { target: { value: "ping" } });
        await fireEvent.click(screen.getByLabelText("Clear search"));
        expect(searchInput.value).toBe("");
    });

    it("collapses a tools section when its header is clicked", async () => {
        render(ToolsPage);
        const toggle = screen.getByRole("button", { name: /Diagnostics/i });
        expect(toggle.getAttribute("aria-expanded")).toBe("true");
        await fireEvent.click(toggle);
        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        expect(loadCollapsedSections().diagnostics).toBe(true);
    });
});
