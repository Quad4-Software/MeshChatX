"use strict";

const fs = require("fs");
const path = require("path");

/**
 * Packaged Electron builds only ship electron/ in asar, so app.getVersion() can
 * read 0.0.0. Prefer app-version.json (synced from package.json) then dev package.json.
 */
function readPackagedAppVersion(fallback = "0.0.0") {
    const candidates = [path.join(__dirname, "app-version.json"), path.join(__dirname, "..", "package.json")];
    for (const candidate of candidates) {
        try {
            const raw = JSON.parse(fs.readFileSync(candidate, "utf8"));
            const version = raw && raw.version;
            if (version) {
                return String(version);
            }
        } catch {
            // try next candidate
        }
    }
    return fallback;
}

module.exports = { readPackagedAppVersion };
