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
        GlobalState.outboundTransferProgressEnabled = true;

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
        GlobalState.outboundTransferProgressEnabled = true;
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

    it("outboundTransferProgressPercent and label track resource transfer", () => {
        const wrapper = mountViewer();
        expect(wrapper.vm.outboundTransferProgressPercent({ state: "sending", progress: 42.5 })).toBe(43);
        expect(wrapper.vm.outboundSendingProgressLabel({ state: "sending", progress: 42.5 })).toBe("43%");
        expect(wrapper.vm.outboundTransferProgressPercent({ state: "sending", progress: 0 })).toBe(0);
        expect(wrapper.vm.outboundTransferProgressPercent({ state: "outbound", progress: 50 })).toBe(50);
        expect(wrapper.vm.outboundTransferProgressPercent({ state: "outbound", progress: 0 })).toBeNull();
        expect(wrapper.vm.outboundTransferProgressPercent({ state: "sending", _pendingPathfinding: true })).toBeNull();
        expect(wrapper.vm.outboundSendingProgressLabel(null)).toBeNull();
    });

    it("showOutboundTransferProgress respects the settings toggle", () => {
        const wrapper = mountViewer();
        const message = { state: "sending", progress: 25 };
        expect(wrapper.vm.showOutboundTransferProgress(message)).toBe(true);
        GlobalState.outboundTransferProgressEnabled = false;
        expect(wrapper.vm.showOutboundTransferProgress(message)).toBe(false);
    });

    it("outboundTransferStatsLabel includes speed, hops, and elapsed time", () => {
        const wrapper = mountViewer();
        const createdAt = new Date(Date.now() - 65000).toISOString();
        wrapper.vm.sendStatusUiMs = Date.now();
        const stats = wrapper.vm.outboundTransferStatsLabel(
            {
                state: "sending",
                progress: 50,
                content: "hello",
                path_hops_at_send: 3,
                created_at: createdAt,
            },
            {
                created_at: createdAt,
            }
        );
        expect(stats).toContain("B/s");
        expect(stats).not.toContain("bps");
        expect(stats).toContain("messages.transfer_progress_hops");
        expect(stats).toMatch(/1:0[45]/);
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
