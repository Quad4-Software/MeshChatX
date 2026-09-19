// SPDX-License-Identifier: 0BSD

import { describe, expect, it } from "vitest";
import {
    normalizeLxmfMessage,
    normalizeSidebandCommandKey,
} from "../../meshchatx/src/frontend/components/messages/lxmf/normalize.js";

describe("normalizeLxmfMessage", () => {
    it("reference: copies msg and leaves created_at when already set", () => {
        const msg = { hash: "abc", created_at: "2020-01-01T00:00:00.000Z", timestamp: 1, state: "delivered" };
        expect(normalizeLxmfMessage(msg, false)).toEqual({
            hash: "abc",
            created_at: "2020-01-01T00:00:00.000Z",
            timestamp: 1,
            state: "delivered",
        });
        expect(normalizeLxmfMessage(msg, false)).not.toBe(msg);
    });

    it("reference: derives created_at ISO from unix timestamp when missing", () => {
        const msg = { hash: "abc", timestamp: 1700000000, state: "delivered" };
        expect(normalizeLxmfMessage(msg, false)).toEqual({
            hash: "abc",
            timestamp: 1700000000,
            state: "delivered",
            created_at: new Date(1700000000 * 1000).toISOString(),
        });
    });

    it("reference: outbound unknown state becomes outbound", () => {
        expect(normalizeLxmfMessage({ state: "unknown" }, true)).toEqual({ state: "outbound" });
        expect(normalizeLxmfMessage({ state: "unknown" }, false)).toEqual({ state: "unknown" });
        expect(normalizeLxmfMessage({ state: "delivered" }, true)).toEqual({ state: "delivered" });
    });

    it("reference: no timestamp and no created_at leaves created_at unset", () => {
        expect(normalizeLxmfMessage({ hash: "x" }, false)).toEqual({ hash: "x" });
    });
});

describe("normalizeSidebandCommandKey", () => {
    it("reference: empty or whitespace-only keys reject", () => {
        expect(normalizeSidebandCommandKey(null)).toBe(null);
        expect(normalizeSidebandCommandKey(undefined)).toBe(null);
        expect(normalizeSidebandCommandKey("")).toBe(null);
        expect(normalizeSidebandCommandKey("   ")).toBe(null);
    });

    it("reference: known aliases map to fixed hex keys", () => {
        expect(normalizeSidebandCommandKey("plugin")).toBe("0x00");
        expect(normalizeSidebandCommandKey("PLUGIN")).toBe("0x00");
        expect(normalizeSidebandCommandKey("telemetry_request")).toBe("0x01");
        expect(normalizeSidebandCommandKey("request")).toBe("0x01");
        expect(normalizeSidebandCommandKey("location_request")).toBe("0x01");
        expect(normalizeSidebandCommandKey("ping")).toBe("0x02");
        expect(normalizeSidebandCommandKey("echo")).toBe("0x03");
        expect(normalizeSidebandCommandKey("signal_report")).toBe("0x04");
    });

    it("reference: decimal 0-255 becomes zero-padded 0xNN", () => {
        expect(normalizeSidebandCommandKey("0")).toBe("0x00");
        expect(normalizeSidebandCommandKey("1")).toBe("0x01");
        expect(normalizeSidebandCommandKey("255")).toBe("0xff");
        expect(normalizeSidebandCommandKey("16")).toBe("0x10");
    });

    it("reference: decimal outside 0-255 rejects", () => {
        expect(normalizeSidebandCommandKey("256")).toBe(null);
        expect(normalizeSidebandCommandKey("-1")).toBe(null);
    });

    it("reference: 0x hex forms normalize to lowercase zero-padded", () => {
        expect(normalizeSidebandCommandKey("0x1")).toBe("0x01");
        expect(normalizeSidebandCommandKey("0x0A")).toBe("0x0a");
        expect(normalizeSidebandCommandKey("0xff")).toBe("0xff");
        expect(normalizeSidebandCommandKey("0xFF")).toBe("0xff");
    });

    it("reference: unknown tokens reject", () => {
        expect(normalizeSidebandCommandKey("nope")).toBe(null);
        expect(normalizeSidebandCommandKey("0xGGG")).toBe(null);
        expect(normalizeSidebandCommandKey("0x100")).toBe(null);
        expect(normalizeSidebandCommandKey("12.5")).toBe(null);
    });
});
