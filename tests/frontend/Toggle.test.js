import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import Toggle from "../../meshchatx/src/frontend/components/forms/Toggle.vue";

function mountToggle(props = {}, options = {}) {
    return mount(Toggle, {
        props: { id: "test-toggle", ...props },
        ...options,
    });
}

describe("Toggle UI", () => {
    it("renders with id", () => {
        const wrapper = mountToggle({ id: "my-toggle" });
        const input = wrapper.find("input");
        expect(input.attributes("id")).toBe("my-toggle");
    });

    it("renders label when provided", () => {
        const wrapper = mountToggle({ label: "Enable feature" });
        expect(wrapper.text()).toContain("Enable feature");
    });

    it("does not render label when not provided", () => {
        const wrapper = mountToggle();
        expect(wrapper.find("span.ml-3").exists()).toBe(false);
    });

    it("emits update:modelValue when toggled", async () => {
        const wrapper = mountToggle({ modelValue: false });
        await wrapper.find("input").setValue(true);
        expect(wrapper.emitted("update:modelValue")).toEqual([[true]]);
    });

    it("checkbox is checked when modelValue true", () => {
        const wrapper = mountToggle({ modelValue: true });
        expect(wrapper.find("input").element.checked).toBe(true);
    });

    it("checkbox is disabled when disabled true", () => {
        const wrapper = mountToggle({ disabled: true });
        expect(wrapper.find("input").attributes("disabled")).toBeDefined();
    });

    it("label has cursor-not-allowed when disabled", () => {
        const wrapper = mountToggle({ disabled: true, label: "Off" });
        expect(wrapper.find("label").classes()).toContain("cursor-not-allowed");
    });
});
