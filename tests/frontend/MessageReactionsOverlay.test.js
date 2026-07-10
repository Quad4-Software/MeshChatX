import { mount } from "@vue/test-utils";
import { describe, it, expect, vi } from "vitest";
import MessageReactionsOverlay from "@/components/messages/MessageReactionsOverlay.vue";

describe("MessageReactionsOverlay", () => {
    const mountOverlay = (props = {}) =>
        mount(MessageReactionsOverlay, {
            props: {
                chatItem: { lxmf_message: { hash: "m1" } },
                cv: {
                    openReactionPicker: vi.fn(),
                    reactionReactorLabel: vi.fn(() => "You"),
                },
                reactions: [],
                showReactButton: true,
                ...props,
            },
            global: {
                mocks: { $t: (key) => key },
                stubs: { MaterialDesignIcon: true },
            },
        });

    it("renders reaction chips and react button", () => {
        const wrapper = mountOverlay({
            reactions: [
                { emoji: "\u{1F44D}", sender: "a", reactionHash: "r1" },
                { emoji: "\u2764\uFE0F", sender: "b", reactionHash: "r2" },
            ],
        });
        expect(wrapper.text()).toContain("\u{1F44D}");
        expect(wrapper.text()).toContain("\u2764\uFE0F");
        expect(wrapper.find("button").exists()).toBe(true);
    });

    it("caps visible reactions and shows +N overflow", () => {
        const reactions = Array.from({ length: 7 }, (_, i) => ({
            emoji: "\u{1F44D}",
            sender: `s${i}`,
            reactionHash: `r${i}`,
        }));
        const wrapper = mountOverlay({ reactions });
        expect(wrapper.text()).toContain("+3");
    });

    it("tolerates null/undefined/non-array reactions without crashing", () => {
        expect(() => mountOverlay({ reactions: null })).not.toThrow();
        expect(() => mountOverlay({ reactions: undefined })).not.toThrow();
        expect(() => mountOverlay({ reactions: "bad" })).not.toThrow();
        expect(() =>
            mountOverlay({
                reactions: [null, undefined, { emoji: "x", sender: "a", reactionHash: "r" }],
            })
        ).not.toThrow();
    });

    it("does not crash when reactionReactorLabel throws", () => {
        const wrapper = mountOverlay({
            reactions: [{ emoji: "\u{1F44D}", sender: "a", reactionHash: "r1" }],
            cv: {
                openReactionPicker: vi.fn(),
                reactionReactorLabel: () => {
                    throw new Error("label boom");
                },
            },
        });
        expect(wrapper.exists()).toBe(true);
        expect(wrapper.text()).toContain("\u{1F44D}");
    });

    it("opens picker via react button", async () => {
        const openReactionPicker = vi.fn();
        const chatItem = { lxmf_message: { hash: "m1" } };
        const wrapper = mountOverlay({
            chatItem,
            cv: { openReactionPicker, reactionReactorLabel: () => "" },
        });
        await wrapper.find("button").trigger("click");
        expect(openReactionPicker).toHaveBeenCalledWith(chatItem);
    });
});
