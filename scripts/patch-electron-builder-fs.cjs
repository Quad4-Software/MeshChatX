#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const targets = [path.join(root, "node_modules", "app-builder-lib", "out", "binDownload.js")];

const preamble = `const __ebFsConstants = (() => {
  try {
    const c = require("fs").constants;
    if (c && c.R_OK != null) {
      return c;
    }
  } catch (_) {}
  try {
    const c = require("node:fs").constants;
    if (c && c.R_OK != null) {
      return c;
    }
  } catch (_) {}
  return { R_OK: 4, W_OK: 2, X_OK: 1 };
})();

`;

const cacheModeFallback = {
    ReadWrite: 0,
    ReadOnly: 1,
    WriteOnly: 2,
    Bypass: 3,
};

function patchBinDownload(source) {
    let next = source;
    let changed = false;

    if (!next.includes("__ebFsConstants")) {
        next = preamble + next;
        next = next.replace(/fs_1\.constants\.R_OK/g, "__ebFsConstants.R_OK");
        next = next.replace(/fs_1\.constants\.W_OK/g, "__ebFsConstants.W_OK");
        next = next.replace(/fs\.constants\.R_OK/g, "__ebFsConstants.R_OK");
        next = next.replace(/fs\.constants\.W_OK/g, "__ebFsConstants.W_OK");
        changed = true;
    }

    if (!next.includes("__ebElectronDownloadCacheMode")) {
        const injectAfterGetRequire =
            /(const get_1 = require\("@electron\/get"\);)/;
        if (injectAfterGetRequire.test(next)) {
            next = next.replace(
                injectAfterGetRequire,
                `$1
const __ebElectronDownloadCacheMode = get_1.ElectronDownloadCacheMode ?? ${JSON.stringify(cacheModeFallback)};`,
            );
            next = next.replace(
                /get_1\.ElectronDownloadCacheMode\.ReadWrite/g,
                "__ebElectronDownloadCacheMode.ReadWrite",
            );
            next = next.replace(
                /in get_1\.ElectronDownloadCacheMode/g,
                "in __ebElectronDownloadCacheMode",
            );
            changed = true;
        }
    }

    return changed ? next : source;
}

for (const target of targets) {
    if (!fs.existsSync(target)) {
        continue;
    }
    const original = fs.readFileSync(target, "utf8");
    const patched = patchBinDownload(original);
    if (patched !== original) {
        fs.writeFileSync(target, patched);
        console.log(`patched ${path.relative(root, target)}`);
    }
}
