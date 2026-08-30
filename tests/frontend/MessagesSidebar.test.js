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

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

import Utils from "../../meshchatx/src/frontend/js/Utils";
import ToastUtils from "../../meshchatx/src/frontend/js/ToastUtils";

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
        isSearchingAnnounces: false,
        hasMoreAnnounces: false,
        totalPeersCount: 0,
        ...overrides,
    };
}

function mountSidebar(props = {}, options = {}) {
    return mount(MessagesSidebar, {
        props: defaultProps(props),
        global: {
            mocks: { $t: (key) => key },
            directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
            stubs: {
                MaterialDesignIcon: {
                    template: '<div class="mdi" :data-icon-name="iconName"></div>',
                    props: ["iconName"],
                },
                LxmfUserIcon: { template: '<div class="lxmf-icon"></div>' },
                RouterLink: {
                    name: "RouterLink",
                    props: ["to"],
                    template: '<a class="router-link-stub"><slot /></a>',
                },
            },
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
        expect(wrapper.text()).toContain("messages.folders");
        expect(wrapper.text()).toContain("messages.all_messages");
        expect(wrapper.text()).toContain("messages.uncategorized");
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
        const allMessagesRow = clickables.find((r) => r.text().includes("messages.all_messages"));
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

    it("shows loading state when isLoading is true", () => {
        const wrapper = mountSidebar({ isLoading: true });
        expect(wrapper.text()).toContain("messages.loading_conversations");
    });

    it("shows no conversations empty state when conversations empty and not loading", () => {
        const wrapper = mountSidebar({ conversations: [], isLoading: false });
        expect(wrapper.text()).toContain("messages.no_conversations");
        expect(wrapper.text()).toContain("messages.no_conversations_hint");
        expect(wrapper.text()).toContain("messages.see_announces_cta");
        expect(wrapper.text()).toContain("messages.add_contact_cta");
        expect(wrapper.text()).not.toContain("messages.add_interface_cta");
        const empty = wrapper.findComponent({ name: "EmptyState" });
        expect(empty.exists()).toBe(true);
        expect(empty.props("plain")).toBe(true);
        expect(empty.classes().join(" ")).not.toMatch(/\bborder\b/);
        expect(wrapper.find(".my-auto").exists()).toBe(false);
        const addContact = wrapper.findComponent({ name: "RouterLink" });
        expect(addContact.exists()).toBe(true);
        expect(addContact.props("to")).toEqual({ name: "contacts" });
    });

    it("see announces switches the sidebar to the announces tab", async () => {
        const wrapper = mountSidebar({ conversations: [], isLoading: false });
        expect(wrapper.vm.tab).toBe("conversations");
        await wrapper.find("[data-testid=messages-see-announces]").trigger("click");
        expect(wrapper.vm.tab).toBe("announces");
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
        const selectionBtn = wrapper.find('button[title="nomadnet.sidebar_selection_mode"]');
        expect(selectionBtn.exists()).toBe(true);
        await selectionBtn.trigger("click");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.selectionMode).toBe(true);
    });

    it("conversations tab has correct layout classes", () => {
        const wrapper = mountSidebar();
        const conversationsPanel = wrapper.find(".flex-1.flex.flex-col.bg-sem-canvas");
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

    async function openAnnouncesTab(wrapper) {
        const tabs = wrapper.findAll("div.flex.w-full.cursor-pointer.border-b-2");
        await tabs[1].trigger("click");
        await wrapper.vm.$nextTick();
    }

    it("shows a spinner next to the search input while an announce search is in progress", async () => {
        const wrapper = mountSidebar({ isSearchingAnnounces: true });
        await openAnnouncesTab(wrapper);

        const spinner = wrapper.find('[data-icon-name="loading"]');
        expect(spinner.exists()).toBe(true);
    });

    it("does not show a search spinner when isSearchingAnnounces is false", async () => {
        const wrapper = mountSidebar({ isSearchingAnnounces: false });
        await openAnnouncesTab(wrapper);

        const spinner = wrapper.find('[data-icon-name="loading"]');
        expect(spinner.exists()).toBe(false);
    });

    it("shows a searching placeholder instead of the empty state while search results are still loading", async () => {
        const wrapper = mountSidebar({
            peers: {},
            totalPeersCount: 0,
            peersSearchTerm: "nonexistent",
            isSearchingAnnounces: true,
        });
        await openAnnouncesTab(wrapper);

        expect(wrapper.text()).toContain("messages.searching_announces");
        expect(wrapper.text()).not.toContain("messages.no_peers_discovered");
        expect(wrapper.text()).not.toContain("messages.no_search_results_peers");
    });

    it("shows the no-results-for-search message once a search finishes with no matches", async () => {
        const wrapper = mountSidebar({
            peers: {},
            totalPeersCount: 0,
            peersSearchTerm: "nonexistent",
            isSearchingAnnounces: false,
        });
        await openAnnouncesTab(wrapper);

        expect(wrapper.text()).toContain("messages.no_search_results");
        expect(wrapper.text()).toContain("messages.no_search_results_peers");
        expect(wrapper.text()).not.toContain("messages.searching_announces");
        expect(wrapper.text()).not.toContain("messages.no_peers_discovered");
    });

    it("does not show the LXMF hash on conversation rows", async () => {
        const conversations = [
            {
                destination_hash: "abc123def456",
                display_name: "Alice",
                updated_at: new Date().toISOString(),
                is_unread: false,
                failed_messages_count: 0,
            },
        ];
        const wrapper = mountSidebar({ conversations });
        await wrapper.vm.$nextTick();
        const row = wrapper.find(".conversation-item");
        expect(row.exists()).toBe(true);
        expect(row.text()).toContain("Alice");
        expect(row.text()).not.toContain("abc123de");
        expect(row.text()).not.toContain("abc123def456");
    });

    it("copies the LXMF hash from the conversation context menu", async () => {
        window.api = {
            get: vi.fn().mockResolvedValue({ data: { is_contact: false } }),
        };
        const writeText = vi.fn().mockResolvedValue(undefined);
        vi.stubGlobal("navigator", {
            ...navigator,
            clipboard: { writeText },
        });
        const conversations = [
            {
                destination_hash: "abc123def456",
                display_name: "Alice",
                updated_at: new Date().toISOString(),
                is_unread: false,
                failed_messages_count: 0,
            },
        ];
        const wrapper = mountSidebar({ conversations });
        await wrapper.vm.$nextTick();
        await wrapper.find(".conversation-item").trigger("contextmenu");
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.contextMenu.show).toBe(true);
        expect(wrapper.vm.contextMenu.targetHash).toBe("abc123def456");
        expect(wrapper.text()).toContain("messages.copy_lxmf");
        const copyItem = wrapper.findAll("button").find((b) => b.text().includes("messages.copy_lxmf"));
        expect(copyItem).toBeTruthy();
        await copyItem.trigger("click");
        await wrapper.vm.$nextTick();
        expect(writeText).toHaveBeenCalledWith("abc123def456");
        expect(ToastUtils.success).toHaveBeenCalledWith("common.copied");
        expect(wrapper.vm.contextMenu.show).toBe(false);
        vi.unstubAllGlobals();
        delete window.api;
    });
});
