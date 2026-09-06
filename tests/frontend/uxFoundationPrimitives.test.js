// SPDX-License-Identifier: 0BSD
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import EmptyState from "@/components/EmptyState.vue";
import LoadingState from "@/components/LoadingState.vue";
import Skeleton from "@/components/Skeleton.vue";
import IconButton from "@/components/IconButton.vue";

describe("UX foundation primitives", () => {
    it("EmptyState uses sem border and muted foreground", () => {
        const wrapper = mount(EmptyState, {
            props: {
                icon: "inbox",
                title: "None",
                description: "Hint",
            },
            global: {
                stubs: { MaterialDesignIcon: true },
            },
        });
        const html = wrapper.html();
        expect(html).toContain("border-sem-border");
        expect(html).toContain("text-sem-fg-muted");
        expect(html).not.toContain("border-gray-300");
    });

    it("LoadingState uses sem accent and reduced-motion kill", () => {
        const wrapper = mount(LoadingState, {
            props: { message: "Loading" },
            global: {
                stubs: { MaterialDesignIcon: true },
            },
        });
        const html = wrapper.html();
        expect(html).toContain("text-sem-accent");
        expect(html).toContain("motion-reduce:animate-none");
        expect(html).toContain("text-sem-fg-muted");
    });

    it("Skeleton variants render pulse with sem surface", () => {
        for (const variant of ["line", "row", "avatar", "card"]) {
            const wrapper = mount(Skeleton, { props: { variant } });
            const html = wrapper.html();
            expect(html).toContain("bg-sem-surface-muted");
            expect(html).toContain("animate-pulse");
            expect(html).toContain("motion-reduce:animate-none");
        }
    });

    it("IconButton exposes focus-ring and press feedback", () => {
        const wrapper = mount(IconButton, {
            slots: { default: "<span>x</span>" },
        });
        const html = wrapper.html();
        expect(html).toContain("focus-ring-sem");
        expect(html).toContain("press-feedback");
        expect(html).toContain("min-h-11");
    });
});
