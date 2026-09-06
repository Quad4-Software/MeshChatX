import { cleanup, fireEvent, render } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import Toggle from "@/ui/svelte/Toggle.svelte";

describe("Toggle UI", () => {
    afterEach(() => cleanup());

    it("renders with id", () => {
        const { container } = render(Toggle, { id: "my-toggle" });
        expect(container.querySelector("input").id).toBe("my-toggle");
    });

    it("renders label when provided", () => {
        const { container } = render(Toggle, { id: "t", label: "Enable feature" });
        expect(container.textContent).toContain("Enable feature");
    });

    it("does not render label when not provided", () => {
        const { container } = render(Toggle, { id: "t" });
        expect(container.querySelector("span")).toBeNull();
    });

    it("calls onchange when toggled", async () => {
        const onchange = vi.fn();
        const { container } = render(Toggle, { id: "t", checked: false, onchange });
        await fireEvent.click(container.querySelector("input"));
        expect(onchange).toHaveBeenCalledWith(true);
    });

    it("checkbox is checked when checked true", () => {
        const { container } = render(Toggle, { id: "t", checked: true });
        expect(container.querySelector("input").checked).toBe(true);
    });

    it("checkbox is disabled when disabled true", () => {
        const { container } = render(Toggle, { id: "t", disabled: true });
        expect(container.querySelector("input").disabled).toBe(true);
    });

    it("label has cursor-not-allowed when disabled", () => {
        const { container } = render(Toggle, { id: "t", disabled: true, label: "Off" });
        expect(container.querySelector("label").className).toContain("cursor-not-allowed");
    });
});
