import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BlockedPage from "../../meshchatx/src/frontend/components/blocked/BlockedPage.vue";

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({
    default: { confirm: vi.fn().mockResolvedValue(true) },
}));
vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({ default: { success: vi.fn(), error: vi.fn() } }));
vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: { formatTimeAgo: (d) => "1h ago" },
}));

const MaterialDesignIcon = { template: '<div class="mdi"></div>', props: ["iconName"] };

function mountBlockedPage() {
    return mount(BlockedPage, {
        global: {
            components: { MaterialDesignIcon },
            mocks: { $t: (key) => key },
        },
    });
}

describe("BlockedPage UI", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        global.api.get = vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/blocked-destinations") return Promise.resolve({ data: { blocked_destinations: [] } });
            if (url === "/api/v1/reticulum/blackhole") return Promise.resolve({ data: { blackholed_identities: {} } });
            return Promise.resolve({ data: {} });
        });
    });

    it("renders title and description", async () => {
        const wrapper = mountBlockedPage();
        await flushPromises();
        expect(wrapper.text()).toContain("banishment.title");
        expect(wrapper.text()).toContain("banishment.description");
    });

    it("renders search input and refresh button", async () => {
        const wrapper = mountBlockedPage();
        await flushPromises();
        expect(wrapper.find('input[type="text"]').exists()).toBe(true);
        expect(wrapper.find("button").exists()).toBe(true);
    });

    it("shows loading state initially then empty state", async () => {
        const wrapper = mountBlockedPage();
        await flushPromises();
        expect(wrapper.vm.isLoading).toBe(false);
        expect(wrapper.text()).toMatch(/banishment\.no_items|nomadnet\.no_announces_yet|banishment\.loading_items/);
    });

    it("renders blocked items when provided", async () => {
        global.api.get = vi.fn().mockImplementation((url, opts) => {
            if (url === "/api/v1/blocked-destinations")
                return Promise.resolve({ data: { blocked_destinations: [{ destination_hash: "abc123" }] } });
            if (url === "/api/v1/reticulum/blackhole") return Promise.resolve({ data: { blackholed_identities: {} } });
            if (url === "/api/v1/announces" && opts?.params?.destination_hash === "abc123")
                return Promise.resolve({
                    data: {
                        announces: [
                            {
                                destination_hash: "abc123",
                                display_name: "Blocked User",
                                identity_hash: "abc123",
                                is_node: false,
                            },
                        ],
                    },
                });
            return Promise.resolve({ data: {} });
        });
        const wrapper = mountBlockedPage();
        await flushPromises();
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.allBlockedIdentities).toHaveLength(1);
        expect(wrapper.vm.allBlockedIdentities[0].display_name).toBe("Blocked User");
        expect(wrapper.text()).toContain("Blocked User");
        expect(wrapper.text()).toContain("abc123");
    });

    it("search input binds to searchQuery", async () => {
        const wrapper = mountBlockedPage();
        await flushPromises();
        const input = wrapper.find('input[type="text"]');
        await input.setValue("test");
        expect(wrapper.vm.searchQuery).toBe("test");
    });

    it("supports multi-select mode for bulk unban", async () => {
        global.api.get = vi.fn().mockImplementation((url, opts) => {
            if (url === "/api/v1/blocked-destinations")
                return Promise.resolve({
                    data: {
                        blocked_destinations: [{ destination_hash: "abc123" }, { destination_hash: "def456" }],
                    },
                });
            if (url === "/api/v1/reticulum/blackhole") return Promise.resolve({ data: { blackholed_identities: {} } });
            if (url === "/api/v1/announces") {
                const hash = opts?.params?.destination_hash;
                return Promise.resolve({
                    data: {
                        announces: [
                            {
                                destination_hash: hash,
                                display_name: hash === "abc123" ? "User A" : "User B",
                                identity_hash: hash,
                                is_node: false,
                            },
                        ],
                    },
                });
            }
            return Promise.resolve({ data: {} });
        });
        global.api.delete = vi.fn().mockResolvedValue({});

        const wrapper = mountBlockedPage();
        await flushPromises();

        expect(wrapper.findAll('input[type="checkbox"]').length).toBe(0);
        await wrapper
            .findAll("button")
            .find((b) => b.text() === "common.select")
            .trigger("click");
        expect(wrapper.vm.selectMode).toBe(true);
        expect(wrapper.findAll('input[type="checkbox"]').length).toBeGreaterThan(0);

        wrapper.vm.selectedIdentities = ["abc123", "def456"];
        await wrapper.vm.$nextTick();

        const liftSelected = wrapper.findAll("button").find((b) => b.text().includes("banishment.lift_selected"));
        expect(liftSelected).toBeTruthy();
        await liftSelected.trigger("click");
        await flushPromises();

        expect(global.api.delete).toHaveBeenCalledTimes(2);
        expect(wrapper.vm.selectMode).toBe(false);
    });
});
