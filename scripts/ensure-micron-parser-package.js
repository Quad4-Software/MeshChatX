#!/usr/bin/env node
// SPDX-License-Identifier: 0BSD
// Git-hosted micron-parser ships without package.json. Normalize metadata so
// electron-builder and Node resolution can find js/micron-parser.js.

const fs = require("fs");
const path = require("path");

const packageDir = path.join(__dirname, "..", "node_modules", "micron-parser");
const packageJsonPath = path.join(packageDir, "package.json");
const entryPath = path.join(packageDir, "js", "micron-parser.js");

if (!fs.existsSync(packageDir) || !fs.existsSync(entryPath)) {
    console.error("micron-parser is missing under node_modules. Run pnpm install, then retry.");
    process.exit(1);
}

const packageJson = {
    name: "micron-parser",
    version: "0.0.0",
    main: "js/micron-parser.js",
    module: "js/micron-parser.js",
};

if (!fs.existsSync(packageJsonPath)) {
    fs.writeFileSync(packageJsonPath, `${JSON.stringify(packageJson, null, 2)}\n`, "utf8");
    console.log("Created node_modules/micron-parser/package.json for module resolution.");
}
