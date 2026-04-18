import { describe, it, expect } from "vitest";
import {
    INCOMING_DELIVERY_MAX_BYTES,
    INCOMING_DELIVERY_PRESET_BYTES,
    clampIncomingDeliveryBytes,
    incomingDeliveryBytesFromCustom,
    incomingDeliveryBytesFromPresetKey,
    syncIncomingDeliveryFieldsFromBytes,
} from "../../meshchatx/src/frontend/js/settings/incomingDeliveryLimit.js";

describe("incomingDeliveryLimit", () => {
    it("clamps to max 1 GiB", () => {
        expect(clampIncomingDeliveryBytes(2_000_000_000)).toBe(INCOMING_DELIVERY_MAX_BYTES);
    });

    it("maps preset keys to bytes", () => {
        expect(incomingDeliveryBytesFromPresetKey("1gb")).toBe(1_000_000_000);
        expect(incomingDeliveryBytesFromPresetKey("custom")).toBeNull();
    });

    it("parses custom MB and GB", () => {
        expect(incomingDeliveryBytesFromCustom(9, "mb")).toBe(9_000_000);
        expect(incomingDeliveryBytesFromCustom(1, "gb")).toBe(1_000_000_000);
    });

    it("syncs preset field for exact preset bytes", () => {
        const s = syncIncomingDeliveryFieldsFromBytes(INCOMING_DELIVERY_PRESET_BYTES["25mb"]);
        expect(s.preset).toBe("25mb");
    });

    it("syncs custom for non-preset bytes", () => {
        const s = syncIncomingDeliveryFieldsFromBytes(9_000_000);
        expect(s.preset).toBe("custom");
        expect(s.customAmount).toBe(9);
        expect(s.customUnit).toBe("mb");
    });
});
