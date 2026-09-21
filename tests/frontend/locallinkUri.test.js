import { describe, it, expect } from "vitest";
import { buildWifiQrPayload, parseWifiQrPayload } from "@/js/locallinkUri";

describe("buildWifiQrPayload", () => {
    it("builds a WPA payload", () => {
        const payload = buildWifiQrPayload({ ssid: "MeshNet", passphrase: "sekret123" });
        expect(payload).toBe("WIFI:T:WPA;S:MeshNet;P:sekret123;;");
    });

    it("builds an open-network payload", () => {
        const payload = buildWifiQrPayload({ ssid: "OpenNet" });
        expect(payload).toBe("WIFI:T:nopass;S:OpenNet;;");
    });

    it("escapes special characters in fields", () => {
        const payload = buildWifiQrPayload({ ssid: "Net;1", passphrase: 'p:a"s\\wxyz' });
        expect(payload).toContain("S:Net\\;1;");
        expect(payload).toContain('P:p\\:a\\"s\\\\wxyz;');
        const parsed = parseWifiQrPayload(payload);
        expect(parsed.ssid).toBe("Net;1");
        expect(parsed.passphrase).toBe('p:a"s\\wxyz');
    });

    it("returns null for missing ssid", () => {
        expect(buildWifiQrPayload({ ssid: "" })).toBeNull();
        expect(buildWifiQrPayload({})).toBeNull();
    });

    it("returns null for oversized ssid", () => {
        expect(buildWifiQrPayload({ ssid: "x".repeat(33) })).toBeNull();
    });

    it("returns null for short or oversized passphrase", () => {
        expect(buildWifiQrPayload({ ssid: "N", passphrase: "short" })).toBeNull();
        expect(buildWifiQrPayload({ ssid: "N", passphrase: "x".repeat(64) })).toBeNull();
    });
});

describe("parseWifiQrPayload", () => {
    it("parses a WPA payload", () => {
        const parsed = parseWifiQrPayload("WIFI:T:WPA;S:MeshNet;P:sekret123;;");
        expect(parsed).toEqual({
            security: "WPA",
            ssid: "MeshNet",
            passphrase: "sekret123",
            hidden: false,
        });
    });

    it("parses an open network", () => {
        const parsed = parseWifiQrPayload("WIFI:T:nopass;S:OpenNet;;");
        expect(parsed.security).toBe("nopass");
        expect(parsed.passphrase).toBeNull();
    });

    it("parses hidden flag", () => {
        const parsed = parseWifiQrPayload("WIFI:S:H;T:WPA;P:sekret123;H:true;;");
        expect(parsed.hidden).toBe(true);
    });

    it("ignores unknown fields per spec", () => {
        const parsed = parseWifiQrPayload("WIFI:S:N;X:whatever;T:WPA;P:sekret123;;");
        expect(parsed.ssid).toBe("N");
    });

    it("rejects non-WIFI payloads", () => {
        expect(parseWifiQrPayload("lxmf://abc")).toBeNull();
        expect(parseWifiQrPayload("https://evil.example")).toBeNull();
        expect(parseWifiQrPayload("")).toBeNull();
        expect(parseWifiQrPayload(null)).toBeNull();
        expect(parseWifiQrPayload(42)).toBeNull();
    });

    it("rejects missing ssid", () => {
        expect(parseWifiQrPayload("WIFI:T:WPA;P:sekret123;;")).toBeNull();
    });

    it("rejects field without key separator", () => {
        expect(parseWifiQrPayload("WIFI:S:N;junk;T:WPA;;")).toBeNull();
    });

    it("rejects dangling escape", () => {
        expect(parseWifiQrPayload("WIFI:S:abc\\")).toBeNull();
    });

    it("rejects oversized ssid", () => {
        expect(parseWifiQrPayload(`WIFI:S:${"x".repeat(33)};T:WPA;;`)).toBeNull();
    });

    it("rejects oversized passphrase", () => {
        expect(parseWifiQrPayload(`WIFI:S:N;T:WPA;P:${"x".repeat(64)};;`)).toBeNull();
    });

    it("rejects unknown security type", () => {
        expect(parseWifiQrPayload("WIFI:T:MAGIC;S:N;;")).toBeNull();
    });

    it("round-trips build then parse", () => {
        const original = { ssid: "DIRECT-xy", passphrase: "hunter2pass" };
        const parsed = parseWifiQrPayload(buildWifiQrPayload(original));
        expect(parsed.ssid).toBe(original.ssid);
        expect(parsed.passphrase).toBe(original.passphrase);
    });
});
