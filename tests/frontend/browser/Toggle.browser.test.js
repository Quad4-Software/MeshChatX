// SPDX-License-Identifier: 0BSD
import { describe, it, expect, vi } from "vitest";
import { render } from "vitest-browser-svelte";
import { page } from "vitest/browser";
import ToggleTestWrapper from "./ToggleTestWrapper.svelte";

describe("Toggle (browser)", () => {
    it("toggles checked state on real click", async () => {
        const onchange = vi.fn();
        const result = await render(ToggleTestWrapper, { onchange });

        const toggle = page.getByRole("switch", { name: "Browser toggle" });
        await expect.element(toggle).not.toBeChecked();
        await toggle.click();
        await expect.element(toggle).toBeChecked();
        expect(onchange).toHaveBeenCalledWith(true);

        await result.unmount();
    });
});
