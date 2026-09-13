import { cleanup, render } from "@testing-library/svelte";
import { afterEach, describe, expect, it } from "vitest";
import MaterialDesignIcon from "@/ui/svelte/MaterialDesignIcon.svelte";

describe("MaterialDesignIcon.svelte", () => {
    afterEach(() => cleanup());

    it("renders svg with correct aria-label", () => {
        const { container } = render(MaterialDesignIcon, { iconName: "home" });
        expect(container.querySelector("svg").getAttribute("aria-label")).toBe("home");
    });

    it("renders an svg element for valid icon", () => {
        const { container } = render(MaterialDesignIcon, { iconName: "home" });
        expect(container.querySelector("svg")).toBeTruthy();
        expect(container.querySelector("path")).toBeTruthy();
    });

    it("falls back to a path for unknown icons", () => {
        const { container } = render(MaterialDesignIcon, { iconName: "non-existent-icon" });
        expect(container.querySelector("path").getAttribute("d")).toBeTruthy();
    });

    it("accepts iconName prop", () => {
        const { container } = render(MaterialDesignIcon, { iconName: "cog" });
        expect(container.querySelector("svg").getAttribute("aria-label")).toBe("cog");
    });
});
