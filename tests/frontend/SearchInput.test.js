// SPDX-License-Identifier: 0BSD

import { render, fireEvent, cleanup } from "@testing-library/svelte";
import { describe, expect, it, afterEach, vi } from "vitest";
import SearchInput from "../../meshchatx/src/frontend/ui/svelte/SearchInput.svelte";

describe("SearchInput.svelte", () => {
    afterEach(() => {
        cleanup();
    });

    it("renders the placeholder and updates value on input", async () => {
        const { container } = render(SearchInput, {
            props: { placeholder: "Search tools..." },
        });
        const input = container.querySelector("input");
        expect(input.getAttribute("placeholder")).toBe("Search tools...");
        expect(input.className).toContain("search-input");

        await fireEvent.input(input, { target: { value: "abc" } });
        expect(input.value).toBe("abc");
    });

    it("shows a clear button only when non-empty and clears on click", async () => {
        const onclear = vi.fn();
        const { container } = render(SearchInput, {
            props: { value: "x", onclear },
        });
        const btn = container.querySelector("button");
        expect(btn).toBeTruthy();

        await fireEvent.click(btn);
        expect(container.querySelector("input").value).toBe("");
        expect(onclear).toHaveBeenCalled();
    });

    it("hides the clear button when the model is empty", () => {
        const { container } = render(SearchInput, {
            props: { value: "" },
        });
        expect(container.querySelector("button")).toBeNull();
    });

    it("clears on Escape", async () => {
        const onclear = vi.fn();
        const { container } = render(SearchInput, {
            props: { value: "abc", onclear },
        });
        await fireEvent.keyDown(container.querySelector("input"), { key: "Escape" });
        expect(container.querySelector("input").value).toBe("");
        expect(onclear).toHaveBeenCalled();
    });

    it("shows a loading spinner instead of the clear button when loading", () => {
        const { container } = render(SearchInput, {
            props: { value: "abc", loading: true },
        });
        expect(container.querySelector("button")).toBeNull();
        expect(container.innerHTML).toContain("animate-spin");
    });
});
