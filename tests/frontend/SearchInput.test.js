import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import SearchInput from "@/components/SearchInput.vue";

const mountInput = (props = {}, attrs = {}) =>
    mount(SearchInput, {
        props: { modelValue: "", ...props },
        attrs,
        global: {
            mocks: { $t: (k) => k },
            stubs: { MaterialDesignIcon: true },
        },
    });

describe("SearchInput.vue", () => {
    it("renders the placeholder and emits update:modelValue on input", async () => {
        const wrapper = mountInput({ placeholder: "Search tools..." });
        const input = wrapper.find("input");
        expect(input.attributes("placeholder")).toBe("Search tools...");
        expect(input.classes()).toContain("search-input");

        await input.setValue("abc");
        expect(wrapper.emitted("update:modelValue")).toEqual([["abc"]]);
    });

    it("shows a clear button only when non-empty and clears on click", async () => {
        const wrapper = mountInput({ modelValue: "x" });
        expect(wrapper.find("button").exists()).toBe(true);

        await wrapper.find("button").trigger("click");
        expect(wrapper.emitted("update:modelValue")).toEqual([[""]]);
        expect(wrapper.emitted("clear")).toBeTruthy();
    });

    it("hides the clear button when the model is empty", () => {
        const wrapper = mountInput({ modelValue: "" });
        expect(wrapper.find("button").exists()).toBe(false);
    });

    it("clears on Escape", async () => {
        const wrapper = mountInput({ modelValue: "abc" });
        await wrapper.find("input").trigger("keydown", { key: "Escape" });
        expect(wrapper.emitted("update:modelValue")).toEqual([[""]]);
    });

    it("shows a loading spinner instead of the clear button when loading", () => {
        const wrapper = mountInput({ modelValue: "abc", loading: true });
        expect(wrapper.find("button").exists()).toBe(false);
        expect(wrapper.html()).toContain("animate-spin");
    });

    it("applies the compact class when compact", () => {
        const wrapper = mountInput({ compact: true });
        expect(wrapper.find("input").classes()).toContain("search-input-compact");
    });

    it("forwards attrs like type, id and aria-label to the inner input", () => {
        const wrapper = mountInput({}, { type: "search", id: "x", "aria-label": "find" });
        const input = wrapper.find("input");
        expect(input.attributes("type")).toBe("search");
        expect(input.attributes("id")).toBe("x");
        expect(input.attributes("aria-label")).toBe("find");
    });
});
