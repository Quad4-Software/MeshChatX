import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import IdentitiesPage from "@/components/settings/IdentitiesPage.vue";

// Mock dependencies
vi.mock("@/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn().mockResolvedValue(true),
    },
}));

vi.mock("@/js/GlobalEmitter", () => ({
    default: {
        on: vi.fn(),
        off: vi.fn(),
        emit: vi.fn(),
    },
}));

describe("IdentitiesPage.vue", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url === "/api/v1/identities") {
                    return Promise.resolve({
                        data: {
                            identities: [
                                {
                                    hash: "hash1",
                                    display_name: "Identity 1",
                                    is_current: true,
                                },
                                {
                                    hash: "hash2",
                                    display_name: "Identity 2",
                                    is_current: false,
                                },
                            ],
                        },
                    });
                }
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: { hotswapped: true } }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.axios = axiosMock;
    });

    afterEach(() => {
        delete window.axios;
        vi.clearAllMocks();
    });

    const mountPage = () => {
        return mount(IdentitiesPage, {
            global: {
                stubs: {
                    MaterialDesignIcon: { template: '<div class="mdi"></div>' },
                },
                mocks: {
                    $t: (key) => key,
                },
            },
        });
    };

    it("renders identity list correctly", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick(); // Wait for axios

        expect(wrapper.text()).toContain("Identity 1");
        expect(wrapper.text()).toContain("Identity 2");
        expect(wrapper.findAll(".glass-card").length).toBe(2);
    });

    it("opens create modal and creates identity", async () => {
        const wrapper = mountPage();
        await wrapper.find("button").trigger("click"); // New Identity button
        expect(wrapper.vm.showCreateModal).toBe(true);

        wrapper.vm.newIdentityName = "New Identity";
        await wrapper.vm.createIdentity();

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/identities/create", {
            display_name: "New Identity",
        });
        expect(wrapper.vm.showCreateModal).toBe(false);
    });

    it("switches identity", async () => {
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();

        const switchButton = wrapper.findAll("button").find((b) => b.attributes("title") === "identities.switch");
        await switchButton.trigger("click");

        expect(axiosMock.post).toHaveBeenCalledWith("/api/v1/identities/switch", {
            identity_hash: "hash2",
        });
    });

    it("performance: measures identity list rendering for many identities", async () => {
        const numIdentities = 500;
        const identities = Array.from({ length: numIdentities }, (_, i) => ({
            hash: `hash${i}`,
            display_name: `Identity ${i}`,
            is_current: i === 0,
        }));

        axiosMock.get.mockResolvedValue({ data: { identities } });

        const start = performance.now();
        const wrapper = mountPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        const end = performance.now();

        const renderTime = end - start;
        console.log(`Rendered ${numIdentities} identities in ${renderTime.toFixed(2)}ms`);

        expect(wrapper.findAll(".glass-card").length).toBe(numIdentities);
        expect(renderTime).toBeLessThan(2000); // Should be reasonably fast
    });

    it("memory: tracks growth after multiple identity list refreshes", async () => {
        const wrapper = mountPage();
        const getMemory = () => process.memoryUsage().heapUsed / (1024 * 1024);

        const initialMem = getMemory();

        for (let i = 0; i < 20; i++) {
            await wrapper.vm.getIdentities();
            await wrapper.vm.$nextTick();
        }

        const finalMem = getMemory();
        const growth = finalMem - initialMem;
        console.log(`Memory growth after 20 refreshes: ${growth.toFixed(2)}MB`);

        expect(growth).toBeLessThan(50); // Arbitrary limit for 500 identities refresh
    });
});
