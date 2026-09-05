import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, cleanup, fireEvent, waitFor, screen } from "@testing-library/svelte";
import LicensesPage from "@/features/licenses/LicensesPage.svelte";
import { filterLicenseRows } from "@/features/licenses/lib/licenseFilter.ts";
import { registerFallbackMessages, registerTranslator } from "@/js/i18n.js";

window.api = {
    get: vi.fn(),
};

describe("filterLicenseRows", () => {
    it("filters by package blob", () => {
        const rows = [
            { name: "keep-be", version: "1", author: "x", license: "MIT" },
            { name: "other-fe", version: "2", author: "y", license: "MIT" },
        ];
        expect(filterLicenseRows(rows, "keep-be")).toHaveLength(1);
        expect(filterLicenseRows(rows, "other-fe")[0].name).toBe("other-fe");
        expect(filterLicenseRows(rows, "")).toHaveLength(2);
    });
});

describe("LicensesPage.svelte", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        registerTranslator(null);
        registerFallbackMessages({
            licenses: {
                section_label: "licenses.section_label",
                title: "licenses.title",
                description: "licenses.description",
                generated_at: "licenses.generated_at",
                frontend_source: "licenses.frontend_source",
                search_placeholder: "Search",
                backend_section: "licenses.backend_section",
                frontend_section: "licenses.frontend_section",
                col_package: "Pkg",
                col_version: "Ver",
                col_author: "Auth",
                col_license: "Lic",
            },
            common: { loading: "Loading", no_results: "None" },
        });
    });

    afterEach(() => {
        cleanup();
    });

    it("loads licenses from the API and renders rows", async () => {
        window.api.get.mockResolvedValue({
            data: {
                backend: [{ name: "alpha-be", version: "1.0.0", author: "A", license: "MIT" }],
                frontend: [{ name: "zebra-fe", version: "2.0.0", author: "Z", license: "Apache-2.0" }],
                meta: {
                    generated_at: "2020-01-01T00:00:00Z",
                    frontend_source: "pnpm",
                },
            },
        });

        render(LicensesPage);

        await waitFor(() => {
            expect(window.api.get).toHaveBeenCalledWith("/api/v1/licenses");
        });
        expect(await screen.findByText("alpha-be")).toBeTruthy();
        expect(screen.getByText("zebra-fe")).toBeTruthy();
    });

    it("filters both sections with the search query", async () => {
        window.api.get.mockResolvedValue({
            data: {
                backend: [{ name: "keep-be", version: "1", author: "x", license: "MIT" }],
                frontend: [{ name: "other-fe", version: "2", author: "y", license: "MIT" }],
                meta: {},
            },
        });

        render(LicensesPage);
        await screen.findByText("keep-be");

        const input = screen.getByPlaceholderText("Search");
        await fireEvent.input(input, { target: { value: "keep-be" } });
        expect(screen.getByText("keep-be")).toBeTruthy();
        expect(screen.queryByText("other-fe")).toBeNull();

        await fireEvent.input(input, { target: { value: "other-fe" } });
        expect(screen.getByText("other-fe")).toBeTruthy();
        expect(screen.queryByText("keep-be")).toBeNull();
    });
});
