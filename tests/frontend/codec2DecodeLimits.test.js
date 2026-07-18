// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    MAX_CODEC2_DECODED_RAW_BYTES,
    MAX_CODEC2_ENCODED_BYTES,
    assertByteLengthAtMost,
} from "../../meshchatx/src/frontend/js/codec2DecodeLimits.js";

describe("codec2DecodeLimits", () => {
    it("accepts buffers within caps", () => {
        const small = new Uint8Array(16);
        expect(assertByteLengthAtMost(small, MAX_CODEC2_ENCODED_BYTES)).toBe(small);
    });

    it("rejects oversized encoded and decoded buffers", () => {
        expect(() => assertByteLengthAtMost(new Uint8Array(MAX_CODEC2_ENCODED_BYTES + 1), MAX_CODEC2_ENCODED_BYTES)).toThrow(
            /exceeds size limit/
        );
        expect(() =>
            assertByteLengthAtMost(new Uint8Array(MAX_CODEC2_DECODED_RAW_BYTES + 1), MAX_CODEC2_DECODED_RAW_BYTES)
        ).toThrow(/exceeds size limit/);
    });

    it("rejects missing data", () => {
        expect(() => assertByteLengthAtMost(null, 10)).toThrow(/Missing/);
    });
});
