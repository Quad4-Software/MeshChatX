import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import SieveFiltersPage from "@/components/tools/SieveFiltersPage.vue";
import { createRouter, createWebHistory } from "vue-router";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
    },
}));

describe("SieveFiltersPage.vue", () => {
    const router = createRouter({
        history: createWebHistory(),
        routes: [{ path: "/tools", name: "tools", component: { template: "<div/>" } }],
    });

    beforeEach(() => {
        vi.clearAllMocks();
        global.api.get = vi.fn((url) => {
            if (url.includes("sieve-filters")) {
                return Promise.resolve({
                    data: {
                        filters: [
                            {
                                id: "r1",
                                enabled: true,
                                terms: ["spam"],
                                action: "ignore",
                                folder_id: null,
                            },
                        ],
                    },
                });
            }
            if (url.includes("folders")) {
                return Promise.resolve({ data: [{ id: 1, name: "Inbox" }] });
            }
            return Promise.resolve({ data: {} });
        });
        global.api.put = vi.fn(() =>
            Promise.resolve({
                data: {
                    filters: [
                        {
                            id: "r1",
                            enabled: true,
                            terms: ["spam"],
                            action: "ignore",
                            folder_id: null,
                        },
                    ],
                },
            })
        );
        window.api = global.api;
    });

    it("loads filters and folders from the API", async () => {
        const wrapper = mount(SieveFiltersPage, {
            global: {
                plugins: [router],
                mocks: { $t: (k) => k },
                stubs: {
                    MaterialDesignIcon: { template: "<span/>", props: ["iconName"] },
                    SieveFlowNetwork: { template: "<div class='sieve-flow-stub'/>" },
                    RouterLink: { template: "<a><slot/></a>", props: ["to"] },
                },
            },
        });
        await Promise.resolve();
        await wrapper.vm.$nextTick();
        await Promise.resolve();
        expect(global.api.get).toHaveBeenCalled();
        expect(wrapper.vm.filters.length).toBe(1);
        expect(wrapper.vm.filters[0].terms).toEqual(["spam"]);
        expect(wrapper.vm.folders.length).toBe(1);
    });

    it("saves filters via PUT", async () => {
        const wrapper = mount(SieveFiltersPage, {
            global: {
                plugins: [router],
                mocks: { $t: (k) => k },
                stubs: {
                    MaterialDesignIcon: { template: "<span/>", props: ["iconName"] },
                    SieveFlowNetwork: { template: "<div/>" },
                    RouterLink: { template: "<a><slot/></a>", props: ["to"] },
                },
            },
        });
        await Promise.resolve();
        await wrapper.vm.$nextTick();
        await Promise.resolve();
        await wrapper.vm.save();
        expect(global.api.put).toHaveBeenCalledWith(
            "/api/v1/lxmf/sieve-filters",
            expect.objectContaining({
                filters: expect.arrayContaining([
                    expect.objectContaining({
                        match_peer_fields: true,
                        match_message: false,
                        match_mode: "substring",
                    }),
                ]),
            })
        );
        expect(ToastUtils.success).toHaveBeenCalled();
    });
});
