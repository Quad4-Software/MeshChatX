import { describe, it, expect } from "vitest";
import {
    buildDisplayGroupsNewestFirst,
    prependDisplayGroupsNewestFirst,
    CONVERSATION_MESSAGES_PAGE_SIZE,
} from "@/components/messages/conversationDisplayGroups.js";

function chatItem(hash, { outbound = false, image = false } = {}) {
    const fields = image ? { image: { image_type: "png" } } : {};
    return {
        type: "lxmf_message",
        is_outbound: outbound,
        lxmf_message: {
            hash,
            content: "",
            state: "delivered",
            fields,
        },
    };
}

function canMerge(item) {
    return !!item?.lxmf_message?.fields?.image;
}

describe("conversationDisplayGroups", () => {
    it("exports a reasonable page size for incremental loads", () => {
        expect(CONVERSATION_MESSAGES_PAGE_SIZE).toBeGreaterThanOrEqual(40);
        expect(CONVERSATION_MESSAGES_PAGE_SIZE).toBeLessThanOrEqual(100);
    });

    it("buildDisplayGroupsNewestFirst merges consecutive image-only rows", () => {
        const items = [chatItem("a", { image: true }), chatItem("b", { image: true }), chatItem("c")];
        const groups = buildDisplayGroupsNewestFirst(items, canMerge);
        expect(groups).toHaveLength(2);
        expect(groups[0].type).toBe("single");
        expect(groups[0].key).toBe("c");
        expect(groups[1].type).toBe("imageGroup");
        expect(groups[1].items).toHaveLength(2);
    });

    it("prependDisplayGroupsNewestFirst matches full rebuild for mixed prepends", () => {
        const existingItems = [
            chatItem("m1", { image: true }),
            chatItem("m2", { image: true }),
            chatItem("m3"),
            chatItem("m4"),
        ];
        const prepended = [chatItem("p1"), chatItem("p2", { image: true }), chatItem("p3", { image: true })];
        const allItems = prepended.concat(existingItems);

        const full = buildDisplayGroupsNewestFirst(allItems, canMerge);
        const base = buildDisplayGroupsNewestFirst(existingItems, canMerge);
        const incremental = prependDisplayGroupsNewestFirst(base, prepended, canMerge);

        expect(incremental.map((g) => g.key)).toEqual(full.map((g) => g.key));
    });

    it("prependDisplayGroupsNewestFirst is fast for large cached threads", () => {
        const existingItems = Array.from({ length: 2000 }, (_, i) => chatItem(`m${i}`));
        const base = buildDisplayGroupsNewestFirst(existingItems, canMerge);
        const prepended = Array.from({ length: 50 }, (_, i) => chatItem(`p${i}`));

        const t0 = performance.now();
        for (let k = 0; k < 40; k++) {
            prependDisplayGroupsNewestFirst(base, prepended, canMerge);
        }
        const ms = performance.now() - t0;

        expect(ms).toBeLessThan(500);
    });
});
