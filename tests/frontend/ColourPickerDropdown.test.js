// SPDX-License-Identifier: 0BSD

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ColourPickerDropdown from "@/components/ColourPickerDropdown.vue";

describe("ColourPickerDropdown.vue", () => {
    it("uses native color input and swatches instead of Vuetify", async () => {
        const wrapper = mount(ColourPickerDropdown, {
            props: { colour: "#3b82f6" },
        });
        expect(wrapper.html()).not.toContain("v-color-picker");
        wrapper.vm.showMenu();
        await wrapper.vm.$nextTick();
        expect(wrapper.find('input[type="color"]').exists()).toBe(true);
        expect(wrapper.findAll("button[type='button']").length).toBeGreaterThan(0);
    });

    it("emits normalized hex without alpha channel", async () => {
        const wrapper = mount(ColourPickerDropdown, {
            props: { colour: "#3b82f6" },
        });
        wrapper.vm.showMenu();
        await wrapper.vm.$nextTick();
        await wrapper.find('input[type="color"]').setValue("#ff0000");
        const events = wrapper.emitted("update:colour");
        expect(events).toBeTruthy();
        expect(events.at(-1)).toEqual(["#ff0000"]);
    });
});
