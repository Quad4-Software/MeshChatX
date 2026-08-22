const { defineConfig, devices } = require("@playwright/test");

// Lighthouse scores must use built assets, not the Vite dev server.
process.env.MESHCHAT_UI_PROD = "1";

if (process.env.E2E_BACKEND_PORT === undefined || process.env.E2E_BACKEND_PORT === "") {
    process.env.E2E_BACKEND_PORT = "18079";
}

const LH_DEBUG_PORT = parseInt(process.env.LH_DEBUG_PORT || "9222", 10);
const baseURL = `http://127.0.0.1:${process.env.E2E_BACKEND_PORT}`;

module.exports = defineConfig({
    testDir: "./tests/ui",
    testMatch: /lighthouse\.spec\.js$/,
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: 1,
    reporter: process.env.CI ? "line" : [["list"], ["html", { open: "never" }]],
    timeout: 180000,
    use: {
        ...devices["Desktop Chrome"],
        baseURL,
        trace: "on-first-retry",
        screenshot: "only-on-failure",
        launchOptions: {
            args: [
                `--remote-debugging-port=${LH_DEBUG_PORT}`,
                // Avoid SW caching skewing cold-load audits on repeat runs.
                "--disable-features=ServiceWorker",
            ],
        },
    },
    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
    ],
    webServer: {
        command: "bash scripts/ui/start-ui-stack.sh",
        // HTTP 200 alone is not enough (status may still be starting). Seeds wait for status=ok.
        url: `${baseURL}/api/v1/status`,
        reuseExistingServer: false,
        timeout: 360000,
        stdout: "pipe",
        stderr: "pipe",
    },
});
