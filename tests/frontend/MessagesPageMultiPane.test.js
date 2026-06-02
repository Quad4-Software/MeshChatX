import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import MessagesPage from "@/components/messages/MessagesPage.vue";

describe("MessagesPage multi-pane", () => {
    let axiosMock;
    let routerReplace;

    beforeEach(() => {
        localStorage.clear();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn(),
        };
        window.api = axiosMock;

        axiosMock.get.mockImplementation((url) => {
            if (url === "/api/v1/config")
                return Promise.resolve({ data: { config: { lxmf_address_hash: "my-hash" } } });
            if (url === "/api/v1/lxmf/conversations") return Promise.resolve({ data: { conversations: [] } });
            if (url === "/api/v1/announces") return Promise.resolve({ data: { announces: [] } });
            if (url === "/api/v1/lxmf/conversation-pins") return Promise.resolve({ data: { peer_hashes: [] } });
            if (url === "/api/v1/lxmf/folders") return Promise.resolve({ data: [] });
            return Promise.resolve({ data: {} });
        });
    });

    afterEach(() => {
        delete window.api;
    });

    const mountMessagesPage = (props = { destinationHash: "" }) => {
        routerReplace = vi.fn();
        return mount(MessagesPage, {
            props,
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { replace: routerReplace },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    MessagesSidebar: {
                        template: '<div class="sidebar-stub"></div>',
                        props: ["conversations", "selectedDestinationHash"],
                    },
                    ConversationViewer: {
                        name: "ConversationViewer",
                        template: '<div class="viewer-stub"></div>',
                        props: ["selectedPeer", "myLxmfAddressHash"],
                        methods: { markConversationAsRead: vi.fn() },
                    },
                    Modal: true,
                },
            },
        });
    };

    it("starts with a single focused pane", () => {
        const wrapper = mountMessagesPage();
        expect(wrapper.vm.panes).toHaveLength(1);
        expect(wrapper.vm.focusedPaneId).toBe(wrapper.vm.panes[0].id);
        expect(wrapper.vm.selectedPeer).toBeNull();
    });

    it("selectedPeer getter and setter are backed by the focused pane", () => {
        const wrapper = mountMessagesPage();
        const peer = { destination_hash: "a".repeat(32), display_name: "Peer A" };
        wrapper.vm.selectedPeer = peer;
        expect(wrapper.vm.focusedPane.peer).toMatchObject({ destination_hash: "a".repeat(32) });
        expect(wrapper.vm.selectedPeer).toMatchObject({ destination_hash: "a".repeat(32) });
    });

    it("limits panes to a single pane on narrow viewports", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = false;
        wrapper.vm.selectedPeer = { destination_hash: "b".repeat(32) };
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.maxPanes).toBe(1);
        expect(wrapper.vm.canAddPane).toBe(false);
        expect(wrapper.vm.visiblePanes).toHaveLength(1);
    });

    it("allows two panes on wide viewports and three on extra-wide", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.isWideEnoughForThreePanes = false;
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.maxPanes).toBe(2);

        wrapper.vm.isWideEnoughForThreePanes = true;
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.maxPanes).toBe(3);
    });

    it("addPane adds and focuses a new empty pane when allowed", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.isWideEnoughForThreePanes = false;
        wrapper.vm.selectedPeer = { destination_hash: "c".repeat(32) };
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.canAddPane).toBe(true);
        wrapper.vm.addPane();

        expect(wrapper.vm.panes).toHaveLength(2);
        expect(wrapper.vm.focusedPaneId).toBe(wrapper.vm.panes[1].id);
        expect(wrapper.vm.panes[1].peer).toBeNull();
        expect(wrapper.vm.multiPaneActive).toBe(true);
    });

    it("does not add panes beyond the maximum", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.isWideEnoughForThreePanes = false;
        wrapper.vm.selectedPeer = { destination_hash: "d".repeat(32) };
        await wrapper.vm.$nextTick();

        wrapper.vm.addPane();
        wrapper.vm.panes[1].peer = { destination_hash: "e".repeat(32) };
        wrapper.vm.addPane();

        expect(wrapper.vm.panes).toHaveLength(2);
    });

    it("onPanePeerUpdate focuses the pane and assigns its peer", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "f".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        const secondId = wrapper.vm.panes[1].id;

        wrapper.vm.focusedPaneId = wrapper.vm.panes[0].id;
        const newPeer = { destination_hash: "1".repeat(32), display_name: "Second" };
        wrapper.vm.onPanePeerUpdate(secondId, newPeer);

        expect(wrapper.vm.focusedPaneId).toBe(secondId);
        expect(wrapper.vm.panes[1].peer).toMatchObject({ destination_hash: "1".repeat(32) });
    });

    it("onPaneClose removes the pane when more than one is open", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "9".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        const secondId = wrapper.vm.panes[1].id;
        const firstId = wrapper.vm.panes[0].id;

        wrapper.vm.onPaneClose(secondId);

        expect(wrapper.vm.panes).toHaveLength(1);
        expect(wrapper.vm.focusedPaneId).toBe(firstId);
    });

    it("onPaneClose on the last pane clears the conversation and route", () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.selectedPeer = { destination_hash: "2".repeat(32) };
        const onlyPaneId = wrapper.vm.panes[0].id;

        wrapper.vm.onPaneClose(onlyPaneId);

        expect(wrapper.vm.panes).toHaveLength(1);
        expect(wrapper.vm.selectedPeer).toBeNull();
        expect(routerReplace).toHaveBeenCalled();
    });

    it("forces a single pane when multi-pane is disabled in config", async () => {
        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.isWideEnoughForThreePanes = true;
        wrapper.vm.config = { ...wrapper.vm.config, messages_multi_pane_enabled: false };
        wrapper.vm.selectedPeer = { destination_hash: "7".repeat(32) };
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.multiPaneEnabled).toBe(false);
        expect(wrapper.vm.maxPanes).toBe(1);
        expect(wrapper.vm.canAddPane).toBe(false);
    });

    it("opens a dropped conversation in the target pane", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        const dest = "8".repeat(32);
        const paneId = wrapper.vm.panes[0].id;

        wrapper.vm.onPaneDrop(paneId, { dataTransfer: { getData: () => dest } });
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.panes[0].peer).toMatchObject({ destination_hash: dest });
        expect(wrapper.vm.dragOverPaneId).toBeNull();
    });

    it("creates a new split pane when a conversation is dropped on the add zone", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.isWideEnoughForThreePanes = false;
        wrapper.vm.selectedPeer = { destination_hash: "5".repeat(32) };
        await wrapper.vm.$nextTick();

        wrapper.vm.onAddZoneDrop({ dataTransfer: { getData: () => "6".repeat(32) } });
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.panes).toHaveLength(2);
        expect(wrapper.vm.panes[1].peer).toMatchObject({ destination_hash: "6".repeat(32) });
        expect(wrapper.vm.isDragOverAddZone).toBe(false);
    });

    it("persists pane layout to localStorage when panes change", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "a".repeat(32), display_name: "Peer A" };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        wrapper.vm.panes[1].peer = { destination_hash: "b".repeat(32), display_name: "Peer B" };
        await wrapper.vm.$nextTick();

        const saved = JSON.parse(localStorage.getItem("meshchatx.messages.panes"));
        expect(saved.panes).toHaveLength(2);
        expect(saved.panes[0]).toMatchObject({ destination_hash: "a".repeat(32), display_name: "Peer A" });
        expect(saved.panes[1]).toMatchObject({ destination_hash: "b".repeat(32) });
        expect(saved.focusedIndex).toBe(1);
    });

    it("restores persisted panes on mount", async () => {
        localStorage.setItem(
            "meshchatx.messages.panes",
            JSON.stringify({
                panes: [
                    { destination_hash: "a".repeat(32), display_name: "Peer A", custom_display_name: null },
                    { destination_hash: "b".repeat(32), display_name: "Peer B", custom_display_name: null },
                ],
                focusedIndex: 1,
            })
        );

        const wrapper = mountMessagesPage();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.panes).toHaveLength(2);
        expect(wrapper.vm.panes[0].peer).toMatchObject({ destination_hash: "a".repeat(32) });
        expect(wrapper.vm.focusedPaneId).toBe(wrapper.vm.panes[1].id);
        expect(wrapper.vm.selectedPeer).toMatchObject({ destination_hash: "b".repeat(32) });
    });

    it("renders a resizer divider between visible panes", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "a".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        wrapper.vm.panes[1].peer = { destination_hash: "b".repeat(32) };
        await wrapper.vm.$nextTick();

        const separators = wrapper.findAll('[role="separator"]');
        expect(separators).toHaveLength(1);
    });

    it("paneFlexValue defaults to 1 and reflects custom sizes when multiple panes are visible", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "a".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        wrapper.vm.panes[1].peer = { destination_hash: "b".repeat(32) };
        await wrapper.vm.$nextTick();

        const leftId = wrapper.vm.panes[0].id;
        const rightId = wrapper.vm.panes[1].id;
        expect(wrapper.vm.paneFlexValue(leftId)).toBe(1);
        wrapper.vm.paneFlex[leftId] = 2.5;
        expect(wrapper.vm.paneFlexValue(leftId)).toBe(2.5);
        expect(wrapper.vm.paneFlexValue(rightId)).toBe(1);
    });

    it("hides unfocused empty panes so the active chat fills the width", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "a".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        wrapper.vm.paneFlex[wrapper.vm.panes[0].id] = 0.9;
        wrapper.vm.paneFlex[wrapper.vm.panes[1].id] = 0.1;
        wrapper.vm.focusedPaneId = wrapper.vm.panes[0].id;
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.visiblePanes).toHaveLength(1);
        expect(wrapper.vm.visiblePanes[0].id).toBe(wrapper.vm.panes[0].id);
        expect(wrapper.vm.paneFlexValue(wrapper.vm.panes[0].id)).toBe(1);
    });

    it("shows an empty pane when it is focused for conversation selection", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "a".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.visiblePanes).toHaveLength(2);
    });

    it("reuses a hidden empty pane when split is opened again", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "a".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        const emptyId = wrapper.vm.panes[1].id;
        wrapper.vm.focusedPaneId = wrapper.vm.panes[0].id;
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.panes).toHaveLength(2);
        wrapper.vm.addPane();
        expect(wrapper.vm.panes).toHaveLength(2);
        expect(wrapper.vm.focusedPaneId).toBe(emptyId);
    });

    it("resizes adjacent panes by dragging and keeps their combined flex constant", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "a".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        wrapper.vm.panes[1].peer = { destination_hash: "b".repeat(32) };
        await wrapper.vm.$nextTick();

        const leftId = wrapper.vm.panes[0].id;
        const rightId = wrapper.vm.panes[1].id;
        const fakeEvent = {
            button: 0,
            clientX: 0,
            preventDefault: () => {},
            currentTarget: {
                previousElementSibling: { getBoundingClientRect: () => ({ width: 300 }) },
                nextElementSibling: { getBoundingClientRect: () => ({ width: 300 }) },
            },
        };

        wrapper.vm.startPaneResize(fakeEvent, leftId, rightId);
        wrapper.vm.onPaneResizeMove({ clientX: 60 });

        expect(wrapper.vm.paneFlexValue(leftId)).toBeCloseTo(1.2, 5);
        expect(wrapper.vm.paneFlexValue(rightId)).toBeCloseTo(0.8, 5);

        wrapper.vm.endPaneResize();
        expect(wrapper.vm.resizingPaneIds).toBeNull();

        const saved = JSON.parse(localStorage.getItem("meshchatx.messages.panes"));
        expect(saved.sizes[0]).toBeCloseTo(1.2, 5);
        expect(saved.sizes[1]).toBeCloseTo(0.8, 5);
    });

    it("resetPaneSizes restores equal flex for all panes", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        wrapper.vm.selectedPeer = { destination_hash: "a".repeat(32) };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        const leftId = wrapper.vm.panes[0].id;
        wrapper.vm.paneFlex[leftId] = 3;

        wrapper.vm.resetPaneSizes();

        for (const pane of wrapper.vm.panes) {
            expect(wrapper.vm.paneFlexValue(pane.id)).toBe(1);
        }
    });

    it("applyToPanePeers patches every pane showing a destination", async () => {
        const wrapper = mountMessagesPage();
        wrapper.vm.isWideViewport = true;
        const dest = "3".repeat(32);
        wrapper.vm.selectedPeer = { destination_hash: dest, is_tracking: false };
        await wrapper.vm.$nextTick();
        wrapper.vm.addPane();
        wrapper.vm.panes[1].peer = { destination_hash: dest, is_tracking: false };

        wrapper.vm.applyToPanePeers(dest, { is_tracking: true });

        expect(wrapper.vm.panes[0].peer.is_tracking).toBe(true);
        expect(wrapper.vm.panes[1].peer.is_tracking).toBe(true);
    });
});
