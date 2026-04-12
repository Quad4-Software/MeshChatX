import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import DialogUtils from "@/js/DialogUtils";
import GlobalEmitter from "@/js/GlobalEmitter";
import GlobalState from "@/js/GlobalState";

const RENDER_THRESHOLD_MS = 500;

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(),
    },
}));

describe("ConversationViewer.vue button interactions", () => {
    let axiosMock;

    beforeEach(() => {
        WebSocketConnection.connect();
        vi.clearAllMocks();
        axiosMock = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
            delete: vi.fn().mockResolvedValue({ data: {} }),
        };
        window.api = axiosMock;

        GlobalState.blockedDestinations = [];
        GlobalState.config = { banished_effect_enabled: false };

        vi.stubGlobal("localStorage", {
            getItem: vi.fn(),
            setItem: vi.fn(),
            removeItem: vi.fn(),
        });
        window.URL.createObjectURL = vi.fn(() => "mock-url");
        vi.stubGlobal(
            "FileReader",
            vi.fn(() => ({
                readAsDataURL: vi.fn(function () {
                    this.result = "data:image/png;base64,mock";
                    this.onload?.({ target: { result: this.result } });
                }),
            }))
        );
    });

    afterEach(() => {
        delete window.api;
        vi.unstubAllGlobals();
        WebSocketConnection.destroy();
    });

    const mountViewer = (overrides = {}) =>
        mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: "a".repeat(32), display_name: "Test Peer" },
                myLxmfAddressHash: "b".repeat(32),
                conversations: [],
                ...overrides,
            },
            global: {
                mocks: { $t: (key) => key },
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

    it("mounts within render threshold", () => {
        const start = performance.now();
        const wrapper = mountViewer();
        const elapsed = performance.now() - start;
        expect(wrapper.find(".flex").exists()).toBe(true);
        expect(elapsed).toBeLessThan(RENDER_THRESHOLD_MS);
    });

    it("banish button calls API when confirmed", async () => {
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const wrapper = mountViewer();
        await wrapper.vm.$nextTick();

        await wrapper.vm.onBanishHeaderClick();

        expect(DialogUtils.confirm).toHaveBeenCalled();
        expect(axiosMock.post).toHaveBeenCalledWith(
            "/api/v1/blocked-destinations",
            expect.objectContaining({ destination_hash: "a".repeat(32) })
        );
        expect(emitSpy).toHaveBeenCalledWith("block-status-changed");
        emitSpy.mockRestore();
    });

    it("banish button hidden when peer is blocked", async () => {
        GlobalState.blockedDestinations = [{ destination_hash: "a".repeat(32) }];
        const wrapper = mountViewer();
        await wrapper.vm.$nextTick();
        wrapper.vm.checkIfSelectedPeerBlocked();
        await wrapper.vm.$nextTick();

        const banishBtn = wrapper.findAll("button").find((b) => b.attributes("title")?.includes("banish"));
        expect(banishBtn).toBeUndefined();
    });

    it("telemetry history modal can be opened", async () => {
        const wrapper = mountViewer();
        await wrapper.vm.$nextTick();

        wrapper.vm.isTelemetryHistoryModalOpen = true;
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.isTelemetryHistoryModalOpen).toBe(true);
    });

    it("close button emits close", async () => {
        const wrapper = mountViewer();
        await wrapper.vm.$nextTick();

        const closeBtn = wrapper.findAll("button").find((b) => b.attributes("title") === "Close");
        expect(closeBtn).toBeDefined();

        await closeBtn.trigger("click");

        expect(wrapper.emitted("close")).toHaveLength(1);
    });

    it("onMessageContextMenu opens menu and Reply works", async () => {
        const wrapper = mountViewer();
        const chatItem = {
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message: {
                hash: "msg-1",
                content: "Hello",
                state: "delivered",
                fields: {},
            },
        };
        wrapper.vm.chatItems = [chatItem];
        await wrapper.vm.$nextTick();

        const replySpy = vi.spyOn(wrapper.vm, "replyToMessage");

        wrapper.vm.onMessageContextMenu({ clientX: 100, clientY: 100 }, chatItem);
        await wrapper.vm.$nextTick();

        expect(wrapper.vm.messageContextMenu.show).toBe(true);

        const menuEl = Array.from(document.body.querySelectorAll(".fixed")).find(
            (el) => el.textContent?.includes("Reply") && el.textContent?.includes("Delete")
        );
        expect(menuEl).toBeTruthy();

        const replyBtn = menuEl?.querySelector("button");
        expect(replyBtn?.textContent).toContain("Reply");

        replyBtn?.click();
        await wrapper.vm.$nextTick();

        expect(replySpy).toHaveBeenCalledWith(chatItem);
    });

    it("message context menu Delete calls deleteChatItem", async () => {
        const wrapper = mountViewer();
        const chatItem = {
            type: "lxmf_message",
            is_outbound: false,
            lxmf_message: { hash: "msg-del", content: "Hi", state: "delivered", fields: {} },
        };
        wrapper.vm.chatItems = [chatItem];
        await wrapper.vm.$nextTick();

        const deleteSpy = vi.spyOn(wrapper.vm, "deleteChatItem");

        wrapper.vm.messageContextMenu.chatItem = chatItem;
        wrapper.vm.messageContextMenu.show = true;
        await wrapper.vm.$nextTick();

        const menuEl = Array.from(document.body.querySelectorAll(".fixed")).find(
            (el) => el.textContent?.includes("Reply") && el.textContent?.includes("Delete")
        );
        const deleteBtn = menuEl
            ? Array.from(menuEl.querySelectorAll("button")).find((b) => b.textContent.includes("Delete"))
            : null;
        expect(deleteBtn).toBeTruthy();

        deleteBtn?.click();
        await wrapper.vm.$nextTick();

        expect(deleteSpy).toHaveBeenCalledWith(chatItem);
    });

    it("call button exists and onStartCall is callable", async () => {
        const wrapper = mountViewer();
        expect(typeof wrapper.vm.onStartCall).toBe("function");
        await wrapper.vm.onStartCall();
    });

    it("share contact button exists and openShareContactModal is callable", async () => {
        const wrapper = mountViewer();
        expect(typeof wrapper.vm.openShareContactModal).toBe("function");
        wrapper.vm.openShareContactModal();
    });
});
