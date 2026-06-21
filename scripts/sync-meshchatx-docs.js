/**
 * Copy docs/*.md into meshchatx/src/frontend/public/meshchatx-docs/ for in-app serving.
 * Source of truth: docs/ at repo root.
 */

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const srcDir = path.join(root, "docs");
const destDir = path.join(root, "meshchatx", "src", "frontend", "public", "meshchatx-docs");

if (!fs.existsSync(srcDir)) {
    console.error(`Missing docs directory: ${srcDir}`);
    process.exit(1);
}

fs.mkdirSync(destDir, { recursive: true });

const sourceFiles = fs
    .readdirSync(srcDir)
    .filter((name) => name.endsWith(".md"))
    .sort();

for (const file of sourceFiles) {
    const src = path.join(srcDir, file);
    const dest = path.join(destDir, file);
    const content = fs.readFileSync(src);
    const prev = fs.existsSync(dest) ? fs.readFileSync(dest) : null;
    if (!prev || !prev.equals(content)) {
        fs.writeFileSync(dest, content);
        console.log(`Synced meshchatx-docs/${file}`);
    }
}

for (const file of fs.readdirSync(destDir)) {
    if (!file.endsWith(".md")) {
        continue;
    }
    if (!sourceFiles.includes(file)) {
        fs.unlinkSync(path.join(destDir, file));
        console.log(`Removed stale meshchatx-docs/${file}`);
    }
}
