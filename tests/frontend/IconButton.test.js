import { cleanup, fireEvent, render } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import IconButton from "@/ui/svelte/IconButton.svelte";

describe("IconButton UI", () => {
    afterEach(() => cleanup());

    it("renders button", () => {
        const { container } = render(IconButton, { title: "Add" });
        expect(container.querySelector("button")).toBeTruthy();
        expect(container.querySelector("button").getAttribute("title")).toBe("Add");
    });

    it("calls onclick when clicked", async () => {
        const onclick = vi.fn();
        const { container } = render(IconButton, { onclick });
        await fireEvent.click(container.querySelector("button"));
        expect(onclick).toHaveBeenCalledTimes(1);
    });

    it("has expected button classes", () => {
        const { container } = render(IconButton);
        const btn = container.querySelector("button");
        expect(btn.className).toContain("rounded-full");
        expect(btn.getAttribute("type")).toBe("button");
    });
});
