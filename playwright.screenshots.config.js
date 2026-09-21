const { defineConfig, devices } = require("@playwright/test");

if (process.env.E2E_BACKEND_PORT === undefined || process.env.E2E_BACKEND_PORT === "") {
    process.env.E2E_BACKEND_PORT = "18079";
}

const HOST = process.env.E2E_VITE_HOST || "127.0.0.1";
const PORT = parseInt(process.env.E2E_VITE_PORT || "5173", 10);
const useProd = process.env.MESHCHAT_UI_PROD === "1";
const baseURL = useProd ? `http://127.0.0.1:${process.env.E2E_BACKEND_PORT}` : `http://${HOST}:${PORT}`;

module.exports = defineConfig({
    testDir: "./tests/ui",
    testMatch: /screenshots\.spec\.js$/,
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: 0,
    workers: 1,
    reporter: [["list"]],
    timeout: 300000,
    use: {
        ...devices["Desktop Chrome"],
        baseURL,
        screenshot: "off",
        trace: "off",
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
