import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const {
    getUserProvidedArguments,
    formatRenderProcessGoneDetails,
    isLocalBackendUrl,
} = require("../../electron/mainHelpers.js");

describe("electron/mainHelpers", () => {
    it("getUserProvidedArguments filters ignored flags and skips argv[0]", () => {
        const argv = ["/app/electron", "--no-https", "--no-sandbox", "--ozone-platform-hint=auto", "--port", "1"];
        expect(getUserProvidedArguments(argv)).toEqual(["--no-https", "--port", "1"]);
    });

    it("formatRenderProcessGoneDetails handles null/undefined", () => {
        expect(formatRenderProcessGoneDetails(null)).toBe("no details");
        expect(formatRenderProcessGoneDetails(undefined)).toBe("no details");
    });

    it("formatRenderProcessGoneDetails serializes reason and exitCode", () => {
        const s = formatRenderProcessGoneDetails({ reason: "crashed", exitCode: 5 });
        expect(s).toContain("crashed");
        expect(s).toContain("5");
    });

    it("isLocalBackendUrl matches localhost backends only", () => {
        expect(isLocalBackendUrl("https://127.0.0.1:9337/api")).toBe(true);
        expect(isLocalBackendUrl("http://localhost:9337/")).toBe(true);
        expect(isLocalBackendUrl("https://example.com")).toBe(false);
        expect(isLocalBackendUrl("")).toBe(false);
    });
});
