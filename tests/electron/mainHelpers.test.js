import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const {
    getUserProvidedArguments,
    formatRenderProcessGoneDetails,
    isLocalBackendUrl,
    shouldOpenInElectronWindow,
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

    it("shouldOpenInElectronWindow keeps local popouts and call windows in Electron", () => {
        expect(shouldOpenInElectronWindow("https://127.0.0.1:9337/#/popout/map")).toBe(true);
        expect(shouldOpenInElectronWindow("https://127.0.0.1:9337/call.html")).toBe(true);
        expect(shouldOpenInElectronWindow("http://localhost:9337/#/popout/messages/abc")).toBe(true);
        expect(shouldOpenInElectronWindow("blob:https://127.0.0.1:9337/print")).toBe(true);
        expect(shouldOpenInElectronWindow("https://127.0.0.1:9337/rnode-flasher/index.html")).toBe(false);
        expect(shouldOpenInElectronWindow("https://example.com/#/popout/map")).toBe(false);
        expect(shouldOpenInElectronWindow("")).toBe(false);
    });
});
