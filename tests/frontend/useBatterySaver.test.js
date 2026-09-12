// SPDX-License-Identifier: 0BSD

import { beforeEach, describe, expect, it, vi } from "vitest";
import { useBatterySaver } from "../../meshchatx/src/frontend/js/settings/useBatterySaver.js";

vi.mock("../../meshchatx/src/frontend/js/settings/batterySaverBitrateApply.js", () => ({
    applyBatterySaverBitrateLimits: vi.fn(async () => ({ updated: ["rnode"] })),
    restoreBatterySaverBitrateLimits: vi.fn(async () => ({ updated: ["rnode"] })),
}));

import {
    applyBatterySaverBitrateLimits,
    restoreBatterySaverBitrateLimits,
} from "../../meshchatx/src/frontend/js/settings/batterySaverBitrateApply.js";

describe("useBatterySaver", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        window.api = { get: vi.fn(async () => ({ data: { interfaces: {} } })) };
    });

    it("loads interface rows sorted by name", async () => {
        window.api.get = vi.fn(async () => ({
            data: {
                interfaces: {
                    zeta: { type: "TCP", bitrate: 9600 },
                    alpha: { type: "RNode", bitrate: 1200 },
                },
            },
        }));
        const bs = useBatterySaver();
        await bs.loadBatteryInterfaceRows();
        expect(bs.batteryInterfaceRows.value.map((r) => r.name)).toEqual(["alpha", "zeta"]);
    });

    it("interface row load failure empties the list", async () => {
        window.api.get = vi.fn(async () => Promise.reject(new Error("down")));
        const bs = useBatterySaver();
        await bs.loadBatteryInterfaceRows();
        expect(bs.batteryInterfaceRows.value).toEqual([]);
    });

    it("enabling applies bitrate limits when configured", async () => {
        const bs = useBatterySaver();
        bs.patchBatterySaver({ applyInterfaceBitrateLimits: true });
        await bs.onBatterySaverEnabledChange(true);
        expect(applyBatterySaverBitrateLimits).toHaveBeenCalledWith({ reload: true });
    });

    it("disabling restores bitrate limits when previous values exist", async () => {
        const bs = useBatterySaver();
        bs.patchBatterySaver({ interfaceBitratePrevious: { rnode: 1200 } });
        await bs.onBatterySaverEnabledChange(false);
        expect(restoreBatterySaverBitrateLimits).toHaveBeenCalledWith({ reload: true });
    });

    it("bitrate limit change drops empty or non-numeric entries", () => {
        const bs = useBatterySaver();
        bs.patchBatterySaver({ interfaceBitrateLimits: { rnode: 1200, bad: 5 } });
        // The v-model writes "" into the raw map before this handler runs.
        bs.batterySaver.value.interfaceBitrateLimits.bad = "";
        bs.onBatteryBitrateLimitChange("bad");
        expect(bs.batterySaver.value.interfaceBitrateLimits.bad).toBeUndefined();
        expect(bs.batterySaver.value.interfaceBitrateLimits.rnode).toBe(1200);
        bs.batterySaver.value.interfaceBitrateLimits.rnode = "2400.7";
        bs.onBatteryBitrateLimitChange("rnode");
        expect(bs.batterySaver.value.interfaceBitrateLimits.rnode).toBe(2401);
    });

    it("apply is guarded while busy", async () => {
        const bs = useBatterySaver();
        bs.batteryBitrateBusy.value = true;
        await bs.applyBatteryBitrateLimitsNow();
        expect(applyBatterySaverBitrateLimits).not.toHaveBeenCalled();
    });
});
