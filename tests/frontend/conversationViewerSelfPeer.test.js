// SPDX-License-Identifier: 0BSD AND MIT
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import ToastUtils from "@/js/ToastUtils";

vi.mock("@/js/ToastUtils", () => ({
    default: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

vi.mock("@/js/WebSocketConnection", () => ({
    default: { on: vi.fn(), off: vi.fn() },
}));

vi.mock("@/js/GlobalEmitter", () => ({
    default: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
}));

describe("ConversationViewer self peer detection", () => {
    const mountViewer = (myLxmf = "aa".repeat(16), identityHash = "bb".repeat(16)) =>
        mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: myLxmf, display_name: "Me" },
                myLxmfAddressHash: myLxmf,
                config: { identity_hash: identityHash, lxmf_address_hash: myLxmf },
            },
            global: {
                mocks: {
                    $t: (key) => key,
                    $route: { query: {} },
                    $router: { push: vi.fn() },
                },
                stubs: {
                    MaterialDesignIcon: true,
                    ConversationPeerHeader: true,
                    ConversationMessageListVirtual: true,
                    SendMessageButton: true,
                    AddImageButton: true,
                    AddAudioButton: true,
                    ContextMenuPanel: true,
                    ContextMenuItem: true,
                    ContextMenuDivider: true,
                    Modal: true,
                    PaperMessageModal: true,
                    ShareContactModal: true,
                    ConversationImageModal: true,
                    LxmfUserIcon: true,
                    AudioWaveformPlayer: true,
                    StickerView: true,
                    InViewAnimatedImg: true,
                    TelemetryHistoryModal: true,
                    ConversationMessageEntry: true,
                },
            },
        });

    it("isSelfLxmfDestination is true for own LXMF hash", async () => {
        const my = "cc".repeat(16);
        const wrapper = mountViewer(my, "dd".repeat(16));
        await flushPromises();
        expect(wrapper.vm.isSelfLxmfDestination(my)).toBe(true);
        expect(wrapper.vm.isSelfLxmfDestination(my.toUpperCase())).toBe(true);
    });

    it("isSelfLxmfDestination is true for own identity hash", async () => {
        const my = "cc".repeat(16);
        const ident = "dd".repeat(16);
        const wrapper = mountViewer(my, ident);
        await flushPromises();
        expect(wrapper.vm.isSelfLxmfDestination(ident)).toBe(true);
    });

    it("isSelfLxmfDestination is false for unrelated peer", async () => {
        const wrapper = mountViewer();
        await flushPromises();
        expect(wrapper.vm.isSelfLxmfDestination("ee".repeat(16))).toBe(false);
        expect(wrapper.vm.isSelfLxmfDestination("")).toBe(false);
    });
});
