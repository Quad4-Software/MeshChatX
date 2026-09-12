import { describe, it, expect } from "vitest";
import { useUnreadStore } from "@/js/stores/unreadStore.js";

describe("unreadStore", () => {
    it("has initial values", () => {
        expect(useUnreadStore().unreadConversationsCount).toBe(0);
    });

    it("can be updated", () => {
        useUnreadStore().unreadConversationsCount = 5;
        expect(useUnreadStore().unreadConversationsCount).toBe(5);
    });
});
