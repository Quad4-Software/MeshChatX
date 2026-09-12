// SPDX-License-Identifier: 0BSD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
    prefetchConversationFirstPage,
    takeConversationPrefetch,
} from "@/js/conversationPrefetch.js";

describe("conversationPrefetch", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("fetches the first page once and hands it out once", async () => {
        const peerHash = "ab".repeat(16);
        const api = { get: vi.fn().mockResolvedValue({ data: { lxmf_messages: [] } }) };
        prefetchConversationFirstPage(api, peerHash, 50);
        prefetchConversationFirstPage(api, peerHash, 50);
        expect(api.get).toHaveBeenCalledTimes(1);
        expect(api.get).toHaveBeenCalledWith(`/api/v1/lxmf-messages/conversation/${peerHash}`, {
            params: { count: 50, order: "desc" },
        });

        const first = await takeConversationPrefetch(peerHash);
        expect(first).toEqual({ data: { lxmf_messages: [] } });
        expect(takeConversationPrefetch(peerHash)).toBeNull();
    });

    it("drops entries older than the TTL and refetches", () => {
        const peerHash = "cd".repeat(16);
        const api = { get: vi.fn().mockResolvedValue({ data: { lxmf_messages: [] } }) };
        prefetchConversationFirstPage(api, peerHash, 50);
        vi.advanceTimersByTime(11000);
        expect(takeConversationPrefetch(peerHash)).toBeNull();

        prefetchConversationFirstPage(api, peerHash, 50);
        expect(api.get).toHaveBeenCalledTimes(2);
    });

    it("resolves to null on fetch failure so callers can fall back", async () => {
        const peerHash = "ef".repeat(16);
        const api = { get: vi.fn().mockRejectedValue(new Error("boom")) };
        prefetchConversationFirstPage(api, peerHash, 50);
        const result = await takeConversationPrefetch(peerHash);
        expect(result).toBeNull();
    });
});
