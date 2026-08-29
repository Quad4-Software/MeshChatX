// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalState from "@/js/GlobalState";
import { CONVERSATION_MESSAGES_PAGE_SIZE } from "@/components/messages/conversationDisplayGroups.js";
import { mount, flushPromises } from "@vue/test-utils";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(),
        prompt: vi.fn(() => Promise.resolve(null)),
    },
}));

describe("conversation incremental load smoke", () => {
    let axiosMock;
    let wrappers;
    const peerHash = "ab".repeat(16);

    const viewerStubs = {
        MaterialDesignIcon: true,
        AddImageButton: true,
        AddAudioButton: true,
        SendMessageButton: true,
        ConversationDropDownMenu: true,
        PaperMessageModal: true,
        AudioWaveformPlayer: true,
        LxmfUserIcon: true,
    };

    function mountViewer() {
        const wrapper = mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: peerHash, display_name: "Peer" },
                myLxmfAddressHash: "my-hash",
                conversations: [],
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
                mocks: { $t: (k) => k, $route: { meta: {} }, $router: { push: vi.fn() } },
                stubs: viewerStubs,
            },
        });
        wrappers.push(wrapper);
        return wrapper;
    }

    beforeEach(() => {
        wrappers = [];
        GlobalState.config.theme = "light";
        GlobalState.config.message_list_virtualization = false;
        WebSocketConnection.connect();
        axiosMock = {
            get: vi.fn(),
            post: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
        vi.stubGlobal("localStorage", {
            getItem: vi.fn(() => null),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        });
    });

    afterEach(async () => {
        for (const wrapper of wrappers.splice(0)) {
            try {
                wrapper.unmount();
            } catch {
                /* ignore teardown races */
            }
        }
        await flushPromises();
        delete window.api;
        vi.unstubAllGlobals();
        WebSocketConnection.destroy();
    });

    function lxmfRow(id) {
        const hash = `hash_${String(id).padStart(4, "0")}`.padEnd(32, "0");
        return {
            id,
            hash,
            source_hash: peerHash,
            destination_hash: "my-hash",
            content: `m-${id}`,
            state: "delivered",
            timestamp: 1700000000 + id,
            fields: {},
        };
    }

    function stubSideGets() {
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
            if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
            if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
            if (url.includes("/contacts/check/")) return Promise.resolve({ data: {} });
            return Promise.resolve({ data: {} });
        });
    }

    it("smoke: initial open requests one page at configured size", async () => {
        const conversationGet = vi.fn().mockResolvedValue({ data: { lxmf_messages: [lxmfRow(1)] } });
        axiosMock.get.mockImplementation((url, config) => {
            if (url.includes("/lxmf-messages/conversation/")) {
                return conversationGet(url, config);
            }
            if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
            if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
            if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
            if (url.includes("/contacts/check/")) return Promise.resolve({ data: {} });
            return Promise.resolve({ data: {} });
        });

        mountViewer();
        await flushPromises();

        expect(conversationGet).toHaveBeenCalledTimes(1);
        expect(conversationGet.mock.calls[0][1].params.count).toBe(CONVERSATION_MESSAGES_PAGE_SIZE);
    });

    it("smoke: second page prepends older rows in ascending id order", async () => {
        const page2OldestFirst = Array.from({ length: 50 }, (_, i) => lxmfRow(51 + i));
        const page1ApiDesc = Array.from({ length: 50 }, (_, i) => lxmfRow(1 + i)).reverse();

        stubSideGets();
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/lxmf-messages/conversation/")) {
                return Promise.resolve({ data: { lxmf_messages: [] } });
            }
            if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
            if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
            if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
            if (url.includes("/contacts/check/")) return Promise.resolve({ data: {} });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountViewer();
        await flushPromises();

        wrapper.vm.chatItems = page2OldestFirst.map((row) => ({
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message: row,
        }));
        wrapper.vm.hasMorePrevious = true;
        wrapper.vm._rebuildDisplayGroupsCache();

        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/lxmf-messages/conversation/")) {
                return Promise.resolve({ data: { lxmf_messages: page1ApiDesc } });
            }
            if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
            if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
            if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
            if (url.includes("/contacts/check/")) return Promise.resolve({ data: {} });
            return Promise.resolve({ data: {} });
        });

        await wrapper.vm.loadPrevious();
        await flushPromises();

        expect(wrapper.vm.chatItems).toHaveLength(100);
        const ids = wrapper.vm.chatItems.map((c) => c.lxmf_message.id);
        for (let i = 1; i < ids.length; i++) {
            expect(ids[i]).toBeGreaterThan(ids[i - 1]);
        }
    });

    it("adversarial: duplicate full page stops further pagination fetches", async () => {
        const duplicatePage = Array.from({ length: CONVERSATION_MESSAGES_PAGE_SIZE }, (_, i) =>
            lxmfRow(100 + i)
        ).reverse();
        stubSideGets();
        let fetches = 0;
        axiosMock.get.mockImplementation((url) => {
            if (url.includes("/lxmf-messages/conversation/")) {
                fetches += 1;
                return Promise.resolve({ data: { lxmf_messages: duplicatePage } });
            }
            if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
            if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
            if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
            if (url.includes("/contacts/check/")) return Promise.resolve({ data: {} });
            return Promise.resolve({ data: {} });
        });

        const wrapper = mountViewer();
        await flushPromises();
        expect(fetches).toBe(1);

        await wrapper.vm.loadPrevious();
        await flushPromises();
        expect(fetches).toBe(2);
        expect(wrapper.vm.hasMorePrevious).toBe(false);

        await wrapper.vm.loadPrevious();
        await flushPromises();
        expect(fetches).toBe(2);
    });
});
