import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("../../meshchatx/src/frontend/js/ToastUtils.js", () => ({
    default: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

import {
    addNomadFavourite,
    renameNomadFavourite,
} from "../../meshchatx/src/frontend/features/nomadnetwork/lib/nomadBrowserData";

describe("nomadBrowserData favourites endpoints", () => {
    let api;

    beforeEach(() => {
        api = { get: vi.fn(), post: vi.fn().mockResolvedValue({}), put: vi.fn(), delete: vi.fn() };
        window.api = api;
    });

    afterEach(() => {
        delete window.api;
        vi.restoreAllMocks();
    });

    it("posts adds to /api/v1/favourites/add", async () => {
        const ok = await addNomadFavourite({
            destination_hash: "ab".repeat(16),
            display_name: "Node",
        });
        expect(ok).toBe(true);
        expect(api.post).toHaveBeenCalledWith(
            "/api/v1/favourites/add",
            expect.objectContaining({
                destination_hash: "ab".repeat(16),
                aspect: "nomadnetwork.node",
            })
        );
    });

    it("posts renames to /favourites/{hash}/rename with display_name", async () => {
        vi.stubGlobal("prompt", undefined);
        const { default: DialogUtils } = await import("../../meshchatx/src/frontend/js/DialogUtils.js");
        vi.spyOn(DialogUtils, "prompt").mockResolvedValue("New Name");

        const hash = "cd".repeat(16);
        const ok = await renameNomadFavourite({ destination_hash: hash });
        expect(ok).toBe(true);
        expect(api.post).toHaveBeenCalledWith(`/api/v1/favourites/${hash}/rename`, {
            display_name: "New Name",
        });
        expect(api.put).not.toHaveBeenCalled();
    });
});
