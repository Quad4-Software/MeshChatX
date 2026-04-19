import { describe, it, expect } from "vitest";
import {
    diagnose,
    evaluateProductMatch,
    ISSUE_NOT_PROVISIONED,
    ISSUE_FIRMWARE_HASH_MISSING,
    ISSUE_FIRMWARE_HASH_MISMATCH,
    ISSUE_PRODUCT_MISMATCH,
    ISSUE_DETECT_FAILED,
} from "@/js/rnode/Diagnostics.js";

const fakeRom = (overrides = {}) => ({
    eeprom: [],
    parse: () => ({
        is_provisioned: true,
        product: 0xa0,
        model: 0xa1,
        hardware_revision: 1,
        serial_number: 1,
        ...overrides,
    }),
});

const fakeRnode = (overrides = {}) => ({
    getFirmwareVersion: async () => "1.80",
    getPlatform: async () => 0x80,
    getBoard: async () => 0x35,
    getMcu: async () => 0x81,
    getRomAsObject: async () => fakeRom(),
    getFirmwareHash: async () => [1, 2, 3, 4],
    getTargetFirmwareHash: async () => [1, 2, 3, 4],
    ...overrides,
});

describe("Diagnostics.diagnose", () => {
    it("flags detect_failed when rnode lacks methods", async () => {
        const result = await diagnose(null);
        expect(result.issues).toContain(ISSUE_DETECT_FAILED);
    });

    it("returns no issues for a healthy provisioned device", async () => {
        const result = await diagnose(fakeRnode(), { timeoutMs: 1000 });
        expect(result.firmwareVersion).toBe("1.80");
        expect(result.isProvisioned).toBe(true);
        expect(result.issues).toEqual([]);
        expect(result.summary.firmware_hash).toBe("01020304");
    });

    it("flags not_provisioned when rom.parse returns falsy", async () => {
        const result = await diagnose(
            fakeRnode({ getRomAsObject: async () => ({ eeprom: [], parse: () => null }) }),
            { timeoutMs: 1000 }
        );
        expect(result.issues).toContain(ISSUE_NOT_PROVISIONED);
        expect(result.suggestionKeys).toContain(
            "tools.rnode_flasher.diagnostics.suggestions.not_provisioned"
        );
    });

    it("flags firmware_hash_missing when target hash is all zero or missing", async () => {
        const result = await diagnose(
            fakeRnode({
                getTargetFirmwareHash: async () => [0, 0, 0, 0],
            }),
            { timeoutMs: 1000 }
        );
        expect(result.issues).toContain(ISSUE_FIRMWARE_HASH_MISSING);
    });

    it("flags firmware_hash_mismatch when hashes differ", async () => {
        const result = await diagnose(
            fakeRnode({
                getFirmwareHash: async () => [1, 2, 3, 4],
                getTargetFirmwareHash: async () => [9, 9, 9, 9],
            }),
            { timeoutMs: 1000 }
        );
        expect(result.issues).toContain(ISSUE_FIRMWARE_HASH_MISMATCH);
    });

    it("flags product_mismatch when expected product differs from EEPROM", async () => {
        const result = await diagnose(fakeRnode(), {
            expectedProductId: 0xff,
            timeoutMs: 1000,
        });
        expect(result.issues).toContain(ISSUE_PRODUCT_MISMATCH);
    });
});

describe("Diagnostics.evaluateProductMatch", () => {
    it("returns missing_data when arguments are missing", () => {
        expect(evaluateProductMatch(null, null)).toMatchObject({ matches: false, reason: "missing_data" });
    });
    it("returns not_provisioned when rom is not provisioned", () => {
        expect(
            evaluateProductMatch({ is_provisioned: false, product: 1, model: 2 }, { productId: 1, modelId: 2 })
        ).toMatchObject({ matches: false, reason: "not_provisioned" });
    });
    it("returns product_mismatch and model_mismatch correctly", () => {
        expect(
            evaluateProductMatch({ is_provisioned: true, product: 1, model: 2 }, { productId: 9, modelId: 2 })
        ).toMatchObject({ matches: false, reason: "product_mismatch" });
        expect(
            evaluateProductMatch({ is_provisioned: true, product: 1, model: 2 }, { productId: 1, modelId: 9 })
        ).toMatchObject({ matches: false, reason: "model_mismatch" });
    });
    it("returns matches=true when everything aligns", () => {
        expect(
            evaluateProductMatch({ is_provisioned: true, product: 1, model: 2 }, { productId: 1, modelId: 2 })
        ).toMatchObject({ matches: true });
    });
});
