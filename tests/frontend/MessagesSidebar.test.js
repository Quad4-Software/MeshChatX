import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach } from "vitest";
import MessagesSidebar from "../../meshchatx/src/frontend/components/messages/MessagesSidebar.vue";

vi.mock("../../meshchatx/src/frontend/js/GlobalState", () => ({
    default: {
        config: {
            theme: "light",
            banished_effect_enabled: false,
            telemetry_enabled: false,
        },
        blockedDestinations: [],
    },
}));

vi.mock("../../meshchatx/src/frontend/js/Utils", () => ({
    default: {
        formatTimeAgo: vi.fn((d) => "1h ago"),
        formatDestinationHash: (h) => (h && h.length >= 8 ? h.slice(0, 8) + "…" : h),
    },
}));

import Utils from "../../meshchatx/src/frontend/js/Utils";

const MaterialDesignIcon = { template: '<div class="mdi"></div>', props: ["iconName"] };
const LxmfUserIcon = { template: '<div class="lxmf-icon"></div>' };

function defaultProps(overrides = {}) {
    return {
        peers: {},
        conversations: [],
        folders: [],
        selectedFolderId: null,
        selectedDestinationHash: "",
        isLoading: false,
        isLoadingMore: false,
        hasMoreConversations: false,
        isLoadingMoreAnnounces: false,
        hasMoreAnnounces: false,
        totalPeersCount: 0,
        ...overrides,
    };
}

function mountSidebar(props = {}, options = {}) {
    return mount(MessagesSidebar, {
        props: defaultProps(props),
        global: {
            components: { MaterialDesignIcon, LxmfUserIcon },
            mocks: { $t: (key) => key },
            directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
        },
        ...options,
    });
}

describe("MessagesSidebar UI", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders with conversations tab active by default", () => {
        const wrapper = mountSidebar();
        expect(wrapper.text()).toContain("messages.conversations");
        expect(wrapper.text()).toContain("messages.announces");
        expect(wrapper.find(".flex.flex-col.w-full").exists()).toBe(true);
    });

    it("shows Folders section with All Messages and Uncategorized", () => {
        const wrapper = mountSidebar();
        expect(wrapper.text()).toContain("Folders");
        expect(wrapper.text()).toContain("All Messages");
        expect(wrapper.text()).toContain("Uncategorized");
    });

    it("shows custom folders when provided", () => {
        const wrapper = mountSidebar({
            folders: [
                { id: 1, name: "Work" },
                { id: 2, name: "Family" },
            ],
        });
        expect(wrapper.text()).toContain("Work");
        expect(wrapper.text()).toContain("Family");
    });

    it("switches to announces tab when Announces tab is clicked", async () => {
        const wrapper = mountSidebar();
        const tabs = wrapper.findAll("div.flex.w-full.cursor-pointer.border-b-2");
        const announcesTab = tabs[1];
        await announcesTab.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.tab).toBe("announces");
        expect(wrapper.text()).toMatch(
            /messages\.search_placeholder_announces|messages\.no_peers_discovered|messages\.waiting_for_announce/
        );
    });

    it("emits folder-click when All Messages is clicked", async () => {
        const wrapper = mountSidebar();
        const clickables = wrapper.findAll(".cursor-pointer");
        const allMessagesRow = clickables.find((r) => r.text().includes("All Messages"));
        expect(allMessagesRow.exists()).toBe(true);
        await allMessagesRow.trigger("click");
        expect(wrapper.emitted("folder-click")).toBeTruthy();
        expect(wrapper.emitted("folder-click")[0]).toEqual([null]);
    });

    it("emits folder-click with folder id when folder row is clicked", async () => {
        const wrapper = mountSidebar({
            folders: [{ id: 10, name: "Archive" }],
        });
        await wrapper.vm.$nextTick();
        const clickables = wrapper.findAll(".cursor-pointer");
        const archiveRow = clickables.find((r) => r.text().includes("Archive"));
        expect(archiveRow.exists()).toBe(true);
        await archiveRow.trigger("click");
        expect(wrapper.emitted("folder-click")).toBeTruthy();
        expect(wrapper.emitted("folder-click").some((e) => e[0] === 10)).toBe(true);
    });

    it("renders conversation list when conversations are provided", async () => {
        const conversations = [
            {
                destination_hash: "abc123",
                display_name: "Alice",
                updated_at: new Date().toISOString(),
                is_unread: false,
                failed_messages_count: 0,
            },
        ];
        const wrapper = mountSidebar({ conversations, selectedDestinationHash: "" });
        await wrapper.vm.$nextTick();
        expect(wrapper.text()).toContain("Alice");
    });

    it("shows loading skeleton when isLoading is true", () => {
        const wrapper = mountSidebar({ isLoading: true });
        expect(wrapper.find(".animate-pulse").exists()).toBe(true);
    });

    it("shows no conversations empty state when conversations empty and not loading", () => {
        const wrapper = mountSidebar({ conversations: [], isLoading: false });
        expect(wrapper.text()).toContain("No Conversations");
        expect(wrapper.text()).toContain("Discover peers on the Announces tab");
    });

    it("toggles selection mode when selection button is clicked", async () => {
        const wrapper = mountSidebar({
            conversations: [
                {
                    destination_hash: "h1",
                    display_name: "Peer",
                    updated_at: new Date().toISOString(),
                    is_unread: false,
                    failed_messages_count: 0,
                },
            ],
        });
        await wrapper.vm.$nextTick();
        const selectionBtn = wrapper.find('button[title="Selection Mode"]');
        expect(selectionBtn.exists()).toBe(true);
        await selectionBtn.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.selectionMode).toBe(true);
    });

    it("conversations tab has correct layout classes", () => {
        const wrapper = mountSidebar();
        const conversationsPanel = wrapper.find(".flex-1.flex.flex-col.bg-white");
        expect(conversationsPanel.exists()).toBe(true);
    });

    it("uses right-edge collapse icons when sidebar position is right", () => {
        const left = mountSidebar({ sidebarPosition: "left" });
        expect(left.vm.expandedTabBarChevronIcon).toBe("chevron-left");
        expect(left.vm.collapsedStripChevronIcon).toBe("chevron-right");

        const right = mountSidebar({ sidebarPosition: "right" });
        expect(right.vm.expandedTabBarChevronIcon).toBe("chevron-right");
        expect(right.vm.collapsedStripChevronIcon).toBe("chevron-left");
    });

    it("emits conversation-click when a conversation row is clicked", async () => {
        const conversations = [
            {
                destination_hash: "dest1",
                display_name: "Bob",
                updated_at: new Date().toISOString(),
                is_unread: false,
                failed_messages_count: 0,
            },
        ];
        const wrapper = mountSidebar({ conversations });
        await wrapper.vm.$nextTick();
        const row = wrapper.find(".conversation-item");
        await row.trigger("click");
        expect(wrapper.emitted("conversation-click")).toBeTruthy();
        expect(wrapper.emitted("conversation-click")[0][0]).toMatchObject({
            destination_hash: "dest1",
            display_name: "Bob",
        });
    });

    it("re-renders time-ago when timeAgoTick updates so times live-update", async () => {
        const formatTimeAgoSpy = vi.mocked(Utils.formatTimeAgo);
        formatTimeAgoSpy.mockClear();
        const conversations = [
            {
                destination_hash: "d1",
                display_name: "Alice",
                updated_at: new Date().toISOString(),
                is_unread: false,
                failed_messages_count: 0,
            },
        ];
        const wrapper = mountSidebar({ conversations });
        await wrapper.vm.$nextTick();
        const callsAfterMount = formatTimeAgoSpy.mock.calls.length;
        expect(callsAfterMount).toBeGreaterThanOrEqual(1);
        wrapper.vm.timeAgoTick = Date.now();
        await wrapper.vm.$nextTick();
        expect(formatTimeAgoSpy.mock.calls.length).toBeGreaterThan(callsAfterMount);
    });

    it("clears time-ago interval on unmount", () => {
        const setIntervalSpy = vi.spyOn(globalThis, "setInterval").mockImplementation((fn, ms) => {
            expect(ms).toBe(60 * 1000);
            return 999;
        });
        const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval");
        const wrapper = mountSidebar();
        expect(setIntervalSpy).toHaveBeenCalled();
        wrapper.unmount();
        expect(clearIntervalSpy).toHaveBeenCalledWith(999);
        setIntervalSpy.mockRestore();
        clearIntervalSpy.mockRestore();
    });
});
