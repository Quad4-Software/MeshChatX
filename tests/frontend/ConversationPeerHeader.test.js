// SPDX-License-Identifier: 0BSD

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import ConversationPeerHeader from "@/features/messages/components/ConversationPeerHeader.svelte";

afterEach(cleanup);

describe("ConversationPeerHeader.svelte", () => {
    const selectedPeer = {
        destination_hash: "aa".repeat(16),
        display_name: "Peer Name",
        custom_display_name: null,
    };

    it("renders the peer name and formatted destination", () => {
        render(ConversationPeerHeader, { selectedPeer });
        expect(screen.getByText("Peer Name")).toBeTruthy();
        expect(document.body.textContent).toContain("aaaa");
    });

    it("opens display-name editing through its callback", async () => {
        const oneditdisplayname = vi.fn();
        render(ConversationPeerHeader, { selectedPeer, oneditdisplayname });

        await fireEvent.click(screen.getByRole("button", { name: /Peer Name/ }));
        expect(oneditdisplayname).toHaveBeenCalledOnce();
    });

    it("shows missing path state", () => {
        render(ConversationPeerHeader, {
            selectedPeer,
            peerPathSnapshot: { path_stale: true, path_unresponsive: false },
            selectedPeerPath: null,
        });

        expect(screen.getByText("No path")).toBeTruthy();
    });
});
