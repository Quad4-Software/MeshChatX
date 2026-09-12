import { describe, it, expect } from "vitest";
import globalState from "@/js/GlobalState";

describe("GlobalState.js", () => {
    it("has initial values", () => {
        expect(globalState.unreadConversationsCount).toBe(0);
    });

    it("can be updated", () => {
        globalState.unreadConversationsCount = 5;
        expect(globalState.unreadConversationsCount).toBe(5);
    });
});
