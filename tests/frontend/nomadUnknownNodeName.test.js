import { describe, expect, it } from "vitest";
import {
    isUnknownNodeDisplayName,
    resolveFavouriteUpsertDisplayName,
    UNKNOWN_NODE_DISPLAY_NAMES,
} from "@/js/nomadUnknownNodeName.js";

describe("nomadUnknownNodeName", () => {
    it("treats empty and known placeholders as unknown", () => {
        expect(isUnknownNodeDisplayName("")).toBe(true);
        expect(isUnknownNodeDisplayName("   ")).toBe(true);
        expect(isUnknownNodeDisplayName(null)).toBe(true);
        expect(isUnknownNodeDisplayName("Unknown Node")).toBe(true);
        expect(isUnknownNodeDisplayName("Anonymous Node")).toBe(true);
        expect(isUnknownNodeDisplayName("Unbekannter Knoten")).toBe(true);
        expect(isUnknownNodeDisplayName("未知节点")).toBe(true);
        expect(isUnknownNodeDisplayName("Real Node")).toBe(false);
    });

    it("honors a localized unknown string from i18n", () => {
        expect(isUnknownNodeDisplayName("Custom Unknown", "Custom Unknown")).toBe(true);
        expect(isUnknownNodeDisplayName("Custom Unknown", "Other")).toBe(false);
    });

    it("resolveFavouriteUpsertDisplayName keeps existing real names", () => {
        expect(
            resolveFavouriteUpsertDisplayName(
                { display_name: "Unknown Node" },
                { display_name: "Kept" },
                "Unknown Node"
            )
        ).toBe("Kept");
        expect(
            resolveFavouriteUpsertDisplayName(
                { display_name: "Unbekannter Knoten" },
                { display_name: "Kept" },
                "Unbekannter Knoten"
            )
        ).toBe("Kept");
    });

    it("resolveFavouriteUpsertDisplayName canonicalizes unknown for new favourites", () => {
        expect(resolveFavouriteUpsertDisplayName({ display_name: "未知节点" }, null, "未知节点")).toBe("Unknown Node");
        expect(resolveFavouriteUpsertDisplayName({ display_name: "Fresh Name" }, null, "Unknown Node")).toBe(
            "Fresh Name"
        );
    });

    it("exports the shared sentinel list", () => {
        expect(UNKNOWN_NODE_DISPLAY_NAMES).toContain("Unknown Node");
        expect(UNKNOWN_NODE_DISPLAY_NAMES).toContain("Неизвестный узел");
    });
});
