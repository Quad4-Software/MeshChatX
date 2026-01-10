import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import BlockedPage from "@/components/blocked/BlockedPage.vue";
import GlobalState from "@/js/GlobalState";

describe("BlockedPage.vue (Banished UI)", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
            delete: vi.fn(),
        };
        window.axios = axiosMock;

        // Mock localization
        const t = (key) => {
            const translations = {
                "common.save": "Save",
                "common.cancel": "Cancel",
            };
            return translations[key] || key;
        };

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/blocked-destinations") {
                return Promise.resolve({
                    data: {
                        blocked_destinations: [
                            { destination_hash: "a".repeat(32), created_at: "2026-01-04T12:00:00Z" },
                        ],
                    },
                });
            }
            if (url === "/api/v1/reticulum/blackhole") {
                return Promise.resolve({
                    data: {
                        blackholed_identities: {
                            ["b".repeat(32)]: {
                                source: "c".repeat(32),
                                reason: "Spam",
                                until: null,
                            },
                        },
                    },
                });
            }
            if (url === "/api/v1/announces") {
                return Promise.resolve({ data: { announces: [] } });
            }
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.axios;
    });

    const mountBlockedPage = () => {
        return mount(BlockedPage, {
            global: {
                mocks: {
                    $t: (key) => {
                        const translations = {
                            "banishment.title": "Banished",
                            "banishment.description": "Manage Banished users and nodes",
                            "banishment.lift_banishment": "Lift Banishment",
                            "banishment.user": "User",
                            "banishment.node": "Node",
                            "banishment.banished_at": "Banished at",
                        };
                        return translations[key] || key;
                    },
                },
                stubs: {
                    MaterialDesignIcon: {
                        template: '<div class="mdi-stub" :data-icon-name="iconName"></div>',
                        props: ["iconName"],
                    },
                },
            },
        });
    };

    it("displays 'Banished' title and subtext", async () => {
        const wrapper = mountBlockedPage();
        // Wait for isLoading to become false
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        expect(wrapper.text()).toContain("Banished");
        expect(wrapper.text()).toContain("Manage Banished users and nodes");
    });

    it("combines local blocked and RNS blackholed items", async () => {
        const wrapper = mountBlockedPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        expect(wrapper.vm.allBlockedItems.length).toBe(2);

        const rnsItem = wrapper.vm.allBlockedItems.find((i) => i.is_rns_blackholed);
        expect(rnsItem).toBeDefined();
        expect(rnsItem.destination_hash).toBe("b".repeat(32));
        expect(rnsItem.rns_reason).toBe("Spam");
    });

    it("displays RNS Blackhole badge for blackholed items", async () => {
        const wrapper = mountBlockedPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        expect(wrapper.text()).toContain("RNS Blackhole");
    });

    it("calls delete API when lifting banishment", async () => {
        // Mock DialogUtils.confirm
        const DialogUtils = await import("@/js/DialogUtils");
        vi.spyOn(DialogUtils.default, "confirm").mockResolvedValue(true);

        const wrapper = mountBlockedPage();
        await vi.waitFor(() => expect(wrapper.vm.isLoading).toBe(false));

        const unblockButtons = wrapper.findAll("button").filter((b) => b.text().includes("Lift Banishment"));
        expect(unblockButtons.length).toBeGreaterThan(0);

        await unblockButtons[0].trigger("click");

        expect(axiosMock.delete).toHaveBeenCalled();
    });
});
