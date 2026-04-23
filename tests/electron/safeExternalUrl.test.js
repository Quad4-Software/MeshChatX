import { describe, it, expect } from "vitest";
import { normalizeExternalUrlForOpen } from "../../electron/safeExternalUrl.js";

describe("safeExternalUrl", () => {
    it("allows http and https origins", () => {
        expect(normalizeExternalUrlForOpen("http://example.com/path")).toBe("http://example.com/path");
        expect(normalizeExternalUrlForOpen("https://example.com/x?y=1#z")).toBe("https://example.com/x?y=1#z");
    });

    it("allows mailto", () => {
        expect(normalizeExternalUrlForOpen("mailto:test@example.com")).toBe("mailto:test@example.com");
    });

    it("rejects javascript and data URLs", () => {
        expect(normalizeExternalUrlForOpen("javascript:alert(1)")).toBeNull();
        expect(normalizeExternalUrlForOpen("data:text/html,<script>1</script>")).toBeNull();
        expect(normalizeExternalUrlForOpen("file:///etc/passwd")).toBeNull();
        expect(normalizeExternalUrlForOpen("vbscript:msgbox(1)")).toBeNull();
    });

    it("rejects non-URL garbage", () => {
        expect(normalizeExternalUrlForOpen("")).toBeNull();
        expect(normalizeExternalUrlForOpen("   ")).toBeNull();
        expect(normalizeExternalUrlForOpen(null)).toBeNull();
        expect(normalizeExternalUrlForOpen(undefined)).toBeNull();
        expect(normalizeExternalUrlForOpen("not a url")).toBeNull();
    });

    it("allows normal http(s) for the system browser (openExternal use case)", () => {
        expect(normalizeExternalUrlForOpen("http://192.168.0.1/")).toBe("http://192.168.0.1/");
        expect(normalizeExternalUrlForOpen("https://example.com/path")).toBe("https://example.com/path");
    });

    it("fuzz: random strings rarely return non-null", () => {
        for (let i = 0; i < 200; i++) {
            const s = String.fromCodePoint(...Array.from({ length: 12 }, () => Math.floor(Math.random() * 0x80)));
            expect(() => normalizeExternalUrlForOpen(s)).not.toThrow();
            const o = normalizeExternalUrlForOpen(s);
            if (o !== null) {
                expect(o.startsWith("http://") || o.startsWith("https://") || o.startsWith("mailto:")).toBe(true);
            }
        }
    });
});
