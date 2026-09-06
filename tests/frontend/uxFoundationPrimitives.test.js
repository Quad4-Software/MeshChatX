// SPDX-License-Identifier: 0BSD
import { cleanup, render } from "@testing-library/svelte";
import { afterEach, describe, expect, it } from "vitest";
import EmptyState from "@/ui/svelte/EmptyState.svelte";
import LoadingState from "@/ui/svelte/LoadingState.svelte";
import Skeleton from "@/ui/svelte/Skeleton.svelte";
import IconButton from "@/ui/svelte/IconButton.svelte";

describe("UX foundation primitives", () => {
    afterEach(() => cleanup());

    it("EmptyState uses sem border and muted foreground", () => {
        const { container } = render(EmptyState, {
            icon: "inbox",
            title: "None",
            description: "Hint",
        });
        const html = container.innerHTML;
        expect(html).toContain("border-sem-border");
        expect(html).toContain("text-sem-fg-muted");
        expect(html).not.toContain("border-gray-300");
    });

    it("LoadingState uses sem accent and reduced-motion kill", () => {
        const { container } = render(LoadingState, { message: "Loading" });
        const html = container.innerHTML;
        expect(html).toContain("text-sem-accent");
        expect(html).toContain("motion-reduce:animate-none");
        expect(html).toContain("text-sem-fg-muted");
    });

    it("Skeleton variants render pulse with sem surface", () => {
        for (const variant of ["line", "row", "avatar", "card"]) {
            const { container, unmount } = render(Skeleton, { variant });
            const html = container.innerHTML;
            expect(html).toContain("bg-sem-surface-muted");
            expect(html).toContain("animate-pulse");
            expect(html).toContain("motion-reduce:animate-none");
            unmount();
        }
    });

    it("IconButton exposes focus-ring and press feedback", () => {
        const { container } = render(IconButton);
        const html = container.innerHTML;
        expect(html).toContain("focus-ring-sem");
        expect(html).toContain("press-feedback");
        expect(html).toContain("min-h-11");
    });
});
