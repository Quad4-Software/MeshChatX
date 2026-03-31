const { defineConfig, devices } = require("@playwright/test");

// Default avoids clashing with a normal dev server on 8000 (e.g. `make run`).
if (process.env.E2E_BACKEND_PORT === undefined || process.env.E2E_BACKEND_PORT === "") {
    process.env.E2E_BACKEND_PORT = "18079";
}

const HOST = process.env.E2E_VITE_HOST || "127.0.0.1";
const PORT = parseInt(process.env.E2E_VITE_PORT || "5173", 10);
const baseURL = `http://${HOST}:${PORT}`;

module.exports = defineConfig({
    testDir: "./tests/e2e",
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: 1,
    reporter: process.env.CI ? "line" : [["list"], ["html", { open: "never" }]],
    use: {
        ...devices["Desktop Chrome"],
        baseURL,
        trace: "on-first-retry",
        screenshot: "only-on-failure",
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
        timeout: 270000,
        stdout: "pipe",
        stderr: "pipe",
    },
});
