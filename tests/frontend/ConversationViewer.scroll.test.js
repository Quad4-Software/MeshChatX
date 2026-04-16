import { mount } from "@vue/test-utils";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import ConversationViewer from "@/components/messages/ConversationViewer.vue";
import WebSocketConnection from "@/js/WebSocketConnection";
import GlobalState from "@/js/GlobalState";

vi.mock("@/js/DialogUtils", () => ({
    default: {
        confirm: vi.fn(() => Promise.resolve(true)),
    },
}));

function makeMessagesScrollTarget({ reverse, scrollTop, scrollHeight, clientHeight }) {
    const outer = document.createElement("div");
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
});
