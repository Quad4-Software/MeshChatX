import { describe, it, expect } from "vitest";
import { countRelayMentions } from "@/js/relayMentionCount.js";

describe("relayMentionCount", () => {
    it("counts mention rooms across hubs", () => {
        expect(
            countRelayMentions([
                { mention_rooms: ["lobby"] },
                { mention_rooms: ["general", "ops"] },
                { mention_rooms: [] },
            ])
        ).toBe(3);
    });

    it("returns zero for invalid input", () => {
        expect(countRelayMentions(null)).toBe(0);
        expect(countRelayMentions([])).toBe(0);
    });
});
