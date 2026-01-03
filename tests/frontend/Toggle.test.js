import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";

describe("Toggle.vue", () => {
    it("renders label when provided", () => {
        const wrapper = mount(Toggle, {
            props: { id: "test-toggle", label: "Test Label" },
        });
        expect(wrapper.text()).toContain("Test Label");
    });

    it("emits update:modelValue on change", async () => {
        const wrapper = mount(Toggle, {
            props: { id: "test-toggle", modelValue: false },
        });
        const input = wrapper.find("input");
        await input.setChecked(true);
        expect(wrapper.emitted("update:modelValue")[0]).toEqual([true]);
    });

    it("reflects modelValue prop", () => {
        const wrapper = mount(Toggle, {
            props: { id: "test-toggle", modelValue: true },
        });
        expect(wrapper.find("input").element.checked).toBe(true);
    });
});
