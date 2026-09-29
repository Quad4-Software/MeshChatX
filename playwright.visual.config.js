const { defineConfig, devices } = require("@playwright/test");

// Visual regression config: identical stack to playwright.config.js, but the
// snapshotPathTemplate re-roots toHaveScreenshot baselines into
// tests/e2e/__screenshots__/ and testMatch scopes collection to the visual
// spec only. Generate or refresh baselines with:
//   playwright test --config playwright.visual.config.js --update-snapshots

if (process.env.E2E_BACKEND_PORT === undefined || process.env.E2E_BACKEND_PORT === "") {
    process.env.E2E_BACKEND_PORT = "18079";
}

const HOST = process.env.E2E_VITE_HOST || "127.0.0.1";
const PORT = parseInt(process.env.E2E_VITE_PORT || "5173", 10);
const baseURL = `http://${HOST}:${PORT}`;

module.exports = defineConfig({
    testDir: "./tests/e2e",
    testMatch: /visual-regression\.spec\.js$/,
    snapshotPathTemplate: "{testDir}/__screenshots__/{arg}{-projectName}{-snapshotSuffix}{ext}",
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: 0,
    workers: 1,
    reporter: process.env.CI ? [["line"]] : [["list"], ["html", { open: "never" }]],
    use: {
        ...devices["Desktop Chrome"],
        baseURL,
        trace: "off",
        screenshot: "off",
    },
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
    ],
    webServer: {
        command: "bash scripts/e2e/start-e2e-stack.sh",
        url: `${baseURL}/`,
        reuseExistingServer: !process.env.CI,
        timeout: 480000,
        stdout: "pipe",
        stderr: "pipe",
    },
});
