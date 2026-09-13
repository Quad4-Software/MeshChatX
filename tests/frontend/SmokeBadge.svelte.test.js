// SPDX-License-Identifier: 0BSD

import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/svelte";
import SmokeBadge from "../../meshchatx/src/frontend/ui/svelte/SmokeBadge.svelte";

describe("SmokeBadge.svelte", () => {
    afterEach(() => {
        cleanup();
    });

    it("renders the default label", () => {
        const { getByTestId } = render(SmokeBadge);
        expect(getByTestId("svelte-smoke-badge").textContent).toBe("ok");
    });

    it("renders a custom label", () => {
        const { getByTestId } = render(SmokeBadge, { props: { label: "svelte5" } });
        expect(getByTestId("svelte-smoke-badge").textContent).toBe("svelte5");
    });
});
