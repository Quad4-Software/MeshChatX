import { describe, it, expect, vi } from "vitest";
import {
    applyReticulumInstanceSettings,
    fetchReticulumInstanceSettings,
} from "@/js/settings/settingsReticulumInstanceService.js";

describe("settingsReticulumInstanceService", () => {
    it("fetches instance settings from the API", async () => {
        const api = {
            get: vi.fn().mockResolvedValue({
                data: {
                    instance: {
                        share_instance: true,
                        local_hops_delta: true,
                    },
                },
            }),
        };
        const instance = await fetchReticulumInstanceSettings(api);
        expect(api.get).toHaveBeenCalledWith("/api/v1/reticulum/instance");
        expect(instance.local_hops_delta).toBe(true);
    });

    it("patches instance settings through the API", async () => {
        const api = {
            patch: vi.fn().mockResolvedValue({
                data: { message: "ok", instance: { local_hops_delta: true } },
            }),
        };
        const response = await applyReticulumInstanceSettings(api, { local_hops_delta: true });
        expect(api.patch).toHaveBeenCalledWith("/api/v1/reticulum/instance", {
            local_hops_delta: true,
        });
        expect(response.data.instance.local_hops_delta).toBe(true);
    });
});
