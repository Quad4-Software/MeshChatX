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

    it("uses checkbox input with correct id", () => {
        const wrapper = mount(Toggle, {
            props: { id: "my-toggle", modelValue: false },
        });
        const input = wrapper.find("input");
        expect(input.attributes("type")).toBe("checkbox");
        expect(input.attributes("id")).toBe("my-toggle");
    });

    it("binds for attribute on label to id", () => {
        const wrapper = mount(Toggle, {
            props: { id: "toggle-1", modelValue: false },
        });
        expect(wrapper.find("label").attributes("for")).toBe("toggle-1");
    });

    it("disables input when disabled prop is true", () => {
        const wrapper = mount(Toggle, {
            props: { id: "t", modelValue: false, disabled: true },
        });
        expect(wrapper.find("input").attributes("disabled")).toBeDefined();
    });

    it("does not emit when toggled while disabled", async () => {
        const wrapper = mount(Toggle, {
            props: { id: "t", modelValue: false, disabled: true },
        });
        await wrapper.find("input").trigger("change");
        expect(wrapper.emitted("update:modelValue")).toBeFalsy();
    });
});
