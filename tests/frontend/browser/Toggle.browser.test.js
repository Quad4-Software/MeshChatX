// SPDX-License-Identifier: 0BSD
import { describe, it, expect } from "vitest";
import { render } from "vitest-browser-svelte";
import { page } from "vitest/browser";
import Toggle from "../../../meshchatx/src/frontend/ui/svelte/Toggle.svelte";

describe("Toggle (browser)", () => {
    it("toggles checked state on real click", async () => {
        const result = await render(Toggle, {
            id: "browser-toggle",
            checked: false,
            label: "Browser toggle",
        });

        const checkbox = page.getByRole("checkbox", { name: "Browser toggle" });
        await expect.element(checkbox).not.toBeChecked();
        await checkbox.click();
        await expect.element(checkbox).toBeChecked();

        await result.unmount();
    });
});
