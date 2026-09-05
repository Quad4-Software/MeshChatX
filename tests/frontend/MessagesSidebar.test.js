// SPDX-License-Identifier: 0BSD

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/svelte";
import MessagesSidebar from "@/features/messages/components/MessagesSidebar.svelte";

function props(overrides = {}) {
    return {
        peers: {},
        conversations: [],
        folders: [],
        selectedFolderId: null,
        selectedDestinationHash: "",
        isLoading: false,
        isLoadingMore: false,
        hasMoreConversations: false,
        isLoadingMoreAnnounces: false,
        isSearchingAnnounces: false,
        hasMoreAnnounces: false,
        totalPeersCount: 0,
        ...overrides,
    };
}

afterEach(cleanup);

describe("MessagesSidebar.svelte", () => {
    it("renders conversation and announce tabs", () => {
        render(MessagesSidebar, props());
        expect(screen.getByText("messages.conversations")).toBeTruthy();
        expect(screen.getByText("messages.announces")).toBeTruthy();
    });

    it("renders folders and calls the folder callback", async () => {
        const onfolderClick = vi.fn();
        render(
            MessagesSidebar,
            props({
                folders: [{ id: 10, name: "Archive" }],
                onfolderClick,
            })
        );

        await fireEvent.click(screen.getByText("Archive"));
        expect(onfolderClick).toHaveBeenCalledWith(10);
    });

    it("renders conversations and calls the conversation callback", async () => {
        const conversation = {
            destination_hash: "abc123",
            display_name: "Alice",
            latest_message_created_at: 10,
            is_unread: false,
            failed_messages_count: 0,
        };
        const onconversationClick = vi.fn();
        render(MessagesSidebar, props({ conversations: [conversation], onconversationClick }));

        await fireEvent.click(screen.getByText("Alice"));
        expect(onconversationClick).toHaveBeenCalledWith(conversation);
    });

    it("puts pinned conversations before newer unpinned rows", () => {
        render(
            MessagesSidebar,
            props({
                conversations: [
                    {
                        destination_hash: "new",
                        display_name: "New",
                        latest_message_created_at: 20,
                    },
                    {
                        destination_hash: "pinned",
                        display_name: "Pinned",
                        latest_message_created_at: 10,
                    },
                ],
                pinnedPeerHashes: ["pinned"],
            })
        );

        const text = document.body.textContent;
        expect(text.indexOf("Pinned")).toBeLessThan(text.indexOf("New"));
    });

    it("activates announces and reports the public callback", async () => {
        const onannouncesTabActivated = vi.fn();
        render(MessagesSidebar, props({ onannouncesTabActivated }));

        await fireEvent.click(screen.getByText("messages.announces"));
        expect(onannouncesTabActivated).toHaveBeenCalledOnce();
    });
});
