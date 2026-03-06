/**
 * Sync app version from package.json to meshchatx/src/version.py.
 * Single source of truth: edit "version" in package.json, then run:
 *   pnpm run version:sync
 * The build script runs this automatically so Python and Electron share the same version.
 */

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const pkgPath = path.join(root, "package.json");
const versionPyPath = path.join(root, "meshchatx", "src", "version.py");

const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
const version = pkg.version;
if (!version || typeof version !== "string") {
  console.error("package.json has no valid 'version' field");
  process.exit(1);
}

const content = `"""Version string synced from package.json. Do not edit by hand.
Run: pnpm run version:sync
"""

__version__ = "${version}"
`;

fs.writeFileSync(versionPyPath, content, "utf8");
console.log(`Synced version ${version} to meshchatx/src/version.py`);
