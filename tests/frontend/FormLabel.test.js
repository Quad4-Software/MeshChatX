import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import FormLabel from "@/components/forms/FormLabel.vue";

describe("FormLabel.vue", () => {
    it("renders slot content", () => {
        const wrapper = mount(FormLabel, {
            slots: {
                default: "Label Text",
            },
        });
        expect(wrapper.text()).toBe("Label Text");
    });

    it("has correct classes", () => {
        const wrapper = mount(FormLabel);
        expect(wrapper.classes()).toContain("block");
        expect(wrapper.classes()).toContain("text-sm");
    });

    it("uses label element", () => {
        const wrapper = mount(FormLabel);
        expect(wrapper.element.tagName).toBe("LABEL");
    });

    it("applies for attribute when provided", () => {
        const wrapper = mount(FormLabel, {
            props: { for: "email-input" },
            slots: { default: "Email" },
        });
        expect(wrapper.attributes("for")).toBe("email-input");
    });

    it("renders empty when slot is empty", () => {
        const wrapper = mount(FormLabel, { slots: { default: "" } });
        expect(wrapper.text()).toBe("");
    });
});
