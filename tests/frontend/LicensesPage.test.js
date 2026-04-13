import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LicensesPage from "@/components/licenses/LicensesPage.vue";

window.api = {
    get: vi.fn(),
};

describe("LicensesPage.vue", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("loads licenses from the API and renders rows", async () => {
        window.api.get.mockResolvedValue({
            data: {
                backend: [{ name: "alpha-be", version: "1.0.0", author: "A", license: "MIT" }],
                frontend: [{ name: "zebra-fe", version: "2.0.0", author: "Z", license: "Apache-2.0" }],
                meta: {
                    generated_at: "2020-01-01T00:00:00Z",
                    frontend_source: "pnpm",
                },
            },
        });

        const wrapper = mount(LicensesPage, {
            global: {
                mocks: { $t: (key, params) => (params ? `${key}:${JSON.stringify(params)}` : key) },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<span class="mdi-stub" />',
                        props: ["iconName"],
                    },
                },
            },
        });

        await new Promise((resolve) => setTimeout(resolve, 10));
        await wrapper.vm.$nextTick();

        expect(window.api.get).toHaveBeenCalledWith("/api/v1/licenses");
        expect(wrapper.text()).toContain("alpha-be");
        expect(wrapper.text()).toContain("zebra-fe");
    });

    it("filters both sections with the search query", async () => {
        window.api.get.mockResolvedValue({
            data: {
                backend: [{ name: "keep-be", version: "1", author: "x", license: "MIT" }],
                frontend: [{ name: "other-fe", version: "2", author: "y", license: "MIT" }],
                meta: {},
            },
        });

        const wrapper = mount(LicensesPage, {
            global: {
                mocks: { $t: (key) => key },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<span class="mdi-stub" />',
                        props: ["iconName"],
                    },
                },
            },
        });

        await new Promise((resolve) => setTimeout(resolve, 10));
        await wrapper.vm.$nextTick();

        await wrapper.find('input[type="search"]').setValue("keep-be");
        expect(wrapper.vm.filteredBackend.length).toBe(1);
        expect(wrapper.vm.filteredFrontend.length).toBe(0);

        await wrapper.find('input[type="search"]').setValue("other-fe");
        expect(wrapper.vm.filteredBackend.length).toBe(0);
        expect(wrapper.vm.filteredFrontend.length).toBe(1);
    });
});
