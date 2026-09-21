// SPDX-License-Identifier: 0BSD

import { cleanup, fireEvent, render, waitFor } from "@testing-library/svelte";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import MiniChat from "@/features/map/components/MiniChat.svelte";

describe("MiniChat.svelte", () => {
    let axiosMock;

    beforeEach(() => {
        axiosMock = {
            get: vi.fn(() => Promise.resolve({ data: { lxmf_messages: [] } })),
            post: vi.fn(() =>
                Promise.resolve({
                    data: { lxmf_message: { hash: "abc", content: "hello", created_at: 99 } },
                })
            ),
        };
        window.api = axiosMock;
    });

    afterEach(() => {
        cleanup();
        delete window.api;
    });

    const renderMiniChat = () =>
        render(MiniChat, { props: { destinationHash: "a".repeat(32) } });

    it("fetches recent messages on mount", async () => {
        renderMiniChat();
        await waitFor(() =>
            expect(axiosMock.get).toHaveBeenCalledWith(expect.stringContaining("lxmf-messages/conversation"))
        );
    });

    it("caps the local message list at 40 entries after sending", async () => {
        const fetched = Array.from({ length: 40 }, (_, i) => ({
            hash: `h${i}`,
            content: `msg-${i}`,
            timestamp: i,
        }));
        // Endpoint returns newest first; the component reverses it.
        axiosMock.get.mockResolvedValue({ data: { lxmf_messages: [...fetched].reverse() } });

        const { container } = renderMiniChat();
        await waitFor(() => expect(container.querySelectorAll(".wrap-break-word").length).toBe(40));

        const input = container.querySelector("input[type=text]");
        await fireEvent.input(input, { target: { value: "hello" } });
        await fireEvent.click(container.querySelector("button[aria-label]"));

        await waitFor(() => {
            const bubbles = [...container.querySelectorAll(".wrap-break-word")];
            expect(bubbles.length).toBeLessThanOrEqual(40);
            expect(bubbles.at(-1).textContent.trim()).toBe("hello");
            expect(bubbles[0].textContent.trim()).toBe("msg-1");
        });
    });
});
