#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const packageDir = path.join(__dirname, "..", "node_modules", "micron-parser");
const packageJsonPath = path.join(packageDir, "package.json");

if (!fs.existsSync(packageDir)) {
    console.log("micron-parser not installed, skipping package metadata normalization.");
    process.exit(0);
}

if (fs.existsSync(packageJsonPath)) {
    process.exit(0);
}

const packageJson = {
    name: "micron-parser",
    version: "0.0.0",
    main: "js/micron-parser.js",
    module: "js/micron-parser.js",
};

fs.writeFileSync(packageJsonPath, `${JSON.stringify(packageJson, null, 2)}\n`, "utf8");
console.log("Created node_modules/micron-parser/package.json for electron-builder dependency scan.");
