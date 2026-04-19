import { describe, it, expect } from "vitest";
import {
    detectCapabilities,
    pickDefaultTransport,
    transportSuggestionKeys,
    TRANSPORT_SERIAL,
    TRANSPORT_BLUETOOTH,
    TRANSPORT_WIFI,
} from "@/js/rnode/Capabilities.js";

const mkEnv = (overrides = {}) => ({
    isSecureContext: true,
    navigator: { userAgent: "Mozilla/5.0", ...(overrides.navigator || {}) },
    ...overrides,
});

describe("Capabilities.detectCapabilities", () => {
    it("reports native serial when navigator.serial is present", () => {
        const env = mkEnv({ navigator: { userAgent: "x", serial: {} } });
        const caps = detectCapabilities({ env });
        expect(caps.transports[TRANSPORT_SERIAL].available).toBe(true);
        expect(caps.transports[TRANSPORT_SERIAL].kind).toBe("native");
    });

    it("reports polyfill serial when usb + serial polyfill module are available", () => {
        const env = mkEnv({ navigator: { userAgent: "x", usb: {} }, serial: {} });
        const caps = detectCapabilities({ env });
        expect(caps.transports[TRANSPORT_SERIAL].available).toBe(true);
        expect(caps.transports[TRANSPORT_SERIAL].polyfilled).toBe(true);
    });

    it("flags missing polyfill when only usb is exposed", () => {
        const env = mkEnv({ navigator: { userAgent: "x", usb: {} } });
        const caps = detectCapabilities({ env });
        expect(caps.transports[TRANSPORT_SERIAL].available).toBe(false);
        expect(caps.transports[TRANSPORT_SERIAL].reason).toBe("polyfill_not_loaded");
    });

    it("reports android_webview_no_serial on Android without USB", () => {
        const env = mkEnv({ navigator: { userAgent: "Linux; Android 11; SomePhone" } });
        const caps = detectCapabilities({ env });
        expect(caps.transports[TRANSPORT_SERIAL].available).toBe(false);
        expect(caps.transports[TRANSPORT_SERIAL].reason).toBe("android_webview_no_serial");
        expect(caps.platform.isAndroid).toBe(true);
    });

    it("reports bluetooth available when navigator.bluetooth is present", () => {
        const env = mkEnv({ navigator: { userAgent: "x", bluetooth: {} } });
        const caps = detectCapabilities({ env });
        expect(caps.transports[TRANSPORT_BLUETOOTH].available).toBe(true);
    });

    it("flags insecure_context for bluetooth when not in secure context", () => {
        const env = mkEnv({ isSecureContext: false, navigator: { userAgent: "x" } });
        const caps = detectCapabilities({ env });
        expect(caps.transports[TRANSPORT_BLUETOOTH].available).toBe(false);
        expect(caps.transports[TRANSPORT_BLUETOOTH].reason).toBe("insecure_context");
    });

    it("always exposes wifi transport as available", () => {
        const env = mkEnv();
        const caps = detectCapabilities({ env });
        expect(caps.transports[TRANSPORT_WIFI].available).toBe(true);
    });
});

describe("Capabilities.pickDefaultTransport", () => {
    it("prefers serial when available", () => {
        const caps = detectCapabilities({ env: mkEnv({ navigator: { userAgent: "x", serial: {}, bluetooth: {} } }) });
        expect(pickDefaultTransport(caps)).toBe(TRANSPORT_SERIAL);
    });
    it("falls back to bluetooth when serial unavailable", () => {
        const caps = detectCapabilities({ env: mkEnv({ navigator: { userAgent: "x", bluetooth: {} } }) });
        expect(pickDefaultTransport(caps)).toBe(TRANSPORT_BLUETOOTH);
    });
    it("falls back to wifi when nothing else", () => {
        const caps = detectCapabilities({ env: mkEnv() });
        expect(pickDefaultTransport(caps)).toBe(TRANSPORT_WIFI);
    });
});

describe("Capabilities.transportSuggestionKeys", () => {
    it("returns empty list when transport is available", () => {
        const caps = detectCapabilities({ env: mkEnv({ navigator: { userAgent: "x", serial: {} } }) });
        expect(transportSuggestionKeys(caps, TRANSPORT_SERIAL)).toEqual([]);
    });
    it("returns reason key + android hint for serial on android", () => {
        const env = mkEnv({ navigator: { userAgent: "Android" } });
        const caps = detectCapabilities({ env });
        const keys = transportSuggestionKeys(caps, TRANSPORT_SERIAL);
        expect(keys).toContain("tools.rnode_flasher.support.serial.android_webview_no_serial");
        expect(keys).toContain("tools.rnode_flasher.support.serial.android_use_chrome");
    });
    it("includes https hint for bluetooth when not secure", () => {
        const env = mkEnv({ isSecureContext: false, navigator: { userAgent: "x" } });
        const caps = detectCapabilities({ env });
        const keys = transportSuggestionKeys(caps, TRANSPORT_BLUETOOTH);
        expect(keys).toContain("tools.rnode_flasher.support.bluetooth.insecure_context");
        expect(keys).toContain("tools.rnode_flasher.support.bluetooth.requires_https");
    });
});
