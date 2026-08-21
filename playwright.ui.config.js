const { defineConfig, devices } = require("@playwright/test");

if (process.env.E2E_BACKEND_PORT === undefined || process.env.E2E_BACKEND_PORT === "") {
    process.env.E2E_BACKEND_PORT = "18079";
}

const HOST = process.env.E2E_VITE_HOST || "127.0.0.1";
const PORT = parseInt(process.env.E2E_VITE_PORT || "5173", 10);
const LH_DEBUG_PORT = parseInt(process.env.LH_DEBUG_PORT || "9222", 10);
const useProd = process.env.MESHCHAT_UI_PROD === "1";
const baseURL = useProd ? `http://127.0.0.1:${process.env.E2E_BACKEND_PORT}` : `http://${HOST}:${PORT}`;

module.exports = defineConfig({
    testDir: "./tests/ui",
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: 1,
    reporter: process.env.CI ? "line" : [["list"], ["html", { open: "never" }]],
    timeout: 120000,
    use: {
        ...devices["Desktop Chrome"],
        baseURL,
        trace: "on-first-retry",
        screenshot: "only-on-failure",
        launchOptions: {
            args: [`--remote-debugging-port=${LH_DEBUG_PORT}`],
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
        url: useProd ? `http://127.0.0.1:${process.env.E2E_BACKEND_PORT}/api/v1/status` : `${baseURL}/`,
        reuseExistingServer: !process.env.CI,
        timeout: 360000,
        stdout: "pipe",
        stderr: "pipe",
    },
});
