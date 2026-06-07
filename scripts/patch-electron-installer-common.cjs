#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const nodeModules = path.join(root, "node_modules");

const needle = "const glob = promisify(require('glob'))";
const globShim = `const __ebGlobModule = require('glob')
const glob = typeof __ebGlobModule === 'function'
  ? promisify(__ebGlobModule)
  : __ebGlobModule.glob.bind(__ebGlobModule)`;

function patchGlobPromisify(source) {
    if (!source.includes(needle) || source.includes("__ebGlobModule")) {
        return source;
    }
    return source.replace(needle, globShim);
}

function walkJsFiles(dir, out = []) {
    if (!fs.existsSync(dir)) {
        return out;
    }
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            if (entry.name === ".git") {
                continue;
            }
            walkJsFiles(full, out);
            continue;
        }
        if (entry.isFile() && entry.name.endsWith(".js")) {
            out.push(full);
        }
    }
    return out;
}

const targetRoots = [
    path.join(nodeModules, "electron-installer-common"),
    path.join(nodeModules, "@electron", "asar"),
    path.join(nodeModules, "asar"),
];

let patched = 0;
for (const targetRoot of targetRoots) {
    for (const file of walkJsFiles(targetRoot)) {
        const original = fs.readFileSync(file, "utf8");
        if (!original.includes(needle)) {
            continue;
        }
        const next = patchGlobPromisify(original);
        if (next === original) {
            continue;
        }
        fs.writeFileSync(file, next);
        patched += 1;
        console.log(`patched ${path.relative(root, file)}`);
    }
}

if (patched === 0) {
    console.log("electron-installer glob shim already applied or not needed");
}
