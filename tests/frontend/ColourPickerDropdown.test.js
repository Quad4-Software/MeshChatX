// SPDX-License-Identifier: 0BSD

import { render, fireEvent, cleanup } from "@testing-library/svelte";
import { describe, expect, it, afterEach, vi } from "vitest";
import ColourPickerDropdown from "../../meshchatx/src/frontend/features/profile/components/ColourPickerDropdown.svelte";

describe("ColourPickerDropdown.svelte", () => {
    afterEach(() => {
        cleanup();
    });

    it("uses native color input and swatches instead of Vuetify", async () => {
        const { container, getByLabelText } = render(ColourPickerDropdown, {
            props: { colour: "#3b82f6" },
        });
        expect(container.innerHTML).not.toContain("v-color-picker");
        await fireEvent.click(getByLabelText("Pick color"));
        expect(container.querySelector('input[type="color"]')).toBeTruthy();
        expect(container.querySelectorAll("button[type='button']").length).toBeGreaterThan(0);
    });

    it("updates colour via onchange without alpha channel", async () => {
        const onchange = vi.fn();
        const { container, getByLabelText } = render(ColourPickerDropdown, {
            props: { colour: "#3b82f6", onchange },
        });
        await fireEvent.click(getByLabelText("Pick color"));
        const input = container.querySelector('input[type="color"]');
        expect(input).toBeTruthy();
        await fireEvent.input(input, { target: { value: "#ff0000" } });
        expect(onchange).toHaveBeenCalledWith("#ff0000");
    });
});
