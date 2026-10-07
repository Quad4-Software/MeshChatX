import { describe, it, expect } from "vitest";
import {
    diffFreshInboundKeys,
    MIN_VIRTUAL_DISPLAY_GROUPS,
    displayGroupsOldestFirst,
    estimateGroupHeight,
    findDisplayGroupIndexForMessageHash,
} from "@/components/messages/messageListVirtual.js";

describe("messageListVirtual.js", () => {
    it("displayGroupsOldestFirst reverses newest-first groups", () => {
        const g = [
            { type: "single", key: "a", chatItem: { lxmf_message: { hash: "a" } } },
            { type: "single", key: "b", chatItem: { lxmf_message: { hash: "b" } } },
        ];
        const o = displayGroupsOldestFirst(g);
        expect(o.map((x) => x.key).join(",")).toBe("b,a");
    });

    it("estimateGroupHeight returns larger size for image groups", () => {
        expect(estimateGroupHeight({ type: "imageGroup", items: [] })).toBeGreaterThan(
            estimateGroupHeight({ type: "single", chatItem: {} })
        );
    });

    it("estimateGroupHeight scales with file attachment count", () => {
        const oneFile = estimateGroupHeight({
            type: "single",
            chatItem: {
                lxmf_message: {
                    content: "",
                    fields: { file_attachments: [{ file_name: "a.zip" }] },
                },
            },
        });
        const threeFiles = estimateGroupHeight({
            type: "single",
            chatItem: {
                lxmf_message: {
                    content: "",
                    fields: {
                        file_attachments: [{ file_name: "a.zip" }, { file_name: "b.zip" }, { file_name: "c.zip" }],
                    },
                },
            },
        });
        expect(threeFiles).toBeGreaterThan(oneFile);
    });

    it("findDisplayGroupIndexForMessageHash finds single and image group members", () => {
        const groups = [
            { type: "single", key: "x", chatItem: { lxmf_message: { hash: "h1" } } },
            {
                type: "imageGroup",
                key: "ig",
                items: [{ lxmf_message: { hash: "h2" } }, { lxmf_message: { hash: "h3" } }],
            },
        ];
        expect(findDisplayGroupIndexForMessageHash(groups, "h1")).toBe(0);
        expect(findDisplayGroupIndexForMessageHash(groups, "h3")).toBe(1);
        expect(findDisplayGroupIndexForMessageHash(groups, "missing")).toBe(-1);
    });

    it("findDisplayGroupIndexForMessageHash skips date dividers", () => {
        const groups = [
            { type: "dateDivider", dayKey: "2026-04-26", key: "d1" },
            { type: "single", key: "x", chatItem: { lxmf_message: { hash: "h1" } } },
        ];
        expect(findDisplayGroupIndexForMessageHash(groups, "h1")).toBe(1);
    });

    it("estimateGroupHeight returns modest height for date dividers", () => {
        expect(estimateGroupHeight({ type: "dateDivider", key: "d" })).toBe(44);
    });

    it("MIN_VIRTUAL_DISPLAY_GROUPS is a positive threshold", () => {
        expect(MIN_VIRTUAL_DISPLAY_GROUPS).toBeGreaterThan(10);
    });
});

describe("diffFreshInboundKeys", () => {
    const single = (key, is_outbound = false) => ({
        type: "single",
        key,
        chatItem: { is_outbound },
    });
    const imageGroup = (key, is_outbound = false) => ({
        type: "imageGroup",
        key,
        items: [{ is_outbound }],
    });

    it("flags inbound keys appended at the tail", () => {
        const known = new Set(["a", "b"]);
        const groups = [single("a"), single("b"), single("c")];
        const { fresh, nextKeys } = diffFreshInboundKeys(groups, known);
        expect(fresh).toEqual(["c"]);
        expect(nextKeys.has("c")).toBe(true);
    });

    it("skips outbound keys appended at the tail", () => {
        const known = new Set(["a"]);
        const groups = [single("a"), single("b", true)];
        expect(diffFreshInboundKeys(groups, known).fresh).toEqual([]);
    });

    it("skips known keys and non-message groups", () => {
        const known = new Set(["a", "b"]);
        const groups = [
            single("a"),
            { type: "dateDivider", key: "d1" },
            single("b"),
        ];
        expect(diffFreshInboundKeys(groups, known).fresh).toEqual([]);
    });

    it("does not flag keys appended beyond the tail window", () => {
        const known = new Set(["a"]);
        const groups = [single("n1")].concat(
            [single("a")],
            Array.from({ length: 10 }, (_, i) => single(`t${i}`)),
        );
        // n1 sits at index 0, outside the last-6 window -> not fresh
        const { fresh } = diffFreshInboundKeys(groups, known);
        expect(fresh).not.toContain("n1");
        expect(fresh.length).toBe(6);
    });

    it("flags inbound image groups", () => {
        const known = new Set(["a"]);
        const groups = [single("a"), imageGroup("g1")];
        expect(diffFreshInboundKeys(groups, known).fresh).toEqual(["g1"]);
    });

    it("handles empty and non-array input", () => {
        const { fresh, nextKeys } = diffFreshInboundKeys(null, new Set());
        expect(fresh).toEqual([]);
        expect(nextKeys.size).toBe(0);
    });
});
