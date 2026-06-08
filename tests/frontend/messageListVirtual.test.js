import { describe, it, expect } from "vitest";
import {
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
