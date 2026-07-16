import { describe, it, expect, beforeEach, vi } from "vitest";
import { buildBitrateApplyPayload, saveBatterySaverPrefs } from "@/js/settings/batterySaverPrefs.js";
import {
    applyBatterySaverBitrateLimits,
    restoreBatterySaverBitrateLimits,
} from "@/js/settings/batterySaverBitrateApply.js";

describe("batterySaverBitrateApply", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    it("buildBitrateApplyPayload snapshots previous bitrates", () => {
        const { bitrates, previous } = buildBitrateApplyPayload(
            { LoRa: { bitrate: "5000" }, TCP: { bitrate: null } },
            { LoRa: 1200, Missing: 100 }
        );
        expect(bitrates).toEqual({ LoRa: 1200 });
        expect(previous).toEqual({ LoRa: 5000 });
    });

    it("applyBatterySaverBitrateLimits posts bitrates and reloads", async () => {
        saveBatterySaverPrefs({
            applyInterfaceBitrateLimits: true,
            interfaceBitrateLimits: { LoRa: 1200 },
        });
        const api = {
            get: vi.fn().mockResolvedValue({
                data: { interfaces: { LoRa: { bitrate: "5000", type: "RNodeInterface" } } },
            }),
            post: vi.fn().mockResolvedValue({
                data: { updated: ["LoRa"], reloaded: true },
            }),
        };
        const result = await applyBatterySaverBitrateLimits({ api, reload: true });
        expect(api.post).toHaveBeenCalledWith("/api/v1/reticulum/interfaces/bitrates", {
            bitrates: { LoRa: 1200 },
            reload: true,
        });
        expect(result).toEqual({ updated: ["LoRa"], reloaded: true });
    });

    it("restoreBatterySaverBitrateLimits restores previous map", async () => {
        saveBatterySaverPrefs({
            interfaceBitratePrevious: { LoRa: 5000 },
        });
        const api = {
            post: vi.fn().mockResolvedValue({
                data: { updated: ["LoRa"], reloaded: true },
            }),
        };
        const result = await restoreBatterySaverBitrateLimits({ api, reload: true });
        expect(api.post).toHaveBeenCalledWith("/api/v1/reticulum/interfaces/bitrates", {
            bitrates: { LoRa: 5000 },
            reload: true,
        });
        expect(result.updated).toEqual(["LoRa"]);
    });
});
