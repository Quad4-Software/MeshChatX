import { describe, expect, it } from "vitest";
import { readPackagedAppVersion } from "../../electron/appVersion.js";

describe("electron/appVersion", () => {
    it("reads version from electron/app-version.json", () => {
        expect(readPackagedAppVersion("0.0.0")).toBe("4.8.3");
    });
});
