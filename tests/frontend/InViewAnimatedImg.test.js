// SPDX-License-Identifier: 0BSD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { attachInView } from "@/js/inViewObserver.js";
import InViewAnimatedImg from "@/features/messages/components/InViewAnimatedImg.svelte";

vi.mock("@/js/inViewObserver.js", () => ({
    attachInView: vi.fn(),
}));

describe("InViewAnimatedImg.svelte", () => {
    let reveal;
    let detach;

    beforeEach(() => {
        detach = vi.fn();
        attachInView.mockImplementation((_element, callback) => {
            reveal = callback;
            return detach;
        });
    });

    afterEach(() => {
        cleanup();
        vi.clearAllMocks();
    });

    it("shows a placeholder until the image intersects", async () => {
        const view = render(InViewAnimatedImg, {
            src: "https://example.invalid/a.gif",
            imgClass: "test-img",
            alt: "animation",
        });

        expect(view.container.querySelector("img")).toBeNull();
        expect(view.container.querySelector('[aria-hidden="true"]')).toBeTruthy();

        reveal({ isIntersecting: true });
        const image = await screen.findByAltText("animation");
        expect(image.getAttribute("src")).toBe("https://example.invalid/a.gif");
        expect(image.classList.contains("test-img")).toBe(true);
    });

    it("keeps the image visible after leaving the viewport", async () => {
        render(InViewAnimatedImg, { src: "https://example.invalid/b.gif", alt: "animation" });
        reveal({ isIntersecting: true });
        expect(await screen.findByAltText("animation")).toBeTruthy();

        reveal({ isIntersecting: false });
        expect(screen.getByAltText("animation")).toBeTruthy();
    });

    it("runs observer cleanup when unmounted", () => {
        const view = render(InViewAnimatedImg, { src: "https://example.invalid/c.gif" });
        view.unmount();
        expect(detach).toHaveBeenCalledOnce();
    });

    it("calls the click callback from the revealed image button", async () => {
        const onclick = vi.fn();
        render(InViewAnimatedImg, {
            src: "https://example.invalid/d.gif",
            alt: "animation",
            onclick,
        });
        reveal({ isIntersecting: true });

        await fireEvent.click(await screen.findByRole("button"));
        expect(onclick).toHaveBeenCalledOnce();
    });

    it("uses fit-parent wrapper and placeholder classes", () => {
        const view = render(InViewAnimatedImg, {
            src: "https://example.invalid/e.gif",
            fitParent: true,
        });

        expect(view.container.firstElementChild.className).toContain("absolute");
        expect(view.container.firstElementChild.className).toContain("inset-0");
        expect(view.container.firstElementChild.className).toContain("overflow-hidden");
        expect(view.container.querySelector('[aria-hidden="true"]').className).toContain("absolute");
        expect(view.container.querySelector('[aria-hidden="true"]').className).toContain("inset-0");
    });
});
