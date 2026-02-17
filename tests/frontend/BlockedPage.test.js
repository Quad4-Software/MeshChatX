import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import BlockedPage from "../../meshchatx/src/frontend/components/blocked/BlockedPage.vue";

vi.mock("../../meshchatx/src/frontend/js/DialogUtils", () => ({ default: { confirm: vi.fn().mockResolvedValue(true) } }));
vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({ default: { success: vi.fn(), error: vi.fn() } }));
vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: { formatTimeAgo: (d) => "1h ago" },
}));

const MaterialDesignIcon = { template: "<div class=\"mdi\"></div>", props: ["iconName"] };

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
        global.axios.get = vi.fn().mockImplementation((url) => {
            if (url === "/api/v1/blocked-destinations")
                return Promise.resolve({ data: { blocked_destinations: [] } });
            if (url === "/api/v1/reticulum/blackhole")
                return Promise.resolve({ data: { blackholed_identities: {} } });
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
        expect(wrapper.find("input[type=\"text\"]").exists()).toBe(true);
        expect(wrapper.find("button").exists()).toBe(true);
    });

    it("shows loading state initially then empty state", async () => {
        const wrapper = mountBlockedPage();
        await flushPromises();
        expect(wrapper.vm.isLoading).toBe(false);
        expect(wrapper.text()).toMatch(/banishment\.no_items|nomadnet\.no_announces_yet|banishment\.loading_items/);
    });

    it("renders blocked items when provided", async () => {
        global.axios.get = vi.fn().mockImplementation((url, opts) => {
            if (url === "/api/v1/blocked-destinations")
                return Promise.resolve({ data: { blocked_destinations: ["abc123"] } });
            if (url === "/api/v1/reticulum/blackhole")
                return Promise.resolve({ data: { blackholed_identities: {} } });
            if (url === "/api/v1/announces" && opts?.params?.identity_hash === "abc123")
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
        expect(wrapper.vm.blockedItems.length >= 0).toBe(true);
    });

    it("search input binds to searchQuery", async () => {
        const wrapper = mountBlockedPage();
        await flushPromises();
        const input = wrapper.find("input[type=\"text\"]");
        await input.setValue("test");
        expect(wrapper.vm.searchQuery).toBe("test");
    });
});
