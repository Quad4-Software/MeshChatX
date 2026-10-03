// Copy each bundled @fontsource package's LICENSE text into
// meshchatx/src/frontend/public/vendor/font-licenses/ so the shipped app
// carries the OFL license text next to the font binaries it embeds.
// Runs as part of prebuild-frontend. The public/ tree ships verbatim.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = path.join(root, "node_modules", "@fontsource");
const destDir = path.join(root, "meshchatx", "src", "frontend", "public", "vendor", "font-licenses");

const copied = [];
if (fs.existsSync(sourceRoot)) {
    fs.mkdirSync(destDir, { recursive: true });
    for (const entry of fs.readdirSync(sourceRoot, { withFileTypes: true })) {
        if (!entry.isDirectory() && !entry.isSymbolicLink()) {
            continue;
        }
        const licensePath = path.join(sourceRoot, entry.name, "LICENSE");
        if (!fs.existsSync(licensePath)) {
            continue;
        }
        fs.copyFileSync(licensePath, path.join(destDir, `${entry.name}.LICENSE.txt`));
        copied.push(entry.name);
    }
}

console.log(`font-licenses: copied ${copied.length} license file(s)`);
