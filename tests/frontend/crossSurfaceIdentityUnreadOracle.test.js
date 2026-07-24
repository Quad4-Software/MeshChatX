// SPDX-License-Identifier: 0BSD

/**
 * Oracle tests for unread badge / DND / identity-switch leakage across
 * conversations, notifications, relay, nomad, rnsh, and map.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import MessagesPage from "../../meshchatx/src/frontend/components/messages/MessagesPage.vue";
import App from "../../meshchatx/src/frontend/components/App.vue";
import GlobalState from "../../meshchatx/src/frontend/js/GlobalState";
import { isPrivateOrLocalHostname } from "../../meshchatx/src/frontend/js/mapLocalUrl.js";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        loading: vi.fn(),
        dismiss: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/NotificationUtils", () => ({
    default: {
        clearMessageNotifications: vi.fn(),
        showNewMessageNotification: vi.fn(),
    },
}));

vi.mock("../../meshchatx/src/frontend/js/NotificationSoundUtils", () => ({
    default: {
        play: vi.fn(async () => false),
    },
}));

describe("conversations unread oracle", () => {
    beforeEach(() => {
        GlobalState.unreadConversationsCount = 3;
        window.api = {
            post: vi.fn(async () => ({ data: {} })),
        };
    });

    it("does not decrement nav unread when dismissing an already-read conversation", async () => {
        // Oracle: badge count may only drop when the conversation was unread.
        // Re-selecting an open read thread must not burn a badge count.
        const peer = "aa".repeat(16);
        const ctx = {
            conversations: [{ destination_hash: peer, is_unread: false }],
            selectedPeer: { destination_hash: peer, is_unread: false },
            paneViewers: {},
            focusedPaneId: 0,
        };

        MessagesPage.methods.dismissUnreadForOpenDestination.call(ctx, peer);
        await vi.waitFor(() => expect(window.api.post).toHaveBeenCalled());

        expect(GlobalState.unreadConversationsCount).toBe(3);
    });

    it("decrements nav unread once when dismissing an unread conversation without a viewer", async () => {
        const peer = "bb".repeat(16);
        const conversation = { destination_hash: peer, is_unread: true };
        const ctx = {
            conversations: [conversation],
            selectedPeer: conversation,
            paneViewers: {},
            focusedPaneId: 0,
        };

        MessagesPage.methods.dismissUnreadForOpenDestination.call(ctx, peer);
        await vi.waitFor(() => expect(window.api.post).toHaveBeenCalled());

        expect(conversation.is_unread).toBe(false);
        expect(GlobalState.unreadConversationsCount).toBe(2);
    });
});

describe("notifications DND unread oracle", () => {
    it("still refreshes unread badge under DND (DND suppresses OS/sound only)", async () => {
        // Oracle: DND must not freeze the Messages nav badge while other pages are open.
        const updateUnreadConversationsCount = vi.fn();
        const ctx = {
            config: { do_not_disturb_enabled: true },
            updateUnreadConversationsCount,
            updateRelayChatUnreadCount: vi.fn(),
        };

        const handlers = App.methods.getShellWsHandlers.call(ctx);
        await handlers["lxmf.delivery"]({
            sieve_suppress_notifications: false,
            remote_identity_name: "Peer",
            remote_identity_hash: "cc".repeat(16),
            lxmf_message: {
                is_incoming: true,
                source_hash: "cc".repeat(16),
                title: "hi",
                content: "hello",
            },
        });

        expect(updateUnreadConversationsCount).toHaveBeenCalled();
    });

    it("still skips unread refresh for sieve-suppressed non-user-facing deliveries", async () => {
        const updateUnreadConversationsCount = vi.fn();
        const ctx = {
            config: { do_not_disturb_enabled: false },
            updateUnreadConversationsCount,
        };
        const handlers = App.methods.getShellWsHandlers.call(ctx);
        await handlers["lxmf.delivery"]({
            sieve_suppress_notifications: true,
            lxmf_message: {
                is_incoming: true,
                source_hash: "dd".repeat(16),
                title: "",
                content: "",
                fields: { telemetry: {} },
            },
        });
        expect(updateUnreadConversationsCount).not.toHaveBeenCalled();
    });
});

describe("map local URL oracle", () => {
    it("treats only RFC1918 and loopback hosts as local, not all 172.*", () => {
        // Oracle: 172.16.0.0/12 is private. 172.15.x and 172.32.x are not.
        expect(isPrivateOrLocalHostname("127.0.0.1")).toBe(true);
        expect(isPrivateOrLocalHostname("10.1.2.3")).toBe(true);
        expect(isPrivateOrLocalHostname("192.168.1.1")).toBe(true);
        expect(isPrivateOrLocalHostname("172.16.0.1")).toBe(true);
        expect(isPrivateOrLocalHostname("172.31.255.255")).toBe(true);
        expect(isPrivateOrLocalHostname("172.15.0.1")).toBe(false);
        expect(isPrivateOrLocalHostname("172.32.0.1")).toBe(false);
        expect(isPrivateOrLocalHostname("8.8.8.8")).toBe(false);
        expect(isPrivateOrLocalHostname("tiles.openstreetmap.org")).toBe(false);
    });
});

describe("identity-switch surface contracts", () => {
    function readFrontend(relativePath) {
        const { readFileSync } = require("fs");
        const { join } = require("path");
        return readFileSync(join(process.cwd(), "meshchatx/src/frontend", relativePath), "utf8");
    }

    it("RelayChatPage listens for identity-switched and clears hub UI state", () => {
        const src = readFrontend("components/relay/RelayChatPage.vue");
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/onIdentitySwitched/);
        expect(src).toMatch(/this\.hubs\s*=\s*\[\]/);
    });

    it("RNSHManagerPage listens for identity-switched and clears session output cache", () => {
        const src = readFrontend("components/tools/RNSHManagerPage.vue");
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/outputsBySession\s*=\s*\{\}/);
    });

    it("NomadNetworkBrowser listens for identity-switched and resets tabs", () => {
        const src = readFrontend("components/nomadnetwork/NomadNetworkBrowser.vue");
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/this\.tabs\s*=\s*\[\]/);
    });

    it("MapBrowser listens for identity-switched and resets tabs", () => {
        const src = readFrontend("components/map/MapBrowser.vue");
        expect(src).toContain('GlobalEmitter.on("identity-switched"');
        expect(src).toMatch(/this\.tabs\s*=\s*\[\]/);
    });
});
