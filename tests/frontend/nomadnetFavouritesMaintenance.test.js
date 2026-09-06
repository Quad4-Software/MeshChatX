// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import DownloadUtils from "@/js/DownloadUtils.js";
import ToastUtils from "@/js/ToastUtils.js";
import GlobalEmitter from "@/js/GlobalEmitter.js";
import {
    exportNomadnetFavouritesLayout,
    importNomadnetFavouritesFile,
} from "@/features/settings/lib/maintenanceActions.js";
import { _resetNomadFavouritesLayoutSaveStateForTests } from "@/js/nomadFavouritesLayoutStore.js";

vi.mock("@/js/DownloadUtils.js", () => ({
    default: {
        downloadFile: vi.fn().mockResolvedValue(undefined),
    },
}));

vi.mock("@/js/ToastUtils.js", () => ({
    default: {
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
    },
}));

vi.mock("@/js/i18n.js", () => ({
    t: (key) => key,
}));

describe("nomadnet favourites maintenance parity", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        _resetNomadFavouritesLayoutSaveStateForTests();
        localStorage.clear();
    });

    it("exports layout via favourites GET plus layout store (not missing nomadnet endpoints)", async () => {
        const api = {
            get: vi.fn(async (url) => {
                if (url === "/api/v1/favourites/layout") {
                    return {
                        data: {
                            layout: {
                                sections: [{ id: "default", name: "Favourites", collapsed: false }],
                                sectionOrder: ["default"],
                                favouritesBySection: { default: ["aabb"] },
                            },
                        },
                    };
                }
                if (url === "/api/v1/favourites") {
                    return { data: { favourites: [{ destination_hash: "aabb" }] } };
                }
                throw new Error(`unexpected get ${url}`);
            }),
            put: vi.fn(),
            post: vi.fn(),
        };

        await exportNomadnetFavouritesLayout(api);

        expect(api.get).toHaveBeenCalledWith("/api/v1/favourites/layout");
        expect(api.get).toHaveBeenCalledWith("/api/v1/favourites");
        expect(api.get).not.toHaveBeenCalledWith("/api/v1/favourites/export/nomadnet");
        expect(DownloadUtils.downloadFile).toHaveBeenCalled();
        const blob = DownloadUtils.downloadFile.mock.calls[0][1];
        const text = await blob.text();
        const body = JSON.parse(text);
        expect(body.format).toBe("meshchatx/nomadnet_favourites/v1");
        expect(body.favourites).toEqual([{ destination_hash: "aabb" }]);
        expect(body.layout.favouritesBySection.default).toEqual(["aabb"]);
        expect(ToastUtils.success).toHaveBeenCalledWith("maintenance.nomadnet_favourites_exported");
    });

    it("imports favourites records and full layout then emits refresh events", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({ data: { layout: null } }),
            put: vi.fn().mockResolvedValue({
                data: {
                    layout: {
                        sections: [{ id: "default", name: "Favourites", collapsed: false }],
                        sectionOrder: ["default"],
                        favouritesBySection: { default: ["ccdd"] },
                    },
                },
            }),
            post: vi.fn().mockResolvedValue({ data: { imported: 1 } }),
        };
        const emitSpy = vi.spyOn(GlobalEmitter, "emit");
        const file = new File(
            [
                JSON.stringify({
                    format: "meshchatx/nomadnet_favourites/v1",
                    favourites: [{ destination_hash: "ccdd" }],
                    layout: {
                        sections: [{ id: "default", name: "Favourites", collapsed: false }],
                        sectionOrder: ["default"],
                        favouritesBySection: { default: ["ccdd"] },
                    },
                }),
            ],
            "favs.json",
            { type: "application/json" }
        );

        importNomadnetFavouritesFile(file, api);
        await vi.waitFor(() => {
            expect(api.post).toHaveBeenCalled();
        });

        expect(api.post).toHaveBeenCalledWith("/api/v1/favourites/import", {
            favourites: [{ destination_hash: "ccdd" }],
        });
        expect(api.post).not.toHaveBeenCalledWith("/api/v1/favourites/import/nomadnet", expect.anything());
        expect(api.put).toHaveBeenCalledWith(
            "/api/v1/favourites/layout",
            expect.objectContaining({
                layout: expect.objectContaining({
                    favouritesBySection: expect.objectContaining({ default: ["ccdd"] }),
                }),
            })
        );
        expect(emitSpy).toHaveBeenCalledWith("nomadnet-favourites-layout-imported");
        expect(emitSpy).toHaveBeenCalledWith("nomadnet-favourites-changed");
        expect(ToastUtils.success).toHaveBeenCalledWith("maintenance.nomadnet_favourites_imported");
    });
});
