const { test, expect } = require("@playwright/test");
const { execFileSync, execSync } = require("child_process");
const path = require("path");

const CRAWL = path.join(__dirname, "../../scripts/e2e/mobile-crawl.py");

function adbDevice() {
    try {
        const out = execSync("adb devices", { encoding: "utf-8", timeout: 5000 });
        return out
            .split("\n")
            .slice(1)
            .some((l) => l.includes("\tdevice"));
    } catch {
        return false;
    }
}

test.describe("Mobile crawl (adb)", () => {
    test.setTimeout(300000);
    test.skip(!adbDevice(), "no adb device connected");

    test("app survives a bounded UI crawl without crashing", () => {
        execFileSync("python3", [CRAWL, "--steps", "40"], {
            stdio: "inherit",
            timeout: 290000,
        });
        expect(true).toBeTruthy();
    });
});
