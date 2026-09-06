// SPDX-License-Identifier: 0BSD
const { defineConfig } = require("@playwright/test");
const path = require("node:path");

module.exports = defineConfig({
    testDir: "./tests/e2e-electron",
    testMatch: "**/*.spec.js",
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 1 : 0,
    workers: 1,
    timeout: 120000,
    reporter: process.env.CI ? "line" : [["list"], ["html", { open: "never" }]],
    use: {
        trace: "on-first-retry",
    },
    projects: [
        {
            name: "electron-shell",
            testMatch: "**/*.spec.js",
        },
    ],
    metadata: {
        harnessMain: path.join(__dirname, "tests/e2e-electron/harness/main.cjs"),
    },
});
