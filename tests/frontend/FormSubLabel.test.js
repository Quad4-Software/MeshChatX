import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import FormSubLabel from "@/components/forms/FormSubLabel.vue";

describe("FormSubLabel.vue", () => {
    it("renders slot content", () => {
        const wrapper = mount(FormSubLabel, {
            slots: {
                default: "Sub Label Text",
            },
        });
        expect(wrapper.text()).toBe("Sub Label Text");
    });

    it("has correct classes", () => {
        const wrapper = mount(FormSubLabel);
        expect(wrapper.classes()).toContain("text-xs");
    });

    it("uses div as root element", () => {
        const wrapper = mount(FormSubLabel, { slots: { default: "Help" } });
        expect(wrapper.element.tagName).toBe("DIV");
    });

    it("renders empty when slot is empty", () => {
        const wrapper = mount(FormSubLabel, { slots: { default: "" } });
        expect(wrapper.text()).toBe("");
    });
});
