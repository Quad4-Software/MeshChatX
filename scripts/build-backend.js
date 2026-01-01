#!/usr/bin/env node

const { execSync } = require("child_process");
try {
    execSync(`poetry run python cx_setup.py build`, { stdio: "inherit" });
} catch (error) {
    console.error("Build failed:", error.message);
    process.exit(1);
}
