import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import { afterEach, describe, expect, it, vi } from "vitest";
import MessageReactionsOverlay from "@/features/messages/components/MessageReactionsOverlay.svelte";

describe("MessageReactionsOverlay", () => {
    const renderOverlay = (props = {}) =>
        render(MessageReactionsOverlay, {
            props: {
                chatItem: { lxmf_message: { hash: "m1" } },
                actions: {
                    openReactionPicker: vi.fn(),
                    reactionReactorLabel: vi.fn(() => "You"),
                },
                reactions: [],
                showReactButton: true,
                ...props,
            },
        });

    afterEach(cleanup);

    it("renders reaction chips and react button", () => {
        renderOverlay({
            reactions: [
                { emoji: "\u{1F44D}", sender: "a", reactionHash: "r1" },
                { emoji: "\u2764\uFE0F", sender: "b", reactionHash: "r2" },
            ],
        });
        expect(screen.getByText("\u{1F44D}")).toBeTruthy();
        expect(screen.getByText("\u2764\uFE0F")).toBeTruthy();
        expect(screen.getByRole("button")).toBeTruthy();
    });

    it("caps visible reactions and shows +N overflow", () => {
        const reactions = Array.from({ length: 7 }, (_, i) => ({
            emoji: "\u{1F44D}",
            sender: `s${i}`,
            reactionHash: `r${i}`,
        }));
        renderOverlay({ reactions });
        expect(screen.getByText("+3")).toBeTruthy();
    });

    it("does not crash when reactionReactorLabel throws", () => {
        renderOverlay({
            reactions: [{ emoji: "\u{1F44D}", sender: "a", reactionHash: "r1" }],
            actions: {
                openReactionPicker: vi.fn(),
                reactionReactorLabel: () => {
                    throw new Error("label boom");
                },
            },
        });
        expect(screen.getByText("\u{1F44D}")).toBeTruthy();
    });

    it("opens picker via react button", async () => {
        const openReactionPicker = vi.fn();
        const chatItem = { lxmf_message: { hash: "m1" } };
        renderOverlay({
            chatItem,
            actions: { openReactionPicker, reactionReactorLabel: () => "" },
        });
        await fireEvent.click(screen.getByRole("button"));
        expect(openReactionPicker).toHaveBeenCalledWith(chatItem);
    });
});
