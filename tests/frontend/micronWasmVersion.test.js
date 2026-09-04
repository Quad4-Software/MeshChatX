import { describe, it, expect } from "vitest";
import {
    bundledMicronWasmReleaseTag,
    normalizeMicronWasmReleaseTag,
    resolveMicronWasmReleaseLabel,
} from "../../meshchatx/src/frontend/js/micronWasmVersion.js";

describe("micronWasmVersion", () => {
    it("normalizes version embedded in wasm filenames", () => {
        expect(normalizeMicronWasmReleaseTag("micron-parser-go-v1.0.7.wasm")).toBe("v1.0.7");
        expect(normalizeMicronWasmReleaseTag("v1.0.7.wasm")).toBe("v1.0.7");
        expect(normalizeMicronWasmReleaseTag("V1.0.7")).toBe("v1.0.7");
    });

    it("returns null for generic wasm filenames", () => {
        expect(normalizeMicronWasmReleaseTag("micron-parser-go.wasm")).toBe(null);
    });

    it("prefers override tag over bundled release", () => {
        expect(
            resolveMicronWasmReleaseLabel({
                overrideReleaseTag: "micron-parser-go-v1.0.7.wasm",
            })
        ).toBe("v1.0.7");
    });

    it("falls back to bundled release when override has no version", () => {
        const bundled = bundledMicronWasmReleaseTag();
        expect(
            resolveMicronWasmReleaseLabel({
                overrideReleaseTag: "micron-parser-go.wasm",
            })
        ).toBe(bundled);
    });
});
