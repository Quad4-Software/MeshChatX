import { mount, flushPromises } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalState from "@/js/GlobalState";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
        alert: vi.fn(),
        prompt: vi.fn(() => Promise.resolve(null)),
    },
}));

function makeMessagesScrollTarget({ reverse, scrollTop, scrollHeight, clientHeight }) {
    const outer = document.createElement("div");
    outer.setAttribute("data-message-list-mode", reverse ? "reverse" : "virtual");
    const inner = document.createElement("div");
    inner.style.flexDirection = reverse ? "column-reverse" : "column";
    outer.appendChild(inner);
    document.body.appendChild(outer);
    Object.defineProperty(outer, "scrollHeight", { value: scrollHeight, configurable: true });
    Object.defineProperty(outer, "clientHeight", { value: clientHeight, configurable: true });
    outer.scrollTop = scrollTop;
    return outer;
}

describe("ConversationViewer.vue scroll behavior", () => {
    beforeEach(() => {
        GlobalState.config.theme = "light";
        WebSocketConnection.connect();
        window.api = {
            get: vi.fn().mockImplementation((url) => {
                if (url.includes("/path")) return Promise.resolve({ data: { path: [] } });
                if (url.includes("/stamp-info")) return Promise.resolve({ data: { stamp_info: {} } });
                if (url.includes("/signal-metrics")) return Promise.resolve({ data: { signal_metrics: {} } });
                return Promise.resolve({ data: {} });
            }),
            post: vi.fn().mockResolvedValue({ data: {} }),
        };
    });

    afterEach(() => {
        delete window.api;
        WebSocketConnection.destroy();
    });

    const mountViewer = () =>
        mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: "abcdabcdabcdabcdabcdabcdabcdabcd", display_name: "Peer" },
                myLxmfAddressHash: "myhashmyhashmyhashmyhashmyhashmyha",
                conversations: [],
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
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

    it("onMessagesScroll sets autoScrollOnNewMessage when near bottom (column-reverse)", () => {
        const wrapper = mountViewer();
        const el = makeMessagesScrollTarget({
            reverse: true,
            scrollTop: 0,
            scrollHeight: 5000,
            clientHeight: 100,
        });
        wrapper.vm.onMessagesScroll({ target: el });
        expect(wrapper.vm.autoScrollOnNewMessage).toBe(true);
        el.remove();
    });

    it("onMessagesScroll clears autoScroll when not near bottom (column-reverse)", () => {
        const wrapper = mountViewer();
        const el = makeMessagesScrollTarget({
            reverse: true,
            scrollTop: 2000,
            scrollHeight: 5000,
            clientHeight: 100,
        });
        wrapper.vm.onMessagesScroll({ target: el });
        expect(wrapper.vm.autoScrollOnNewMessage).toBe(false);
        el.remove();
    });

    it("onMessagesScroll calls loadPrevious when near older-history edge (column-reverse)", () => {
        const wrapper = mountViewer();
        const spy = vi.spyOn(wrapper.vm, "loadPrevious").mockImplementation(() => {});
        const el = makeMessagesScrollTarget({
            reverse: true,
            scrollTop: 4450,
            scrollHeight: 5000,
            clientHeight: 100,
        });
        wrapper.vm.onMessagesScroll({ target: el });
        expect(spy).toHaveBeenCalledTimes(1);
        wrapper.vm.onMessagesScroll({ target: el });
        expect(spy).toHaveBeenCalledTimes(1);
        el.remove();
    });

    it("onMessagesScroll does not hammer loadPrevious while held at older-history edge", () => {
        const wrapper = mountViewer();
        const spy = vi.spyOn(wrapper.vm, "loadPrevious").mockImplementation(() => {});
        const el = makeMessagesScrollTarget({
            reverse: true,
            scrollTop: 4450,
            scrollHeight: 5000,
            clientHeight: 100,
        });
        wrapper.vm.onMessagesScroll({ target: el });
        wrapper.vm.onMessagesScroll({ target: el });
        wrapper.vm.onMessagesScroll({ target: el });
        expect(spy).toHaveBeenCalledTimes(1);
        el.remove();
    });

    it("runs resetStaleConversationScrollSurface after selectedPeer changes", async () => {
        const peerA = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        const peerB = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
        const wrapper = mount(ConversationViewer, {
            props: {
                selectedPeer: { destination_hash: peerA, display_name: "A" },
                myLxmfAddressHash: "myhashmyhashmyhashmyhashmyhashmyha",
                conversations: [],
            },
            global: {
                directives: { "click-outside": { mounted: () => {}, unmounted: () => {} } },
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
                    ConversationPeerHeader: true,
                    ConversationMessageEntry: true,
                    ConversationMessageListVirtual: true,
                    TelemetryHistoryModal: true,
                },
            },
        });
        const spy = vi.spyOn(wrapper.vm, "resetStaleConversationScrollSurface");
        await wrapper.setProps({
            selectedPeer: { destination_hash: peerB, display_name: "B" },
        });
        await flushPromises();
        await wrapper.vm.$nextTick();
        expect(spy).toHaveBeenCalled();
    });

    it("onMessagesScroll away from bottom cancels pending scroll-to-bottom settle", async () => {
        const wrapper = mountViewer();
        await flushPromises();

        const el = makeMessagesScrollTarget({
            reverse: true,
            scrollTop: 0,
            scrollHeight: 5000,
            clientHeight: 400,
        });
        Object.defineProperty(wrapper.vm.$refs, "messagesScroll", {
            configurable: true,
            writable: true,
            value: el,
        });
        Object.defineProperty(wrapper.vm, "selectedPeerChatItems", {
            configurable: true,
            get: () => [{ type: "lxmf_message", lxmf_message: { hash: "aa".repeat(16) } }],
        });

        let currentScrollTop = 0;
        Object.defineProperty(el, "scrollTop", {
            configurable: true,
            get: () => currentScrollTop,
            set: (v) => {
                currentScrollTop = v;
            },
        });

        // Drop any open-conversation settle/pin left from mount initialLoad.
        wrapper.vm.cancelPendingScrollToBottom();

        const cancelSpy = vi.spyOn(wrapper.vm, "cancelPendingScrollToBottom");
        wrapper.vm.autoScrollOnNewMessage = true;
        const genAtStart = wrapper.vm.scrollBottomGen;
        wrapper.vm.scrollMessagesToBottom({ pinAfter: true });
        expect(wrapper.vm.scrollBottomGen).toBeGreaterThan(genAtStart);

        // User leaves the newest edge while settle/pin is still active (attachment decode pending).
        currentScrollTop = 1800;
        wrapper.vm.onMessagesScroll({ target: el });

        expect(wrapper.vm.autoScrollOnNewMessage).toBe(false);
        expect(cancelSpy).toHaveBeenCalled();
        expect(wrapper.vm.conversationOpenPinUntil).toBe(0);
        expect(wrapper.vm.openConversationScrollObserver).toBeNull();

        const genAfterCancel = wrapper.vm.scrollBottomGen;
        currentScrollTop = 1800;
        await flushPromises();
        await wrapper.vm.$nextTick();
        await wrapper.vm.$nextTick();
        // Stale settle must not revive a newer generation or yank scrollTop back to 0.
        expect(wrapper.vm.scrollBottomGen).toBe(genAfterCancel);
        expect(currentScrollTop).toBe(1800);

        el.remove();
    });

    it("open pin refuses to start when user has left the newest edge", async () => {
        const wrapper = mountViewer();
        await flushPromises();
        wrapper.vm.cancelPendingScrollToBottom();
        const el = makeMessagesScrollTarget({
            reverse: true,
            scrollTop: 2200,
            scrollHeight: 5000,
            clientHeight: 400,
        });
        Object.defineProperty(wrapper.vm.$refs, "messagesScroll", {
            configurable: true,
            writable: true,
            value: el,
        });
        wrapper.vm.autoScrollOnNewMessage = false;
        const gen = wrapper.vm.scrollBottomGen;
        wrapper.vm._startOpenConversationScrollPin(gen, () => gen !== wrapper.vm.scrollBottomGen);
        expect(wrapper.vm.openConversationScrollObserver).toBeNull();
        expect(wrapper.vm.conversationOpenPinUntil).toBe(0);
        el.remove();
    });

    it("cancelPendingScrollToBottom stales settle generation and disconnects open pin", async () => {
        const wrapper = mountViewer();
        await flushPromises();
        const el = makeMessagesScrollTarget({
            reverse: true,
            scrollTop: 0,
            scrollHeight: 2000,
            clientHeight: 400,
        });
        Object.defineProperty(wrapper.vm.$refs, "messagesScroll", {
            configurable: true,
            writable: true,
            value: el,
        });
        const genBefore = wrapper.vm.scrollBottomGen;
        wrapper.vm.conversationOpenPinUntil = Date.now() + 5000;
        wrapper.vm.openConversationScrollObserver = {
            disconnect: vi.fn(),
        };
        wrapper.vm.cancelPendingScrollToBottom();
        expect(wrapper.vm.scrollBottomGen).toBeGreaterThan(genBefore);
        expect(wrapper.vm.openConversationScrollObserver).toBeNull();
        expect(wrapper.vm.conversationOpenPinUntil).toBe(0);
        el.remove();
    });
});
