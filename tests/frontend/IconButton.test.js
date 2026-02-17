import { mount } from "@vue/test-utils";
import { describe, it, expect } from "vitest";
import IconButton from "../../meshchatx/src/frontend/components/IconButton.vue";

function mountIconButton(slots = {}) {
    return mount(IconButton, {
        slots: { default: slots.default ?? "<span class=\"icon\">X</span>" },
    });
}

describe("IconButton UI", () => {
    it("renders button with slot content", () => {
        const wrapper = mountIconButton({ default: "<span class=\"icon\">+</span>" });
        expect(wrapper.find("button").exists()).toBe(true);
        expect(wrapper.find(".icon").exists()).toBe(true);
        expect(wrapper.text()).toContain("+");
    });

    it("emits click when clicked", async () => {
        const wrapper = mountIconButton();
        await wrapper.find("button").trigger("click");
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("has expected button classes", () => {
        const wrapper = mountIconButton();
        const btn = wrapper.find("button");
        expect(btn.classes()).toContain("rounded-full");
        expect(btn.attributes("type")).toBe("button");
    });
});
