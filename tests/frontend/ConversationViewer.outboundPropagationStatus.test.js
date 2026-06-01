import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalState from "@/js/GlobalState";

describe("ConversationViewer outbound propagation status", () => {
    let axiosMock;

    beforeEach(() => {
        GlobalState.config.theme = "light";
        GlobalState.config.message_outbound_bubble_color = "#4f46e5";
        GlobalState.config.message_waiting_bubble_color = "#e5e7eb";
        GlobalState.config.warn_on_stranger_links = true;
        GlobalState.detailedOutboundSendStatus = true;

        WebSocketConnection.connect();
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { lxmf_stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        GlobalState.detailedOutboundSendStatus = false;
        delete window.api;
        WebSocketConnection.destroy();
    });

    const mountViewer = (extraMocks = {}) =>
        mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: "peerhash111111111111111111111111", display_name: "Peer" },
                myLxmfAddressHash: "myhash11111111111111111111111111",
                conversations: [],
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
                mocks: {
                    $t: (key, params) => {
                        if (params && Object.keys(params).length) {
                            return `${key}:${JSON.stringify(params)}`;
                        }
                        return key;
                    },
                    $route: { meta: {} },
                    $router: { push: vi.fn() },
                    ...extraMocks,
                },
                stubs: {
                    MaterialDesignIcon: true,
                    AddImageButton: true,
                    AddAudioButton: true,
                    SendMessageButton: true,
                    ConversationDropDownMenu: true,
                    PaperMessageModal: true,
                    AudioWaveformPlayer: true,
                    LxmfUserIcon: true,
                },
            },
        });

    it("outboundSentStatusTitle uses propagation copy when method is propagated", () => {
        const wrapper = mountViewer();
        expect(wrapper.vm.outboundSentStatusTitle({ method: "propagated", state: "sent" })).toBe(
            "messages.outbound_on_propagation_node"
        );
        expect(wrapper.vm.outboundSentStatusTitle({ method: "direct", state: "sent" })).toBe(
            "messages.outbound_sent_network"
        );
        expect(wrapper.vm.outboundSentStatusTitle(null)).toBe("");
    });

    it("outboundSendingStatusTooltip uses propagation pending strings for propagated method", () => {
        const wrapper = mountViewer();
        const withProgress = wrapper.vm.outboundSendingStatusTooltip({
            method: "propagated",
            state: "sending",
            progress: 40,
        });
        expect(withProgress).toContain("messages.outbound_pending_propagation_with_progress");
        expect(withProgress).toContain('"progress":"40"');

        const pending = wrapper.vm.outboundSendingStatusTooltip({
            method: "propagated",
            state: "sending",
            progress: 0,
        });
        expect(pending).toBe("messages.outbound_pending_propagation");

        expect(
            wrapper.vm.outboundSendingStatusTooltip({
                method: "propagated",
                state: "outbound",
            })
        ).toBe("messages.outbound_pending_propagation");
    });

    it("outboundBubbleStatusHoverTitle uses propagation pending for outbound state", () => {
        const wrapper = mountViewer();
        expect(
            wrapper.vm.outboundBubbleStatusHoverTitle({
                method: "propagated",
                state: "outbound",
            })
        ).toBe("messages.outbound_pending_propagation");
    });

    it("outboundSendingStatusTooltip uses solving stamps copy when solving_stamps is set", () => {
        const wrapper = mountViewer();
        expect(
            wrapper.vm.outboundSendingStatusTooltip({
                state: "outbound",
                solving_stamps: true,
            })
        ).toBe("messages.outbound_solving_stamps");
    });

    it("outboundBubbleStatusHoverTitle uses solving stamps short copy when solving_stamps is set", () => {
        const wrapper = mountViewer();
        expect(
            wrapper.vm.outboundBubbleStatusHoverTitle({
                state: "outbound",
                solving_stamps: true,
            })
        ).toBe("messages.outbound_solving_stamps_short");
    });

    it("onLxmfMessageUpdated preserves solving_stamps when websocket omits the field", () => {
        const wrapper = mountViewer();
        const hash = "abc123def456789012345678901234ab";
        wrapper.vm.chatItems = [
            {
                type: "lxmf_message",
                is_outbound: true,
                lxmf_message: {
                    hash,
                    destination_hash: "peerhash111111111111111111111111",
                    state: "outbound",
                    solving_stamps: true,
                    content: "hi",
                    fields: {},
                },
            },
        ];

        wrapper.vm.onLxmfMessageUpdated({
            hash,
            state: "sending",
        });

        expect(wrapper.vm.chatItems[0].lxmf_message.solving_stamps).toBe(true);
    });

    it("onLxmfMessageUpdated clears solving_stamps when websocket sets it false", () => {
        const wrapper = mountViewer();
        const hash = "abc123def456789012345678901234ab";
        wrapper.vm.chatItems = [
            {
                type: "lxmf_message",
                is_outbound: true,
                lxmf_message: {
                    hash,
                    destination_hash: "peerhash111111111111111111111111",
                    state: "outbound",
                    solving_stamps: true,
                    content: "hi",
                    fields: {},
                },
            },
        ];

        wrapper.vm.onLxmfMessageUpdated({
            hash,
            state: "sending",
            solving_stamps: false,
        });

        expect(wrapper.vm.chatItems[0].lxmf_message.solving_stamps).toBe(false);
    });

    it("onLxmfMessageUpdated preserves merged method when websocket sends propagated handoff", () => {
        const wrapper = mountViewer();
        const hash = "abc123def456789012345678901234ab";
        wrapper.vm.chatItems = [
            {
                type: "lxmf_message",
                is_outbound: true,
                lxmf_message: {
                    hash,
                    destination_hash: "peerhash111111111111111111111111",
                    state: "sending",
                    method: "direct",
                    progress: 10,
                    content: "hi",
                    fields: {},
                },
            },
        ];

        wrapper.vm.onLxmfMessageUpdated({
            hash,
            state: "sent",
            method: "propagated",
            progress: 100,
        });

        const row = wrapper.vm.chatItems[0].lxmf_message;
        expect(row.state).toBe("sent");
        expect(row.method).toBe("propagated");
        expect(row.progress).toBe(100);
    });
});
